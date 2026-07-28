"""
app.py
------
CortexEdit FastAPI Application.
Endpoints:
  GET  /                          → Serve index.html
  POST /api/upload_files          → Upload de arquivos de vídeo (multipart)
  POST /api/start_job             → Inicia o pipeline de produção
  GET  /api/status                → Estado atual do pipeline (polling)
  GET  /api/download/{job_id}/{filename} → Download de arquivo exportado
  POST /api/transcribe            → Transcrição direta de vídeo (upload + SRT)
  DELETE /api/cancel              → Cancela o job atual (best-effort)
  GET  /api/jobs                  → Histórico de jobs
  GET  /api/jobs/{job_id}         → Detalhes de um job
  GET  /api/jobs/{job_id}/logs    → Logs de um job
  GET  /api/jobs/{job_id}/agents  → Resultados dos agentes
"""

import os
import sys
import uuid
import threading
import shutil
import logging
import subprocess
from pathlib import Path

# Garante que o diretório backend/ está no sys.path para imports internos
_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from pipeline_orchestrator import PipelineOrchestrator
from modules.whisper_module import WhisperModule
from modules.subtitle_module import SubtitleModule
from database import init_db, SessionLocal
import crud

logger = logging.getLogger(__name__)

app = FastAPI(title="CortexEdit API", version="2.0")

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / ".." / "frontend"
UPLOADS_DIR = BASE_DIR / ".." / "uploads"
EXPORTS_DIR = BASE_DIR / ".." / "exports"

UPLOADS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# ── Inicializar banco de dados ────────────────────────────────────────────
init_db()

# ── Servir frontend estático ──────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/style.css")
def serve_css():
    return FileResponse(str(FRONTEND_DIR / "style.css"), media_type="text/css")

@app.get("/app.js")
def serve_js():
    return FileResponse(str(FRONTEND_DIR / "app.js"), media_type="text/javascript")

# ── Instância global do orquestrador ─────────────────────────────────────
orchestrator = PipelineOrchestrator()


