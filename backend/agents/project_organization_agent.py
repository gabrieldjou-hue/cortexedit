"""
project_organization_agent.py
-----------------------------
Agente 03 — Organizacao de Projeto.
Estrutura automaticamente o projeto: agrupa cameras, gravacoes,
entrevistas, cenas; detecta datas e identifica dispositivos.
"""

import os
import logging
from typing import Dict, Any, List
from datetime import datetime

from agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class ProjectOrganizationAgent(BaseAgent):
    def __init__(self):
        super().__init__("project_organization")

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Organizacao baseada em metadados do arquivo e nomeclatura simples.",
            "Sem integracao com deteccao real de cameras/dispositivos.",
        ]

        project_assets = task.get("project_assets", {})
        video_files = project_assets.get("video_files", [])
        files_metadata = project_assets.get("files_metadata", [])

        groups = {
            "cameras": {},
            "dates": {},
            "scenes": [],
            "interviews": [],
        }

        for meta in files_metadata:
            path = meta.get("path", "")
            filename = os.path.basename(path)
            mod_time = os.path.getmtime(path) if os.path.exists(path) else 0
            date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d") if mod_time else "unknown"

            device = self._guess_device(filename, meta)
            if device not in groups["cameras"]:
                groups["cameras"][device] = []
            groups["cameras"][device].append(path)

            if date_str not in groups["dates"]:
                groups["dates"][date_str] = []
            groups["dates"][date_str].append(path)

            groups["scenes"].append({
                "file": path,
                "suggested_scene": self._guess_scene(filename),
                "date": date_str,
                "device": device,
            })

        project_name = self._generate_project_name(groups, video_files)
        logs.append(f"Projeto organizado: '{project_name}'")
        logs.append(f"Dispositivos detectados: {list(groups['cameras'].keys())}")
        logs.append(f"Dias de gravacao: {list(groups['dates'].keys())}")
        logs.append(f"Cenas sugeridas: {len(groups['scenes'])}")

        return self._make_result(
            success=True,
            data={
                "project_name": project_name,
                "groups": groups,
                "organization": {
                    "cameras": {k: len(v) for k, v in groups["cameras"].items()},
                    "dates": {k: len(v) for k, v in groups["dates"].items()},
                    "total_scenes": len(groups["scenes"]),
                },
            },
            extra_logs=logs,
            confidence=0.8,
            limitations=limitations,
            suggestions=[
                "Integrar leitura de metadados EXIF/MXF para identificar cameras reais.",
                "Implementar clustering de cenas por similaridade visual.",
            ],
        )

    def _guess_device(self, filename: str, meta: Dict) -> str:
        name_lower = filename.lower()
        if "gopro" in name_lower or "hero" in name_lower:
            return "GoPro"
        if "sony" in name_lower or "a7" in name_lower or "fs" in name_lower:
            return "Sony"
        if "canon" in name_lower or "c" in name_lower or "5d" in name_lower:
            return "Canon"
        if "nikon" in name_lower or "d" in name_lower:
            return "Nikon"
        if "iphone" in name_lower or "ios" in name_lower or "mobile" in name_lower:
            return "iPhone"
        if "screen" in name_lower or "recording" in name_lower or "zoom" in name_lower:
            return "ScreenCapture"
        width = meta.get("width", 0)
        height = meta.get("height", 0)
        if width >= 3840:
            return "Camera_4K"
        if width >= 1920:
            return "Camera_HD"
        return "Camera_SD"

    def _guess_scene(self, filename: str) -> str:
        name_lower = filename.lower()
        if "intro" in name_lower:
            return "Abertura"
        if "outro" in name_lower or "end" in name_lower:
            return "Encerramento"
        if "interview" in name_lower or "entrevista" in name_lower:
            return "Entrevista"
        if "broll" in name_lower or "b-roll" in name_lower or "cobertura" in name_lower:
            return "B-Roll"
        if "product" in name_lower or "produto" in name_lower:
            return "Produto"
        return "Cena Principal"

    def _generate_project_name(self, groups: Dict, files: List[str]) -> str:
        dates = sorted(groups["dates"].keys())
        if dates and dates[0] != "unknown":
            return f"Projeto_{dates[0]}"
        if files:
            base = os.path.basename(files[0])
            name = os.path.splitext(base)[0]
            return f"Projeto_{name[:20]}"
        return "Projeto_Sem_Nome"
