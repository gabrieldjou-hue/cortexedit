"""
transcription_agent.py
---------------------
Agente de Transcrição (Artigo 5).
Responsável por converter fala em texto, identificar locutores
e gerar timestamps palavra a palavra.
Usa faster-whisper para STT real com fallback para dados simulados.
"""

import os
import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent, AgentResult
from modules.whisper_module import WhisperModule

logger = logging.getLogger(__name__)


class TranscriptionAgent(BaseAgent):

    def __init__(self, model_size: str = "tiny"):
        super().__init__("transcription")
        self.whisper = WhisperModule(model_size=model_size)

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = []
        suggestions = []

        project_assets = task.get("project_assets", {})
        video_files = project_assets.get("video_files", [])

        if not video_files:
            logs.append("Nenhum arquivo de vídeo para transcrever.")
            return self._make_result(
                success=True,
                data={"transcripts": []},
                extra_logs=logs,
                confidence=1.0,
            )

        transcripts = []
        total_words = 0

        for file in video_files:
            if not os.path.exists(file):
                logs.append(f"Arquivo nao encontrado: {file}")
                continue

            logs.append(f"Transcrevendo: {os.path.basename(file)}...")
            result = self.whisper.transcribe_video(file)
            transcripts.append(result)
            total_words += len(result.get("words", []))

            lang = result.get("language", "pt-BR")
            dur = result.get("duration", 0)
            wc = len(result.get("words", []))
            logs.append(
                f"  OK: {wc} palavras | lingua={lang} | duracao={dur:.1f}s"
            )

        if total_words == 0:
            limitations.append(
                "Nenhuma palavra transcrita — modo simulado ativado."
            )
            suggestions.append(
                "Verificar se o audio do video contem fala."
            )

        suggestions.extend([
            "Aumentar modelo Whisper (base/small) para melhor precisao.",
            "Implementar diarizacao de locutores (pyannote-audio).",
        ])

        confidence = min(0.95, 0.5 + (total_words * 0.01))
        if total_words == 0:
            confidence = 0.5

        return self._make_result(
            success=True,
            data={"transcripts": transcripts},
            extra_logs=logs,
            confidence=round(confidence, 2),
            limitations=limitations,
            suggestions=suggestions,
        )
