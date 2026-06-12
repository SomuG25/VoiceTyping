"""
File Transcriber UI — Standalone tkinter window for transcribing audio/video files.

Opens from the system tray "Transcribe File..." menu item.
Converts any audio/video format to WAV using ffmpeg, then transcribes
using local faster-whisper (no API key, no internet needed).
"""

import os
import sys
import shutil
import threading
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from pathlib import Path
from typing import Optional

# fmt: off
SUPPORTED_FORMATS = {
    ".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".flac",
    ".webm", ".mkv", ".avi", ".mov", ".aac", ".wma",
}

MODELS = ["tiny", "base", "small", "medium", "large-v3"]
LANGUAGES = {
    "Auto-detect": None,
    "English":     "en",
    "Hindi":       "hi",
    "Marathi":     "mr",
    "Spanish":     "es",
    "French":      "fr",
    "German":      "de",
    "Japanese":    "ja",
}

BG          = "#0d0d0f"
BG2         = "#16161a"
BG3         = "#1e1e24"
ACCENT      = "#3b82f6"
ACCENT2     = "#60a5fa"
GREEN       = "#22c55e"
RED         = "#ef4444"
TEXT        = "#e2e8f0"
TEXT_DIM    = "#94a3b8"
BORDER      = "#2d2d3a"
# fmt: on


