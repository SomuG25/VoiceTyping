<div align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Orbitron&size=32&duration=3000&pause=1000&color=00F2FF&center=true&vCenter=true&width=500&lines=VOICE+TYPING;Speak.+Type.+Done." alt="Voice Typing" />
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" />
  <img src="https://img.shields.io/badge/platform-Windows%2011-brightgreen" alt="Platform" />
  <img src="https://img.shields.io/badge/offline-100%25-brightgreen" alt="Offline" />
</p>

<p align="center">
  <b>Voice Typing</b> turns your speech into text in any window — <b>completely offline</b>.
  <br>No API keys. No internet. Just double-tap Space and talk.
</p>

---

## How It Works

1. **Double-tap Space** — microphone opens. The Arc Reactor UI appears.
2. **Speak** — your voice is recorded locally.
3. **Double-tap Space again** — recording stops. faster-whisper transcribes your speech and types it wherever your cursor is.
4. **Triple-tap Space** — retype the last recording (useful if something went wrong).

---

## Installation

### 1. Clone
```bash
git clone https://github.com/SomuG25/VoiceTyping.git
cd VoiceTyping
```

### 2. Create a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note:** The first run will download the Whisper model (~400 MB) to your local cache. This only happens once.

### 4. Run
```bash
python main.py
```

The app runs silently in your system tray. Double-tap Space to record.

### Optional: Launch on Startup
Run `create_shortcut.ps1` in PowerShell to add Voice Typing to your Windows startup folder.

---

## Features

| | |
|---|---|
| **Double-tap Space** | Open microphone — no looking for hotkeys |
| **Triple-tap Space** | Retry the last transcription |
| **100% Offline** | Local faster-whisper + Silero VAD on your PC |
| **Arc Reactor UI** | Iron Man-style overlay with live amplitude |
| **Recording Archive** | Every recording saved to `recordings/` with matching `.txt` |
| **System Tray** | Right-click for start/stop/retry/exit |

---

## Model Selection

Configure in `config.json`:

| Setting | Default | Options |
|---------|---------|---------|
| `whisper_model` | `base` | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `whisper_device` | `cpu` | `cpu`, `cuda`, `auto` |
| `whisper_compute_type` | `int8` | `int8`, `float16`, `float32`, `auto` |
| `vad_threshold` | `0.5` | `0.0` – `1.0` (lower = more sensitive) |

- **tiny** — fastest, least accurate (1 GB RAM)
- **base** — good balance, ~400 MB model
- **small** — more accurate, slower on CPU

For GPU acceleration, set `whisper_device` to `"cuda"` and `whisper_compute_type` to `"float16"`.

---

## Configuration

Edit `config.json` to customize:

```json
{
  "audio_device": null,
  "audio_device_name": "Realtek",
  "overlay_enabled": true,
  "typing_delay": 0.01,
  "whisper_model": "base",
  "whisper_device": "cpu",
  "whisper_compute_type": "int8",
  "vad_threshold": 0.5
}
```

---

## Troubleshooting

<details>
<summary><b>No microphone detected</b></summary>

Run `python audio_capture.py` to see all detected devices. Set `audio_device` in `config.json` to the correct index. The app auto-prioritizes Realtek/physical mics over virtual devices.
</details>

<details>
<summary><b>Whisper model fails to download</b></summary>

Set the environment variable `HF_ENDPOINT=https://hf-mirror.com` if you are behind a firewall. Or manually download the model from HuggingFace to `~/.cache/huggingface/hub/`.
</details>

<details>
<summary><b>Transcription is slow</b></summary>

Use `"tiny"` or `"base"` model. On CPU, `small` and above can take several seconds. If you have an NVIDIA GPU, set `whisper_device` to `"cuda"`.
</details>

<details>
<summary><b>Text doesn't appear after stopping</b></summary>

Make sure your cursor is in a text field. The app pastes via Ctrl+V. If the target app blocks paste, try a different window.
</details>

<details>
<summary><b>Double-tap Space not detected</b></summary>

Run the app as Administrator. Some applications capture keyboard input at a lower level. You can also start/stop from the system tray menu.
</details>

---

## Tech Stack

| Component | Library |
|-----------|---------|
| Transcription | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) |
| VAD (voice detection) | Silero VAD (built into faster-whisper) |
| Audio capture | PyAudio |
| Keyboard detection | [keyboard](https://github.com/boppreh/keyboard) |
| Text injection | pyautogui + pyperclip |
| System tray | pystray + Pillow |
| UI overlay | Tkinter + NumPy |

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with faster-whisper · Iron Man vibes · Zero internet required</sub>
</p>
