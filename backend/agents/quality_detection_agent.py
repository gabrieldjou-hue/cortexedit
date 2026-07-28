"""
quality_detection_agent.py
--------------------------
Agente 07 — Deteccao de Qualidade.
Detecta tremores, desfoque, superexposicao, subexposicao,
ruido, falhas de audio e avalia estabilidade.
NUNCA corrige — somente detecta (Artigo 5).
ATUALMENTE SIMULADO — placeholder para analise real de frames.
"""

import os
import logging
from typing import Dict, Any, List

from agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class QualityDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__("quality_detection")

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Deteccao de qualidade simulada: sem analise real de frames.",
            "Nao ha integracao com FFmpeg para deteccao de blur/shake.",
        ]

        project_assets = task.get("project_assets", {})
        files_metadata = project_assets.get("files_metadata", [])
        video_files = project_assets.get("video_files", [])

        issues: List[Dict] = []
        total_score = 0.0
        file_count = len(video_files) or 1

        for i, meta in enumerate(files_metadata):
            file_path = meta.get("path", video_files[i] if i < len(video_files) else "unknown")
            width = meta.get("width", 0)
            height = meta.get("height", 0)
            fps = meta.get("fps", 0.0)
            file_issues = []

            score = 1.0

            if width < 640 or height < 480:
                file_issues.append("Baixa resolucao")
                score -= 0.2
            if fps < 15:
                file_issues.append("Taxa de quadros muito baixa")
                score -= 0.15
            if width == 0 and height == 0:
                file_issues.append("Metadados de video ausentes")
                score -= 0.3

            if file_issues:
                issues.append({
                    "file": file_path,
                    "issues": file_issues,
                    "quality_score": round(max(0.0, score), 2),
                })
            total_score += score

        avg_quality = round(total_score / file_count, 2)
        logs.append(f"Qualidade media dos arquivos: {avg_quality}")
        logs.append(f"Arquivos com problemas: {len(issues)}/{file_count}")

        if issues:
            logs.append("Problemas encontrados:")
            for iss in issues[:3]:
                logs.append(f"  - {os.path.basename(iss['file'])}: {', '.join(iss['issues'])}")

        return self._make_result(
            success=True,
            data={
                "avg_quality_score": avg_quality,
                "issues": issues,
                "total_issues": len(issues),
                "files_analyzed": file_count,
            },
            extra_logs=logs,
            confidence=0.5 if issues else 0.9,
            limitations=limitations,
            suggestions=[
                "Integrar FFmpeg blur/shake detection filters.",
                "Implementar analise de histograma para exposicao.",
                "Adicionar deteccao de ruido de audio via FFmpeg astats.",
            ],
        )
