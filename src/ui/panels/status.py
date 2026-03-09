import tkinter as tk
from tkinter import ttk

class StatusPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Status")

        self._labels = {}

        rows = [
            ("Run State", "run_state"),
            ("Mode", "station_mode"),
            ("Elapsed (s)", "elapsed_s"),
            ("Side Motor", "side_motor"),
            ("Top Motor (S1)", "top_motor_station1"),
            ("Top Motor (S2)", "top_motor_station2"),
            ("Message", "message"),
        ]

        for r, (title, key) in enumerate(rows):
            ttk.Label(self, text=f"{title}:").grid(row=r, column=0, sticky="w", padx=10, pady=2)
            val = ttk.Label(self, text="—")
            val.grid(row=r, column=1, sticky="w", padx=10, pady=2)
            self._labels[key] = val

        self.columnconfigure(1, weight=1)

    def update(self, status) -> None:
        self._labels["run_state"].configure(text=str(status.run_state.value))
        self._labels["station_mode"].configure(text=str(status.station_mode.value if status.station_mode else "—"))
        self._labels["elapsed_s"].configure(text=f"{status.elapsed_s:.1f}")
        self._labels["side_motor"].configure(text=str(status.side_motor.value))
        self._labels["top_motor_station1"].configure(text=str(status.top_motor_station1.value))
        self._labels["top_motor_station2"].configure(text=str(status.top_motor_station2.value))
        self._labels["message"].configure(text=str(status.message))