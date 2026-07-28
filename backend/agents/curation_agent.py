"""
curation_agent.py
-----------------
Agente 08 — Curadoria.
Escolhe os melhores momentos: melhores falas, imagens, reacoes,
enquadramentos, momentos emocionantes, informativos e impactantes.
Elimina erros, pausas, silencio, repeticoes e interrupcoes.
"""

import logging
from typing import Dict, Any, List

from agents.base_agent import BaseAgent, AgentResult
from modules.org_module import OrganizationModule

logger = logging.getLogger(__name__)


class CurationAgent(BaseAgent):
    def __init__(self):
        super().__init__("curation")
        self._module = OrganizationModule()

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Deteccao de silencio e pausas simulada (sem analise de waveform).",
            "Qualidade de take baseada em metadados tecnicos, nao em conteudo.",
        ]

        analysis = task.get("analysis", {})
        profile = task.get("profile", {})
        quality_data = task.get("quality_data", {})
        semantic = task.get("semantic", {})

        # Constroi narrativa base via modulo existente (selecao por perfil)
        narrative = self._module.build_narrative(analysis, profile)
        selected_takes: List[Dict] = narrative.get("selected_takes", [])

        # Enriquece com dados de qualidade
        issues_map = {}
        if quality_data:
            for issue in quality_data.get("issues", []):
                issues_map[issue.get("file", "")] = issue.get("issues", [])

        # Filtra takes com problemas graves de qualidade
        curated = []
        rejected = []
        for take in selected_takes:
            file_issues = issues_map.get(take.get("file", ""), [])
            quality_score = 1.0 - (len(file_issues) * 0.15)

            if quality_score >= 0.5:
                curated.append({**take, "quality_score": round(quality_score, 2)})
            else:
                rejected.append({**take, "reason": file_issues})

        # Enriquece com dados semanticos (trechos importantes)
        important_segments = semantic.get("important_segments", []) if semantic else []
        for take in curated:
            for seg in important_segments:
                if (seg.get("file") == take.get("file") and
                        abs(seg.get("start", 0) - take.get("start", 0)) < 5):
                    take["importance"] = seg.get("relevance", 0.5)
                    break
            else:
                take["importance"] = 0.5

        n_curated = len(curated)
        logs.append(f"Curadoria: {n_curated} take(s) selecionado(s)")
        logs.append(f"Rejeitados por qualidade: {len(rejected)}")

        if rejected:
            logs.append("Takes rejeitados:")
            for r in rejected[:3]:
                logs.append(f"  - {r.get('file', '?')}: {', '.join(r.get('reason', ['qualidade baixa']))}")

        narrative["selected_takes"] = curated
        narrative["total_segments"] = n_curated
        narrative["rejected_count"] = len(rejected)

        return self._make_result(
            success=True,
            data=narrative,
            extra_logs=logs,
            confidence=0.85 if n_curated > 0 else 0.3,
            limitations=limitations,
            suggestions=[
                "Implementar deteccao de silencio real com FFmpeg silencedetect.",
                "Adicionar analise de foco e exposicao por frame.",
                "Usar pontuacao de importancia semantica para priorizar takes.",
            ],
        )
