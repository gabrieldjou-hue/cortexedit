"""
scripting_agent.py
------------------
Agente 10 — Roteirizacao.
Cria estrutura narrativa, insere ganchos, cria momentos de impacto,
define ordem ideal. NUNCA inventa fatos.
"""

import logging
from typing import Dict, Any, List

from agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class ScriptingAgent(BaseAgent):
    def __init__(self):
        super().__init__("scripting")

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Roteirizacao simulada: sem integracao com modelos de storytelling.",
            "Ganchos e momentos de impacto gerados heuristicamente.",
        ]

        narrative = task.get("narrative", {})
        structure = narrative.get("structure", []) if narrative else []
        semantic = task.get("semantic", {})
        important_segments = semantic.get("important_segments", []) if semantic else []
        keywords = semantic.get("keywords", []) if semantic else []

        if not structure:
            logs.append("Estrutura narrativa vazia — roteirizacao nao aplicavel.")
            return self._make_result(
                success=True,
                data={
                    "script": [],
                    "hooks": [],
                    "impact_moments": [],
                    "total_beats": 0,
                },
                extra_logs=logs,
                confidence=0.5,
                limitations=limitations,
            )

        script = []
        hooks = []
        impact_moments = []
        important_indices = {}

        for seg in important_segments:
            file_path = seg.get("file", "")
            start = seg.get("start", 0.0)
            important_indices[f"{file_path}_{start}"] = seg

        for i, beat in enumerate(structure):
            beat_key = f"{beat.get('file', '')}_{beat.get('start', 0.0)}"
            is_important = beat_key in important_indices

            beat_entry = {
                "sequence": i + 1,
                "file": beat.get("file", ""),
                "start": beat.get("start", 0.0),
                "end": beat.get("end", 0.0),
                "act": beat.get("act", "development"),
                "type": "important" if is_important else "transition",
                "description": self._describe_beat(beat, is_important, keywords),
            }
            script.append(beat_entry)

            if is_important:
                impact_moments.append(beat_entry)

        if len(script) >= 3:
            hooks.append(script[0])
        if len(script) >= 2:
            mid = len(script) // 2
            hooks.append(script[mid])

        logs.append(f"Roteiro gerado: {len(script)} beat(s)")
        logs.append(f"Momentos de impacto: {len(impact_moments)}")
        logs.append(f"Ganchos: {len(hooks)}")

        return self._make_result(
            success=True,
            data={
                "script": script,
                "hooks": hooks,
                "impact_moments": impact_moments,
                "total_beats": len(script),
            },
            extra_logs=logs,
            confidence=0.75,
            limitations=limitations,
            suggestions=[
                "Integrar modelo de storytelling (GPT/LLM) para beats narrativos.",
                "Implementar deteccao de clímax baseada em energia audiovisual.",
            ],
        )

    def _describe_beat(self, beat: Dict, important: bool, keywords: List[str]) -> str:
        act = beat.get("act", "development")
        if important:
            return f"Ponto alto: momento-chave do conteudo"
        if act == "beginning":
            return "Abertura: estabelecendo contexto"
        if act == "ending":
            return "Fechamento: conclusao do tema"
        kw = ", ".join(keywords[:2]) if keywords else "conteudo"
        return f"Transicao: {kw}"
