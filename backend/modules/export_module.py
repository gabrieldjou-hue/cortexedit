"""
export_module.py
----------------
Módulo de Exportação Real usando FFmpeg.
Transcodifica o master.mp4 para múltiplos formatos/deliverables em paralelo.
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable

from modules.ffmpeg_utils import run_ffmpeg, build_export_args, EXPORT_PRESETS

logger = logging.getLogger(__name__)


class ExportModule:
    """
    Módulo de Exportação.
    Gera múltiplas saídas a partir do Master File usando FFmpeg.
    Suporta paralelismo (ThreadPoolExecutor) para exportações simultâneas.
    """

    def transcode_outputs(
        self,
        master_path: str,
        export_formats: List[str],
        output_dir: str = None,
        subtitle_path: Optional[str] = None,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Transcodifica o master para cada formato solicitado.

        Args:
            master_path: Caminho do arquivo master renderizado.
            export_formats: Lista de nomes de formato (ex: ["16:9 4K", "Audio Only"]).
            output_dir: Pasta de saída. Padrão: mesma pasta do master.
            subtitle_path: SRT opcional para burn-in nos exports.
            log_fn: Callback de logging em tempo real.

        Returns:
            Lista de dicts com { format, path, success, size_mb }.
        """
        if not os.path.exists(master_path):
            _log(log_fn, f"ExportModule: Master não encontrado: {master_path}")
            return []

        if not output_dir:
            output_dir = os.path.dirname(master_path)
        os.makedirs(output_dir, exist_ok=True)

        # Filtra formatos válidos
        valid_formats = [f for f in export_formats if f in EXPORT_PRESETS]
        invalid = [f for f in export_formats if f not in EXPORT_PRESETS]
        if invalid:
            _log(log_fn, f"ExportModule: Formatos desconhecidos ignorados: {invalid}")

        if not valid_formats:
            _log(log_fn, "ExportModule: Nenhum formato válido para exportar.")
            return []

        _log(log_fn, f"ExportModule: Exportando {len(valid_formats)} formato(s): {valid_formats}")

        results = []

        # Exportações sequenciais (mais seguro para CPU; habilite paralelo se tiver GPU)
        for fmt in valid_formats:
            result = self._export_single(
                master_path, fmt, output_dir, subtitle_path, log_fn
            )
            results.append(result)

        # Resumo
        ok = sum(1 for r in results if r["success"])
        _log(log_fn, f"ExportModule: {ok}/{len(results)} exportações concluídas com sucesso.")
        return results

    def _export_single(
        self,
        master_path: str,
        fmt: str,
        output_dir: str,
        subtitle_path: Optional[str],
        log_fn: Optional[Callable[[str], None]],
    ) -> Dict[str, Any]:
        """Exporta um único formato e retorna resultado."""
        preset = EXPORT_PRESETS[fmt]
        filename = f"{preset['suffix']}.{preset['ext']}"
        output_path = os.path.join(output_dir, filename)

        _log(log_fn, f"  → Exportando [{fmt}] → {filename}")

        try:
            args = build_export_args(master_path, output_path, fmt, subtitle_path)
            success = run_ffmpeg(args, log_fn=None)  # Suprime logs granulares por formato

            size_mb = 0.0
            if success and os.path.exists(output_path):
                size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 2)
                _log(log_fn, f"  ✓ [{fmt}] concluído – {size_mb} MB")
            elif not success:
                _log(log_fn, f"  ✗ [{fmt}] falhou.")

            return {
                "format": fmt,
                "filename": filename,
                "path": output_path,
                "success": success,
                "size_mb": size_mb,
            }

        except Exception as e:
            _log(log_fn, f"  ✗ [{fmt}] erro: {e}")
            return {
                "format": fmt,
                "filename": filename,
                "path": output_path,
                "success": False,
                "size_mb": 0.0,
            }


def _log(fn, msg):
    logger.info(msg)
    if fn:
        fn(msg)
