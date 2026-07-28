"""
render_module.py
----------------
Módulo de Renderização Real usando FFmpeg.
Concatena os clipes da EDL, aplica mix de áudio, queima legendas
e gera um arquivo master de alta qualidade.
"""

import os
import logging
from typing import Dict, Any, Optional, Callable

from modules.ffmpeg_utils import run_ffmpeg, create_concat_list

logger = logging.getLogger(__name__)


class RenderModule:
    """
    Módulo de Renderização.
    Usa FFmpeg concat demuxer para unir clipes e gerar o master.mp4.
    """

    def compose_and_render(
        self,
        edl: Dict[str, Any],
        audio_mix: Dict[str, Any],
        color_data: Dict[str, Any],
        subtitles: Dict[str, Any],
        graphics: Dict[str, Any],
        output_dir: str = None,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Compõe e renderiza o master file a partir da EDL.

        Estratégia:
          1. Usa FFmpeg concat demuxer para unir todos os clipes em sequência.
          2. Se houver arquivo SRT de legendas, queima no vídeo.
          3. Aplica normalização de áudio básica (-af loudnorm).
          4. Gera master.mp4 em qualidade alta (CRF 18).

        Retorna o caminho do master renderizado.
        """
        clips: list = edl.get("clips", [])
        job_id: str = edl.get("job_id", "unknown")
        subtitle_path: Optional[str] = subtitles.get("srt_path")

        if not output_dir:
            output_dir = os.path.join(
                os.path.dirname(__file__), '..', '..', 'exports', job_id
            )
        os.makedirs(output_dir, exist_ok=True)

        master_path = os.path.join(output_dir, "master.mp4")

        if not clips:
            logger.warning("RenderModule: EDL has no clips. Skipping render.")
            return master_path

        # ----------------------------------------------------------------
        # Caso 1: Apenas 1 arquivo → copia direto (fast path)
        # ----------------------------------------------------------------
        if len(clips) == 1:
            src = clips[0].get("file", "")
            if os.path.exists(src):
                _log(log_fn, f"RenderModule: Single file – fast path copy.")
                args = self._build_single_args(src, master_path, subtitle_path)
                success = run_ffmpeg(args, log_fn=log_fn)
                if success:
                    _log(log_fn, f"RenderModule: Master ready → {master_path}")
                    return master_path

        # ----------------------------------------------------------------
        # Caso 2: Múltiplos arquivos → concat demuxer
        # ----------------------------------------------------------------
        concat_txt = os.path.join(output_dir, "concat_list.txt")
        file_paths = [c["file"] for c in clips if os.path.exists(c.get("file", ""))]

        if not file_paths:
            logger.warning("RenderModule: No valid source files found in EDL clips.")
            return master_path

        create_concat_list(file_paths, concat_txt)
        _log(log_fn, f"RenderModule: Concatenating {len(file_paths)} clip(s)...")

        args = self._build_concat_args(concat_txt, master_path, subtitle_path)
        success = run_ffmpeg(args, log_fn=log_fn)

        if success:
            _log(log_fn, f"RenderModule: Master render complete → {master_path}")
        else:
            _log(log_fn, "RenderModule: Render failed – check FFmpeg logs.")

        return master_path

    # ------------------------------------------------------------------
    # Builders de argumentos FFmpeg
    # ------------------------------------------------------------------

    def _build_single_args(
        self, src: str, output: str, subtitle_path: Optional[str]
    ):
        vf_filters = []

        # Normalização de áudio
        audio_filter = "loudnorm=I=-16:TP=-1.5:LRA=11"

        if subtitle_path and os.path.exists(subtitle_path):
            safe_sub = subtitle_path.replace("\\", "/").replace(":", "\\:")
            vf_filters.append(f"subtitles='{safe_sub}'")

        args = ["-i", src]
        if vf_filters:
            args += ["-vf", ",".join(vf_filters)]
        args += [
            "-af", audio_filter,
            "-vcodec", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-acodec", "aac",
            "-ab", "192k",
            "-movflags", "+faststart",
            output,
        ]
        return args

    def _build_concat_args(
        self, concat_txt: str, output: str, subtitle_path: Optional[str]
    ):
        vf_filters = []
        audio_filter = "loudnorm=I=-16:TP=-1.5:LRA=11"

        if subtitle_path and os.path.exists(subtitle_path):
            safe_sub = subtitle_path.replace("\\", "/").replace(":", "\\:")
            vf_filters.append(f"subtitles='{safe_sub}'")

        args = [
            "-f", "concat",
            "-safe", "0",
            "-i", concat_txt,
        ]
        if vf_filters:
            args += ["-vf", ",".join(vf_filters)]
        args += [
            "-af", audio_filter,
            "-vcodec", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-acodec", "aac",
            "-ab", "192k",
            "-movflags", "+faststart",
            output,
        ]
        return args


def _log(fn, msg):
    logger.info(msg)
    if fn:
        fn(msg)
