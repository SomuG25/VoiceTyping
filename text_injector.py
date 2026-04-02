"""
Text injection module for Voice Typing application.
Auto-types transcribed text into the active window.
"""

import time
import threading
from typing import Optional
import pyautogui
import pyperclip


# Configure pyautogui for safety
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.0      # No pause between actions


class TextInjector:
    """Injects text into the active window by simulating keyboard input."""
    
    def __init__(self, typing_delay: float = 0.01):
        """
        Initialize text injector.
        
        Args:
            typing_delay: Delay between characters in seconds (default: 10ms)
        """
        self._typing_delay = typing_delay
        self._typing_lock = threading.Lock()
        self._is_typing = False
        self._pending_text = ""
        self._type_thread: Optional[threading.Thread] = None
    
    def type_text(self, text: str, use_clipboard: bool = False) -> None:
        """
        Type text into the active window.
        
        Args:
            text: Text to type
            use_clipboard: If True, use clipboard paste instead of typing
        """
        if not text:
            return
        
        with self._typing_lock:
            # Always use clipboard paste for safety - avoids key code interpretation
            self._paste_text(text)
    
    def _type_text_direct(self, text: str) -> None:
        """Type text directly using keyboard simulation."""
        try:
            # Small delay to ensure window focus
            time.sleep(0.05)
            
            # Type each character
            for char in text:
                pyautogui.write(char, interval=self._typing_delay)
                
        except Exception as e:
            print(f"Typing error: {e}")
            # Fallback to clipboard
            self._paste_text(text)
    
    def _paste_text(self, text: str) -> None:
        """Paste text using clipboard."""
        try:
            # Save current clipboard content
            original_clipboard = ""
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                pass
            
            # Copy text to clipboard
            pyperclip.copy(text)
            
            # Small delay to ensure window focus
            time.sleep(0.05)
            
            # Paste using Ctrl+V
            pyautogui.hotkey('ctrl', 'v')
            
            # Small delay before restoring clipboard
            time.sleep(0.1)
            
            # Restore original clipboard
            try:
                pyperclip.copy(original_clipboard)
            except Exception:
                pass
                
        except Exception as e:
            print(f"Paste error: {e}")
    
    def type_text_async(self, text: str) -> None:
        """
        Queue text for asynchronous typing.
        Text is accumulated and typed with proper spacing.
        
        Args:
            text: Text to type
        """
        if not text:
            return
        
        # Add to pending text
        with self._typing_lock:
            if self._pending_text and not self._pending_text.endswith(" "):
                self._pending_text += " "
            self._pending_text += text
        
        # Start typing thread if not running
        if self._type_thread is None or not self._type_thread.is_alive():
            self._type_thread = threading.Thread(target=self._async_type_loop, daemon=True)
            self._type_thread.start()
    
    def _async_type_loop(self) -> None:
        """Background thread for async typing."""
        while True:
            text_to_type = ""
            
            with self._typing_lock:
                if self._pending_text:
                    text_to_type = self._pending_text
                    self._pending_text = ""
            
            if text_to_type:
                self._is_typing = True
                self._type_text_direct(text_to_type)
                self._is_typing = False
            else:
                # No more text, exit loop
                break
            
            time.sleep(0.05)
    
    def press_key(self, key: str) -> None:
        """
        Press a special key.
        
        Args:
            key: Key name (e.g., 'enter', 'backspace', 'tab')
        """
        try:
            pyautogui.press(key)
        except Exception as e:
            print(f"Key press error: {e}")
    
    def press_hotkey(self, *keys: str) -> None:
        """
        Press a hotkey combination.
        
        Args:
            keys: Key names (e.g., 'ctrl', 'z' for Ctrl+Z)
        """
        try:
            pyautogui.hotkey(*keys)
        except Exception as e:
            print(f"Hotkey error: {e}")
    
    @property
    def typing_delay(self) -> float:
        """Get current typing delay."""
        return self._typing_delay
    
    @typing_delay.setter
    def typing_delay(self, value: float) -> None:
        """Set typing delay."""
        self._typing_delay = max(0.001, value)  # Minimum 1ms
    
    @property
    def is_typing(self) -> bool:
        """Check if currently typing."""
        return self._is_typing


# Voice command handlers
class VoiceCommands:
    """Handles special voice commands like 'new line' or 'period'."""
    
    COMMANDS = {
        "new line": "\n",
        "newline": "\n",
        "enter": "\n",
        "period": ".",
        "full stop": ".",
        "comma": ",",
        "question mark": "?",
        "exclamation mark": "!",
        "exclamation point": "!",
        "colon": ":",
        "semicolon": ";",
        "quote": '"',
        "open quote": '"',
        "close quote": '"',
        "apostrophe": "'",
        "hyphen": "-",
        "dash": "-",
        "underscore": "_",
        "at sign": "@",
        "hashtag": "#",
        "dollar sign": "$",
        "percent": "%",
        "ampersand": "&",
        "asterisk": "*",
        "open paren": "(",
        "close paren": ")",
        "open bracket": "[",
        "close bracket": "]",
        "open brace": "{",
        "close brace": "}",
        "space": " ",
        "tab": "\t",
    }
    
    @classmethod
    def process_text(cls, text: str) -> str:
        """
        Process text - returns text as-is (voice command substitution disabled).
        This ensures literal words are typed, not symbols.
        
        Args:
            text: Input text
            
        Returns:
            Same text, unmodified (safe mode)
        """
        # DISABLED: Voice command substitution to prevent accidental key presses
        # User requested literal word typing only
        # To re-enable, uncomment the loop below:
        #
        # result = text.lower()
        # for command, replacement in cls.COMMANDS.items():
        #     result = result.replace(command, replacement)
        # return result
        
        return text  # Return text as-is


def test_injector():
    """Test text injection."""
    print("Testing text injector...")
    print("Will type 'Hello World!' in 3 seconds...")
    print("Click on a text field (Notepad, browser, etc.)")
    
    time.sleep(3)
    
    injector = TextInjector()
    injector.type_text("Hello World! ")
    
    print("\nTesting voice commands...")
    text = VoiceCommands.process_text("Hello new line World period")
    print(f"Processed: '{text}'")
    injector.type_text(text)
    
    print("\nText injection test complete!")


if __name__ == "__main__":
    test_injector()
