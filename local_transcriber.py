"""
Local speech-to-text using faster-whisper.
No API key, no network, no session limits — runs entirely on your PC.
"""

import numpy as np
from typing import Callable, Optional


SAMPLE_RATE = 16000  # Must match audio_capture.py


class LocalTranscriber:
    """Transcribe speech locally using faster-whisper.

    No artificial length limit — long audio is automatically split into
    30-second segments by faster-whisper's internal VAD and assembled back.
    """

    def __init__(self, model_size: str = "base", device: str = "cpu",
                 compute_type: str = "int8", vad_threshold: float = 0.3,
                 language: str = "en"):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._vad_threshold = vad_threshold
        self._language = language

        self._model = None

        self._on_transcription: Optional[Callable[[str], None]] = None
        self._on_status: Optional[Callable[[str], None]] = None

    # -------------------------------------------------------------------------
    # Lazy loading
    # -------------------------------------------------------------------------

    def _ensure_model(self):
        if self._model is not None:
            return
        self._emit_status("Loading Whisper model...")
        from faster_whisper import WhisperModel
        self._model = WhisperModel(
            self._model_size,
            device=self._device,
            compute_type=self._compute_type,
        )
        self._emit_status("Ready")

    def load_model(self):
        """Pre-load model. Call once at startup or it auto-loads on first use."""
        self._emit_status("Loading models...")
        self._ensure_model()
        self._emit_status("Ready")

    # -------------------------------------------------------------------------
    # Transcription — no length limit
    # -------------------------------------------------------------------------

    def transcribe(self, audio_data: bytes) -> str:
        """Convert raw PCM16 mono 16kHz audio bytes to text.

        No artificial length limit. faster-whisper internally splits audio
        into ~30s chunks using Silero VAD, transcribes each, and merges.
        """
        if not audio_data or len(audio_data) < 1600:  # less than ~0.1s
            return ""

        try:
            self._ensure_model()

            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            duration = len(audio_np) / SAMPLE_RATE
            print(f"[Local] Transcribing {duration:.1f}s of audio...")

            segments, info = self._model.transcribe(
                audio_np,
                language=self._language,
                beam_size=5,
                # Let faster-whisper's internal VAD handle segmentation.
                # High min_silence ensures it doesn't split mid-sentence.
                vad_filter=True,
                vad_parameters=dict(
                    threshold=self._vad_threshold,
                    min_speech_duration_ms=400,
                    min_silence_duration_ms=1200,
                    speech_pad_ms=400,
                ),
            )

            # Collect all segments — no truncation
            parts = []
            for seg in segments:
                if seg.text and seg.text.strip():
                    parts.append(seg.text.strip())
                    print(f"  [seg {len(parts)}] {seg.text.strip()}")

            text = " ".join(parts).strip()
            if text:
                print(f"[Local] Total: \"{text}\"")
            else:
                print("[Local] No speech detected")
            return text

        except Exception as e:
            print(f"[Local] Transcription error: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def transcribe_wav_file(self, wav_path: str) -> str:
        """Transcribe a WAV file (Win+F4 retry)."""
        import wave as wav
        try:
            with wav.open(wav_path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
            return self.transcribe(frames)
        except Exception as e:
            print(f"[Local] WAV transcription error: {e}")
            return ""

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def audio_chunks_to_bytes(self, chunks: list) -> bytes:
        return b"".join(chunks)

    def set_transcription_callback(self, fn: Callable[[str], None]):
        self._on_transcription = fn

    def set_status_callback(self, fn: Callable[[str], None]):
        self._on_status = fn

    def _emit_status(self, status: str):
        print(f"[LocalTranscriber] {status}")
        if self._on_status:
            self._on_status(status)

    @property
    def model_size(self) -> str:
        return self._model_size

    @property
    def is_ready(self) -> bool:
        return self._model is not None
