import tkinter as tk
from ...controller.tester_controller import StationMode, RunState


class TempGraphPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Temperature Graph (Sim)")
        self.canvas = tk.Canvas(self, height=280)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)

        self.max_points = 200
        self.data_s1 = []
        self.data_s2 = []

        self.y_min = 20.0
        self.y_max = 40.0

        self.bind("<Configure>", lambda e: self._redraw())

    def update(self, *, temps: dict, mode: StationMode, run_state: RunState) -> None:
        running = (run_state == RunState.RUNNING)

        active_s1 = (mode == StationMode.S1) or (mode == StationMode.BOTH)
        active_s2 = (mode == StationMode.S2) or (mode == StationMode.BOTH)

        # Only append points while running (keeps graph “session-like”)
        if running:
            if active_s1:
                self.data_s1.append(float(temps.get("S1", 0.0)))
            if active_s2:
                self.data_s2.append(float(temps.get("S2", 0.0)))

            self.data_s1 = self.data_s1[-self.max_points:]
            self.data_s2 = self.data_s2[-self.max_points:]

        # If stopped, you can choose to clear (comment out if you want history)
        if run_state == RunState.IDLE:
            self.data_s1.clear()
            self.data_s2.clear()

        self._redraw()

    def _redraw(self) -> None:
        self.canvas.delete("all")
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())

        # Axes
        pad = 40
        x0, y0 = pad, h - pad
        x1, y1 = w - pad, pad
        self.canvas.create_line(x0, y0, x1, y0)
        self.canvas.create_line(x0, y0, x0, y1)

        # Y labels
        self.canvas.create_text(10, y0, text=f"{self.y_min:.0f}", anchor="w")
        self.canvas.create_text(10, y1, text=f"{self.y_max:.0f}", anchor="w")

        # Draw series
        self._draw_series(self.data_s1, x0, y0, x1, y1)
        self._draw_series(self.data_s2, x0, y0, x1, y1, dash=(3, 3))

        # Legend (simple)
        self.canvas.create_text(x0 + 60, y1 + 10, text="S1 (solid)   S2 (dashed)", anchor="w")

    def _draw_series(self, data, x0, y0, x1, y1, dash=None) -> None:
        if len(data) < 2:
            return
        n = len(data)
        xs = []
        ys = []
        for i, val in enumerate(data):
            x = x0 + (x1 - x0) * (i / max(1, n - 1))
            y = y0 - (y0 - y1) * ((val - self.y_min) / max(0.0001, (self.y_max - self.y_min)))
            xs.append(x)
            ys.append(y)

        points = []
        for x, y in zip(xs, ys):
            points.extend([x, y])

        self.canvas.create_line(*points, dash=dash)