"""
System tray application for Voice Typing.
Provides background service with status indicators and menu options.
"""

import threading
import time
from typing import Callable, Optional
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem, Menu


class TrayApp:
    """System tray application for Voice Typing."""
    
    # Status colors
    COLORS = {
        'idle': '#808080',      # Gray
        'listening': '#22c55e', # Green
        'processing': '#3b82f6', # Blue
        'error': '#ef4444'      # Red
    }
    
    def __init__(self):
        """Initialize tray application."""
        self._icon: Optional[pystray.Icon] = None
        self._status = 'idle'
        self._is_recording = False
        self._running = False
        
        # Callbacks
        self._on_toggle: Optional[Callable[[], None]] = None
        self._on_settings: Optional[Callable[[], None]] = None
        self._on_exit: Optional[Callable[[], None]] = None
    
    def _create_icon_image(self, color: str = '#808080') -> Image.Image:
        """
        Create tray icon image.
        
        Args:
            color: Icon color in hex format
            
        Returns:
            PIL Image object
        """
        # Create a 64x64 image
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Parse color
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        # Draw microphone icon (simplified)
        # Microphone body
        draw.ellipse([20, 8, 44, 40], fill=(r, g, b, 255))
        draw.rectangle([20, 24, 44, 40], fill=(r, g, b, 255))
        
        # Microphone stand
        draw.arc([14, 24, 50, 52], 0, 180, fill=(r, g, b, 255), width=4)
        draw.line([32, 52, 32, 58], fill=(r, g, b, 255), width=4)
        draw.line([22, 58, 42, 58], fill=(r, g, b, 255), width=4)
        
        return image
    
    def _get_menu(self) -> Menu:
        """Create the tray menu."""
        return Menu(
            MenuItem(
                lambda _: "🔴 Stop Recording" if self._is_recording else "🎤 Start Recording",
                self._on_toggle_click,
                default=True
            ),
            Menu.SEPARATOR,
            MenuItem("⚙️ Settings", self._on_settings_click),
            Menu.SEPARATOR,
            MenuItem("❌ Exit", self._on_exit_click)
        )
    
    def _on_toggle_click(self, icon, item) -> None:
        """Handle toggle menu click."""
        if self._on_toggle:
            self._on_toggle()
    
    def _on_settings_click(self, icon, item) -> None:
        """Handle settings menu click."""
        if self._on_settings:
            self._on_settings()
    
    def _on_exit_click(self, icon, item) -> None:
        """Handle exit menu click."""
        self.stop()
        if self._on_exit:
            self._on_exit()
    
    def start(self, 
              on_toggle: Optional[Callable[[], None]] = None,
              on_settings: Optional[Callable[[], None]] = None,
              on_exit: Optional[Callable[[], None]] = None) -> None:
        """
        Start the tray application.
        
        Args:
            on_toggle: Callback for toggle recording
            on_settings: Callback for settings
            on_exit: Callback for exit
        """
        self._on_toggle = on_toggle
        self._on_settings = on_settings
        self._on_exit = on_exit
        self._running = True
        
        # Create icon
        self._icon = pystray.Icon(
            name="VoiceTyping",
            icon=self._create_icon_image(self.COLORS['idle']),
            title="Voice Typing - Press Win+H to toggle",
            menu=self._get_menu()
        )
        
        # Run in background thread
        self._icon.run_detached()
    
    def stop(self) -> None:
        """Stop the tray application."""
        self._running = False
        
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
    
    def set_status(self, status: str) -> None:
        """
        Update tray icon status.
        
        Args:
            status: One of 'idle', 'listening', 'processing', 'error'
        """
        self._status = status
        color = self.COLORS.get(status, self.COLORS['idle'])
        
        if self._icon:
            try:
                self._icon.icon = self._create_icon_image(color)
                
                # Update tooltip
                tooltips = {
                    'idle': "Voice Typing - Press Win+H to toggle",
                    'listening': "Voice Typing - Listening...",
                    'processing': "Voice Typing - Processing...",
                    'error': "Voice Typing - Error"
                }
                self._icon.title = tooltips.get(status, tooltips['idle'])
            except Exception:
                pass
    
    def set_recording(self, recording: bool) -> None:
        """
        Update recording state.
        
        Args:
            recording: True if recording, False otherwise
        """
        self._is_recording = recording
        self.set_status('listening' if recording else 'idle')
        
        # Update menu
        if self._icon:
            try:
                self._icon.update_menu()
            except Exception:
                pass
    
    def show_notification(self, title: str, message: str) -> None:
        """
        Show a notification from the tray.
        
        Args:
            title: Notification title
            message: Notification message
        """
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass


def test_tray():
    """Test tray application."""
    print("Testing tray application...")
    print("Look for the microphone icon in your system tray.")
    print("Press Ctrl+C to exit.")
    
    tray = TrayApp()
    
    def on_toggle():
        print("Toggle clicked!")
        tray.set_recording(not tray._is_recording)
    
    def on_exit():
        print("Exit clicked!")
    
    tray.start(on_toggle=on_toggle, on_exit=on_exit)
    
    # Show notification
    time.sleep(1)
    tray.show_notification("Voice Typing", "Application started!")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tray.stop()
        print("\nTray test complete!")


if __name__ == "__main__":
    test_tray()
