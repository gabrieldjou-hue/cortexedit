"""
subtitle_module.py
------------------
Módulo de Legendas.
Gera arquivo SRT estruturalmente correto a partir das transcrições do AI Engine.
Se Whisper não estiver disponível, gera SRT de demonstração.
"""

import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SubtitleModule:
    """
    Gera arquivos SRT para burn-in no render ou distribuição.
    Formato: blocos numerados com timecodes HH:MM:SS,mmm.
    """

    def generate_subs(
        self,
        transcripts: Optional[List[Dict]],
        edl: Dict[str, Any],
        profile: Dict[str, Any],
        output_dir: str = None,
    ) -> Dict[str, Any]:
        logger.info("SubtitleModule: Generating subtitle file.")

        job_id = edl.get("job_id", "unknown")
        if not output_dir:
            output_dir = os.path.join(
                os.path.dirname(__file__), '..', '..', 'exports', job_id
            )
        os.makedirs(output_dir, exist_ok=True)

        srt_path = os.path.join(output_dir, "subtitles.srt")
        srt_content = self._build_srt(transcripts, edl)

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        logger.info(f"SubtitleModule: SRT written → {srt_path}")
        return {"srt_path": srt_path, "format": "SRT"}

    def _build_srt(
        self, transcripts: Optional[List[Dict]], edl: Dict[str, Any]
    ) -> str:
        """
        Constrói o conteúdo SRT.
        Se houver transcrições do AI Engine, usa as palavras reais.
        Caso contrário, gera legendas de demonstração baseadas nos clips da EDL.
        """
        blocks = []
        idx = 1

        if transcripts:
            # Agrupa palavras em linhas de ~7 palavras cada
            for transcript in transcripts:
                words = transcript.get("words", [])
                chunk = []
                chunk_start = None
                for w in words:
                    if chunk_start is None:
                        chunk_start = w.get("start", 0.0)
                    chunk.append(w.get("word", ""))
                    if len(chunk) >= 7:
                        chunk_end = w.get("end", chunk_start + 2.0)
                        blocks.append((idx, chunk_start, chunk_end, " ".join(chunk)))
                        idx += 1
                        chunk = []
                        chunk_start = None
                if chunk and chunk_start is not None:
                    chunk_end = words[-1].get("end", chunk_start + 2.0) if words else chunk_start + 2.0
                    blocks.append((idx, chunk_start, chunk_end, " ".join(chunk)))
                    idx += 1

        if not blocks:
            # Legendas de demo baseadas na duração da EDL
            total = edl.get("total_duration", 10.0)
            demo_lines = [
                "Bem-vindos à produção CortexEdit.",
                "Este conteúdo foi editado automaticamente por IA.",
                "Pipeline: Ingestion → Analysis → AI → Render → Export.",
                "Obrigado por assistir!",
            ]
            step = total / max(len(demo_lines), 1)
            for i, line in enumerate(demo_lines):
                t_in = i * step
                t_out = t_in + step - 0.5
                if t_in >= total:
                    break
                blocks.append((i + 1, t_in, min(t_out, total), line))

        lines = []
        for num, t_in, t_out, text in blocks:
            lines.append(str(num))
            lines.append(f"{_fmt_tc(t_in)} --> {_fmt_tc(t_out)}")
            lines.append(text)
            lines.append("")

        return "\n".join(lines)


def _fmt_tc(seconds: float) -> str:
    """Formata segundos no formato SRT: HH:MM:SS,mmm"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
