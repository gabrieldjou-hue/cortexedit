"""
analysis_module.py
------------------
Extrai metadados técnicos completos dos arquivos via ffprobe
e gera análise de cenas/cortes para alimentar o AI Engine.
"""

import logging
import os
from typing import Dict, Any, List

from modules.ffmpeg_utils import get_video_info

logger = logging.getLogger(__name__)


class AnalysisModule:
    """
    Módulo de Análise Técnica.
    Usa ffprobe para extrair resolução, codec, fps, duração e canais de áudio
    de cada arquivo do projeto.
    """

    def extract_features(self, project_assets: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa todos os arquivos de vídeo do projeto.
        Retorna um dicionário com metadados consolidados e sugestão de
        cortes uniformes para o AI Engine.
        """
        files_metadata: List[Dict[str, Any]] = project_assets.get("files_metadata", [])
        video_files: List[str] = project_assets.get("video_files", [])

        # Se já temos metadados do ingestion, reusa; senão extrai via ffprobe
        if not files_metadata:
            files_metadata = [get_video_info(p) for p in video_files]

        # Consolidar metadados
        total_duration = sum(m.get("duration", 0.0) for m in files_metadata)
        avg_fps = self._avg_fps(files_metadata)
        primary_res = self._primary_resolution(files_metadata)
        has_audio = any(m.get("has_audio", False) for m in files_metadata)

        logger.info(
            f"AnalysisModule: {len(files_metadata)} file(s) | "
            f"{total_duration:.1f}s total | {primary_res} | {avg_fps:.2f} fps | "
            f"audio={'yes' if has_audio else 'no'}"
        )

        # Gerar pontos de corte sugeridos (1 corte a cada ~30s por arquivo)
        cut_points = self._generate_cut_suggestions(files_metadata)

        return {
            "files_metadata": files_metadata,
            "total_duration": total_duration,
            "avg_fps": avg_fps,
            "primary_resolution": primary_res,
            "has_audio": has_audio,
            "cut_suggestions": cut_points,
            "file_count": len(files_metadata),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _avg_fps(self, metadata: List[Dict[str, Any]]) -> float:
        fps_values = [m["fps"] for m in metadata if m.get("fps", 0) > 0]
        return sum(fps_values) / len(fps_values) if fps_values else 30.0

    def _primary_resolution(self, metadata: List[Dict[str, Any]]) -> str:
        for m in metadata:
            w, h = m.get("width", 0), m.get("height", 0)
            if w > 0 and h > 0:
                return f"{w}x{h}"
        return "unknown"

    def _generate_cut_suggestions(
        self, metadata: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Gera pontos de corte sugeridos para cada arquivo.
        Estratégia simples: segmentos de 30s. O AI Engine refina isso depois.
        """
        cuts = []
        for m in metadata:
            duration = m.get("duration", 0.0)
            path = m.get("path", "")
            segment_len = 30.0
            t = 0.0
            while t < duration:
                end = min(t + segment_len, duration)
                cuts.append({"file": path, "in": round(t, 2), "out": round(end, 2)})
                t = end
        return cuts
