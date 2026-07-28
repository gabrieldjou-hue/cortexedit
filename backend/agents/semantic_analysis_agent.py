"""
semantic_analysis_agent.py
--------------------------
Agente 06 — Analise Semantica.
Entende assuntos, identifica temas, detecta palavras-chave,
cria resumo, identifica topicos e trechos importantes.
ATUALMENTE SIMULADO — placeholder para NLP real.
"""

import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class SemanticAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__("semantic_analysis")

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Analise semantica simulada: sem integracao com NLP (BERT/GPT).",
            "Resumo e topicos gerados heuristicamente.",
        ]

        transcripts = task.get("transcripts", {})
        cv_data = task.get("cv_data", {})

        transcript_list = transcripts.get("transcripts", []) if transcripts else []

        topics = ["Apresentacao", "Conteudo Principal", "Encerramento"]
        keywords = ["tecnologia", "inovacao", "futuro", "inteligencia artificial"]
        summary = "Conteudo audiovisual com foco em tecnologia e inovacao."

        important_segments = []
        for t in transcript_list:
            words = t.get("words", [])
            if words:
                important_segments.append({
                    "file": t.get("file", ""),
                    "start": words[0].get("start", 0.0),
                    "end": words[-1].get("end", 10.0),
                    "reason": "trecho com fala detectada",
                    "relevance": 0.7,
                })

        logs.append(f"Topicos identificados: {len(topics)}")
        logs.append(f"Palavras-chave: {keywords}")
        logs.append(f"Segmentos importantes: {len(important_segments)}")

        return self._make_result(
            success=True,
            data={
                "topics": topics,
                "keywords": keywords,
                "summary": summary,
                "important_segments": important_segments,
                "language": "pt-BR",
            },
            extra_logs=logs,
            confidence=0.5,
            limitations=limitations,
            suggestions=[
                "Integrar modelo BERT/GPT para extracao de topicos real.",
                "Implementar summarization com NLP (HuggingFace transformers).",
                "Adicionar deteccao de sentimento por segmento.",
            ],
        )
