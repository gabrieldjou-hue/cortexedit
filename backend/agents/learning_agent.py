"""
learning_agent.py
-----------------
Agente 22 — Aprendizado.
Avalia feedback do usuario, mede qualidade, sugere melhorias
e cria novos presets.
NUNCA modifica automaticamente o comportamento do sistema.
Todas as sugestoes deverao ser aprovadas pelo Master.
ATUALMENTE SIMULADO — estrutura para aprendizado futuro.
"""

import logging
from typing import Dict, Any, List

from agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class LearningAgent(BaseAgent):
    def __init__(self):
        super().__init__("learning")

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Aprendizado simulado: sem modelo de ML para recomendacoes.",
            "Nao ha historico de feedback do usuario para analise.",
        ]

        qc_report = task.get("qc_report", {})
        profile = task.get("profile", {})
        ctx = context.get_all() if hasattr(context, 'get_all') else {}

        suggestions: List[str] = []
        new_presets: List[Dict] = []

        if qc_report:
            issues = qc_report.get("issues", [])
            if issues:
                suggestions.append("Revisar pipeline para resolver issues do QC.")
                for issue in issues[:3]:
                    suggestions.append(f"Melhoria sugerida: {issue}")

        qc_approved = qc_report.get("approved", True) if qc_report else True
        profile_name = profile.get("name", "default")

        if not qc_approved:
            suggestions.append("QC reprovou — ajustar parametros de exportacao.")
            suggestions.append("Verificar qualidade dos arquivos de origem.")

        if ctx.get("errors"):
            n_errors = len(ctx["errors"])
            suggestions.append(f"Corrigir {n_errors} erro(s) ocorridos no pipeline.")

        learnings = {
            "profile_used": profile_name,
            "qc_approved": qc_approved,
            "suggestions": suggestions,
            "new_presets_suggested": new_presets,
            "metrics": {
                "total_suggestions": len(suggestions),
                "requires_attention": not qc_approved,
            },
        }

        logs.append(f"aprendizado: analise concluida para perfil '{profile_name}'")
        logs.append(f"aprendizado: {len(suggestions)} sugestao(oes) gerada(s)")
        if suggestions:
            for s in suggestions[:3]:
                logs.append(f"  * {s}")

        return self._make_result(
            success=True,
            data=learnings,
            extra_logs=logs,
            confidence=0.5,
            limitations=limitations,
            suggestions=[
                "Coletar feedback explicito do usuario apos cada exportacao.",
                "Implementar modelo de recomendacao baseado em historico.",
                "Criar sistema de presets colaborativos (crowdsourced).",
            ],
        )
