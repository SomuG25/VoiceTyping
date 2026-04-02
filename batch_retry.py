"""
Batch retry transcription for Voice Typing.

When the user presses Ctrl+Shift+R, this module re-transcribes
the last saved recording (last_recording.wav) using the Gemini
batch generate_content API (not the Live API, since we have a file).

This is a fallback for cases where the Live API session failed
or the transcription was incorrect.
"""

import wave
import base64
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types


BATCH_MODEL = "gemini-2.5-flash"  # Stable model for file-based transcription


def transcribe_wav_file(wav_path: str, api_key: str) -> Optional[str]:
    """
    Transcribe a saved WAV file using Gemini batch generate_content.

    Args:
        wav_path: Path to the WAV file
        api_key:  Google AI API key

    Returns:
        Transcribed text, or None if failed
    """
    path = Path(wav_path)
    if not path.exists():
        print(f"[Retry] File not found: {wav_path}")
        return None

    try:
        # Read WAV file
        with wave.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()

        print(f"[Retry] Re-transcribing {path.name} "
              f"({sample_rate}Hz, {channels}ch, {len(frames)} bytes)...")

        # Encode audio for API
        audio_b64 = base64.b64encode(frames).decode("utf-8")

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=BATCH_MODEL,
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                data=audio_b64,
                                mime_type=f"audio/wav",
                            )
                        ),
                        types.Part(text=(
                            "Transcribe the speech in this audio exactly as spoken. "
                            "Output only the transcribed text, no explanations."
                        )),
                    ]
                )
            ],
        )

        text = response.text.strip() if response.text else None
        if text:
            print(f"[Retry] Transcription: \"{text}\"")
        else:
            print("[Retry] No text in response")
        return text

    except Exception as e:
        print(f"[Retry] Transcription failed: {e}")
        return None
