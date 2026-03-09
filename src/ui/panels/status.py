import tkinter as tk
from ...controller.tester_controller import RunState
from ..theme import PANEL, FG, MUTED, FONT_MED, FONT_BIG, GREEN, BLUE, YELLOW, RED


def fmt_hhmm(seconds: float) -> str:
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h:02d}:{m:02d}"


class StatusPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Status", bg=PANEL, fg=FG, font=("DejaVu Sans", 11, "bold"))

        self._vals = {}

        rows = [
            ("Run State", "run_state"),
            ("Mode", "station_mode"),
            ("Elapsed (HH:MM)", "elapsed_hhmm"),
            ("Side Motor", "side_motor"),
            ("Top Motor (S1)", "top_motor_station1"),
            ("Top Motor (S2)", "top_motor_station2"),
            ("Message", "message"),
            ("Log File", "log_path"),
        ]

        for r, (label, key) in enumerate(rows):
            tk.Label(self, text=f"{label}:", bg=PANEL, fg=MUTED, font=FONT_MED).grid(
                row=r, column=0, sticky="w", padx=10, pady=2
            )
            v = tk.Label(self, text="—", bg=PANEL, fg=FG, font=FONT_MED)
            v.grid(row=r, column=1, sticky="w", padx=10, pady=2)
            self._vals[key] = v

        self.grid_columnconfigure(1, weight=1)

    def update(self, status) -> None:
        # state color
        state = status.run_state.value
        color = FG
        if state == RunState.RUNNING.value:
            color = GREEN
        elif state == RunState.PAUSED.value:
            color = YELLOW
        elif state == RunState.ERROR.value:
            color = RED

        self._vals["run_state"].configure(text=state, fg=color)
        self._vals["station_mode"].configure(text=(status.station_mode.value if status.station_mode else "—"), fg=BLUE)
        self._vals["elapsed_hhmm"].configure(text=fmt_hhmm(status.elapsed_s), fg=FG)

        self._vals["side_motor"].configure(text=status.side_motor.value)
        self._vals["top_motor_station1"].configure(text=status.top_motor_station1.value)
        self._vals["top_motor_station2"].configure(text=status.top_motor_station2.value)
        self._vals["message"].configure(text=str(status.message))

    def set_log_path(self, path: str) -> None:
        self._vals["log_path"].configure(text=path)