"""
Arc Reactor UI - Iron Man Mark III "Jarvis" Edition
Features:
- "Amber" Processing State (Jarvis Analysis Mode)
- Parallax/Gyroscopic Ring Effects
- Radar Sweep Animation
- Reactive Energy Overload
"""

import tkinter as tk
import threading
import numpy as np
import math
from typing import Optional

class ArcReactorUI:
    """Iron Man Arc Reactor style voice visualizer (Mark III Design)."""
    
    # --- STARK INDUSTRIES PALETTE ---
    BG_COLOR = "#050505"           # Transparent Key
    
    # State: LISTENING (Arc Reactor Blue)
    COLOR_LISTEN_MAIN = "#00F2FF"  # Cyan
    COLOR_LISTEN_CORE = "#FFFFFF"  # White Hot
    COLOR_LISTEN_GLOW = "#007AFF"  # Deep Blue glow
    
    # State: PROCESSING (Jarvis Amber)
    COLOR_PROCESS_MAIN = "#FFD700" # Gold/Amber
    COLOR_PROCESS_CORE = "#FF8C00" # Dark Orange
    COLOR_PROCESS_GLOW = "#FF4500" # Red-Orange glow
    
    # HUD Details
    HUD_DARK = "#1A252A"           # Dark mechanical grey
    HUD_GRID = "#004852"           # Faint grid lines
    
    WINDOW_SIZE = 320
    CENTER_X = 160
    CENTER_Y = 160
    BASE_RADIUS = 35
    
    def __init__(self):
        """Initialize the Stark Tech UI."""
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        
        self._is_recording = False   # True = Listening, False = Processing
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Data
        self._amplitude = 0.0
        self._amplitude_lock = threading.Lock()
        
        # Animation Physics
        self._rotation_angle = 0.0
        self._scan_line_y = 0.0      # For the radar sweep
        self._scan_direction = 1     # 1 = down, -1 = up
        
    def _create_window(self) -> None:
        """Create the floating HUD window."""
        self._root = tk.Tk()
        self._root.title("Stark HUD")
        self._root.overrideredirect(True)
        self._root.attributes('-topmost', True)
        self._root.attributes('-transparentcolor', self.BG_COLOR)
        
        # Configure Geometry
        self._root.configure(bg=self.BG_COLOR)
        self._root.geometry(f"{self.WINDOW_SIZE}x{self.WINDOW_SIZE}")
        
        # Center Bottom Placement
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = (screen_w - self.WINDOW_SIZE) // 2
        y = screen_h - self.WINDOW_SIZE - 60
        self._root.geometry(f"+{x}+{y}")
        
        self._canvas = tk.Canvas(
            self._root,
            width=self.WINDOW_SIZE,
            height=self.WINDOW_SIZE,
            bg=self.BG_COLOR,
            highlightthickness=0
        )
        self._canvas.pack()
        self._root.withdraw()
    
    def _get_palette(self):
        """Returns the current color theme based on state."""
        if self._is_recording:
            return self.COLOR_LISTEN_MAIN, self.COLOR_LISTEN_CORE, self.COLOR_LISTEN_GLOW
        else:
            return self.COLOR_PROCESS_MAIN, self.COLOR_PROCESS_CORE, self.COLOR_PROCESS_GLOW

    def _draw_reactor(self) -> None:
        """Main Render Loop."""
        if not self._canvas or not self._running: return
        self._canvas.delete("all")
        
        cx, cy = self.CENTER_X, self.CENTER_Y
        main_color, core_color, glow_color = self._get_palette()
        
        # Smooth amplitude
        with self._amplitude_lock:
            amp = self._amplitude
        
        # Animation Variables
        # If processing, spin faster (thinking), otherwise spin slow (idle)
        spin_speed = 3.0 if not self._is_recording else 0.5
        pulse = (math.sin(self._rotation_angle * 0.1) * 2) + 2
        expansion = (amp * 40) if self._is_recording else 5 # Breathing when processing
        
        # --- LAYER 1: The Palladium Ring (The Mechanical Base) ---
        # This is the iconic "blocky" ring of the Mark III
        self._draw_palladium_ring(cx, cy, 65, 85, main_color, 10)

        # --- LAYER 2: Gyroscopic HUD Rings (Parallax) ---
        # We draw these slightly oval to give a 3D effect
        self._draw_gyro_rings(cx, cy, 95 + (expansion*0.5), main_color, spin_speed)

        # --- LAYER 3: The Core (Energy Source) ---
        # Glow
        glow_rad = self.BASE_RADIUS + expansion + pulse
        self._draw_circle(cx, cy, glow_rad, "", outline=glow_color, width=2)
        
        # Solid Core
        core_rad = self.BASE_RADIUS + (expansion * 0.3)
        self._draw_circle(cx, cy, core_rad, core_color, outline=main_color, width=3)
        
        # --- LAYER 4: Processing Scanner (Only when NOT listening) ---
        if not self._is_recording:
            self._draw_scanner(cx, cy, main_color)
            
        # --- LAYER 5: Decorator Tech ---
        self._draw_ticks(cx, cy, 130, self.HUD_GRID)

    def _draw_palladium_ring(self, cx, cy, r_in, r_out, color, segments):
        """Draws the trapezoidal capacitor blocks."""
        angle_step = 360 / segments
        gap = 10 # degrees
        
        # If processing, this ring rotates slowly
        rot_offset = self._rotation_angle * 0.2 if not self._is_recording else 0
        
        for i in range(segments):
            start_deg = (i * angle_step) + (gap/2) + rot_offset
            end_deg = ((i+1) * angle_step) - (gap/2) + rot_offset
            
            # Convert polar to cartesian
            sa, ea = math.radians(start_deg), math.radians(end_deg)
            
            points = [
                cx + math.cos(sa) * r_in, cy + math.sin(sa) * r_in, # Inner 1
                cx + math.cos(ea) * r_in, cy + math.sin(ea) * r_in, # Inner 2
                cx + math.cos(ea) * r_out, cy + math.sin(ea) * r_out, # Outer 2
                cx + math.cos(sa) * r_out, cy + math.sin(sa) * r_out  # Outer 1
            ]
            self._canvas.create_polygon(points, fill=self.HUD_DARK, outline=color, width=1)

    def _draw_gyro_rings(self, cx, cy, r, color, speed_mult):
        """Draws rotating holographic rings with 3D parallax."""
        
        # Ring 1: Fast Thin Ring
        angle_1 = (self._rotation_angle * 2 * speed_mult) % 360
        self._canvas.create_arc(
            cx-r, cy-r, cx+r, cy+r,
            start=angle_1, extent=220, style=tk.ARC,
            outline=color, width=1
        )
        
        # Ring 2: Thick Segmented Ring (Opposite rotation)
        r2 = r + 15
        angle_2 = -(self._rotation_angle * 1.5 * speed_mult) % 360
        self._canvas.create_arc(
            cx-r2, cy-r2, cx+r2, cy+r2,
            start=angle_2, extent=60, style=tk.ARC,
            outline=color, width=4
        )
        self._canvas.create_arc(
            cx-r2, cy-r2, cx+r2, cy+r2,
            start=angle_2 + 180, extent=60, style=tk.ARC,
            outline=color, width=4
        )

    def _draw_scanner(self, cx, cy, color):
        """Draws a vertical scanning line when processing."""
        limit = 60 # Scan height limit
        
        # Update scan line position
        self._scan_line_y += (3 * self._scan_direction)
        if abs(self._scan_line_y) > limit:
            self._scan_direction *= -1
            
        y_pos = cy + self._scan_line_y
        
        # Draw the scan line
        self._canvas.create_line(cx - 50, y_pos, cx + 50, y_pos, fill=color, width=2)
        
        # Draw faint "grid" being scanned
        self._canvas.create_rectangle(cx-40, cy-60, cx+40, cy+60, outline=self.HUD_GRID, width=1)

    def _draw_ticks(self, cx, cy, r, color):
        """Draws fixed HUD ticks."""
        for i in range(0, 360, 30):
            rad = math.radians(i)
            x1 = cx + math.cos(rad) * r
            y1 = cy + math.sin(rad) * r
            x2 = cx + math.cos(rad) * (r + 5)
            y2 = cy + math.sin(rad) * (r + 5)
            self._canvas.create_line(x1, y1, x2, y2, fill=color)

    def _draw_circle(self, x, y, r, color, alpha=1.0, **kwargs):
        """Helper for circles."""
        self._canvas.create_oval(
            x-r, y-r, x+r, y+r, 
            fill=color if 'outline' not in kwargs else "", 
            outline=kwargs.get('outline', ""), 
            width=kwargs.get('width', 0)
        )

    # --- STANDARD METHODS (Unchanged) ---
    def _animate(self) -> None:
        if not self._running: return
        self._rotation_angle += 1
        with self._amplitude_lock:
            self._amplitude *= 0.85
        self._draw_reactor()
        if self._root: self._root.after(16, self._animate)
        
    def update_amplitude(self, audio_chunk: bytes) -> None:
        if not self._is_recording or not audio_chunk: return
        try:
            samples = np.frombuffer(audio_chunk, dtype=np.int16)
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            normalized = min(1.0, rms / 500)
            with self._amplitude_lock:
                self._amplitude = max(self._amplitude, normalized)
        except Exception: pass

    def set_recording(self, recording: bool) -> None:
        self._is_recording = recording
        if not self._root: return
        
        if recording:
            self.show()
            with self._amplitude_lock: self._amplitude = 0.0
        else:
            # When stopping recording, we stay visible for a moment 
            # to show the "Processing" (Amber) animation
            self._root.after(3000, self.hide)
            
    def show(self): 
        if self._root: self._root.deiconify()
    def hide(self): 
        if self._root: self._root.withdraw()
    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    def stop(self):
        self._running = False
        if self._root: self._root.destroy()
    def _run(self):
        self._create_window()
        self._root.after(100, self._animate)
        self._root.mainloop()
    def set_status(self, status): pass