import tkinter as tk
from ...controller.tester_controller import StationMode, RunState
from ..theme import PANEL, FG, MUTED, FONT_BIG, GREEN, BLUE, GRID


class TempDisplayPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Temperatures (Sim)", bg=PANEL, fg=FG, font=("DejaVu Sans", 11, "bold"))

        self._s1_hist = []
        self._s2_hist = []
        self._max_hist = 80

        # Station 1
        self.s1_label = tk.Label(self, text="S1: — °C", bg=PANEL, fg=GREEN, font=FONT_BIG)
        self.s1_canvas = tk.Canvas(self, bg="#000000", height=55, highlightthickness=1, highlightbackground=GRID)
        self.s1_state = tk.Label(self, text="Inactive", bg=PANEL, fg=MUTED)

        # Station 2
        self.s2_label = tk.Label(self, text="S2: — °C", bg=PANEL, fg=BLUE, font=FONT_BIG)
        self.s2_canvas = tk.Canvas(self, bg="#000000", height=55, highlightthickness=1, highlightbackground=GRID)
        self.s2_state = tk.Label(self, text="Inactive", bg=PANEL, fg=MUTED)

        # Layout
        self.s1_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))
        self.s2_label.grid(row=0, column=1, sticky="w", padx=10, pady=(10, 2))

        self.s1_canvas.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 2))
        self.s2_canvas.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 2))

        self.s1_state.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))
        self.s2_state.grid(row=2, column=1, sticky="w", padx=10, pady=(0, 10))

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def clear_sparklines(self) -> None:
        self._s1_hist.clear()
        self._s2_hist.clear()
        self._draw_spark(self.s1_canvas, [], GREEN)
        self._draw_spark(self.s2_canvas, [], BLUE)

    def update(self, *, temps: dict, mode: StationMode, run_state: RunState) -> None:
        t1 = float(temps.get("S1", 0.0))
        t2 = float(temps.get("S2", 0.0))

        self.s1_label.configure(text=f"S1: {t1:.2f} °C")
        self.s2_label.configure(text=f"S2: {t2:.2f} °C")

        active_s1 = (mode == StationMode.S1) or (mode == StationMode.BOTH)
        active_s2 = (mode == StationMode.S2) or (mode == StationMode.BOTH)
        running = (run_state == RunState.RUNNING)

        self.s1_state.configure(text=("Active" if (running and active_s1) else "Inactive"))
        self.s2_state.configure(text=("Active" if (running and active_s2) else "Inactive"))

        # Append history (append so the mini-graphs look alive)
        self._s1_hist.append(t1)
        self._s2_hist.append(t2)
        self._s1_hist = self._s1_hist[-self._max_hist:]
        self._s2_hist = self._s2_hist[-self._max_hist:]

        self._draw_spark(self.s1_canvas, self._s1_hist, GREEN)
        self._draw_spark(self.s2_canvas, self._s2_hist, BLUE)

    def _draw_spark(self, canvas: tk.Canvas, data: list[float], color: str) -> None:
        canvas.delete("all")
        w = max(1, canvas.winfo_width())
        h = max(1, canvas.winfo_height())

        # simple grid line
        canvas.create_line(0, h/2, w, h/2, fill="#1c1c1c")

        if len(data) < 2:
            return

        mn = min(data)
        mx = max(data)
        if mx - mn < 0.5:
            mx = mn + 0.5

        pts = []
        n = len(data)
        for i, v in enumerate(data):
            x = (i / (n - 1)) * (w - 2) + 1
            y = h - 1 - ((v - mn) / (mx - mn)) * (h - 2)
            pts.extend([x, y])

        canvas.create_line(*pts, fill=color, width=2)