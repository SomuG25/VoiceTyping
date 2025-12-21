"""
Configuration management for Voice Typing application.
Handles loading/saving settings from config.json and environment variables.
"""

import json
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default configuration
DEFAULT_CONFIG = {
    "api_key": "",
    "hotkey": "win+h",
    "audio_device": null,
    "overlay_enabled": True,
    "auto_start": False,
    "typing_delay": 0.01
}

# Config file path (same directory as this script)
CONFIG_PATH = Path(__file__).parent / "config.json"


class Config:
    """Configuration manager for the Voice Typing application."""
    
    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self) -> None:
        """Load configuration from config.json and environment variables."""
        # Load from file if exists
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config.json: {e}")
        
        # Override with environment variables (from .env or system)
        env_api_key = os.environ.get("GEMINI_API_KEY")
        if env_api_key:
            self._config["api_key"] = env_api_key
    
    def save(self) -> None:
        """Save current configuration to config.json."""
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(self._config, f, indent=4)
        except IOError as e:
            print(f"Error: Could not save config.json: {e}")
    
    @property
    def api_key(self) -> str:
        """Get the Gemini API key."""
        return self._config.get("api_key", "")
    
    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set the Gemini API key."""
        self._config["api_key"] = value
    
    @property
    def hotkey(self) -> str:
        """Get the hotkey combination (e.g., 'win+h')."""
        return self._config.get("hotkey", "win+h")
    
    @hotkey.setter
    def hotkey(self, value: str) -> None:
        """Set the hotkey combination."""
        self._config["hotkey"] = value
    
    @property
    def audio_device(self) -> Optional[int]:
        """Get the audio device index (None for default)."""
        return self._config.get("audio_device")
    
    @audio_device.setter
    def audio_device(self, value: Optional[int]) -> None:
        """Set the audio device index."""
        self._config["audio_device"] = value
    
    @property
    def overlay_enabled(self) -> bool:
        """Check if the overlay UI is enabled."""
        return self._config.get("overlay_enabled", True)
    
    @overlay_enabled.setter
    def overlay_enabled(self, value: bool) -> None:
        """Enable/disable the overlay UI."""
        self._config["overlay_enabled"] = value
    
    @property
    def auto_start(self) -> bool:
        """Check if auto-start with Windows is enabled."""
        return self._config.get("auto_start", False)
    
    @auto_start.setter
    def auto_start(self, value: bool) -> None:
        """Enable/disable auto-start with Windows."""
        self._config["auto_start"] = value
    
    @property
    def typing_delay(self) -> float:
        """Get the delay between typed characters (in seconds)."""
        return self._config.get("typing_delay", 0.01)
    
    @typing_delay.setter
    def typing_delay(self, value: float) -> None:
        """Set the delay between typed characters."""
        self._config["typing_delay"] = value


# Global config instance
config = Config()
