"""
master_orchestrator.py
----------------------
Master Orchestrator Agent (MOA) — Agente 01 do SIPA.
Autoridade maxima do sistema. Nao executa processamento audiovisual.
Sua funcao e exclusivamente estrategica e de coordenacao dos 22 agentes.

Integrado com banco de dados para persistencia de resultados.
"""

import os
import uuid
import time
import logging
from typing import Dict, Any, List, Optional, Callable

from agents.base_agent import BaseAgent, AgentResult
from agents import (
    IngestionAgent, ProjectOrganizationAgent, ComputerVisionAgent,
    TranscriptionAgent, SemanticAnalysisAgent, QualityDetectionAgent,
    CurationAgent, NarrativeAgent, ScriptingAgent, EditingAgent,
    ColorizationAgent, AudioAgent, MusicAgent, SubtitleAgent,
    VisualIdentityAgent, MotionGraphicsAgent, ExportAgent,
    QualityControlAgent, LogsAuditAgent, MemoryAgent, LearningAgent,
    NarrativeAnalysisAgent,
)
from context import SharedContext
from modules.ffmpeg_utils import check_ffmpeg, EXPORT_PRESETS
from database import SessionLocal
import crud

logger = logging.getLogger(__name__)

STAGE_NAMES = ["Ingestion", "Analysis", "AI Engine", "Editing", "Render & Export"]


