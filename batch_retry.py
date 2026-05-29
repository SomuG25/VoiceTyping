"""
Batch retry transcription for Voice Typing.

When the user presses Win+F4, this module re-transcribes
the last saved recording (last_recording.wav) using local faster-whisper.

No API key required — runs entirely offline.
"""

import wave as wav_module
from pathlib import Path
from typing import Optional


def transcribe_wav_file(wav_path: str, transcriber=None) -> Optional[str]:
    """
    Transcribe a saved WAV file using local faster-whisper.

    Args:
        wav_path: Path to the WAV file
        transcriber: LocalTranscriber instance (if None, creates a temporary one)

    Returns:
        Transcribed text, or None if failed
    """
    path = Path(wav_path)
    if not path.exists():
        print(f"[Retry] File not found: {wav_path}")
        return None

    try:
        # Read WAV file
        with wav_module.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()

        print(f"[Retry] Re-transcribing {path.name} "
              f"({sample_rate}Hz, {channels}ch, {len(frames)} bytes)...")

        if transcriber is not None:
            return transcriber.transcribe(frames)
        else:
            # Standalone mode: create a temporary transcriber
            from local_transcriber import LocalTranscriber
            t = LocalTranscriber(model_size="base")
            t.load_model()
            return t.transcribe(frames)

    except Exception as e:
        print(f"[Retry] Transcription failed: {e}")
        return None
