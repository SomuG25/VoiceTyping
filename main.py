"""
Voice Typing Application — Main Entry Point

Real-time voice-to-text using local faster-whisper.
Double-tap Space  → start / stop recording + type text
Triple-tap Space  → retry last recording

No API key, no OS conflicts — runs entirely offline on your PC.
"""

import sys
import wave
import signal
import threading
import time
from pathlib import Path
from datetime import datetime

from config import config
from audio_capture import AudioCapture
from local_transcriber import LocalTranscriber
from hotkey_handler import HotkeyHandler
from text_injector import TextInjector, VoiceCommands
from arc_reactor_ui import ArcReactorUI
from tray_app import TrayApp


RECORDINGS_DIR = Path(__file__).parent / "recordings"


class VoiceTypingApp:
    """Main Voice Typing application controller."""

    def __init__(self):
        self._audio_capture: AudioCapture = None
        self._transcriber: LocalTranscriber = None
        self._hotkey_handler: HotkeyHandler = None
        self._text_injector: TextInjector = None
        self._ui: ArcReactorUI = None
        self._tray: TrayApp = None

        self._is_recording = False
        self._running = False
        self._audio_buffer: list = []

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _initialize_components(self) -> None:
        print("Initializing Voice Typing (Local Whisper Mode)...")

        RECORDINGS_DIR.mkdir(exist_ok=True)

        self._audio_capture = AudioCapture(device_index=config.audio_device)

        self._transcriber = LocalTranscriber(
            model_size=config.whisper_model,
            device=config.whisper_device,
            compute_type=config.whisper_compute_type,
            vad_threshold=config.vad_threshold,
        )
        threading.Thread(target=self._transcriber.load_model, daemon=True).start()

        self._hotkey_handler = HotkeyHandler()
        self._hotkey_handler.register("toggle", self._toggle_recording)
        self._hotkey_handler.register("retry", self._retry_last)

        self._text_injector = TextInjector(typing_delay=config.typing_delay)
        self._ui = ArcReactorUI()
        self._tray = TrayApp()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _toggle_recording(self) -> None:
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        if self._is_recording:
            return

        print("\n[REC] STARTED — speak now (double-space to stop)")
        self._is_recording = True
        self._audio_buffer = []
        start_time = time.time()

        if self._ui:
            self._ui.set_recording(True)
            self._ui.set_core_text("REC")
        if self._tray:
            self._tray.set_recording(True)

        def on_audio(data: bytes):
            self._audio_buffer.append(data)
            if self._ui:
                self._ui.update_amplitude(data)

        self._audio_capture.start(on_audio)

        # Timer in core
        def timer_loop():
            while self._is_recording:
                elapsed = int(time.time() - start_time)
                mins, secs = divmod(elapsed, 60)
                if self._ui:
                    self._ui.set_core_text(f"{mins}:{secs:02d}")
                time.sleep(0.25)

        threading.Thread(target=timer_loop, daemon=True).start()

    def _stop_recording(self) -> None:
        if not self._is_recording:
            return

        print("[REC] STOPPED — transcribing...")
        self._is_recording = False

        if self._audio_capture:
            self._audio_capture.stop()

        if self._ui:
            self._ui.set_core_text("...")

        self._save_and_transcribe()

    # ------------------------------------------------------------------
    # Save + transcribe
    # ------------------------------------------------------------------

    def _save_and_transcribe(self) -> None:
        if not self._audio_buffer:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_wav = RECORDINGS_DIR / f"rec_{timestamp}.wav"
        legacy_wav = Path("last_recording.wav")

        try:
            for path in (legacy_wav, archive_wav):
                with wave.open(str(path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    for chunk in self._audio_buffer:
                        wf.writeframes(chunk)
            duration = sum(len(c) for c in self._audio_buffer) / (16000 * 2)
            print(f"[Save] {archive_wav.name} ({duration:.1f}s)")
        except Exception as e:
            print(f"[Save] Error: {e}")

        if self._ui:
            self._ui.set_recording(False)
        if self._tray:
            self._tray.set_recording(False)
            self._tray.set_status("processing")

        audio_data = b"".join(self._audio_buffer)

        def finish():
            text = self._transcriber.transcribe(audio_data)
            if text:
                txt_path = archive_wav.with_suffix(".txt")
                try:
                    txt_path.write_text(text, encoding="utf-8")
                except Exception:
                    pass
                self._type_text(text)

            if self._tray:
                self._tray.set_status("idle")
            if self._ui:
                self._ui.hide_after_delay(1000)

        threading.Thread(target=finish, daemon=True).start()

    def _type_text(self, text: str) -> None:
        print(f"[App] Typed: {text}")
        processed = VoiceCommands.process_text(text)
        if self._text_injector:
            self._text_injector.type_text(processed)

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    def _retry_last(self) -> None:
        if self._is_recording:
            print("[Retry] Busy — recording in progress")
            return

        wav_path = Path("last_recording.wav")
        if not wav_path.exists():
            print("[Retry] Nothing to retry — record first")
            if self._ui:
                self._ui.show()
                self._ui.set_core_text("N/A")
                self._ui.hide_after_delay(1500)
            return

        print("[Retry] Re-transcribing...")
        if self._ui:
            self._ui.show()

        def do_retry():
            text = self._transcriber.transcribe_wav_file(str(wav_path))
            if text:
                self._type_text(text)
            else:
                print("[Retry] No speech detected")
            if self._ui:
                self._ui.hide_after_delay(1000)

        threading.Thread(target=do_retry, daemon=True).start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_exit(self) -> None:
        print("Exiting Voice Typing...")
        self.stop()

    def start(self) -> None:
        self._initialize_components()
        self._running = True

        if self._ui:
            self._ui.start()

        if self._tray:
            self._tray.start(
                on_toggle=self._toggle_recording,
                on_retry=self._retry_last,
                on_exit=self._on_exit,
            )
            self._tray.show_notification(
                "Voice Typing",
                "Double-Space = record  |  Triple-Space = retry",
            )

        if self._hotkey_handler:
            self._hotkey_handler.start()

        num_recs = len(list(RECORDINGS_DIR.glob("*.wav")))
        print(f"\nVoice Typing ready!")
        print(f"  Double-tap SPACE  → start / stop recording")
        print(f"  Triple-tap SPACE  → retry last recording")
        print(f"  Model: {config.whisper_model}  |  Saved: {num_recs} recordings")
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

        if self._ui:
            self._ui.stop()
        if self._tray:
            self._tray.stop()

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


def main():
    print("=" * 50)
    print("  Voice Typing")
    print("  Local faster-whisper — runs offline on your PC")
    print("=" * 50)
    print()

    app = VoiceTypingApp()
    app.run()


if __name__ == "__main__":
    main()
