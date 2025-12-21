"""
Batch transcription module for Voice Typing application.
Records audio, then sends complete recording to Gemini for transcription.
Higher accuracy than real-time streaming.
"""

import asyncio
import io
import wave
from typing import Callable, Optional
from google import genai
from google.genai import types

# Model for transcription
MODEL = "gemini-2.5-flash"


class BatchTranscriber:
    """Batch speech-to-text using Gemini API."""
    
    def __init__(self, api_key: str):
        """
        Initialize the batch transcriber.
        
        Args:
            api_key: Google AI API key
        """
        self._api_key = api_key
        self._client: Optional[genai.Client] = None
        self._on_transcription: Optional[Callable[[str], None]] = None
        self._on_status: Optional[Callable[[str], None]] = None
    
    def _initialize_client(self) -> None:
        """Initialize the Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
    
    def _convert_pcm_to_wav(self, pcm_bytes: bytes) -> bytes:
        """
        Convert raw PCM audio to WAV format.
        
        Args:
            pcm_bytes: Raw PCM 16-bit, 16kHz mono audio data
            
        Returns:
            WAV formatted audio bytes
        """
        # Create in-memory WAV file
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)       # Mono
            wf.setsampwidth(2)       # 16-bit = 2 bytes
            wf.setframerate(16000)   # 16kHz
            wf.writeframes(pcm_bytes)
        
        wav_buffer.seek(0)
        return wav_buffer.read()
    
    async def transcribe(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_bytes: PCM 16-bit, 16kHz mono audio data
            
        Returns:
            Transcribed text or None on error
        """
        if not audio_bytes:
            return None
        
        self._initialize_client()
        
        if self._on_status:
            self._on_status("Processing...")
        
        try:
            # Convert PCM to WAV format (Gemini supports WAV, not raw PCM)
            wav_bytes = self._convert_pcm_to_wav(audio_bytes)
            
            # Create audio part with correct MIME type
            audio_part = types.Part.from_bytes(
                data=wav_bytes,
                mime_type="audio/wav"  # Use WAV format, not raw PCM
            )
            
            # Simple, natural transcription prompt
            prompt = "Transcribe this audio accurately. Output only the spoken words."
            
            # Send to Gemini for transcription
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=MODEL,
                contents=[
                    prompt,
                    audio_part
                ]
            )
            
            if response and response.text:
                text = response.text.strip()
                
                if self._on_status:
                    self._on_status("Done")
                
                if self._on_transcription:
                    self._on_transcription(text)
                
                return text
            
            return None
            
        except Exception as e:
            print(f"Transcription error: {e}")
            if self._on_status:
                self._on_status(f"Error: {e}")
            return None
    
    def transcribe_sync(self, audio_bytes: bytes) -> Optional[str]:
        """
        Synchronous transcription (blocking).
        
        Args:
            audio_bytes: PCM 16-bit, 16kHz mono audio data
            
        Returns:
            Transcribed text or None on error
        """
        return asyncio.run(self.transcribe(audio_bytes))
    
    def set_transcription_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for receiving transcriptions."""
        self._on_transcription = callback
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for status updates."""
        self._on_status = callback


def test_transcription(api_key: str, audio_file: str):
    """Test batch transcription with an audio file."""
    print("Testing batch transcription...")
    
    with open(audio_file, 'rb') as f:
        audio_bytes = f.read()
    
    transcriber = BatchTranscriber(api_key)
    
    def on_status(status: str):
        print(f"Status: {status}")
    
    def on_transcription(text: str):
        print(f"Transcription: {text}")
    
    transcriber.set_status_callback(on_status)
    transcriber.set_transcription_callback(on_transcription)
    
    result = transcriber.transcribe_sync(audio_bytes)
    print(f"Result: {result}")


if __name__ == "__main__":
    import sys
    from config import config
    
    if len(sys.argv) < 2:
        print("Usage: python batch_transcriber.py <audio_file.pcm>")
    else:
        test_transcription(config.api_key, sys.argv[1])
