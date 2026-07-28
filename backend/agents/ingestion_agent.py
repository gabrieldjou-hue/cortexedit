"""
ingestion_agent.py
------------------
Agente de Ingestão (Artigo 5).
Responsável por monitorar, validar e organizar arquivos de mídia.
"""

import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent, AgentResult
from modules.ingestion_module import IngestionModule

logger = logging.getLogger(__name__)


class IngestionAgent(BaseAgent):
    """
    Valida formatos, extrai metadados e organiza o pacote de mídia.
    Entrega: pacote organizado de mídia (project_assets).
    """

    def __init__(self):
        super().__init__("ingestion")
        self._module = IngestionModule()

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []

        uploaded_files = task.get("uploaded_files", [])
        watch_folder = task.get("watch_folder")

        if uploaded_files:
            project_assets = self._module.ingest_uploaded_files(uploaded_files)
        elif watch_folder:
            project_assets = self._module.scan_and_group(watch_folder)
        else:
            return self._make_result(
                success=False,
                error="Nenhum arquivo ou pasta fornecido.",
                limitations=["Requisição sem dados de entrada."],
            )

        n_files = project_assets.get("file_count", 0)
        total_dur = project_assets.get("total_duration_sec", 0.0)
        logs.append(f"{n_files} arquivo(s) encontrado(s), {total_dur:.1f}s total")

        limitations = []
        if not n_files:
            limitations.append("Nenhum arquivo válido encontrado para ingestão.")

        return self._make_result(
            success=True,
            data=project_assets,
            extra_logs=logs,
            confidence=0.95 if n_files > 0 else 0.5,
            limitations=limitations,
        )
