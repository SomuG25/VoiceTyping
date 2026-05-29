"""
Space-tap triggers for Voice Typing.
No OS conflicts — just tap space.

Double-tap Space  → toggle recording
Triple-tap Space  → retry last recording
"""

import time
import threading
from typing import Callable, Optional

import keyboard


DOUBLE_WINDOW = 0.35   # max gap for double-tap
TRIPLE_WINDOW = 0.45   # max gap for third tap


class HotkeyHandler:
    """Detects double-tap and triple-tap Space. Zero OS conflicts.

    Space still works normally for typing — only rapid multi-taps trigger actions.
    """

    def __init__(self):
        self._running = False
        self._on_toggle: Optional[Callable[[], None]] = None
        self._on_retry: Optional[Callable[[], None]] = None
        self._pending: Optional[threading.Timer] = None
        self._last_tap = 0.0
        self._tap_count = 0

    def register(self, action: str, callback: Callable[[], None]) -> None:
        if action == "toggle":
            self._on_toggle = callback
        elif action == "retry":
            self._on_retry = callback

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        keyboard.on_press_key("space", self._on_space, suppress=False)
        print("[Hotkey] Double-Space = record  |  Triple-Space = retry")

    def stop(self) -> None:
        self._running = False
        self._cancel_pending()
        keyboard.unhook_all()

    def _cancel_pending(self):
        if self._pending:
            self._pending.cancel()
            self._pending = None

    def _on_space(self, event) -> None:
        now = time.time()
        gap = now - self._last_tap
        self._last_tap = now

        if gap > DOUBLE_WINDOW:
            # Fresh start — first tap of a new sequence
            self._cancel_pending()
            self._tap_count = 1
            return

        # Fast tap (within window)
        self._tap_count += 1

        if self._tap_count == 2:
            # Could be double-tap or start of triple-tap
            # Wait to see if third tap arrives
            self._cancel_pending()
            self._pending = threading.Timer(TRIPLE_WINDOW, self._fire_toggle)
            self._pending.daemon = True
            self._pending.start()

        elif self._tap_count == 3:
            # Triple-tap confirmed
            self._cancel_pending()
            self._tap_count = 0
            if self._on_retry:
                threading.Thread(target=self._on_retry, daemon=True).start()

    def _fire_toggle(self):
        """Timer expired — no third tap, so double-tap = toggle."""
        self._pending = None
        self._tap_count = 0
        if self._on_toggle:
            self._on_toggle()
