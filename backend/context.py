"""
context.py
----------
Memoria compartilhada central do SIPA.
Gerenciada exclusivamente pelo Master Orchestrator Agent (MOA).
Todos os 22 agentes compartilham este contexto.
"""

import time
import threading
from typing import Dict, Any


class SharedContext:
    """
    Contexto compartilhado thread-safe.
    Agentes especializados apenas LEEM; apenas o Master ESCREVE.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._fresh()

    def _fresh(self) -> Dict[str, Any]:
        return {
            "job_id": None,
            "profile": None,
            "export_formats": None,
            "project_assets": None,
            "project_organization": None,
            "cv_data": None,
            "transcripts": None,
            "semantic": None,
            "quality_detection": None,
            "curation": None,
            "narrative": None,
            "script": None,
            "edl": None,
            "audio_mix": None,
            "color_data": None,
            "subtitles": None,
            "visual_identity": None,
            "graphics": None,
            "music": None,
            "master_path": None,
            "exports": None,
            "qc_report": None,
            "logs_audit": None,
            "memory": None,
            "learning": None,
            "logs": [],
            "errors": [],
            "state": "idle",
            "stage_index": -1,
            "stage_percent": 0,
        }

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any):
        with self._lock:
            self._data[key] = value

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def log(self, message: str, level: str = "info"):
        with self._lock:
            self._data["logs"].append({
                "timestamp": time.time(),
                "message": message,
                "level": level,
            })

    def add_error(self, agent: str, error: str):
        with self._lock:
            self._data["errors"].append({
                "agent": agent,
                "error": error,
                "timestamp": time.time(),
            })

    def clear(self):
        with self._lock:
            fresh = self._fresh()
            fresh["logs"] = []
            fresh["errors"] = []
            self._data = fresh
