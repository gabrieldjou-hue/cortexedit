"""
export_agent.py
--------------
Agente de Exportacao (Artigo 5).
Responsavel por renderizacao master, compressao, conversao multi-formato
e organizacao dos arquivos finais.
"""

import os
import logging
from typing import Dict, Any

from modules.ffmpeg_utils import EXPORT_PRESETS
from agents.base_agent import BaseAgent, AgentResult
from modules.render_module import RenderModule
from modules.export_module import ExportModule

logger = logging.getLogger(__name__)


class ExportAgent(BaseAgent):
    def __init__(self):
        super().__init__("export")
        self._render = RenderModule()
        self._export = ExportModule()

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = []
        suggestions = []

        edl = task.get("edl", {})
        audio_mix = task.get("audio_mix", {})
        color_data = task.get("color_data", {})
        subtitles = task.get("subtitles", {})
        graphics = task.get("graphics", {})
        export_formats = task.get("export_formats", [])
        output_dir = task.get("output_dir", "")
        ffmpeg_ok = task.get("ffmpeg_ok", False)
        job_id = task.get("job_id", "unknown")

        n_clips = len(edl.get("clips", []))
        output_files = []
        master_path = None

        if ffmpeg_ok and n_clips > 0:
            logs.append("Renderizando master.mp4 com FFmpeg...")
            master_path = self._render.compose_and_render(
                edl, audio_mix, color_data, subtitles, graphics,
                output_dir=output_dir,
                log_fn=lambda msg: logs.append(msg),
            )

            if os.path.exists(master_path):
                size_mb = round(os.path.getsize(master_path) / (1024 * 1024), 2)
                logs.append(f"Master renderizado: {master_path} ({size_mb} MB)")
                output_files.append({
                    "label": "Master (Alta Qualidade)",
                    "filename": "master.mp4",
                    "format": "master",
                    "size_mb": size_mb,
                    "job_id": job_id,
                })

                srt_path = subtitles.get("srt_path") if subtitles else None
                logs.append(f"Exportando para {len(export_formats)} formato(s)...")
                export_results = self._export.transcode_outputs(
                    master_path,
                    export_formats,
                    output_dir=output_dir,
                    subtitle_path=srt_path,
                    log_fn=lambda msg: logs.append(msg),
                )

                for r in export_results:
                    if r.get("success"):
                        output_files.append({
                            "label": r["format"],
                            "filename": r["filename"],
                            "format": r["format"],
                            "size_mb": r["size_mb"],
                            "job_id": job_id,
                        })

                if srt_path and os.path.exists(srt_path):
                    output_files.append({
                        "label": "Legendas (SRT)",
                        "filename": "subtitles.srt",
                        "format": "subtitle",
                        "size_mb": round(os.path.getsize(srt_path) / 1024, 3),
                        "job_id": job_id,
                    })
            else:
                logs.append("Master nao encontrado apos renderizacao.")
                limitations.append("Renderizacao FFmpeg falhou.")
        else:
            logs.append("Modo simulacao: gerando arquivos de demonstracao...")
            for fmt in export_formats:
                dummy_name = f"DEMO_{fmt.replace(' ', '_').replace(':', 'x')}.mp4"
                dummy_path = os.path.join(output_dir, dummy_name)
                with open(dummy_path, "w") as f:
                    f.write(f"[DEMO] Formato: {fmt} | Job: {job_id}")
                output_files.append({
                    "label": fmt,
                    "filename": dummy_name,
                    "format": fmt,
                    "size_mb": 0.001,
                    "job_id": job_id,
                })
            if not ffmpeg_ok and n_clips > 0:
                limitations.append("FFmpeg nao disponivel: modo simulacao ativado.")

        export_data = {
            "master_path": master_path,
            "output_files": output_files,
            "export_count": len(output_files),
        }

        return self._make_result(
            success=True,
            data=export_data,
            files=[f["filename"] for f in output_files],
            extra_logs=logs,
            confidence=0.85 if ffmpeg_ok else 0.5,
            limitations=limitations,
            suggestions=suggestions,
        )
