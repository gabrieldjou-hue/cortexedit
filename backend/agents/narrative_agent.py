"""
narrative_agent.py
------------------
Agente 09 — Narrativa.
Monta automaticamente uma sequencia logica, cria ritmo,
define inicio, desenvolvimento e encerramento.
NUNCA modifica conteudo — somente reorganiza.
"""

import logging
from typing import Dict, Any, List

from agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class NarrativeAgent(BaseAgent):
    def __init__(self):
        super().__init__("narrative")

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Estrutura narrativa gerada heuristicamente (regras).",
            "Sem analise de ritmo baseada em energia do audio.",
        ]

        curation = task.get("curation", {})
        selected_takes = curation.get("selected_takes", []) if curation else []
        semantic = task.get("semantic", {})
        important_segments = semantic.get("important_segments", []) if semantic else []

        if not selected_takes:
            logs.append("Nenhum take disponivel para organizar narrativa.")
            return self._make_result(
                success=True,
                data={
                    "structure": [],
                    "acts": {"beginning": [], "development": [], "ending": []},
                    "total_segments": 0,
                },
                extra_logs=logs,
                confidence=0.5,
                limitations=limitations,
            )

        total = len(selected_takes)
        split_begin = max(1, int(total * 0.15))
        split_end = max(1, int(total * 0.15))

        acts = {
            "beginning": selected_takes[:split_begin],
            "development": selected_takes[split_begin:-split_end] if split_end < total - split_begin else selected_takes[split_begin:],
            "ending": selected_takes[-split_end:] if split_end > 0 else [],
        }

        structure = []
        for act_name, takes in acts.items():
            for take in takes:
                structure.append({
                    **take,
                    "act": act_name,
                    "narrative_position": len(structure),
                })

        logs.append(f"Narrativa organizada em 3 atos:")
        logs.append(f"  Inicio: {len(acts['beginning'])} segmento(s)")
        logs.append(f"  Desenvolvimento: {len(acts['development'])} segmento(s)")
        logs.append(f"  Encerramento: {len(acts['ending'])} segmento(s)")
        logs.append(f"  Total: {len(structure)} segmento(s)")

        return self._make_result(
            success=True,
            data={
                "structure": structure,
                "acts": {k: len(v) for k, v in acts.items()},
                "total_segments": len(structure),
            },
            extra_logs=logs,
            confidence=0.85,
            limitations=limitations,
            suggestions=[
                "Implementar deteccao de ritmo baseada em energia de audio.",
                "Adicionar analise de tensao narrativa (story arc).",
            ],
        )
