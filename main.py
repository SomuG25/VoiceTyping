"""
Voice Typing Application — Main Entry Point

Real-time voice-to-text using Gemini 3.1 Flash Live (Native Audio).
Press Win+H to start/stop recording.
Press Win+F4 to re-transcribe the last recording.

Free API key: https://aistudio.google.com/
"""

import sys
import wave
import signal
import threading
import asyncio
import time
from pathlib import Path

from config import config
from audio_capture import AudioCapture
from gemini_transcriber import GeminiTranscriber
from hotkey_handler import HotkeyHandler
from text_injector import TextInjector, VoiceCommands
from arc_reactor_ui import ArcReactorUI
from tray_app import TrayApp
from batch_retry import transcribe_wav_file


class VoiceTypingApp:
    """Main Voice Typing application controller."""

    def __init__(self):
        self._audio_capture: AudioCapture = None
        self._transcriber: GeminiTranscriber = None
        self._hotkey_handler: HotkeyHandler = None
        self._text_injector: TextInjector = None
        self._ui: ArcReactorUI = None
        self._tray: TrayApp = None

        self._is_recording = False
        self._running = False

        # Dedicated asyncio loop for the Gemini Live WebSocket
        self._loop: asyncio.AbstractEventLoop = None
        self._loop_thread: threading.Thread = None

        # Audio buffer — filled while recording, written to WAV on stop
        self._audio_buffer: list = []

    # -------------------------------------------------------------------------
    # Setup
    # -------------------------------------------------------------------------

    def _validate_config(self) -> bool:
        if not config.api_key:
            print("Error: No API key found!")
            print(f"Please add GEMINI_API_KEY to: {Path(__file__).parent / '.env'}")
            return False
        return True

    def _initialize_components(self) -> None:
        """Initialize all components and connect to Gemini once."""
        print("Initializing Voice Typing (Native Audio Mode)...")

        # Audio capture
        self._audio_capture = AudioCapture(device_index=config.audio_device)

        # Background asyncio loop for Gemini Live API WebSocket
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True,
            name="GeminiLiveLoop",
        )
        self._loop_thread.start()

        # Transcriber — persistent session
        self._transcriber = GeminiTranscriber(
            api_key=config.api_key,
            model=config.transcription_model,
        )
        self._transcriber.set_transcription_callback(self._on_transcription)
        self._transcriber.set_status_callback(self._on_status)
        self._transcriber.set_interim_callback(self._on_interim)

        # Connect ONCE at startup (no per-recording WebSocket overhead)
        print("Connecting to Gemini Live API...")
        future = asyncio.run_coroutine_threadsafe(
            self._transcriber.connect(), self._loop
        )
        try:
            connected = future.result(timeout=15)
            if not connected:
                print("Warning: Could not connect to Gemini at startup.")
                print("         Will retry automatically on first recording.")
        except Exception as e:
            print(f"Warning: Startup connection error: {e}")

        # Hotkey handler (multi-hotkey)
        self._hotkey_handler = HotkeyHandler()
        self._hotkey_handler.register(config.hotkey, self._toggle_recording)
        self._hotkey_handler.register(config.retry_hotkey, self._retry_last_recording)

        # Text injector
        self._text_injector = TextInjector(typing_delay=config.typing_delay)

        # Arc Reactor UI
        self._ui = ArcReactorUI()

        # System tray
        self._tray = TrayApp()

    # -------------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------------

    def _on_transcription(self, text: str) -> None:
        """Handle final transcription — type it into the active window."""
        if not text:
            return

        print(f"[App] Typed: {text}")

        if self._ui:
            preview = f"✓ {text[:40]}..." if len(text) > 40 else f"✓ {text}"
            self._ui.set_status(preview)

        processed = VoiceCommands.process_text(text)
        if self._text_injector:
            self._text_injector.type_text(processed)

    def _on_interim(self, chunk: str) -> None:
        """Handle interim transcription chunks — show live in Arc Reactor UI."""
        if self._ui:
            self._ui.set_status(chunk)

    def _on_status(self, status: str) -> None:
        """Handle status updates from transcriber."""
        print(f"Status: {status}")
        if self._ui:
            self._ui.set_status(status)

    # -------------------------------------------------------------------------
    # Recording control
    # -------------------------------------------------------------------------

    def _toggle_recording(self) -> None:
        """Win+H: toggle recording on/off."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        """Start recording — instant since session is already connected."""
        if self._is_recording:
            return

        print("\nRecording started — speak now (Win+H to stop)")
        self._is_recording = True
        self._audio_buffer = []  # reset audio buffer for this session

        if self._ui:
            self._ui.set_recording(True)
        if self._tray:
            self._tray.set_recording(True)

        # Tell transcriber to begin accepting audio (instant, no WebSocket cost)
        self._transcriber.start_recording()

        # Audio callback: stream to Gemini + buffer for retry save
        def on_audio(data: bytes):
            self._transcriber.send_audio_sync(data)
            self._audio_buffer.append(data)
            if self._ui:
                self._ui.update_amplitude(data)

        self._audio_capture.start(on_audio)

    def _stop_recording(self) -> None:
        """Stop recording, save WAV, collect final transcription."""
        if not self._is_recording:
            return

        print("Recording stopped — processing...")
        self._is_recording = False

        # Stop audio capture
        if self._audio_capture:
            self._audio_capture.stop()

        # Save audio buffer as WAV for potential retry
        self._save_last_recording()

        if self._ui:
            self._ui.set_recording(False)
            self._ui.set_status("Processing...")
        if self._tray:
            self._tray.set_recording(False)
            self._tray.set_status("processing")

        # Flush final transcription in background (keeps session alive)
        def finish():
            self._transcriber.stop_recording()  # waits for turn_complete
            if self._tray:
                self._tray.set_status("idle")

        threading.Thread(target=finish, daemon=True).start()

    # -------------------------------------------------------------------------
    # Last recording save + retry
    # -------------------------------------------------------------------------

    def _save_last_recording(self) -> None:
        """Write the current audio buffer to last_recording.wav."""
        if not self._audio_buffer:
            return
        try:
            wav_path = Path(__file__).parent / config.last_recording_path
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)   # 16-bit PCM
                wf.setframerate(16000)  # 16 kHz
                for chunk in self._audio_buffer:
                    wf.writeframes(chunk)
            duration = sum(len(c) for c in self._audio_buffer) / (16000 * 2)
            print(f"[Retry] Saved {wav_path.name} ({duration:.1f}s)")
        except Exception as e:
            print(f"[Retry] Could not save recording: {e}")

    def _retry_last_recording(self) -> None:
        """Win+F4: re-transcribe last_recording.wav using batch API."""
        if self._is_recording:
            print("[Retry] Cannot retry while recording is active")
            return

        wav_path = Path(__file__).parent / config.last_recording_path
        if not wav_path.exists():
            print("[Retry] No recording to retry (record something first)")
            if self._ui:
                self._ui.set_status("No recording to retry")
            return

        print(f"[Retry] Re-transcribing {wav_path.name} (Win+F4)...")
        if self._ui:
            self._ui.set_status("Retrying...")
            self._ui.show()

        def do_retry():
            text = transcribe_wav_file(str(wav_path), config.api_key)
            if text:
                processed = VoiceCommands.process_text(text)
                if self._text_injector:
                    self._text_injector.type_text(processed)
                if self._ui:
                    preview = f"✓ {text[:40]}..." if len(text) > 40 else f"✓ {text}"
                    self._ui.set_status(preview)
            else:
                print("[Retry] No text returned — check recording and API key")
                if self._ui:
                    self._ui.set_status("Retry failed")

        threading.Thread(target=do_retry, daemon=True).start()

    # -------------------------------------------------------------------------
    # App lifecycle
    # -------------------------------------------------------------------------

    def _on_exit(self) -> None:
        print("Exiting Voice Typing...")
        self.stop()

    def start(self) -> None:
        if not self._validate_config():
            sys.exit(1)

        self._initialize_components()
        self._running = True

        if self._ui:
            self._ui.start()

        if self._tray:
            self._tray.start(on_toggle=self._toggle_recording, on_exit=self._on_exit)
            hotkey_display = config.hotkey.upper().replace("+", " + ")
            self._tray.show_notification(
                "Voice Typing",
                f"{hotkey_display} to record  |  Win+F4 to retry",
            )

        if self._hotkey_handler:
            self._hotkey_handler.start()

        print(f"\nVoice Typing ready!")
        print(f"  {config.hotkey.upper()}   → start / stop recording")
        print(f"  WIN+F4  → retry last recording")
        print("App is running in the system tray.\n")

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False

        if self._is_recording:
            self._audio_capture.stop()
            self._is_recording = False

        if self._hotkey_handler:
            self._hotkey_handler.stop()

        # Disconnect from Gemini cleanly
        if self._loop and self._transcriber:
            future = asyncio.run_coroutine_threadsafe(
                self._transcriber.disconnect(), self._loop
            )
            try:
                future.result(timeout=5)
            except Exception:
                pass

        if self._ui:
            self._ui.stop()
        if self._tray:
            self._tray.stop()

        # Stop the asyncio loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        print("Voice Typing stopped.")

    def run(self) -> None:
        self.start()

        def signal_handler(sig, frame):
            print("\nInterrupt received...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()


# -------------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------------

def main():
    print("=" * 50)
    print("  Voice Typing")
    print("  Gemini 3.1 Flash Live — Native Audio")
    print("=" * 50)
    print()

    app = VoiceTypingApp()
    app.run()


if __name__ == "__main__":
    main()
