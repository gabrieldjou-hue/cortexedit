"""
ffmpeg_utils.py
---------------
Helper centralizado para execução de FFmpeg e ffprobe.
Gerencia subprocessos, captura progresso em tempo real e define
presets de exportação para os formatos suportados pela plataforma.
"""

import subprocess
import shutil
import json
import logging
import os
from typing import Callable, Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Presets de exportação (formato → parâmetros FFmpeg)
# ---------------------------------------------------------------------------
EXPORT_PRESETS: Dict[str, Dict[str, Any]] = {
    "16:9 4K": {
        "suffix": "4K_16x9",
        "ext": "mp4",
        "vf": "scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2",
        "vcodec": "libx264",
        "crf": "18",
        "preset": "fast",
        "acodec": "aac",
        "ab": "192k",
    },
    "9:16 1080p": {
        "suffix": "1080p_9x16",
        "ext": "mp4",
        "vf": "crop=ih*9/16:ih,scale=1080:1920",
        "vcodec": "libx264",
        "crf": "20",
        "preset": "fast",
        "acodec": "aac",
        "ab": "192k",
    },
    "1:1 Square": {
        "suffix": "1080_square",
        "ext": "mp4",
        "vf": "crop=min(iw\\,ih):min(iw\\,ih),scale=1080:1080",
        "vcodec": "libx264",
        "crf": "20",
        "preset": "fast",
        "acodec": "aac",
        "ab": "128k",
    },
    "Audio Only": {
        "suffix": "audio_only",
        "ext": "mp3",
        "vf": None,
        "vcodec": None,
        "crf": None,
        "preset": None,
        "acodec": "libmp3lame",
        "ab": "192k",
    },
}


# ---------------------------------------------------------------------------
# Verificação de dependências
# ---------------------------------------------------------------------------
def check_ffmpeg() -> bool:
    """Verifica se ffmpeg e ffprobe estão disponíveis no PATH."""
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ffprobe_ok = shutil.which("ffprobe") is not None
    if not ffmpeg_ok:
        logger.error("FFmpeg não encontrado no PATH. Instale em https://ffmpeg.org/download.html")
    if not ffprobe_ok:
        logger.error("ffprobe não encontrado no PATH.")
    return ffmpeg_ok and ffprobe_ok


# ---------------------------------------------------------------------------
# ffprobe
# ---------------------------------------------------------------------------
def ffprobe_json(file_path: str) -> Dict[str, Any]:
    """
    Executa ffprobe e retorna os metadados do arquivo como dict.
    Retorna dict vazio se o arquivo não for válido ou ffprobe falhar.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        file_path,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning(f"ffprobe falhou para {file_path}: {e}")
    return {}


def get_video_info(file_path: str) -> Dict[str, Any]:
    """
    Extrai informações essenciais de vídeo/áudio de um arquivo.
    Retorna dict com: duration, width, height, fps, video_codec,
                      audio_codec, has_audio, file_size_mb.
    """
    data = ffprobe_json(file_path)
    info: Dict[str, Any] = {
        "path": file_path,
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "video_codec": "unknown",
        "audio_codec": "none",
        "has_audio": False,
        "file_size_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2) if os.path.exists(file_path) else 0,
    }

    fmt = data.get("format", {})
    if fmt.get("duration"):
        info["duration"] = float(fmt["duration"])

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type", "")
        if codec_type == "video":
            info["video_codec"] = stream.get("codec_name", "unknown")
            info["width"] = stream.get("width", 0)
            info["height"] = stream.get("height", 0)
            # fps pode vir como "30000/1001"
            fps_str = stream.get("r_frame_rate", "0/1")
            try:
                num, den = fps_str.split("/")
                info["fps"] = round(int(num) / int(den), 3) if int(den) > 0 else 0.0
            except (ValueError, ZeroDivisionError):
                info["fps"] = 0.0
        elif codec_type == "audio":
            info["audio_codec"] = stream.get("codec_name", "unknown")
            info["has_audio"] = True

    return info


# ---------------------------------------------------------------------------
# Execução FFmpeg com progresso em tempo real
# ---------------------------------------------------------------------------
def run_ffmpeg(
    args: List[str],
    log_fn: Optional[Callable[[str], None]] = None,
    timeout: int = 3600,
) -> bool:
    """
    Executa ffmpeg com os argumentos fornecidos.
    Captura stderr em tempo real e envia para log_fn se fornecida.
    Retorna True se sucesso, False se falhar.
    """
    cmd = ["ffmpeg", "-y"] + args  # -y: sobrescrever sem perguntar
    if log_fn:
        log_fn(f"FFmpeg: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        # Lê stderr linha a linha para capturar progresso
        for line in process.stderr:
            line = line.strip()
            if line and log_fn:
                # Filtra linhas de progresso muito verbosas
                if "frame=" in line or "size=" in line or "time=" in line:
                    log_fn(f"⚙ {line}")
                elif line.startswith("ffmpeg") or "Error" in line or "error" in line:
                    log_fn(f"⚠ {line}")

        process.wait(timeout=timeout)
        success = process.returncode == 0
        if log_fn:
            if success:
                log_fn("✓ FFmpeg concluído com sucesso.")
            else:
                log_fn(f"✗ FFmpeg terminou com código {process.returncode}")
        return success

    except subprocess.TimeoutExpired:
        process.kill()
        if log_fn:
            log_fn("✗ FFmpeg timeout – processo encerrado.")
        return False
    except FileNotFoundError:
        if log_fn:
            log_fn("✗ FFmpeg não encontrado no PATH.")
        return False


# ---------------------------------------------------------------------------
# Utilitários de edição
# ---------------------------------------------------------------------------
def create_concat_list(file_paths: List[str], output_txt: str) -> str:
    """
    Cria um arquivo de texto no formato FFmpeg concat demuxer.
    Retorna o caminho do arquivo gerado.
    """
    with open(output_txt, "w", encoding="utf-8") as f:
        for path in file_paths:
            # FFmpeg concat precisa de paths com / e sem caracteres especiais problemáticos
            safe_path = path.replace("\\", "/")
            f.write(f"file '{safe_path}'\n")
    return output_txt


def build_export_args(
    master_path: str,
    output_path: str,
    preset_key: str,
    subtitle_path: Optional[str] = None,
) -> List[str]:
    """
    Constrói os argumentos FFmpeg para um preset de exportação específico.
    """
    preset = EXPORT_PRESETS.get(preset_key)
    if not preset:
        raise ValueError(f"Preset desconhecido: {preset_key}")

    args = ["-i", master_path]

    if preset["vcodec"] is None:
        # Audio Only
        args += ["-vn", "-acodec", preset["acodec"], "-ab", preset["ab"]]
    else:
        vf = preset["vf"] or ""
        if subtitle_path and os.path.exists(subtitle_path):
            # Burn subtitles – caminhos precisam de escape
            safe_sub = subtitle_path.replace("\\", "/").replace(":", "\\:")
            vf = f"{vf},subtitles='{safe_sub}'" if vf else f"subtitles='{safe_sub}'"

        if vf:
            args += ["-vf", vf]

        args += [
            "-vcodec", preset["vcodec"],
            "-crf", preset["crf"],
            "-preset", preset["preset"],
            "-acodec", preset["acodec"],
            "-ab", preset["ab"],
            "-movflags", "+faststart",  # Streaming-ready MP4
        ]

    args.append(output_path)
    return args
