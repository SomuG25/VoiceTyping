"""
Global hotkey handler for Voice Typing application.

Supports multiple simultaneous hotkeys, each with its own callback.
Uses pynput for system-wide key detection.

Default hotkeys:
  win+h           → toggle recording
  ctrl+shift+r    → retry last recording
"""

import threading
from typing import Callable, Dict, Optional, Set
from pynput import keyboard


class HotkeyHandler:
    """Handles multiple global hotkeys with independent callbacks."""

    def __init__(self):
        """Initialize the hotkey handler (no hotkeys registered yet)."""
        self._listener: Optional[keyboard.Listener] = None
        self._pressed_keys: Set[str] = set()
        self._running = False
        # Map of frozenset(required_keys) → callback
        self._hotkeys: Dict[frozenset, Callable[[], None]] = {}

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        """Register a hotkey and its callback.

        Args:
            hotkey: Hotkey string like "win+h", "ctrl+shift+r"
            callback: Function to call when the hotkey is pressed
        """
        keys = self._parse_hotkey(hotkey)
        self._hotkeys[frozenset(keys)] = callback
        print(f"[Hotkey] Registered: {hotkey.lower()}")

    def unregister(self, hotkey: str) -> None:
        """Unregister a hotkey."""
        keys = frozenset(self._parse_hotkey(hotkey))
        self._hotkeys.pop(keys, None)

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start listening for all registered hotkeys."""
        if self._running:
            return

        self._running = True
        self._pressed_keys.clear()

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def _on_press(self, key) -> None:
        """Track pressed keys and fire callbacks when combinations match."""
        key_name = self._normalize_key(key)
        if not key_name:
            return

        self._pressed_keys.add(key_name)

        # Check every registered hotkey
        for required, callback in self._hotkeys.items():
            if required.issubset(self._pressed_keys):
                # Fire callback in a daemon thread to avoid blocking the listener
                threading.Thread(target=callback, daemon=True).start()
                # Clear pressed keys to prevent repeated triggers
                self._pressed_keys.clear()
                return

    def _on_release(self, key) -> None:
        """Remove released key from tracking set."""
        key_name = self._normalize_key(key)
        if key_name:
            self._pressed_keys.discard(key_name)

    # -------------------------------------------------------------------------
    # Key normalization helpers
    # -------------------------------------------------------------------------

    def _parse_hotkey(self, hotkey: str) -> Set[str]:
        """Parse 'win+h' or 'ctrl+shift+r' into a set of normalized key names."""
        parts = hotkey.lower().replace(" ", "").split("+")
        keys: Set[str] = set()
        for part in parts:
            if part in ("win", "cmd", "super"):
                keys.add("cmd")
            elif part in ("ctrl", "control"):
                keys.add("ctrl")
            elif part in ("alt", "option"):
                keys.add("alt")
            elif part == "shift":
                keys.add("shift")
            else:
                keys.add(part)
        return keys

    def _normalize_key(self, key) -> Optional[str]:
        """Map a pynput key object to a normalized string."""
        try:
            if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
                return "cmd"
            if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                return "ctrl"
            if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                return "alt"
            if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
                return "shift"
            if hasattr(key, "char") and key.char:
                return key.char.lower()
            if hasattr(key, "name"):
                return key.name.lower()
            return None
        except Exception:
            return None


# -------------------------------------------------------------------------
# Standalone test
# -------------------------------------------------------------------------

def test_hotkeys():
    handler = HotkeyHandler()
    count = [0]

    def on_toggle():
        count[0] += 1
        print(f"[Test] Win+H pressed (count={count[0]})")
        if count[0] >= 3:
            handler.stop()

    def on_retry():
        print("[Test] Ctrl+Shift+R pressed — retry!")

    handler.register("win+h", on_toggle)
    handler.register("ctrl+shift+r", on_retry)
    handler.start()

    print("Press Win+H (3×) to exit, Ctrl+Shift+R to test retry")
    try:
        handler._listener.join()
    except KeyboardInterrupt:
        handler.stop()


if __name__ == "__main__":
    test_hotkeys()
