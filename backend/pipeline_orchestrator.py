"""
pipeline_orchestrator.py
------------------------
Orquestrador central da plataforma CortexEdit.
Agora delega toda a orquestracao ao Master Orchestrator Agent (MOA),
que coordena os 13 agentes especializados do SIPA.

Compatibilidade retroativa mantida para a API.
Integrado com banco de dados para persistencia de jobs.
"""

import os
import uuid
import threading
import logging
from typing import Dict, Any, List, Optional

from agents.master_orchestrator import MasterOrchestratorAgent
from modules.ffmpeg_utils import check_ffmpeg, EXPORT_PRESETS
from database import SessionLocal
import crud

logger = logging.getLogger(__name__)

STAGE_NAMES = ["Ingestion", "Analysis", "AI Engine", "Editing", "Render & Export"]


class PipelineOrchestrator:
    """
    Fachada para o sistema multi-agente SIPA.
    Mantem a mesma interface publica para compatibilidade com app.py.
    Internamente delega tudo ao Master Orchestrator Agent.
    Persiste estado e resultados no banco de dados.
    """

    def __init__(self):
        self.moa = MasterOrchestratorAgent()
        self.ffmpeg_ok = check_ffmpeg()
        self._reset_state()

    def _reset_state(self):
        self.is_running: bool = False
        self.current_stage: int = -1
        self.current_stage_name: str = ""
        self.stage_percent: int = 0
        self.logs: List[Dict] = []
        self.job_id: Optional[str] = None
        self.output_files: List[Dict] = []
        self.error: Optional[str] = None

    def get_state(self) -> Dict[str, Any]:
        try:
            status = self.moa.get_status()
            ctx = self.moa.context.get_all()
            exports = ctx.get("exports") or {}
            return {
                "is_running": status["is_running"],
                "current_stage": status["current_stage"],
                "current_stage_name": status["current_stage_name"],
                "stage_percent": status["stage_percent"],
                "logs": status["logs"],
                "job_id": ctx.get("job_id"),
                "output_files": exports.get("output_files", []) if exports else self.output_files,
                "error": ctx.get("errors", [None])[-1] if ctx.get("errors") else None,
                "ffmpeg_available": self.ffmpeg_ok,
                "state": ctx.get("state"),
            }
        except Exception:
            return {
                "is_running": self.is_running,
                "current_stage": self.current_stage,
                "current_stage_name": self.current_stage_name,
                "stage_percent": self.stage_percent,
                "logs": self.logs[-100:],
                "job_id": self.job_id,
                "output_files": self.output_files,
                "error": self.error,
                "ffmpeg_available": self.ffmpeg_ok,
            }

    def _log(self, msg: str, level: str = "info"):
        self.logs.append({"timestamp": __import__("time").time(), "message": msg, "level": level})

    def run_pipeline_async(
        self,
        uploaded_files: List[str],
        profile: Dict[str, Any],
        watch_folder: Optional[str] = None,
    ):
        if self.is_running:
            logger.warning("Tentativa de iniciar pipeline com outro em execucao.")
            return

        self._reset_state()
        self.is_running = True

        export_dir = os.path.join(
            os.path.dirname(__file__), '..', 'exports'
        )

        def log_fn(msg: str, level: str = "info"):
            self.logs.append({"timestamp": __import__("time").time(), "message": msg, "level": level})

        def stage_fn(index: int, percent: int):
            self.current_stage = index
            self.current_stage_name = STAGE_NAMES[index] if index < len(STAGE_NAMES) else ""

        def progress_fn(percent: int):
            self.stage_percent = percent

        self.moa.set_callbacks(log_fn=log_fn, stage_fn=stage_fn, progress_fn=progress_fn)

        def run():
            db = SessionLocal()
            try:
                result = self.moa.execute({
                    "uploaded_files": uploaded_files,
                    "watch_folder": watch_folder,
                    "profile": profile,
                    "export_dir": export_dir,
                })

                if result.success and result.data:
                    self.job_id = result.data.get("job_id")
                    self.output_files = result.data.get("output_files", [])

                    crud.complete_job(
                        db,
                        job_id=self.job_id,
                        status="completed",
                        output_files=self.output_files,
                        qc_approved=result.data.get("qc_report", {}).get("approved"),
                        qc_issues=result.data.get("qc_report", {}).get("issues", []),
                        total_duration=result.data.get("total_time"),
                    )

                    ctx = self.moa.context.get_all()
                    if ctx.get("logs"):
                        crud.save_logs(db, self.job_id, ctx["logs"])
                    if ctx.get("errors"):
                        crud.save_errors(db, self.job_id, ctx["errors"])

            except Exception as e:
                if self.job_id:
                    try:
                        crud.complete_job(
                            db,
                            job_id=self.job_id,
                            status="error",
                            error_message=str(e),
                        )
                    except Exception:
                        logger.exception("Falha ao registrar erro no banco")
                logger.exception("Pipeline falhou")
            finally:
                self.is_running = False
                db.close()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