class MasterOrchestratorAgent(BaseAgent):
    """
    MOA — Coordena os 22 agentes especializados do SIPA.
    """

    def __init__(self):
        super().__init__("master_orchestrator")
        self.ffmpeg_ok = check_ffmpeg()
        self.context = SharedContext()
        self._agents: Dict[str, BaseAgent] = {}
        self._init_agents()
        self._callbacks: Dict[str, Callable] = {}
        self._agents_executed: List[str] = []
        self._db = None

    def set_callbacks(self, log_fn: Callable, stage_fn: Callable, progress_fn: Callable):
        self._callbacks["log"] = log_fn
        self._callbacks["stage"] = stage_fn
        self._callbacks["progress"] = progress_fn

    def _init_agents(self):
        self._agents = {
            "ingestion": IngestionAgent(),
            "project_organization": ProjectOrganizationAgent(),
            "computer_vision": ComputerVisionAgent(),
            "transcription": TranscriptionAgent(),
            "narrative_analysis": NarrativeAnalysisAgent(),
            "semantic_analysis": SemanticAnalysisAgent(),
            "quality_detection": QualityDetectionAgent(),
            "curation": CurationAgent(),
            "narrative": NarrativeAgent(),
            "scripting": ScriptingAgent(),
            "editing": EditingAgent(),
            "colorization": ColorizationAgent(),
            "audio": AudioAgent(),
            "music": MusicAgent(),
            "subtitle": SubtitleAgent(),
            "visual_identity": VisualIdentityAgent(),
            "motion_graphics": MotionGraphicsAgent(),
            "export": ExportAgent(),
            "quality_control": QualityControlAgent(),
            "logs_audit": LogsAuditAgent(),
            "memory": MemoryAgent(),
            "learning": LearningAgent(),
        }

    # ── Execucao principal ─────────────────────────────────────────────────

    def execute(self, task: Dict[str, Any], context=None) -> AgentResult:
        self._start_timer()
        self._agents_executed = []
        self.context.clear()

        self._db = SessionLocal()

        uploaded_files = task.get("uploaded_files", [])
        watch_folder = task.get("watch_folder")
        profile = task.get("profile", {})
        profile_name = profile.get("name", "default")
        export_formats = profile.get("exports", list(EXPORT_PRESETS.keys()))
        export_dir = task.get("export_dir")

        if not export_dir:
            export_dir = os.path.join(
                os.path.dirname(__file__), '..', '..', 'exports'
            )

        job_id = str(uuid.uuid4())[:8]
        export_dir = os.path.join(export_dir, job_id)
        os.makedirs(export_dir, exist_ok=True)

        self.context.set("job_id", job_id)
        self.context.set("profile", profile)
        self.context.set("export_formats", export_formats)
        self.context.set("export_dir", export_dir)
        self.context.set("ffmpeg_ok", self.ffmpeg_ok)
        self.context.set("state", "running")
        self.context.set("stage_index", -1)

        crud.create_job(
            self._db,
            job_id=job_id,
            profile_name=profile_name,
            profile_data=profile,
            export_formats=export_formats,
            ffmpeg_available=self.ffmpeg_ok,
        )

        self._log(f"{'='*50}")
        self._log(f"MASTER ORCHESTRATOR — JOB {job_id}")
        self._log(f"Perfil: {profile_name} | Formatos: {export_formats}")
        self._log(f"FFmpeg: {'SIM' if self.ffmpeg_ok else 'NAO (modo simulacao)'}")
        self._log(f"{'='*50}")

        try:
            # ═══════════════════════════════════════════════════════════════
            # STAGE 0 — INGESTION (Agentes 02, 03)
            # ═══════════════════════════════════════════════════════════════
            self._stage(0, 5)
            r = self._run_agent("ingestion", {
                "uploaded_files": uploaded_files, "watch_folder": watch_folder,
            })
            self.context.set("project_assets", r.data)
            self._log_agent_result(r)
            self._progress(50)

            r = self._run_agent("project_organization", {
                "project_assets": r.data,
            })
            self.context.set("project_organization", r.data)
            self._log_agent_result(r)
            self._progress(100)

            # ═══════════════════════════════════════════════════════════════
            # STAGE 1 — ANALYSIS (Agentes 04, 05, 06, 07)
            # ═══════════════════════════════════════════════════════════════
            self._stage(1, 5)
            project_assets = self.context.get("project_assets")

            r_cv = self._run_agent("computer_vision", {
                "project_assets": project_assets,
            })
            self.context.set("cv_data", r_cv.data)
            self._log_agent_result(r_cv)
            self._progress(20)

            r_ts = self._run_agent("transcription", {
                "project_assets": project_assets,
            })
            self.context.set("transcripts", r_ts.data)
            self._log_agent_result(r_ts)
            self._progress(40)

            r_analysis = self._run_agent("narrative_analysis", {
                "project_assets": project_assets,
                "cv_data": r_cv.data,
                "transcripts": r_ts.data,
            })
            self.context.set("analysis", r_analysis.data)
            self._log_agent_result(r_analysis)
            self._progress(60)

            r_semantic = self._run_agent("semantic_analysis", {
                "transcripts": r_ts.data,
                "cv_data": r_cv.data,
            })
            self.context.set("semantic", r_semantic.data)
            self._log_agent_result(r_semantic)
            self._progress(80)

            r_quality = self._run_agent("quality_detection", {
                "project_assets": project_assets,
            })
            self.context.set("quality_detection", r_quality.data)
            self._log_agent_result(r_quality)
            self._progress(100)

            # ═══════════════════════════════════════════════════════════════
            # STAGE 2 — AI ENGINE (Agentes 08, 09, 10)
            # ═══════════════════════════════════════════════════════════════
            self._stage(2, 5)
            analysis = self.context.get("analysis")
            semantic = self.context.get("semantic")
            quality = self.context.get("quality_detection")

            r_curation = self._run_agent("curation", {
                "analysis": analysis, "profile": profile,
                "quality_data": quality, "semantic": semantic,
            })
            self.context.set("curation", r_curation.data)
            self._log_agent_result(r_curation)
            self._progress(40)

            r_narrative = self._run_agent("narrative", {
                "curation": r_curation.data, "semantic": semantic,
            })
            self.context.set("narrative", r_narrative.data)
            self._log_agent_result(r_narrative)
            self._progress(70)

            r_script = self._run_agent("scripting", {
                "narrative": r_narrative.data, "semantic": semantic,
            })
            self.context.set("script", r_script.data)
            self._log_agent_result(r_script)
            self._progress(100)

            # ═══════════════════════════════════════════════════════════════
            # STAGE 3 — EDITING (Agentes 11, 12, 13, 14, 15, 16, 17)
            # ═══════════════════════════════════════════════════════════════
            self._stage(3, 5)
            narrative_data = self.context.get("narrative")
            script = self.context.get("script")
            transcripts = self.context.get("transcripts")

            r_edit = self._run_agent("editing", {
                "narrative": narrative_data, "profile": profile, "script": script,
            })
            self.context.set("edl", r_edit.data)
            self._log_agent_result(r_edit)
            self._progress(15)

            r_color = self._run_agent("colorization", {
                "edl": r_edit.data, "profile": profile,
            })
            self.context.set("color_data", r_color.data)
            self._log_agent_result(r_color)
            self._progress(30)

            r_audio = self._run_agent("audio", {
                "edl": r_edit.data, "profile": profile,
            })
            self.context.set("audio_mix", r_audio.data)
            self._log_agent_result(r_audio)
            self._progress(45)

            r_music = self._run_agent("music", {
                "profile": profile, "edl": r_edit.data,
            })
            self.context.set("music", r_music.data)
            self._log_agent_result(r_music)
            self._progress(55)

            r_sub = self._run_agent("subtitle", {
                "transcripts": transcripts, "edl": r_edit.data,
                "profile": profile, "output_dir": export_dir,
            })
            self.context.set("subtitles", r_sub.data)
            self._log_agent_result(r_sub)
            self._progress(70)

            r_brand = self._run_agent("visual_identity", {
                "profile": profile, "narrative": narrative_data,
            })
            self.context.set("visual_identity", r_brand.data)
            self._log_agent_result(r_brand)
            self._progress(85)

            r_mg = self._run_agent("motion_graphics", {
                "narrative": narrative_data, "profile": profile, "script": script,
            })
            self.context.set("graphics", r_mg.data)
            self._log_agent_result(r_mg)
            self._progress(100)

            # ═══════════════════════════════════════════════════════════════
            # STAGE 4 — RENDER, EXPORT, QC, AUDIT, MEMORY, LEARNING
            # ═══════════════════════════════════════════════════════════════
            self._stage(4, 5)
            edl = self.context.get("edl")
            audio_mix = self.context.get("audio_mix")
            color_data = self.context.get("color_data")
            subtitles = self.context.get("subtitles")
            graphics = self.context.get("graphics")

            r_export = self._run_agent("export", {
                "edl": edl, "audio_mix": audio_mix, "color_data": color_data,
                "subtitles": subtitles, "graphics": graphics,
                "export_formats": export_formats, "output_dir": export_dir,
                "ffmpeg_ok": self.ffmpeg_ok, "job_id": job_id,
            })
            self.context.set("exports", r_export.data)
            self._log_agent_result(r_export)
            self._progress(40)

            r_qc = self._run_agent("quality_control", {
                "exports": r_export.data, "edl": edl,
                "profile": profile, "export_formats": export_formats,
            })
            self.context.set("qc_report", r_qc.data)
            self._log_agent_result(r_qc)
            self._progress(60)

            qc_data = r_qc.data or {}
            if qc_data.get("approved"):
                self._log("QUALITY CONTROL: Todos os itens aprovados.")
            else:
                issues = qc_data.get("issues", [])
                self._log(f"QUALITY CONTROL: {len(issues)} issue(s) — revisar.", "warning")
                for iss in issues[:5]:
                    self._log(f"  QC: {iss}", "warning")

            total_time = self._elapsed()
            r_audit = self._run_agent("logs_audit", {
                "job_id": job_id, "export_dir": export_dir,
                "agents_executed": self._agents_executed,
                "total_execution_time": total_time,
            })
            self.context.set("logs_audit", r_audit.data)
            self._log_agent_result(r_audit)
            self._progress(80)

            self._run_agent("memory", {
                "action": "save", "key": f"profile_{profile_name}",
                "value": profile,
            })
            self._progress(90)

            r_learning = self._run_agent("learning", {
                "qc_report": qc_data, "profile": profile,
            })
            self.context.set("learning", r_learning.data)
            self._log_agent_result(r_learning)
            self._progress(100)

            output_files = r_export.data.get("output_files", []) if r_export.data else []
            self.context.set("state", "completed")

            self._log(f"{'='*50}")
            self._log(f"JOB {job_id} FINALIZADO — {total_time:.1f}s")
            self._log(f"Agentes executados: {len(self._agents_executed)}")
            self._log(f"Arquivos gerados: {len(output_files)}")
            self._log(f"{'='*50}")

            return self._make_result(
                success=True,
                data={
                    "job_id": job_id,
                    "output_files": output_files,
                    "qc_report": qc_data,
                    "agents_executed": self._agents_executed,
                    "total_time": total_time,
                },
                confidence=0.95,
            )

        except Exception as e:
            self.context.set("state", "error")
            self.context.add_error(self.agent_id, str(e))
            self._log(f"PIPELINE FALHOU: {e}", "error")
            logger.exception("MOA exception:")
            return self._make_result(
                success=False, error=str(e), confidence=0.0,
            )
        finally:
            if self._db:
                self._db.close()
                self._db = None

    # ── API de status ──────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        ctx = self.context.get_all()
        si = ctx.get("stage_index", -1)
        return {
            "is_running": ctx.get("state") == "running",
            "current_stage": si,
            "current_stage_name": STAGE_NAMES[si] if 0 <= si < len(STAGE_NAMES) else "",
            "stage_percent": ctx.get("stage_percent", 0),
            "logs": ctx.get("logs", [])[-150:],
            "job_id": ctx.get("job_id"),
            "output_files": [],
            "error": None,
            "ffmpeg_available": self.ffmpeg_ok,
            "state": ctx.get("state"),
        }

    # ── Internos ───────────────────────────────────────────────────────────

    def _run_agent(self, name: str, task_data: Dict[str, Any]) -> AgentResult:
        agent = self._agents.get(name)
        if not agent:
            raise RuntimeError(f"Agente '{name}' nao registrado.")
        self._agents_executed.append(name)
        self._log(f"[{name}] Executando...")
        result = agent.execute(task_data, self.context)

        if self._db and self.context.get("job_id"):
            try:
                crud.save_agent_result(
                    self._db,
                    job_id=self.context.get("job_id"),
                    agent_name=name,
                    success=result.success,
                    data=result.data,
                    execution_time=result.execution_time,
                    confidence=result.confidence,
                    limitations=result.limitations,
                    suggestions=result.suggestions,
                    error=result.error,
                )
            except Exception as e:
                logger.warning(f"Falha ao salvar resultado do agente '{name}' no banco: {e}")

        if not result.success:
            self.context.add_error(name, result.error or "erro desconhecido")
            raise RuntimeError(f"Agente '{name}' falhou: {result.error}")
        return result

    def _log(self, msg: str, level: str = "info"):
        self.context.log(msg, level)
        if "log" in self._callbacks:
            self._callbacks["log"](msg, level)

    def _stage(self, index: int, percent: int = 0):
        self.context.set("stage_index", index)
        self.context.set("stage_percent", percent)
        self._log(f"[Stage {index+1}/{len(STAGE_NAMES)}] {STAGE_NAMES[index]}")
        if "stage" in self._callbacks:
            self._callbacks["stage"](index, percent)

    def _progress(self, percent: int):
        self.context.set("stage_percent", percent)
        if "progress" in self._callbacks:
            self._callbacks["progress"](percent)

    def _log_agent_result(self, result: AgentResult):
        self._log(f"  OK: {result.agent_id} | confianca={result.confidence} | {result.execution_time}s")
        for log_msg in result.logs[:3]:
            self._log(f"    {log_msg}")
