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
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Default configuration
DEFAULT_CONFIG = {
    "api_key": "",
    "hotkey": "win+h",
    "retry_hotkey": "win+f4",
    "audio_device": None,
    "audio_device_name": "Realtek",
    "transcription_model": "gemini-3.1-flash-live-preview",
    "last_recording_path": "last_recording.wav",
    "overlay_enabled": True,
    "auto_start": False,
    "typing_delay": 0.01,
    "reconnect_max_attempts": 3,
    "session_max_minutes": 9,
}

CONFIG_PATH = Path(__file__).parent / "config.json"


class Config:
    """Configuration manager for the Voice Typing application."""

    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> None:
        """Load configuration from config.json and environment variables."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r") as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config.json: {e}")

        # Environment variable always takes priority
        env_api_key = os.environ.get("GEMINI_API_KEY")
        if env_api_key:
            self._config["api_key"] = env_api_key

    def save(self) -> None:
        """Save current configuration to config.json."""
        save_config = {k: v for k, v in self._config.items() if k != "api_key"}
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(save_config, f, indent=4)
        except IOError as e:
            print(f"Error: Could not save config.json: {e}")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def api_key(self) -> str:
        return self._config.get("api_key", "")

    @api_key.setter
    def api_key(self, value: str) -> None:
        self._config["api_key"] = value

    @property
    def hotkey(self) -> str:
        return self._config.get("hotkey", "win+h")

    @hotkey.setter
    def hotkey(self, value: str) -> None:
        self._config["hotkey"] = value

    @property
    def retry_hotkey(self) -> str:
        """Hotkey to re-transcribe last_recording.wav (default: win+f4)."""
        return self._config.get("retry_hotkey", "win+f4")

    @retry_hotkey.setter
    def retry_hotkey(self, value: str) -> None:
        self._config["retry_hotkey"] = value

    @property
    def audio_device(self) -> Optional[int]:
        return self._config.get("audio_device")

    @audio_device.setter
    def audio_device(self, value: Optional[int]) -> None:
        self._config["audio_device"] = value

    @property
    def overlay_enabled(self) -> bool:
        return self._config.get("overlay_enabled", True)

    @overlay_enabled.setter
    def overlay_enabled(self, value: bool) -> None:
        self._config["overlay_enabled"] = value

    @property
    def auto_start(self) -> bool:
        return self._config.get("auto_start", False)

    @auto_start.setter
    def auto_start(self, value: bool) -> None:
        self._config["auto_start"] = value

    @property
    def transcription_model(self) -> str:
        return self._config.get("transcription_model", "gemini-3.1-flash-live-preview")

    @transcription_model.setter
    def transcription_model(self, value: str) -> None:
        self._config["transcription_model"] = value

    @property
    def last_recording_path(self) -> str:
        """Path to save the last recording WAV for retry."""
        return self._config.get("last_recording_path", "last_recording.wav")

    @last_recording_path.setter
    def last_recording_path(self, value: str) -> None:
        self._config["last_recording_path"] = value

    @property
    def typing_delay(self) -> float:
        return self._config.get("typing_delay", 0.01)

    @typing_delay.setter
    def typing_delay(self, value: float) -> None:
        self._config["typing_delay"] = value

    @property
    def reconnect_max_attempts(self) -> int:
        return self._config.get("reconnect_max_attempts", 3)

    @property
    def session_max_minutes(self) -> int:
        return self._config.get("session_max_minutes", 9)


# Global config instance
config = Config()