class FileTranscriberUI:
    """Dark-themed tkinter window for file transcription."""

    def __init__(self, default_model: str = "medium"):
        self._root: Optional[tk.Tk] = None
        self._default_model = default_model
        self._cancel_flag = threading.Event()
        self._is_transcribing = False

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def open(self) -> None:
        """Open (or raise) the transcriber window. Safe to call from any thread."""
        if self._root and self._root.winfo_exists():
            self._root.lift()
            self._root.focus_force()
            return
        # Run on main thread via after() if called from a non-GUI thread
        self._build_and_run()

    def open_threadsafe(self) -> None:
        """Open the window from a non-tkinter thread (e.g., tray callback)."""
        threading.Thread(target=self._build_and_run, daemon=True).start()

    # -------------------------------------------------------------------------
    # Window construction
    # -------------------------------------------------------------------------

    def _build_and_run(self) -> None:
        self._root = tk.Tk()
        root = self._root

        root.title("🎙️ File Transcriber — Local Whisper")
        root.geometry("780x660")
        root.minsize(640, 520)
        root.configure(bg=BG)
        root.resizable(True, True)

        # ── Style ─────────────────────────────────────────────────────────────
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Dim.TLabel", background=BG, foreground=TEXT_DIM, font=("Segoe UI", 9))
        style.configure(
            "TCombobox",
            fieldbackground=BG3, background=BG3, foreground=TEXT,
            selectbackground=ACCENT, selectforeground="white",
            arrowcolor=TEXT_DIM,
        )
        style.map("TCombobox", fieldbackground=[("readonly", BG3)])
        style.configure("TProgressbar", troughcolor=BG3, background=ACCENT, thickness=6)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(root, bg=BG2, pady=14)
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="📄  File Transcriber", bg=BG2, fg=TEXT,
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left", padx=20)
        tk.Label(
            hdr, text="Powered by local faster-whisper  •  No internet needed",
            bg=BG2, fg=TEXT_DIM, font=("Segoe UI", 9),
        ).pack(side="right", padx=20)

        # ── Body ──────────────────────────────────────────────────────────────
        body = tk.Frame(root, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # File picker row
        tk.Label(body, text="Audio / Video File", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")

        file_row = tk.Frame(body, bg=BG)
        file_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 14))
        body.columnconfigure(0, weight=1)

        self._file_var = tk.StringVar()
        file_entry = tk.Entry(
            file_row, textvariable=self._file_var, bg=BG3, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
            state="readonly",
        )
        file_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        tk.Button(
            file_row, text="  Browse…  ", bg=ACCENT, fg="white",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            activebackground=ACCENT2, activeforeground="white",
            command=self._browse_file, padx=4, pady=4,
        ).pack(side="left")

        # Options row
        opts = tk.Frame(body, bg=BG)
        opts.grid(row=2, column=0, sticky="ew", pady=(0, 14))

        tk.Label(opts, text="Model:", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(side="left")
        self._model_var = tk.StringVar(value=self._default_model)
        model_cb = ttk.Combobox(
            opts, textvariable=self._model_var, values=MODELS,
            state="readonly", width=12, font=("Segoe UI", 10),
        )
        model_cb.pack(side="left", padx=(6, 20))

        tk.Label(opts, text="Language:", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(side="left")
        self._lang_var = tk.StringVar(value="English")
        lang_cb = ttk.Combobox(
            opts, textvariable=self._lang_var, values=list(LANGUAGES.keys()),
            state="readonly", width=14, font=("Segoe UI", 10),
        )
        lang_cb.pack(side="left", padx=(6, 0))

        # Buttons row
        btn_row = tk.Frame(body, bg=BG)
        btn_row.grid(row=3, column=0, sticky="ew", pady=(0, 14))

        self._transcribe_btn = tk.Button(
            btn_row, text="  ▶  Transcribe  ", bg=GREEN, fg="white",
            font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2",
            activebackground="#16a34a", activeforeground="white",
            command=self._start_transcription, padx=10, pady=6,
        )
        self._transcribe_btn.pack(side="left", padx=(0, 10))

        self._cancel_btn = tk.Button(
            btn_row, text="  ✕  Cancel  ", bg=BG3, fg=TEXT_DIM,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            activebackground=RED, activeforeground="white",
            command=self._cancel, padx=8, pady=6, state="disabled",
        )
        self._cancel_btn.pack(side="left")

        # Progress bar
        self._progress = ttk.Progressbar(body, mode="indeterminate",
                                          style="TProgressbar")
        self._progress.grid(row=4, column=0, sticky="ew", pady=(0, 14))

        # Status log
        tk.Label(body, text="Status Log", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).grid(row=5, column=0, sticky="w")
        self._log = scrolledtext.ScrolledText(
            body, height=6, bg=BG2, fg=TEXT_DIM, insertbackground=TEXT,
            font=("Consolas", 9), relief="flat", state="disabled",
            wrap="word", bd=0,
        )
        self._log.grid(row=6, column=0, sticky="nsew", pady=(4, 14))
        body.rowconfigure(6, weight=0)

        # Output area
        tk.Label(body, text="Transcription Output", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).grid(row=7, column=0, sticky="w")
        self._output = scrolledtext.ScrolledText(
            body, height=10, bg=BG3, fg=TEXT, insertbackground=TEXT,
            font=("Segoe UI", 11), relief="flat", wrap="word", bd=0,
        )
        self._output.grid(row=8, column=0, sticky="nsew", pady=(4, 14))
        body.rowconfigure(8, weight=1)

        # Action buttons row
        save_row = tk.Frame(body, bg=BG)
        save_row.grid(row=9, column=0, sticky="ew")

        tk.Button(
            save_row, text="💾  Save .txt", bg=BG3, fg=TEXT,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            activebackground=ACCENT, activeforeground="white",
            command=self._save_txt, padx=8, pady=5,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            save_row, text="📋  Copy All", bg=BG3, fg=TEXT,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            activebackground=ACCENT, activeforeground="white",
            command=self._copy_all, padx=8, pady=5,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            save_row, text="🗑  Clear", bg=BG3, fg=TEXT_DIM,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            activebackground=BG2, activeforeground=TEXT,
            command=self._clear_output, padx=8, pady=5,
        ).pack(side="left")

        # ffmpeg warning if missing
        if not shutil.which("ffmpeg"):
            warn = tk.Label(
                save_row,
                text="⚠️  ffmpeg not found — WAV only (run: winget install ffmpeg)",
                bg=BG, fg="#f59e0b", font=("Segoe UI", 9),
            )
            warn.pack(side="right")

        # ── Initial log ───────────────────────────────────────────────────────
        self._log_line("Ready. Select a file and click Transcribe.")

        root.mainloop()

    # -------------------------------------------------------------------------
    # File browsing
    # -------------------------------------------------------------------------

    def _browse_file(self) -> None:
        ext_str = " ".join(f"*{e}" for e in sorted(SUPPORTED_FORMATS))
        path = filedialog.askopenfilename(
            title="Select Audio / Video File",
            filetypes=[
                ("Audio & Video", ext_str),
                ("MP3", "*.mp3"), ("MP4", "*.mp4"), ("WAV", "*.wav"),
                ("M4A", "*.m4a"), ("OGG / FLAC", "*.ogg *.flac"),
                ("All Files", "*.*"),
            ],
        )
        if path:
            self._file_var.set(path)
            self._log_line(f"Selected: {Path(path).name}")

    # -------------------------------------------------------------------------
    # Transcription
    # -------------------------------------------------------------------------

    def _start_transcription(self) -> None:
        src = self._file_var.get().strip()
        if not src:
            self._log_line("⚠️  No file selected.")
            return
        if not Path(src).exists():
            self._log_line("⚠️  File not found.")
            return

        self._cancel_flag.clear()
        self._is_transcribing = True
        self._transcribe_btn.config(state="disabled")
        self._cancel_btn.config(state="normal")
        self._progress.start(12)
        self._clear_output()

        threading.Thread(
            target=self._run_transcription, args=(src,), daemon=True
        ).start()

    def _run_transcription(self, src: str) -> None:
        tmp_wav = None
        try:
            src_path = Path(src)
            ext = src_path.suffix.lower()

            # ── Step 1: Convert to 16kHz mono WAV if needed ──────────────────
            if ext == ".wav":
                wav_path = src_path
                self._log_line("✔  Already WAV — no conversion needed.")
            else:
                if not shutil.which("ffmpeg"):
                    self._log_line("❌  ffmpeg not found!")
                    self._log_line("   Install: winget install ffmpeg")
                    self._log_line("   Then restart the app.")
                    return

                self._log_line(f"🔄  Converting {ext.upper()} → WAV (16kHz mono)…")
                tmp_fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
                os.close(tmp_fd)

                cmd = [
                    "ffmpeg", "-y", "-i", str(src_path),
                    "-vn",                   # strip video stream
                    "-acodec", "pcm_s16le",  # 16-bit PCM
                    "-ar", "16000",          # 16kHz — Whisper native rate
                    "-ac", "1",              # mono
                    tmp_wav,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self._log_line("❌  ffmpeg conversion failed:")
                    for line in result.stderr.splitlines()[-6:]:
                        self._log_line(f"   {line}")
                    return

                wav_path = Path(tmp_wav)
                size_mb = wav_path.stat().st_size / (1024 * 1024)
                self._log_line(f"✔  Converted — {size_mb:.1f} MB WAV ready.")

            if self._cancel_flag.is_set():
                self._log_line("Cancelled.")
                return

            # ── Step 2: Load Whisper model ────────────────────────────────────
            model_size = self._model_var.get()
            lang_name  = self._lang_var.get()
            language   = LANGUAGES.get(lang_name)

            self._log_line(f"📦  Loading Whisper {model_size} model…")
            self._log_line("   (first run downloads model — ~1-2 GB, please wait)")

            from faster_whisper import WhisperModel
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            self._log_line("✔  Model loaded.")

            if self._cancel_flag.is_set():
                self._log_line("Cancelled.")
                return

            # ── Step 3: Transcribe ────────────────────────────────────────────
            import wave as wavlib
            with wavlib.open(str(wav_path), "rb") as wf:
                duration_s = wf.getnframes() / wf.getframerate()

            mins, secs = divmod(int(duration_s), 60)
            self._log_line(f"🎙️  Transcribing {mins}m {secs:02d}s of audio…")
            self._log_line("   Medium model on CPU: ~1× real-time — please wait.")

            segments, info = model.transcribe(
                str(wav_path),
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.3,
                    min_speech_duration_ms=400,
                    min_silence_duration_ms=800,
                    speech_pad_ms=400,
                ),
            )

            self._log_line(
                f"🔍  Detected language: {info.language} "
                f"({info.language_probability:.0%} confidence)"
            )

            # Collect segments with live append to output box
            parts = []
            for i, seg in enumerate(segments, 1):
                if self._cancel_flag.is_set():
                    self._log_line("⚠️  Cancelled mid-transcription.")
                    break
                text = seg.text.strip()
                if text:
                    parts.append(text)
                    # Show each segment as it comes in
                    self._append_output(text + " ")
                    self._log_line(f"  [{i}] ({seg.start:.0f}s) {text[:60]}…"
                                   if len(text) > 60 else f"  [{i}] ({seg.start:.0f}s) {text}")

            if parts and not self._cancel_flag.is_set():
                self._log_line(f"✅  Done! {len(parts)} segments transcribed.")
                self._auto_save(src_path, " ".join(parts))
            elif not parts:
                self._log_line("⚠️  No speech detected in file.")

        except Exception as e:
            self._log_line(f"❌  Error: {e}")
            import traceback
            for line in traceback.format_exc().splitlines():
                self._log_line(f"   {line}")
        finally:
            # Clean up temp WAV
            if tmp_wav and Path(tmp_wav).exists():
                try:
                    os.remove(tmp_wav)
                except Exception:
                    pass
            self._done()

    def _auto_save(self, src_path: Path, text: str) -> None:
        """Auto-save .txt next to the source file."""
        try:
            txt_path = src_path.with_suffix(".txt")
            txt_path.write_text(text, encoding="utf-8")
            self._log_line(f"💾  Auto-saved: {txt_path.name}")
        except Exception as e:
            self._log_line(f"   (Auto-save failed: {e})")

    def _cancel(self) -> None:
        self._cancel_flag.set()
        self._log_line("⚠️  Cancelling…")

    def _done(self) -> None:
        """Reset UI state after transcription ends (called from worker thread)."""
        if self._root:
            self._root.after(0, self._reset_ui)

    def _reset_ui(self) -> None:
        self._is_transcribing = False
        self._progress.stop()
        self._transcribe_btn.config(state="normal")
        self._cancel_btn.config(state="disabled")

    # -------------------------------------------------------------------------
    # Output helpers
    # -------------------------------------------------------------------------

    def _log_line(self, msg: str) -> None:
        """Append a line to the status log (thread-safe)."""
        def _do():
            self._log.config(state="normal")
            self._log.insert("end", msg + "\n")
            self._log.see("end")
            self._log.config(state="disabled")
        if self._root:
            self._root.after(0, _do)

    def _append_output(self, text: str) -> None:
        """Append text to the output area (thread-safe)."""
        def _do():
            self._output.insert("end", text)
            self._output.see("end")
        if self._root:
            self._root.after(0, _do)

    def _clear_output(self) -> None:
        self._output.delete("1.0", "end")
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    def _save_txt(self) -> None:
        text = self._output.get("1.0", "end").strip()
        if not text:
            self._log_line("⚠️  Nothing to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt"), ("All Files", "*.*")],
            title="Save Transcription",
        )
        if path:
            Path(path).write_text(text, encoding="utf-8")
            self._log_line(f"💾  Saved to: {Path(path).name}")

    def _copy_all(self) -> None:
        text = self._output.get("1.0", "end").strip()
        if not text:
            return
        self._root.clipboard_clear()
        self._root.clipboard_append(text)
        self._log_line("📋  Copied to clipboard.")


# ──────────────────────────────────────────────────────────────────────────────
# Standalone test
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ui = FileTranscriberUI(default_model="medium")
    ui.open()
