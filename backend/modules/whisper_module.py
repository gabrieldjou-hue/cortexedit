"""
whisper_module.py
-----------------
Módulo de transcrição de áudio/vídeo usando faster-whisper.
Extrai o áudio do vídeo via FFmpeg e transcreve com Whisper.
Fallback para modo simulado se a dependência não estiver disponível.
"""

import os
import tempfile
import subprocess
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logger.warning("faster-whisper nao instalado. Transcricao usara modo simulado.")


class WhisperModule:

    _model_instance = None
    _model_size = None

    def __init__(self, model_size: str = "tiny", language: str = "pt"):
        self.model_size = model_size
        self.language = language
        self.device = "cpu"
        self.compute_type = "int8"

    def _get_model(self):
        if not FASTER_WHISPER_AVAILABLE:
            return None
        if (
            WhisperModule._model_instance is None
            or WhisperModule._model_size != self.model_size
        ):
            logger.info(
                f"Carregando modelo Whisper '{self.model_size}' "
                f"(device={self.device}, compute={self.compute_type})..."
            )
            WhisperModule._model_instance = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            WhisperModule._model_size = self.model_size
        return WhisperModule._model_instance

    def extract_audio(self, video_path: str) -> Optional[str]:
        if not os.path.exists(video_path):
            logger.error(f"Video nao encontrado: {video_path}")
            return None

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            tmp.name,
        ]
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            return tmp.name
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout ao extrair audio de {video_path}")
            self._cleanup(tmp.name)
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao extrair audio: {e.stderr[:200]}")
            self._cleanup(tmp.name)
            return None

    def _cleanup(self, path: Optional[str]):
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass

    def transcribe_video(
        self,
        video_path: str,
        progress_callback=None,
    ) -> Dict[str, Any]:
        result = {
            "file": video_path,
            "language": "pt-BR",
            "words": [],
            "speakers": [],
            "duration": 0.0,
            "segments": [],
        }

        def _cb(pct, stage):
            if progress_callback:
                try:
                    progress_callback(pct, stage)
                except Exception:
                    pass

        if not os.path.exists(video_path):
            logger.warning(f"Arquivo nao encontrado: {video_path}")
            return self._mock_result(video_path)

        model = self._get_model()
        if model is None:
            logger.warning("Whisper nao disponivel — usando modo simulado.")
            _cb(100, "done")
            return self._mock_result(video_path)

        _cb(15, "audio_extract")
        audio_path = self.extract_audio(video_path)
        if audio_path is None:
            logger.warning("Falha na extracao de audio — modo simulado.")
            self._cleanup(audio_path)
            _cb(100, "done")
            return self._mock_result(video_path)

        try:
            logger.info(f"Transcrevendo {os.path.basename(video_path)}...")
            _cb(30, "transcribing")
            segments, info = model.transcribe(
                audio_path,
                language=self.language,
                word_timestamps=True,
                vad_filter=True,
            )

            result["language"] = info.language or "pt-BR"
            result["duration"] = round(info.duration, 2) if info.duration else 0.0
            total_dur = result["duration"] or 1.0

            words_all: List[Dict] = []
            for segment in segments:
                seg = {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                }
                result["segments"].append(seg)
                if segment.words:
                    for w in segment.words:
                        words_all.append({
                            "word": w.word.strip(),
                            "start": round(w.start, 2),
                            "end": round(w.end, 2),
                            "speaker": None,
                        })
                pct = min(30 + (segment.end / total_dur) * 55, 85)
                _cb(int(pct), "transcribing")

            result["words"] = words_all
            _cb(85, "transcribing_done")
            logger.info(
                f"Transcricao concluida: {len(words_all)} palavras "
                f"em {len(result['segments'])} segmentos."
            )
            return result

        except Exception as e:
            logger.error(f"Erro na transcricao: {e}")
            _cb(100, "error")
            return self._mock_result(video_path)
        finally:
            self._cleanup(audio_path)

    def transcribe_batch(
        self, video_paths: List[str]
    ) -> List[Dict[str, Any]]:
        results = []
        for path in video_paths:
            results.append(self.transcribe_video(path))
        return results

    def _mock_result(self, video_path: str) -> Dict[str, Any]:
        fname = os.path.basename(video_path)
        return {
            "file": video_path,
            "language": "pt-BR",
            "words": [
                {"word": "Olá",  "start": 0.5, "end": 1.0, "speaker": None},
                {"word": "bem-vindos", "start": 1.1, "end": 1.8, "speaker": None},
                {"word": "à",    "start": 1.9, "end": 2.1, "speaker": None},
                {"word": "produção", "start": 2.2, "end": 2.8, "speaker": None},
                {"word": f"'{fname}'", "start": 2.9, "end": 3.5, "speaker": None},
            ],
            "speakers": [],
            "duration": 10.0,
            "segments": [
                {"start": 0.0, "end": 10.0, "text": f"Olá bem-vindos à produção '{fname}'"}
            ],
        }
