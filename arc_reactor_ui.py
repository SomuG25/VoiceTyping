"""
Arc Reactor UI - Iron Man Mark III "Jarvis" Edition
- True translucent overlay via Win32 layered window
- Gradient glass panel with HUD border + corner accents
- Glow text with layered shadow rendering
- Sci-fi scanline effect
- Timer inside the reactor core while recording
"""

import tkinter as tk
import threading
import numpy as np
import math
from typing import Optional

# Win32 for layered-window translucency
import win32gui
import win32con


class ArcReactorUI:
    """Translucent Iron Man HUD overlay with live transcription."""

    TRANSPARENT_KEY = "#050505"
    GLASS_ALPHA = 220  # 0-255, 220 = ~86% opaque

    COLOR_LISTEN_MAIN = "#00F2FF"
    COLOR_LISTEN_CORE = "#FFFFFF"
    COLOR_LISTEN_GLOW = "#007AFF"

    COLOR_PROCESS_MAIN = "#FFD700"
    COLOR_PROCESS_CORE = "#FF8C00"
    COLOR_PROCESS_GLOW = "#FF4500"

    HUD_DARK = "#1A252A"
    HUD_GRID = "#003840"

    CANVAS_SIZE = 520
    CENTER_X = 260
    CENTER_Y = 150
    BASE_RADIUS = 35
    TEXT_MAX_CHARS = 55

    def __init__(self):
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None

        self._is_recording = False
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._amplitude = 0.0
        self._amplitude_lock = threading.Lock()

        self._rotation_angle = 0.0
        self._scan_line_y = 0.0
        self._scan_direction = 1
        self._pulse_phase = 0.0  # For text glow animation

        self._status_text = ""
        self._core_text = ""
        self._live_text = ""

    # ------------------------------------------------------------------
    # Window
    # ------------------------------------------------------------------

    def _create_window(self) -> None:
        self._root = tk.Tk()
        self._root.title("Voice Typing HUD")
        self._root.overrideredirect(True)
        self._root.attributes('-topmost', True)
        self._root.attributes('-transparentcolor', self.TRANSPARENT_KEY)
        self._root.configure(bg=self.TRANSPARENT_KEY)
        self._root.geometry(f"{self.CANVAS_SIZE}x{self.CANVAS_SIZE}")

        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = (screen_w - self.CANVAS_SIZE) // 2
        y = screen_h - self.CANVAS_SIZE - 20
        self._root.geometry(f"+{x}+{y}")

        self._canvas = tk.Canvas(
            self._root, width=self.CANVAS_SIZE, height=self.CANVAS_SIZE,
            bg=self.TRANSPARENT_KEY, highlightthickness=0,
        )
        self._canvas.pack()
        self._root.withdraw()

        # Apply Win32 layered window for true translucency
        self._root.after(150, self._apply_glass)

    def _apply_glass(self):
        """Enable per-window alpha blending via Win32 layered window."""
        try:
            hwnd = self._root.winfo_id()
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                hwnd, win32con.GWL_EXSTYLE,
                ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT,
            )
            win32gui.SetLayeredWindowAttributes(
                hwnd, 0, self.GLASS_ALPHA, win32con.LWA_ALPHA,
            )
        except Exception:
            pass  # Graceful fallback if Win32 call fails

    # ------------------------------------------------------------------
    # Palette
    # ------------------------------------------------------------------

    def _get_palette(self):
        if self._is_recording:
            return self.COLOR_LISTEN_MAIN, self.COLOR_LISTEN_CORE, self.COLOR_LISTEN_GLOW
        return self.COLOR_PROCESS_MAIN, self.COLOR_PROCESS_CORE, self.COLOR_PROCESS_GLOW

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _glow_text(self, x, y, text, color, glow, font, width=None, anchor="n"):
        """Multi-layer glow text — draws 3 layers for soft neon effect."""
        # Outer glow (dimmest, widest spread)
        self._canvas.create_text(
            x + 2, y + 2, text=text, fill=glow, font=font,
            anchor=anchor, width=width, state="normal",
        )
        self._canvas.create_text(
            x - 2, y - 2, text=text, fill=glow, font=font,
            anchor=anchor, width=width, state="normal",
        )
        # Inner glow
        self._canvas.create_text(
            x + 1, y + 1, text=text,
            fill="#406678", font=font, anchor=anchor, width=width,
        )
        # Foreground
        self._canvas.create_text(
            x, y, text=text, fill=color, font=font, anchor=anchor, width=width,
        )

    def _draw_gradient_panel(self, x1, y1, x2, y2, r=14):
        """Glass panel with vertical gradient + HUD border + corner accents."""
        h = y2 - y1

        # Gradient: lighter glass at top → deeper at bottom
        for i in range(int(h)):
            ratio = i / max(h - 1, 1)
            r_val = int(18 + (1 - ratio) * 14)
            g_val = int(24 + (1 - ratio) * 14)
            b_val = int(30 + (1 - ratio) * 14)
            color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            self._canvas.create_line(x1, y1 + i, x2, y1 + i, fill=color)

        # Rounded border — cyan HUD outline
        points = self._rounded_points(x1, y1, x2, y2, r, steps=20)
        self._canvas.create_polygon(points, fill="", outline="#1A4A5A", width=2, smooth=True)

        # Corner accents — small diagonal tech marks at each corner
        for cx, cy, dx, dy in [
            (x1 + 6, y1 + 6, 1, 1),   # top-left
            (x2 - 6, y1 + 6, -1, 1),  # top-right
            (x1 + 6, y2 - 6, 1, -1),  # bottom-left
            (x2 - 6, y2 - 6, -1, -1), # bottom-right
        ]:
            for i in range(3):
                self._canvas.create_line(
                    cx, cy + i * 5 * dy,
                    cx + 12 * dx, cy + i * 5 * dy,
                    fill="#00F2FF", width=1,
                )
                self._canvas.create_line(
                    cx + i * 5 * dx, cy,
                    cx + i * 5 * dx, cy + 12 * dy,
                    fill="#00F2FF", width=1,
                )

        # Scanlines — faint horizontal lines for HUD screen effect
        for i in range(int((y2 - y1) // 8)):
            ly = y1 + 12 + i * 8
            if ly < y2 - 12:
                self._canvas.create_line(
                    x1 + 14, ly, x2 - 14, ly,
                    fill="#FFFFFF", width=1, stipple="gray25",
                )

    def _rounded_points(self, x1, y1, x2, y2, r, steps=10):
        """Generate polygon points for a rounded rectangle."""
        points = []
        for a in range(steps):
            ang = math.pi / 2 * (a / (steps - 1))
            points.extend([x2 - r + r * math.cos(ang), y1 + r - r * math.sin(ang)])
        for a in range(steps):
            ang = math.pi / 2 * (a / (steps - 1))
            points.extend([x2 - r + r * math.sin(ang), y2 - r + r * math.cos(ang)])
        for a in range(steps):
            ang = math.pi / 2 * (a / (steps - 1))
            points.extend([x1 + r - r * math.cos(ang), y2 - r + r * math.sin(ang)])
        for a in range(steps):
            ang = math.pi / 2 * (a / (steps - 1))
            points.extend([x1 + r - r * math.sin(ang), y1 + r - r * math.cos(ang)])
        return points

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def _draw_reactor(self) -> None:
        if not self._canvas or not self._running:
            return
        self._canvas.delete("all")

        cx, cy = self.CENTER_X, self.CENTER_Y
        main, core, glow = self._get_palette()

        with self._amplitude_lock:
            amp = self._amplitude

        spin = 3.0 if not self._is_recording else 0.5
        pulse = (math.sin(self._rotation_angle * 0.1) * 2) + 2
        expansion = (amp * 40) if self._is_recording else 5

        # ---- Rings ----
        self._draw_palladium_ring(cx, cy, 65, 85, main, 10)
        self._draw_gyro_rings(cx, cy, 95 + (expansion * 0.5), main, spin)

        # ---- Core glow ----
        glow_rad = self.BASE_RADIUS + expansion + pulse
        self._canvas.create_oval(
            cx - glow_rad, cy - glow_rad,
            cx + glow_rad, cy + glow_rad,
            outline=glow, width=2,
        )

        # ---- Core solid ----
        core_rad = self.BASE_RADIUS + (expansion * 0.3)
        self._canvas.create_oval(
            cx - core_rad, cy - core_rad,
            cx + core_rad, cy + core_rad,
            fill=core, outline=main, width=3,
        )

        # ---- Core text: timer ----
        if self._core_text:
            self._canvas.create_text(
                cx, cy, text=self._core_text,
                fill=self.HUD_DARK, font=("Consolas", 13, "bold"),
            )

        # ---- Scanner (processing mode) ----
        if not self._is_recording:
            self._draw_scanner(cx, cy, main)

        # ---- Ticks ----
        self._draw_ticks(cx, cy, 125, self.HUD_GRID)

        # ---- Status line ----
        if self._status_text:
            self._canvas.create_text(
                cx, cy + 95, text=self._status_text,
                fill=main, font=("Consolas", 9),
            )

        # ---- Live transcription panel ----
        if self._live_text:
            display = self._live_text
            panel_w = min(len(display) * 10 + 40, self.CANVAS_SIZE - 40)
            panel_x1 = cx - panel_w / 2
            panel_x2 = cx + panel_w / 2
            panel_y1 = cy + 112
            panel_y2 = cy + 172

            self._draw_gradient_panel(panel_x1, panel_y1, panel_x2, panel_y2, r=14)
            self._glow_text(
                cx, (panel_y1 + panel_y2) // 2, text=display,
                color="#E8F4FF", glow="#003848",
                font=("Consolas", 15, "bold"),
            )

    def _draw_palladium_ring(self, cx, cy, r_in, r_out, color, segments):
        angle_step = 360 / segments
        gap = 10
        rot_offset = self._rotation_angle * 0.2 if not self._is_recording else 0
        for i in range(segments):
            s = (i * angle_step) + (gap / 2) + rot_offset
            e = ((i + 1) * angle_step) - (gap / 2) + rot_offset
            sa, ea = math.radians(s), math.radians(e)
            pts = [
                cx + math.cos(sa) * r_in, cy + math.sin(sa) * r_in,
                cx + math.cos(ea) * r_in, cy + math.sin(ea) * r_in,
                cx + math.cos(ea) * r_out, cy + math.sin(ea) * r_out,
                cx + math.cos(sa) * r_out, cy + math.sin(sa) * r_out,
            ]
            self._canvas.create_polygon(pts, fill=self.HUD_DARK, outline=color, width=1)

    def _draw_gyro_rings(self, cx, cy, r, color, speed):
        a1 = (self._rotation_angle * 2 * speed) % 360
        self._canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                                start=a1, extent=220, style=tk.ARC,
                                outline=color, width=1)
        r2 = r + 15
        a2 = -(self._rotation_angle * 1.5 * speed) % 360
        for offset in (0, 180):
            self._canvas.create_arc(cx - r2, cy - r2, cx + r2, cy + r2,
                                    start=a2 + offset, extent=60, style=tk.ARC,
                                    outline=color, width=4)

    def _draw_scanner(self, cx, cy, color):
        limit = 55
        self._scan_line_y += (3 * self._scan_direction)
        if abs(self._scan_line_y) > limit:
            self._scan_direction *= -1
        y_pos = cy + self._scan_line_y
        self._canvas.create_line(cx - 45, y_pos, cx + 45, y_pos, fill=color, width=2)
        self._canvas.create_rectangle(cx - 38, cy - 55, cx + 38, cy + 55,
                                      outline=self.HUD_GRID, width=1)

    def _draw_ticks(self, cx, cy, r, color):
        for i in range(0, 360, 30):
            rad = math.radians(i)
            self._canvas.create_line(
                cx + math.cos(rad) * r, cy + math.sin(rad) * r,
                cx + math.cos(rad) * (r + 5), cy + math.sin(rad) * (r + 5),
                fill=color,
            )

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------

    def _animate(self) -> None:
        if not self._running:
            return
        self._rotation_angle += 1
        self._pulse_phase += 0.05
        with self._amplitude_lock:
            self._amplitude *= 0.85
        self._draw_reactor()
        if self._root:
            self._root.after(16, self._animate)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_amplitude(self, audio_chunk: bytes) -> None:
        if not self._is_recording or not audio_chunk:
            return
        try:
            samples = np.frombuffer(audio_chunk, dtype=np.int16)
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            normalized = min(1.0, rms / 500)
            with self._amplitude_lock:
                self._amplitude = max(self._amplitude, normalized)
        except Exception:
            pass

    def set_recording(self, recording: bool) -> None:
        self._is_recording = recording
        if not self._root:
            return
        if recording:
            self.show()
            self._live_text = ""
            self._core_text = ""
            with self._amplitude_lock:
                self._amplitude = 0.0
        else:
            self._core_text = ""
            self._root.after(3000, self.hide)

    def set_status(self, status: str):
        self._status_text = status

    def set_core_text(self, text: str):
        self._core_text = text

    def set_live_text(self, text: str):
        self._live_text = text

    def show(self):
        if self._root:
            self._root.deiconify()

    def hide(self):
        if self._root:
            self._root.withdraw()

    def hide_after_delay(self, ms: int = 2000):
        if self._root:
            self._root.after(ms, self.hide)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._root:
            self._root.destroy()

    def _run(self):
        self._create_window()
        self._root.after(100, self._animate)
        self._root.mainloop()
