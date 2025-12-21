"""
Global hotkey handler for Voice Typing application.
Uses pynput for system-wide hotkey detection (Win+H by default).
"""

import threading
from typing import Callable, Optional
from pynput import keyboard


class HotkeyHandler:
    """Handles global hotkey detection for toggling voice recording."""
    
    def __init__(self, hotkey: str = "win+h"):
        """
        Initialize hotkey handler.
        
        Args:
            hotkey: Hotkey combination string (e.g., "win+h", "ctrl+shift+v")
        """
        self._hotkey_str = hotkey.lower()
        self._on_toggle: Optional[Callable[[], None]] = None
        self._listener: Optional[keyboard.Listener] = None
        self._pressed_keys: set = set()
        self._running = False
        
        # Parse hotkey into required keys
        self._required_keys = self._parse_hotkey(hotkey)
    
    def _parse_hotkey(self, hotkey: str) -> set:
        """
        Parse hotkey string into a set of key names.
        
        Args:
            hotkey: Hotkey string like "win+h" or "ctrl+shift+v"
            
        Returns:
            Set of key identifiers
        """
        parts = hotkey.lower().replace(" ", "").split("+")
        keys = set()
        
        for part in parts:
            if part in ("win", "cmd", "super"):
                keys.add("cmd")  # pynput uses cmd for Windows key
            elif part in ("ctrl", "control"):
                keys.add("ctrl")
            elif part in ("alt", "option"):
                keys.add("alt")
            elif part in ("shift",):
                keys.add("shift")
            else:
                keys.add(part)  # Regular key like 'h', 'v', etc.
        
        return keys
    
    def _get_key_name(self, key) -> Optional[str]:
        """
        Get normalized key name from pynput key object.
        
        Args:
            key: pynput key object
            
        Returns:
            Normalized key name string
        """
        try:
            # Special keys
            if key == keyboard.Key.cmd or key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r:
                return "cmd"
            elif key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                return "ctrl"
            elif key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                return "alt"
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                return "shift"
            
            # Regular keys
            if hasattr(key, 'char') and key.char:
                return key.char.lower()
            elif hasattr(key, 'vk'):
                # Try to get character from virtual key code
                if hasattr(key, 'name'):
                    return key.name.lower()
            
            return None
            
        except Exception:
            return None
    
    def _on_press(self, key) -> None:
        """Handle key press event."""
        key_name = self._get_key_name(key)
        if key_name:
            self._pressed_keys.add(key_name)
            
            # Check if hotkey combination is pressed
            if self._required_keys.issubset(self._pressed_keys):
                if self._on_toggle:
                    self._on_toggle()
                # Clear pressed keys to prevent repeated triggers
                self._pressed_keys.clear()
    
    def _on_release(self, key) -> None:
        """Handle key release event."""
        key_name = self._get_key_name(key)
        if key_name:
            self._pressed_keys.discard(key_name)
    
    def start(self, on_toggle: Callable[[], None]) -> None:
        """
        Start listening for hotkey.
        
        Args:
            on_toggle: Callback function to call when hotkey is pressed
        """
        if self._running:
            return
        
        self._on_toggle = on_toggle
        self._running = True
        self._pressed_keys.clear()
        
        # Start listener in background
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()
    
    def stop(self) -> None:
        """Stop listening for hotkey."""
        self._running = False
        
        if self._listener:
            self._listener.stop()
            self._listener = None
        
        self._pressed_keys.clear()
    
    @property
    def hotkey(self) -> str:
        """Get current hotkey string."""
        return self._hotkey_str
    
    @hotkey.setter
    def hotkey(self, value: str) -> None:
        """Set new hotkey combination."""
        self._hotkey_str = value.lower()
        self._required_keys = self._parse_hotkey(value)
        self._pressed_keys.clear()


def test_hotkey():
    """Test hotkey detection."""
    print("Testing hotkey handler...")
    print("Press Win+H to toggle (press 3 times to exit)")
    
    handler = HotkeyHandler("win+h")
    toggle_count = [0]
    
    def on_toggle():
        toggle_count[0] += 1
        print(f"Hotkey pressed! (count: {toggle_count[0]})")
        if toggle_count[0] >= 3:
            handler.stop()
    
    handler.start(on_toggle)
    
    # Wait for handler to process
    try:
        handler._listener.join()
    except KeyboardInterrupt:
        handler.stop()
    
    print("Hotkey test complete!")


if __name__ == "__main__":
    test_hotkey()
