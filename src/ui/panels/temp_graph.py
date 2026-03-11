import tkinter as tk
from math import ceil

from ...controller.tester_controller import StationMode, RunState
from ..theme import PANEL, FG, GRID, AXIS, GREEN, BLUE, MUTED


def fmt_hhmm(seconds: float) -> str:
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h:02d}:{m:02d}"


class TempGraphPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Temperature vs Time", bg=PANEL, fg=FG, font=("DejaVu Sans", 11, "bold"))
        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)

        # Store ALL points for the run (x=elapsed_s)
        self.s1_points: list[tuple[float, float]] = []
        self.s2_points: list[tuple[float, float]] = []

        self._last_run_state = RunState.IDLE
        self.bind("<Configure>", lambda e: self._redraw())

    def clear(self) -> None:
        self.s1_points.clear()
        self.s2_points.clear()
        self._redraw()

    def update(self, *, elapsed_s: float, temps: dict, mode: StationMode, run_state: RunState) -> None:
        active_s1 = (mode == StationMode.S1) or (mode == StationMode.BOTH)
        active_s2 = (mode == StationMode.S2) or (mode == StationMode.BOTH)

        # Start of a new run: clear points (so each test graph is separate)
        if self._last_run_state == RunState.IDLE and run_state == RunState.RUNNING:
            self.clear()

        # Append points only while running (keeps x-axis meaningful)
        if run_state == RunState.RUNNING:
            if active_s1:
                self.s1_points.append((float(elapsed_s), float(temps.get("S1", 0.0))))
            if active_s2:
                self.s2_points.append((float(elapsed_s), float(temps.get("S2", 0.0))))

        self._last_run_state = run_state
        self._redraw()

    def _redraw(self) -> None:
        c = self.canvas
        c.delete("all")
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())

        pad = 55
        x0, y0 = pad, h - pad
        x1, y1 = w - pad, pad

        # Determine x range
        max_x = 0.0
        if self.s1_points:
            max_x = max(max_x, self.s1_points[-1][0])
        if self.s2_points:
            max_x = max(max_x, self.s2_points[-1][0])
        max_x = max(max_x, 1.0)

        # Determine y range from data (with padding)
        all_y = [p[1] for p in self.s1_points] + [p[1] for p in self.s2_points]
        if all_y:
            y_min = min(all_y)
            y_max = max(all_y)
        else:
            y_min, y_max = 20.0, 40.0

        pad_y = 1.5
        y_min -= pad_y
        y_max += pad_y
        if y_max - y_min < 3.0:
            y_max = y_min + 3.0

        # Grid + ticks
        x_step = self._nice_x_step(max_x)       # seconds per vertical grid line
        y_step = self._nice_y_step(y_min, y_max)

        # Vertical grid lines and x labels
        t = 0.0
        while t <= max_x + 1e-6:
            x = self._map_x(t, x0, x1, max_x)
            c.create_line(x, y0, x, y1, fill=GRID)
            c.create_text(x, y0 + 18, text=fmt_hhmm(t), fill=MUTED, font=("DejaVu Sans", 9))
            t += x_step

        # Horizontal grid lines and y labels
        y_tick = self._ceil_to(y_min, y_step)
        while y_tick <= y_max + 1e-6:
            y = self._map_y(y_tick, y0, y1, y_min, y_max)
            c.create_line(x0, y, x1, y, fill=GRID)
            c.create_text(x0 - 10, y, text=f"{y_tick:.0f}", fill=MUTED, font=("DejaVu Sans", 9), anchor="e")
            y_tick += y_step

        # Axes
        c.create_line(x0, y0, x1, y0, fill=AXIS, width=2)
        c.create_line(x0, y0, x0, y1, fill=AXIS, width=2)
        c.create_text((x0 + x1) / 2, h - 18, text="Time (HH:MM)", fill=FG)
        c.create_text(18, (y0 + y1) / 2, text="Temp (°C)", fill=FG, angle=90)

        # Draw series (downsampled for performance)
        self._draw_series(self.s1_points, x0, y0, x1, y1, max_x, y_min, y_max, color=GREEN, dash=None)
        self._draw_series(self.s2_points, x0, y0, x1, y1, max_x, y_min, y_max, color=BLUE, dash=(4, 3))

        # Legend
        lx = x1 - 160
        ly = y1 + 10
        c.create_rectangle(lx, ly, x1, ly + 42, fill="#0a0a0a", outline=GRID)
        c.create_line(lx + 10, ly + 14, lx + 40, ly + 14, fill=GREEN, width=2)
        c.create_text(lx + 50, ly + 14, text="Station 1", fill=FG, anchor="w")
        c.create_line(lx + 10, ly + 30, lx + 40, ly + 30, fill=BLUE, width=2, dash=(4, 3))
        c.create_text(lx + 50, ly + 30, text="Station 2", fill=FG, anchor="w")

    def _draw_series(self, pts, x0, y0, x1, y1, max_x, y_min, y_max, color, dash):
        if len(pts) < 2:
            return

        # Downsample to avoid drawing thousands of points every refresh
        max_draw = 800
        step = max(1, len(pts) // max_draw)
        sample = pts[::step]

        coords = []
        for t, val in sample:
            x = self._map_x(t, x0, x1, max_x)
            y = self._map_y(val, y0, y1, y_min, y_max)
            coords.extend([x, y])

        self.canvas.create_line(*coords, fill=color, width=2, dash=dash)

    @staticmethod
    def _map_x(t, x0, x1, max_x):
        return x0 + (x1 - x0) * (t / max_x)

    @staticmethod
    def _map_y(v, y0, y1, y_min, y_max):
        return y0 - (y0 - y1) * ((v - y_min) / (y_max - y_min))

    @staticmethod
    def _nice_x_step(max_x_s: float) -> float:
        # Choose grid spacing so labels don’t get crowded
        # (seconds): 1m, 5m, 10m, 30m, 1h
        options = [60, 300, 600, 1800, 3600]
        target_lines = 6
        best = options[0]
        best_diff = float("inf")
        for s in options:
            lines = max_x_s / s
            diff = abs(lines - target_lines)
            if diff < best_diff:
                best, best_diff = s, diff
        return float(best)

    @staticmethod
    def _nice_y_step(y_min: float, y_max: float) -> float:
        span = y_max - y_min
        raw = span / 8.0
        # Nice steps: 0.5, 1, 2, 5
        for step in [0.5, 1, 2, 5, 10]:
            if step >= raw:
                return float(step)
        return 10.0

    @staticmethod
    def _ceil_to(v: float, step: float) -> float:
        return ceil(v / step) * step