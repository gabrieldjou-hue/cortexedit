"""
ingestion_module.py
-------------------
Valida e ingere arquivos de vídeo recebidos via upload ou pasta local.
Usa ffprobe para verificar a integridade dos arquivos.
"""

import os
import logging
from typing import List, Dict, Any

from modules.ffmpeg_utils import get_video_info, check_ffmpeg

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {'.mp4', '.mov', '.mxf', '.avi', '.mkv', '.webm', '.m4v', '.ts', '.braw'}


class IngestionModule:
    """
    Módulo de Ingestão.
    Aceita uma lista de caminhos de arquivo (uploads locais) ou uma pasta,
    valida os formatos suportados e extrai metadados básicos via ffprobe.
    """

    def __init__(self):
        self.ffmpeg_available = check_ffmpeg()

    def scan_and_group(self, folder_path: str) -> Dict[str, Any]:
        """Compatibilidade: varre uma pasta local e retorna assets."""
        logger.info(f"IngestionModule: Scanning directory {folder_path}")
        discovered = []

        if os.path.exists(folder_path):
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if os.path.splitext(file)[1].lower() in SUPPORTED_FORMATS:
                        discovered.append(os.path.join(root, file))
        else:
            logger.warning(f"Directory '{folder_path}' not found. No files discovered.")

        return self._build_project_data(folder_path, discovered)

    def ingest_uploaded_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Ponto de entrada principal: recebe lista de paths de arquivos
        já salvos no servidor e os valida.
        """
        logger.info(f"IngestionModule: Ingesting {len(file_paths)} uploaded file(s).")
        valid_files = []
        rejected = []

        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            if not os.path.exists(path):
                logger.warning(f"File not found: {path}")
                rejected.append(path)
            elif ext not in SUPPORTED_FORMATS:
                logger.warning(f"Unsupported format '{ext}': {path}")
                rejected.append(path)
            else:
                valid_files.append(path)

        if rejected:
            logger.warning(f"Rejected {len(rejected)} file(s): {rejected}")

        logger.info(f"IngestionModule: {len(valid_files)} valid file(s) ready for processing.")
        return self._build_project_data("uploaded", valid_files)

    def _build_project_data(self, source: str, file_paths: List[str]) -> Dict[str, Any]:
        """Constrói o dict de projeto com metadados básicos de cada arquivo."""
        files_with_meta = []
        total_duration = 0.0

        for path in file_paths:
            if self.ffmpeg_available:
                meta = get_video_info(path)
            else:
                # Fallback sem FFmpeg – metadados mínimos
                meta = {
                    "path": path,
                    "duration": 0.0,
                    "width": 0, "height": 0, "fps": 0.0,
                    "video_codec": "unknown", "audio_codec": "unknown",
                    "has_audio": True,
                    "file_size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
                }
            files_with_meta.append(meta)
            total_duration += meta.get("duration", 0.0)

        return {
            "project_id": f"proj_{abs(hash(source + str(len(file_paths))))}",
            "source": source,
            "video_files": file_paths,
            "files_metadata": files_with_meta,
            "audio_files": [],
            "total_duration_sec": round(total_duration, 2),
            "file_count": len(file_paths),
        }
