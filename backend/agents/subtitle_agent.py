"""
subtitle_agent.py
-----------------
Agente de Legendas (Artigo 5).
Responsavel por gerar legendas, sincronizar, destacar palavras e aplicar estilo.
"""

import os
import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent, AgentResult
from modules.subtitle_module import SubtitleModule

logger = logging.getLogger(__name__)


class SubtitleAgent(BaseAgent):
    def __init__(self):
        super().__init__("subtitle")
        self._module = SubtitleModule()

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []

        transcripts = task.get("transcripts", {})
        edl = task.get("edl", {})
        profile = task.get("profile", {})
        output_dir = task.get("output_dir")

        result = self._module.generate_subs(
            transcripts.get("transcripts") if transcripts else None,
            edl,
            profile,
            output_dir=output_dir,
        )

        srt_path = result.get("srt_path", "")
        logs.append(f"Arquivo SRT gerado: {srt_path}")
        if os.path.exists(srt_path):
            size_kb = round(os.path.getsize(srt_path) / 1024, 2)
            logs.append(f"Tamanho: {size_kb} KB")

        limitations = []
        if not transcripts or not transcripts.get("transcripts"):
            limitations.append("Legendas de demonstracao: sem transcricoes reais.")

        return self._make_result(
            success=True,
            data=result,
            files=[srt_path] if os.path.exists(srt_path) else [],
            extra_logs=logs,
            confidence=0.9,
            limitations=limitations,
            suggestions=[
                "Adicionar estilizacao de legendas (SRT com tags HTML).",
                "Implementar destaque de palavras em tempo real.",
            ],
        )
