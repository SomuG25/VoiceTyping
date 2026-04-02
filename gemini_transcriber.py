"""
Gemini Live API transcription module.

Architecture:
- connect() once at app start → persistent session
- start_recording() / stop_recording() → toggle audio, no WebSocket overhead
- Session watchdog reconnects at 9 min (before 10-min forced disconnect)
- Auto-reconnect with exponential backoff on failures
- Thread-safe audio sending via loop.call_soon_threadsafe
"""

import asyncio
import time
from typing import Callable, Optional
from google import genai
from google.genai import types

# gemini-live-2.5-flash-native-audio = GA (stable, correct official name) ✅
# gemini-3.1-flash-live-preview        = Preview (inconsistent, skip for now)
DEFAULT_MODEL = "gemini-live-2.5-flash-native-audio"

# Reconnect proactively before the 10-minute hard session limit
SESSION_MAX_SECONDS = 9 * 60  # 9 minutes
MAX_RECONNECT_ATTEMPTS = 3


class GeminiTranscriber:
    """Persistent real-time speech-to-text using Gemini Live API.

    Usage:
        t = GeminiTranscriber(api_key)
        t.set_transcription_callback(fn)
        await t.connect()          # call once at app start

        t.start_recording()        # on Win+H press (instant, no WebSocket cost)
        ...stream audio via send_audio_sync()...
        t.stop_recording()         # on Win+H press again

        await t.disconnect()       # on app exit only
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._api_key = api_key
        self._model = model

        # Session state
        self._client: Optional[genai.Client] = None
        self._session = None
        self._session_context = None
        self._is_connected = False
        self._running = False
        self._recording = False
        self._session_start_time: float = 0.0

        # Callbacks
        self._on_transcription: Optional[Callable[[str], None]] = None
        self._on_status: Optional[Callable[[str], None]] = None
        self._on_interim: Optional[Callable[[str], None]] = None  # live UI preview

        # Async primitives (created inside the event loop in connect())
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._audio_queue: Optional[asyncio.Queue] = None
        self._turn_complete_event: Optional[asyncio.Event] = None

        # Background tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._send_task: Optional[asyncio.Task] = None
        self._watchdog_task: Optional[asyncio.Task] = None

        # Transcription buffer — collects VAD chunks before emitting
        self._transcription_buffer: list = []

    # -------------------------------------------------------------------------
    # Config
    # -------------------------------------------------------------------------

    def _get_config(self) -> dict:
        """Live API session config.

        IMPORTANT: Native audio models MUST use response_modalities=["AUDIO"].
        Setting TEXT causes a 1011 internal error.

        VAD tuned to 600ms silence so pauses trigger faster than default ~1500ms.
        """
        return {
            "response_modalities": ["AUDIO"],
            "input_audio_transcription": {},
            "realtime_input_config": {
                "automatic_activity_detection": {
                    "disabled": False,
                    "end_of_speech_sensitivity": "END_SENSITIVITY_HIGH",
                    "silence_duration_ms": 600,
                }
            },
        }

    # -------------------------------------------------------------------------
    # Internal connect / disconnect helpers
    # -------------------------------------------------------------------------

    async def _do_connect(self) -> bool:
        """Open a new WebSocket session."""
        try:
            self._client = genai.Client(api_key=self._api_key)
            self._session_context = self._client.aio.live.connect(
                model=self._model,
                config=self._get_config(),
            )
            self._session = await self._session_context.__aenter__()
            self._is_connected = True
            self._session_start_time = time.time()
            print(f"[Gemini] Connected — {self._model}")
            return True
        except Exception as e:
            print(f"[Gemini] Connection error: {e}")
            self._is_connected = False
            return False

    async def _do_disconnect(self) -> None:
        """Close the WebSocket session cleanly."""
        self._is_connected = False
        if self._session_context:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._session_context = None
            self._session = None

    async def _cancel_tasks(self) -> None:
        """Cancel all background asyncio tasks."""
        for task in [self._receive_task, self._send_task, self._watchdog_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._receive_task = None
        self._send_task = None
        self._watchdog_task = None

    def _start_background_tasks(self) -> None:
        """Spin up receive / send / watchdog tasks."""
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._send_task = asyncio.create_task(self._send_loop())
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())

    # -------------------------------------------------------------------------
    # Reconnect
    # -------------------------------------------------------------------------

    async def _reconnect(self, reason: str = "") -> bool:
        """Reconnect with exponential backoff. Keeps session alive transparently."""
        if reason:
            print(f"[Gemini] Reconnecting ({reason})...")
        if self._on_status:
            self._on_status("Reconnecting...")

        await self._cancel_tasks()
        await self._do_disconnect()

        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            delay = 2 ** (attempt - 1)  # 1s → 2s → 4s
            print(f"[Gemini] Reconnect attempt {attempt}/{MAX_RECONNECT_ATTEMPTS}"
                  f" (wait {delay}s)...")
            await asyncio.sleep(delay)

            if await self._do_connect():
                # Reset async queue and event for new session
                self._audio_queue = asyncio.Queue(maxsize=100)
                self._turn_complete_event = asyncio.Event()
                self._start_background_tasks()
                print("[Gemini] Reconnected successfully")
                if self._on_status:
                    self._on_status("Ready")
                return True

        print("[Gemini] All reconnect attempts failed")
        if self._on_status:
            self._on_status("Connection lost — restart app")
        return False

    # -------------------------------------------------------------------------
    # Public lifecycle
    # -------------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect once at app start. Stays connected until disconnect()."""
        self._loop = asyncio.get_event_loop()
        self._audio_queue = asyncio.Queue(maxsize=100)
        self._turn_complete_event = asyncio.Event()

        if not await self._do_connect():
            if self._on_status:
                self._on_status("Connection failed")
            return False

        self._running = True
        self._start_background_tasks()

        if self._on_status:
            self._on_status("Ready")
        return True

    async def disconnect(self) -> None:
        """Full shutdown — call only on app exit."""
        self._running = False
        self._recording = False
        await self._cancel_tasks()
        await self._do_disconnect()
        self._loop = None
        if self._on_status:
            self._on_status("Disconnected")

    # -------------------------------------------------------------------------
    # Recording control (called from main thread via run_coroutine_threadsafe)
    # -------------------------------------------------------------------------

    async def _start_recording_async(self) -> None:
        """Begin a recording session (instant — no WebSocket overhead)."""
        self._transcription_buffer.clear()
        if self._turn_complete_event:
            self._turn_complete_event.clear()
        self._recording = True
        print("[Gemini] Recording started")

    async def _stop_recording_async(self) -> None:
        """End a recording session, emit ALL buffered text at once, keep session alive."""
        self._recording = False

        if not (self._session and self._is_connected):
            print("[Gemini] Not connected — cannot stop recording")
            return

        try:
            if self._turn_complete_event:
                self._turn_complete_event.clear()

            await self._session.send_realtime_input(audio_stream_end=True)
            print("[Gemini] Audio stream ended — waiting for final chunk...")

            # Wait for the last turn_complete after stream end (up to 3s)
            try:
                await asyncio.wait_for(self._turn_complete_event.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                print("[Gemini] Timeout — emitting whatever was buffered")

            # Emit ALL text collected during the recording as a single string
            self._emit_transcription()

        except Exception as e:
            print(f"[Gemini] Stop recording error: {e}")
            self._emit_transcription()  # best-effort flush on error

    def start_recording(self) -> None:
        """Thread-safe: begin recording. Call from audio capture / main thread."""
        if self._loop and self._is_connected:
            asyncio.run_coroutine_threadsafe(
                self._start_recording_async(), self._loop
            )
        else:
            print("[Gemini] Cannot start recording — not connected")

    def stop_recording(self) -> None:
        """Thread-safe blocking: stop recording and wait for transcription."""
        if self._loop and self._is_connected:
            future = asyncio.run_coroutine_threadsafe(
                self._stop_recording_async(), self._loop
            )
            try:
                future.result(timeout=6)
            except Exception as e:
                print(f"[Gemini] stop_recording error: {e}")
        else:
            print("[Gemini] Cannot stop recording — not connected")

    # -------------------------------------------------------------------------
    # Audio sending
    # -------------------------------------------------------------------------

    def send_audio_sync(self, audio_bytes: bytes) -> None:
        """Thread-safe: enqueue PCM audio from the audio capture thread.

        Uses loop.call_soon_threadsafe because asyncio.Queue is NOT thread-safe.
        """
        if (self._is_connected and self._recording
                and self._loop and self._audio_queue):
            try:
                self._loop.call_soon_threadsafe(
                    self._audio_queue.put_nowait, audio_bytes
                )
            except asyncio.QueueFull:
                pass  # Drop chunk — better than blocking the audio thread

    # -------------------------------------------------------------------------
    # Background loops
    # -------------------------------------------------------------------------

    async def _send_loop(self) -> None:
        """Drain audio queue and stream PCM chunks to Gemini."""
        while self._running:
            try:
                try:
                    audio_bytes = await asyncio.wait_for(
                        self._audio_queue.get(), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue

                if self._session and audio_bytes and self._recording:
                    await self._session.send_realtime_input(
                        audio=types.Blob(
                            data=audio_bytes,
                            mime_type="audio/pcm;rate=16000",
                        )
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Gemini] Send error: {e}")
                await asyncio.sleep(0.1)

    async def _receive_loop(self) -> None:
        """Receive transcription messages from Gemini.

        HOW IT WORKS:
        - Server-side VAD detects natural pauses (silence_duration_ms = 600ms)
        - input_transcription chunks arrive after each pause → buffered
        - turn_complete fires after each utterance → we only set the event
        - ALL buffered text is emitted as ONE string when Win+H stop is pressed
        """
        while self._running and self._is_connected:
            try:
                async for msg in self._session.receive():
                    if not self._running:
                        break

                    # GoAway: server about to force-disconnect
                    if hasattr(msg, "go_away") and msg.go_away:
                        print("[Gemini] GoAway received — reconnecting...")
                        asyncio.create_task(self._reconnect("server go_away"))
                        return

                    if msg.server_content:
                        # Interim chunk → show in UI IMMEDIATELY while speaking
                        if msg.server_content.input_transcription:
                            text = msg.server_content.input_transcription.text
                            if text and text.strip():
                                self._transcription_buffer.append(text.strip())
                                print(f"[Chunk] {text.strip()}")
                                if self._on_interim:
                                    self._on_interim(text.strip())

                        # VAD pause detected — keep buffering, DON'T type yet
                        # All text will type at once on Win+H stop
                        if msg.server_content.turn_complete:
                            print("[Gemini] VAD pause — buffering (types on Win+H stop)")
                            if self._turn_complete_event:
                                self._turn_complete_event.set()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Gemini] Receive error: {e}")
                if self._running:
                    await self._reconnect(f"receive error: {e}")
                    return

    async def _watchdog_loop(self) -> None:
        """Proactively reconnect before the 10-minute hard session limit.

        Gemini Live API WebSocket sessions are capped at ~10 minutes.
        We reconnect at 9 minutes to prevent mid-recording disconnects.
        """
        while self._running:
            await asyncio.sleep(60)  # check every minute
            if not self._running:
                break

            elapsed = time.time() - self._session_start_time
            if elapsed >= SESSION_MAX_SECONDS and not self._recording:
                print(f"[Gemini] Session at {elapsed/60:.1f} min — proactive reconnect")
                await self._reconnect("session lifetime limit")

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _emit_transcription(self) -> None:
        """Assemble buffered chunks into final text and fire callback."""
        if self._transcription_buffer:
            full_text = " ".join(self._transcription_buffer).strip()
            self._transcription_buffer.clear()
            if full_text and self._on_transcription:
                print(f"[Gemini] → \"{full_text}\"")
                self._on_transcription(full_text)
        else:
            print("[Gemini] No transcription (buffer empty)")

    # -------------------------------------------------------------------------
    # Callback setters
    # -------------------------------------------------------------------------

    def set_transcription_callback(self, fn: Callable[[str], None]) -> None:
        """Called with final text after each VAD-detected utterance."""
        self._on_transcription = fn

    def set_status_callback(self, fn: Callable[[str], None]) -> None:
        """Called with status strings (Ready, Reconnecting, etc.)."""
        self._on_status = fn

    def set_interim_callback(self, fn: Callable[[str], None]) -> None:
        """Called with each interim chunk for live UI preview."""
        self._on_interim = fn

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def is_recording(self) -> bool:
        return self._recording


# -------------------------------------------------------------------------
# Connection test
# -------------------------------------------------------------------------

async def test_connection(api_key: str) -> bool:
    """Test connection to Gemini Live API."""
    print("Testing Gemini Live API connection...")

    t = GeminiTranscriber(api_key)
    t.set_status_callback(lambda s: print(f"Status: {s}"))
    t.set_transcription_callback(lambda s: print(f"Transcription: {s}"))

    if await t.connect():
        print("Connection successful!")
        await asyncio.sleep(2)
        await t.disconnect()
        return True

    print("Connection failed!")
    return False


if __name__ == "__main__":
    import os
    from config import config
    api_key = config.api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Error: Set GEMINI_API_KEY in .env file")
    else:
        asyncio.run(test_connection(api_key))
