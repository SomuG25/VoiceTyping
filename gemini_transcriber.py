"""
Gemini Live API transcription module for Voice Typing application.
Streams audio to Gemini and receives real-time transcriptions.
Uses the official google-genai SDK pattern from docs.
"""

import asyncio
from typing import Callable, Optional
from google import genai
from google.genai import types

# Model for real-time audio transcription (December 2025 release)
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"


class GeminiTranscriber:
    """Real-time speech-to-text using Gemini Live API."""
    
    def __init__(self, api_key: str):
        """
        Initialize the Gemini transcriber.
        
        Args:
            api_key: Google AI API key
        """
        self._api_key = api_key
        self._client: Optional[genai.Client] = None
        self._session = None
        self._is_connected = False
        self._on_transcription: Optional[Callable[[str], None]] = None
        self._on_status: Optional[Callable[[str], None]] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._audio_queue: asyncio.Queue = asyncio.Queue(maxsize=20)
        self._send_task: Optional[asyncio.Task] = None
        self._running = False
        self._session_context = None
    
    def _get_config(self) -> dict:
        """Get the Live API configuration."""
        # IMPORTANT: response_modalities must be AUDIO for native audio model
        # input_audio_transcription enables transcription of what user says
        return {
            "response_modalities": ["AUDIO"],
            "input_audio_transcription": {},  # Enable input transcription
        }
    
    async def connect(self) -> bool:
        """
        Establish connection to Gemini Live API.
        
        Returns:
            True if connected successfully
        """
        if self._is_connected:
            return True
        
        try:
            # Initialize client with API key
            self._client = genai.Client(api_key=self._api_key)
            
            # Connect to Live API using async context manager
            self._session_context = self._client.aio.live.connect(
                model=MODEL,
                config=self._get_config()
            )
            self._session = await self._session_context.__aenter__()
            
            self._is_connected = True
            self._running = True
            
            # Start background tasks
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._send_task = asyncio.create_task(self._send_loop())
            
            if self._on_status:
                self._on_status("Connected")
            
            return True
            
        except Exception as e:
            print(f"Gemini connection error: {e}")
            if self._on_status:
                self._on_status(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Gemini Live API."""
        self._running = False
        
        # Cancel background tasks
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        
        if self._send_task:
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass
            self._send_task = None
        
        # Close session
        if self._session_context:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._session_context = None
            self._session = None
        
        self._is_connected = False
        
        if self._on_status:
            self._on_status("Disconnected")
    
    async def send_audio(self, audio_bytes: bytes) -> None:
        """
        Queue audio bytes to send to Gemini.
        
        Args:
            audio_bytes: PCM 16-bit, 16kHz mono audio data
        """
        if self._is_connected:
            try:
                await self._audio_queue.put(audio_bytes)
            except asyncio.QueueFull:
                pass  # Drop if queue full
    
    def send_audio_sync(self, audio_bytes: bytes) -> None:
        """
        Synchronous method to queue audio bytes.
        For use from non-async code (like audio callback).
        
        Args:
            audio_bytes: PCM 16-bit, 16kHz mono audio data
        """
        if self._is_connected:
            try:
                self._audio_queue.put_nowait(audio_bytes)
            except asyncio.QueueFull:
                pass  # Drop audio if queue is full
    
    async def _send_loop(self) -> None:
        """Background task to send queued audio to Gemini."""
        while self._running and self._is_connected:
            try:
                # Get audio from queue with timeout
                try:
                    audio_bytes = await asyncio.wait_for(
                        self._audio_queue.get(), 
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Send to Gemini using types.Blob (official format from docs)
                if self._session and audio_bytes:
                    await self._session.send_realtime_input(
                        audio=types.Blob(
                            data=audio_bytes,
                            mime_type='audio/pcm;rate=16000'
                        )
                    )
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Send error: {e}")
                await asyncio.sleep(0.1)
    
    async def _receive_loop(self) -> None:
        """Background task to receive transcriptions from Gemini."""
        while self._running and self._is_connected:
            try:
                # Use async for directly on session.receive()
                async for msg in self._session.receive():
                    if not self._running:
                        break
                    
                    # Check for server content
                    if msg.server_content:
                        # Handle input transcription (what user said)
                        if msg.server_content.input_transcription:
                            text = msg.server_content.input_transcription.text
                            if text and self._on_transcription:
                                print(f"Transcription: {text}")
                                self._on_transcription(text)
                                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Receive error: {e}")
                if self._running:
                    await asyncio.sleep(1)
    
    async def send_audio_stream_end(self) -> None:
        """Signal end of audio stream to Gemini."""
        if self._session and self._is_connected:
            try:
                await self._session.send_realtime_input(audio_stream_end=True)
            except Exception as e:
                print(f"Error sending stream end: {e}")
    
    def set_transcription_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for receiving transcriptions."""
        self._on_transcription = callback
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for status updates."""
        self._on_status = callback
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Gemini."""
        return self._is_connected


async def test_connection(api_key: str) -> bool:
    """Test connection to Gemini Live API."""
    print("Testing Gemini Live API connection...")
    
    transcriber = GeminiTranscriber(api_key)
    
    def on_status(status: str):
        print(f"Status: {status}")
    
    def on_transcription(text: str):
        print(f"Transcription: {text}")
    
    transcriber.set_status_callback(on_status)
    transcriber.set_transcription_callback(on_transcription)
    
    if await transcriber.connect():
        print("Connection successful!")
        await asyncio.sleep(2)
        await transcriber.disconnect()
        return True
    else:
        print("Connection failed!")
        return False


if __name__ == "__main__":
    import os
    from config import config
    api_key = config.api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Error: Set GEMINI_API_KEY environment variable or add to config.json")
    else:
        asyncio.run(test_connection(api_key))