# ── Modelos Pydantic ──────────────────────────────────────────────────────
class JobRequest(BaseModel):
    upload_session_id: Optional[str] = None   # ID retornado pelo upload
    watch_folder: Optional[str] = None         # Alternativa: pasta local
    profile: dict


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.post("/api/upload_files")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Recebe múltiplos arquivos de vídeo via multipart/form-data.
    Salva em uploads/{session_id}/ e retorna o session_id + lista de arquivos.
    Registra a sessão no banco de dados.
    """
    session_id = str(uuid.uuid4())[:8]
    session_dir = UPLOADS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    errors = []

    for upload in files:
        try:
            dest = session_dir / upload.filename
            contents = await upload.read()
            with open(dest, "wb") as f:
                f.write(contents)
            size_mb = round(len(contents) / (1024 * 1024), 2)
            saved_files.append({
                "filename": upload.filename,
                "path": str(dest),
                "size_mb": size_mb,
                "content_type": upload.content_type,
            })
        except Exception as e:
            errors.append({"filename": upload.filename, "error": str(e)})

    db = SessionLocal()
    try:
        crud.create_upload_session(db, session_id, saved_files)
    except Exception as e:
        logger.warning(f"Falha ao registrar sessão de upload no banco: {e}")
    finally:
        db.close()

    return {
        "session_id": session_id,
        "files": saved_files,
        "errors": errors,
        "message": f"{len(saved_files)} arquivo(s) carregado(s) com sucesso.",
    }


@app.post("/api/start_job")
def start_job(request: JobRequest):
    """Inicia o pipeline de produção para um session_id ou watch_folder."""
    if orchestrator.is_running:
        return JSONResponse(
            status_code=400,
            content={"error": "Um job já está em execução. Aguarde ou cancele."}
        )

    uploaded_files = []

    if request.upload_session_id:
        session_dir = UPLOADS_DIR / request.upload_session_id
        if session_dir.exists():
            uploaded_files = [str(p) for p in session_dir.iterdir() if p.is_file()]
        else:
            return JSONResponse(
                status_code=404,
                content={"error": f"Session '{request.upload_session_id}' não encontrada."}
            )

    # Lança pipeline em thread para não bloquear a API
    thread = threading.Thread(
        target=orchestrator.run_pipeline_async,
        args=(uploaded_files, request.profile, request.watch_folder),
        daemon=True,
    )
    thread.start()

    return {
        "status": "started",
        "message": "Pipeline iniciado com sucesso.",
        "ffmpeg_available": orchestrator.ffmpeg_ok,
    }


@app.get("/api/status")
def get_status():
    """Retorna o estado completo do pipeline atual."""
    return orchestrator.get_state()


@app.get("/api/download/{job_id}/{filename}")
def download_file(job_id: str, filename: str):
    """
    Serve um arquivo exportado para download.
    Segurança: valida que o filename não contém traversal de diretório.
    """
    safe_name = Path(filename).name  # Remove qualquer path traversal
    file_path = EXPORTS_DIR / job_id / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo '{filename}' não encontrado.")

    # Define media type adequado
    ext = file_path.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".mp3": "audio/mpeg",
        ".srt": "text/plain",
        ".mov": "video/quicktime",
        ".mkv": "video/x-matroska",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=safe_name,
    )


@app.delete("/api/cancel")
def cancel_job():
    """Sinaliza cancelamento do job atual (best-effort)."""
    if not orchestrator.is_running:
        return {"status": "idle", "message": "Nenhum job em execução."}
    # Força o estado para parado (a thread terminará naturalmente)
    orchestrator.is_running = False
    orchestrator._log("Job cancelado pelo usuário.", "warning")
    return {"status": "cancelling", "message": "Cancelamento solicitado."}


# ── Histórico de Jobs ────────────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """Retorna a lista de jobs processados, do mais recente ao mais antigo."""
    db = SessionLocal()
    try:
        jobs = crud.list_jobs(db, limit=limit, offset=offset)
        total = crud.count_jobs(db)
        return {
            "jobs": [j.to_dict() for j in jobs],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        db.close()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    """Retorna os detalhes completos de um job específico."""
    db = SessionLocal()
    try:
        job = crud.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' não encontrado.")
        return job.to_dict()
    finally:
        db.close()


@app.get("/api/jobs/{job_id}/logs")
def get_job_logs(job_id: str, limit: int = Query(500, ge=1, le=2000)):
    """Retorna os logs de um job específico."""
    db = SessionLocal()
    try:
        job = crud.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' não encontrado.")
        logs = crud.get_logs(db, job_id, limit=limit)
        return {
            "job_id": job_id,
            "logs": [l.to_dict() for l in logs],
            "total": len(logs),
        }
    finally:
        db.close()


@app.get("/api/jobs/{job_id}/agents")
def get_job_agents(job_id: str):
    """Retorna os resultados dos agentes de um job específico."""
    db = SessionLocal()
    try:
        job = crud.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' não encontrado.")
        results = crud.get_agent_results(db, job_id)
        return {
            "job_id": job_id,
            "agents": [r.to_dict() for r in results],
            "total": len(results),
        }
    finally:
        db.close()


# ── Transcrição Direta (Assíncrona com Progresso) ───────────────────────────

_transcribe_jobs: dict = {}


@app.post("/api/transcribe")
async def transcribe_video(file: UploadFile = File(...)):
    """
    Inicia transcrição assíncrona de um vídeo.
    Retorna job_id imediatamente — o frontend deve pollar /api/transcribe/progress/{job_id}.
    """
    job_id = str(uuid.uuid4())[:8]
    job_dir = EXPORTS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    dest = job_dir / file.filename
    contents = await file.read()
    with open(dest, "wb") as f:
        f.write(contents)

    _transcribe_jobs[job_id] = {
        "percent": 0,
        "stage": "init",
        "message": "Iniciando transcrição...",
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_transcription,
        args=(job_id, str(dest), file.filename),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


@app.get("/api/transcribe/progress/{job_id}")
async def transcribe_progress(job_id: str):
    """Retorna o estado atual da transcrição."""
    job = _transcribe_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job de transcrição não encontrado.")
    return job


def _run_transcription(job_id: str, video_path: str, filename: str):
    """Executa a transcrição em background, atualizando progresso."""
    job = _transcribe_jobs[job_id]
    try:
        job.update({"percent": 5, "stage": "init", "message": "Preparando transcrição..."})

        whisper = WhisperModule(model_size="tiny", language="pt")

        def on_progress(pct, stage):
            stage_messages = {
                "audio_extract": "Extraindo áudio do vídeo...",
                "transcribing": f"Transcrevendo áudio... {pct}%",
                "transcribing_done": "Transcrição concluída!",
                "done": "Concluído!",
                "error": "Erro na transcrição.",
            }
            job["percent"] = max(min(pct, 99), job.get("percent", 0))
            job["stage"] = stage
            job["message"] = stage_messages.get(stage, f"Processando... {pct}%")

        job.update({"percent": 10, "stage": "audio_extract", "message": "Extraindo áudio do vídeo..."})
        transcript = whisper.transcribe_video(video_path, progress_callback=on_progress)

        job.update({"percent": 90, "stage": "srt", "message": "Gerando legendas SRT..."})
        edl = {"job_id": job_id, "total_duration": transcript.get("duration", 10.0)}
        sub_module = SubtitleModule()
        srt_result = sub_module.generate_subs(
            transcripts=[transcript],
            edl=edl,
            profile={},
            output_dir=str(EXPORTS_DIR / job_id),
        )

        srt_content = ""
        srt_path = srt_result.get("srt_path", "")
        if srt_path and os.path.exists(srt_path):
            with open(srt_path, "r", encoding="utf-8") as f:
                srt_content = f.read()

        job.update({
            "percent": 100,
            "stage": "done",
            "message": "Concluído!",
            "result": {
                "job_id": job_id,
                "video_filename": filename,
                "srt_content": srt_content,
                "segments": transcript.get("segments", []),
                "words": transcript.get("words", []),
                "duration": transcript.get("duration", 0.0),
                "language": transcript.get("language", "pt-BR"),
                "video_url": f"/api/download/{job_id}/{filename}",
                "srt_url": f"/api/download/{job_id}/subtitles.srt",
            },
        })

    except Exception as e:
        logger.error(f"Erro na transcrição {job_id}: {e}")
        job.update({
            "percent": 100,
            "stage": "error",
            "message": f"Erro: {str(e)}",
            "error": str(e),
        })


# ── Burn-in de Legendas no Vídeo ───────────────────────────────────────────

_burn_jobs: dict = {}


@app.post("/api/burn-subtitles")
async def burn_subtitles(job_id: str = Form(...), srt_content: str = Form(...)):
    """
    Grava legendas editadas diretamente no vídeo usando FFmpeg.
    Retorna um job_id assíncrono — poll /api/burn-progress/{burn_job_id}.
    """
    burn_id = str(uuid.uuid4())[:8]
    job_dir = EXPORTS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job de transcrição não encontrado.")

    video_candidates = list(job_dir.glob("*.mp4")) + list(job_dir.glob("*.mov")) + list(job_dir.glob("*.mkv"))
    if not video_candidates:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado no job.")

    original_video = video_candidates[0]
    edited_srt = job_dir / "edited.srt"
    with open(edited_srt, "w", encoding="utf-8") as f:
        f.write(srt_content)

    output_name = f"{original_video.stem}_legended.mp4"
    output_path = job_dir / output_name

    _burn_jobs[burn_id] = {
        "percent": 0,
        "stage": "init",
        "message": "Preparando...",
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_burn,
        args=(burn_id, str(original_video), str(edited_srt), str(output_path), job_id, output_name),
        daemon=True,
    )
    thread.start()

    return {"burn_job_id": burn_id}


@app.get("/api/burn-progress/{burn_id}")
async def burn_progress(burn_id: str):
    job = _burn_jobs.get(burn_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job de burn-in não encontrado.")
    return job


def _run_burn(burn_id: str, video_path: str, srt_path: str, output_path: str, job_id: str, output_name: str):
    job = _burn_jobs[burn_id]
    try:
        job.update({"percent": 10, "stage": "encoding", "message": "Gravando legendas no vídeo..."})

        srt_ffmpeg = srt_path.replace("\\", "/").replace(":", "\\:")
        style = (
            "FontName=Arial,FontSize=22"
            ",PrimaryColour=&H00FFFFFF"
            ",OutlineColour=&H00000000"
            ",BackColour=&H80000000"
            ",Outline=2,Shadow=1"
            ",MarginV=30"
        )
        vf = f"subtitles='{srt_ffmpeg}':force_style='{style}'"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", vf,
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path,
        ]

        job.update({"percent": 30, "stage": "encoding", "message": "Codificando vídeo com legendas..."})

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            stderr_tail = result.stderr[-500:] if result.stderr else "Erro desconhecido"
            raise RuntimeError(f"FFmpeg falhou: {stderr_tail}")

        if not os.path.exists(output_path):
            raise RuntimeError("Arquivo de saída não foi criado.")

        job.update({
            "percent": 100,
            "stage": "done",
            "message": "Vídeo com legendas pronto!",
            "result": {
                "video_url": f"/api/download/{job_id}/{output_name}",
                "filename": output_name,
            },
        })

    except Exception as e:
        logger.error(f"Erro no burn-in {burn_id}: {e}")
        job.update({
            "percent": 100,
            "stage": "error",
            "message": f"Erro: {str(e)}",
            "error": str(e),
        })


# ── Recorte de Trechos ─────────────────────────────────────────────────────

@app.post("/api/cut-clip")
async def cut_clip(
    session_id: str = Form(...),
    filename: str = Form(...),
    start: float = Form(...),
    end: float = Form(...),
):
    """Recorta um trecho do vídeo usando FFmpeg stream copy (rápido, sem re-encoding)."""
    src = UPLOADS_DIR / session_id / filename
    if not src.exists():
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")

    if end <= start:
        raise HTTPException(status_code=400, detail="O ponto final deve ser maior que o inicial.")

    clip_name = f"{Path(filename).stem}_{int(start)}-{int(end)}.mp4"
    out_dir = EXPORTS_DIR / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / clip_name

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(src),
        "-to", str(end - start),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-300:] if result.stderr else "FFmpeg error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao recortar: {e}")

    if not out_path.exists():
        raise HTTPException(status_code=500, detail="Arquivo de saída não foi criado.")

    return {
        "clip_url": f"/api/download/{session_id}/{clip_name}",
        "filename": clip_name,
        "start": start,
        "end": end,
        "duration": round(end - start, 2),
    }


# ── Corte em Lote (Batch Cut) ──────────────────────────────────────────────

from pydantic import BaseModel as PydanticBaseModel

class BatchCutRequest(PydanticBaseModel):
    session_id: str
    filename: str
    clips: list  # [{start, end, text?}]

_batch_cut_jobs: dict = {}


@app.post("/api/batch-cut")
async def batch_cut(request: BatchCutRequest):
    """Inicia corte em lote de múltiplos trechos. Retorna job_id para polling."""
    src = UPLOADS_DIR / request.session_id / request.filename
    if not src.exists():
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")

    valid_clips = [c for c in request.clips if c.get("end", 0) > c.get("start", 0)]
    if not valid_clips:
        raise HTTPException(status_code=400, detail="Nenhum trecho válido para recortar.")

    cut_id = str(uuid.uuid4())[:8]
    out_dir = EXPORTS_DIR / request.session_id
    out_dir.mkdir(parents=True, exist_ok=True)

    _batch_cut_jobs[cut_id] = {
        "percent": 0,
        "stage": "processing",
        "message": f"Cortando {len(valid_clips)} trecho(s)...",
        "done": 0,
        "total": len(valid_clips),
        "detail": "",
        "clips": [],
        "error": None,
    }

    thread = threading.Thread(
        target=_run_batch_cut,
        args=(cut_id, str(src), request.session_id, request.filename, valid_clips, str(out_dir)),
        daemon=True,
    )
    thread.start()

    return {"job_id": cut_id}


@app.get("/api/batch-cut/progress/{cut_id}")
async def batch_cut_progress(cut_id: str):
    job = _batch_cut_jobs.get(cut_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job de corte em lote não encontrado.")
    return job


def _run_batch_cut(cut_id: str, src_path: str, session_id: str, filename: str, clips: list, out_dir: str):
    job = _batch_cut_jobs[cut_id]
    stem = Path(filename).stem
    generated = []

    try:
        for i, clip in enumerate(clips):
            start = float(clip["start"])
            end = float(clip["end"])
            text = clip.get("text", "")
            dur = end - start

            clip_name = f"{stem}_clip{i+1:02d}_{int(start)}-{int(end)}.mp4"
            out_path = os.path.join(out_dir, clip_name)

            job["detail"] = f"Clip {i+1}/{len(clips)}: {seconds_to_ts(start)} → {seconds_to_ts(end)}"

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", src_path,
                "-to", str(dur),
                "-c", "copy",
                "-movflags", "+faststart",
                out_path,
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0 and os.path.exists(out_path):
                    size_mb = round(os.path.getsize(out_path) / (1024 * 1024), 2)
                    generated.append({
                        "clip_url": f"/api/download/{session_id}/{clip_name}",
                        "filename": clip_name,
                        "start": start,
                        "end": end,
                        "duration": round(dur, 2),
                        "size_mb": size_mb,
                        "text": text,
                    })
                else:
                    logger.warning(f"FFmpeg falhou no clip {i+1}: {result.stderr[-200:] if result.stderr else ''}")
            except Exception as e:
                logger.warning(f"Erro no clip {i+1}: {e}")

            job["done"] = i + 1
            job["percent"] = round(((i + 1) / len(clips)) * 100)
            job["message"] = f"Cortando... {i + 1}/{len(clips)}"

        job.update({
            "percent": 100,
            "stage": "done",
            "message": f"{len(generated)} clip(s) gerado(s) com sucesso.",
            "clips": generated,
            "detail": "",
        })

    except Exception as e:
        job.update({
            "percent": 100,
            "stage": "error",
            "message": f"Erro: {str(e)}",
            "error": str(e),
        })


def seconds_to_ts(sec: float) -> str:
    sec = max(0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
