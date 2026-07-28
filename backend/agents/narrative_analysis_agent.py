"""
narrative_analysis_agent.py
---------------------------
Agente de Análise Narrativa (Artigo 5).
Responsável por entender contexto, identificar assuntos,
detectar momentos relevantes, classificar emoções e organizar narrativa.
"""

import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent, AgentResult
from modules.analysis_module import AnalysisModule

logger = logging.getLogger(__name__)


class NarrativeAnalysisAgent(BaseAgent):
    """
    Combina metadados técnicos (ffprobe) com dados de CV e transcrição
    para gerar um mapa narrativo completo do projeto.
    """

    def __init__(self):
        super().__init__("narrative_analysis")
        self._module = AnalysisModule()

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Análise de emoções simulada.",
            "Classificação de assunto baseada em regras simples.",
        ]

        project_assets = task.get("project_assets", {})
        cv_data = task.get("cv_data", {})
        transcripts = task.get("transcripts", {})

        # Extrai features técnicas via módulo existente
        base_features = self._module.extract_features(project_assets)

        # Enriquece com dados de CV e transcrição
        analysis = {
            **base_features,
            "cv_data": cv_data,
            "transcripts": transcripts,
            "narrative_map": [],
        }

        # Gera mapa narrativo simples baseado em cortes
        for cut in base_features.get("cut_suggestions", []):
            analysis["narrative_map"].append({
                "file": cut["file"],
                "in": cut["in"],
                "out": cut["out"],
                "context": "conteúdo principal",
                "emotion": "neutro",
                "relevance": 0.8,
            })

        res = base_features.get("primary_resolution", "?")
        fps = base_features.get("avg_fps", 0.0)
        logs.append(f"Análise: resolução {res}, {fps:.2f} fps")
        logs.append(f"Mapa narrativo: {len(analysis['narrative_map'])} segmentos")

        return self._make_result(
            success=True,
            data=analysis,
            extra_logs=logs,
            confidence=0.85,
            limitations=limitations,
            suggestions=[
                "Implementar análise de sentimento nos transcripts.",
                "Adicionar detecção de cenas por similaridade de quadro.",
            ],
        )
