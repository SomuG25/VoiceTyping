"""
Voice Typing Application - Main Entry Point (Batch Mode)

A system-wide voice typing application for Windows 11 using Google Gemini API.
Press Win+H to start recording, press again to stop and transcribe.

Usage:
    python main.py

Requirements:
    - Set GEMINI_API_KEY environment variable or add to config.json
    - Install dependencies: pip install -r requirements.txt
"""

import asyncio
import sys
import signal
import threading
import io

from config import config
from audio_capture import AudioCapture
from batch_transcriber import BatchTranscriber
from hotkey_handler import HotkeyHandler
from text_injector import TextInjector, VoiceCommands
from arc_reactor_ui import ArcReactorUI
from tray_app import TrayApp


class VoiceTypingApp:
    """Main Voice Typing application controller (Batch Mode)."""
    
    def __init__(self):
        """Initialize the Voice Typing application."""
        self._audio_capture: AudioCapture = None
        self._transcriber: BatchTranscriber = None
        self._hotkey_handler: HotkeyHandler = None
        self._text_injector: TextInjector = None
        self._ui: ArcReactorUI = None
        self._tray: TrayApp = None
        
        self._is_recording = False
        self._running = False
        self._audio_buffer = io.BytesIO()  # Buffer to store recorded audio
        self._buffer_lock = threading.Lock()
    
    def _validate_config(self) -> bool:
        """Validate configuration."""
        if not config.api_key:
            print("Error: No API key found!")
            print("Set GEMINI_API_KEY environment variable or add to config.json")
            return False
        return True
    
    def _initialize_components(self) -> None:
        """Initialize all application components."""
        print("Initializing Voice Typing (Batch Mode)...")
        
        # Audio capture
        self._audio_capture = AudioCapture(device_index=config.audio_device)
        
        # Batch transcriber (higher accuracy)
        self._transcriber = BatchTranscriber(api_key=config.api_key)
        self._transcriber.set_transcription_callback(self._on_transcription)
        self._transcriber.set_status_callback(self._on_status)
        
        # Hotkey handler
        self._hotkey_handler = HotkeyHandler(hotkey=config.hotkey)
        
        # Text injector
        self._text_injector = TextInjector(typing_delay=config.typing_delay)
        
        # Arc Reactor UI (Iron Man Visualizer)
        self._ui = ArcReactorUI()
        
        # System tray
        self._tray = TrayApp()
    
    def _on_transcription(self, text: str) -> None:
        """
        Handle transcription result.
        
        Args:
            text: Transcribed text
        """
        if not text:
            return
        
        print(f"Transcribed: {text}")
        
        # Update waveform status
        if self._ui:
            self._ui.set_status(f"✓ {text[:40]}..." if len(text) > 40 else f"✓ {text}")
        
        # Process voice commands
        processed_text = VoiceCommands.process_text(text)
        
        # Type the text
        if self._text_injector:
            self._text_injector.type_text(processed_text)
    
    def _on_status(self, status: str) -> None:
        """
        Handle status update.
        
        Args:
            status: Status message
        """
        print(f"Status: {status}")
        
        if self._ui:
            self._ui.set_status(status)
    
    def _toggle_recording(self) -> None:
        """Toggle recording on/off."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()
    
    def _start_recording(self) -> None:
        """Start voice recording."""
        if self._is_recording:
            return
        
        print("Recording started... (Press Win+H to stop)")
        self._is_recording = True
        
        # Clear audio buffer
        with self._buffer_lock:
            self._audio_buffer = io.BytesIO()
        
        # Update UI
        if self._ui:
            self._ui.set_recording(True)
        if self._tray:
            self._tray.set_recording(True)
        
        # Start audio capture - audio goes to buffer AND waveform
        def on_audio(data: bytes):
            with self._buffer_lock:
                self._audio_buffer.write(data)
            # Update waveform visualization
            if self._ui:
                self._ui.update_amplitude(data)
        
        self._audio_capture.start(on_audio)
    
    def _stop_recording(self) -> None:
        """Stop recording and transcribe."""
        if not self._is_recording:
            return
        
        print("Recording stopped. Processing...")
        self._is_recording = False
        
        # Stop audio capture
        if self._audio_capture:
            self._audio_capture.stop()
        
        # Update UI
        if self._ui:
            self._ui.set_recording(False)
            self._ui.set_status("Processing...")
        if self._tray:
            self._tray.set_recording(False)
            self._tray.set_status('processing')
        
        # Get recorded audio
        with self._buffer_lock:
            audio_bytes = self._audio_buffer.getvalue()
        
        if not audio_bytes:
            print("No audio recorded!")
            if self._ui:
                self._ui.set_status("No audio recorded")
            return
        
        print(f"Recorded {len(audio_bytes)} bytes of audio")
        
        # DEBUG: Save audio to verify what's being recorded
        import wave
        debug_file = "last_recording.wav"
        try:
            with wave.open(debug_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_bytes)
            print(f"DEBUG: Saved audio to {debug_file} - play to verify!")
        except Exception as e:
            print(f"DEBUG: Could not save audio: {e}")
        
        # Transcribe in background thread
        def transcribe():
            result = self._transcriber.transcribe_sync(audio_bytes)
            if result:
                print(f"Transcription complete: {result[:50]}...")
            else:
                print("Transcription failed or empty")
            
            # Reset UI
            if self._tray:
                self._tray.set_status('idle')
        
        threading.Thread(target=transcribe, daemon=True).start()
    
    def _on_exit(self) -> None:
        """Handle application exit."""
        print("Exiting Voice Typing...")
        self.stop()
    
    def start(self) -> None:
        """Start the Voice Typing application."""
        # Validate config
        if not self._validate_config():
            sys.exit(1)
        
        # Initialize components
        self._initialize_components()
        self._running = True
        
        # Start waveform UI
        if self._ui:
            self._ui.start()
        
        # Start system tray
        if self._tray:
            self._tray.start(
                on_toggle=self._toggle_recording,
                on_exit=self._on_exit
            )
            self._tray.show_notification(
                "Voice Typing",
                f"Press {config.hotkey.upper().replace('+', ' + ')} to start/stop recording"
            )
        
        # Start hotkey listener
        if self._hotkey_handler:
            self._hotkey_handler.start(self._toggle_recording)
        
        print(f"\nVoice Typing started! (Batch Mode)")
        print(f"Press {config.hotkey.upper()} to start recording")
        print(f"Press {config.hotkey.upper()} again to stop and transcribe")
        print("The app is running in the system tray.\n")
    
    def stop(self) -> None:
        """Stop the Voice Typing application."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop recording if active
        if self._is_recording:
            self._audio_capture.stop()
            self._is_recording = False
        
        # Stop components
        if self._hotkey_handler:
            self._hotkey_handler.stop()
        
        if self._ui:
            self._ui.stop()
        
        if self._tray:
            self._tray.stop()
        
        print("Voice Typing stopped.")
    
    def run(self) -> None:
        """Run the application (blocking)."""
        self.start()
        
        # Handle Ctrl+C
        def signal_handler(sig, frame):
            print("\nReceived interrupt signal...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep main thread alive
        try:
            while self._running:
                import time
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()


def main():
    """Main entry point."""
    print("=" * 50)
    print("  Voice Typing - Batch Mode")
    print("  Powered by Google Gemini API")
    print("=" * 50)
    print()
    
    app = VoiceTypingApp()
    app.run()


if __name__ == "__main__":
    main()
