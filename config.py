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
    "audio_device": None,
    "audio_device_name": "Realtek",
    "last_recording_path": "last_recording.wav",
    "overlay_enabled": True,
    "auto_start": False,
    "typing_delay": 0.01,
    "whisper_model": "base",
    "whisper_device": "cpu",
    "whisper_compute_type": "int8",
    "vad_threshold": 0.5,
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

    def save(self) -> None:
        """Save current configuration to config.json."""
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self._config, f, indent=4)
        except IOError as e:
            print(f"Error: Could not save config.json: {e}")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

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
    def whisper_model(self) -> str:
        """faster-whisper model size: tiny, base, small, medium, large-v3."""
        return self._config.get("whisper_model", "base")

    @whisper_model.setter
    def whisper_model(self, value: str) -> None:
        self._config["whisper_model"] = value

    @property
    def whisper_device(self) -> str:
        """Device for Whisper inference: auto, cpu, cuda."""
        return self._config.get("whisper_device", "auto")

    @whisper_device.setter
    def whisper_device(self, value: str) -> None:
        self._config["whisper_device"] = value

    @property
    def whisper_compute_type(self) -> str:
        """Compute type: auto, int8, float16, float32."""
        return self._config.get("whisper_compute_type", "auto")

    @whisper_compute_type.setter
    def whisper_compute_type(self, value: str) -> None:
        self._config["whisper_compute_type"] = value

    @property
    def vad_threshold(self) -> float:
        """Silero VAD speech probability threshold (0.0-1.0)."""
        return self._config.get("vad_threshold", 0.5)

    @vad_threshold.setter
    def vad_threshold(self, value: float) -> None:
        self._config["vad_threshold"] = value


# Global config instance
config = Config()
