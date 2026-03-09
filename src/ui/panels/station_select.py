import tkinter as tk
from tkinter import messagebox

from ...controller.tester_controller import TesterController, StationMode, RunState
from ..theme import PANEL, FG, MUTED, BLUE, FONT_MED, FONT_BIG


class StationSelectPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc, controller: TesterController) -> None:
        super().__init__(parent, text="Station Selection", bg=PANEL, fg=FG, font=("DejaVu Sans", 11, "bold"))
        self.controller = controller
        self._var = tk.StringVar(value=StationMode.S1.value)

        tk.Label(self, text="Choose mode (only while IDLE):", bg=PANEL, fg=MUTED, font=FONT_BIG).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        row = tk.Frame(self, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(0, 10))

        self._rb_s1 = tk.Radiobutton(
            row, text="Station 1", value=StationMode.S1.value, variable=self._var,
            command=self._on_change, bg=PANEL, fg=FG, selectcolor=PANEL,
            activebackground=PANEL, activeforeground=FG, font=FONT_BIG
        )
        self._rb_s2 = tk.Radiobutton(
            row, text="Station 2", value=StationMode.S2.value, variable=self._var,
            command=self._on_change, bg=PANEL, fg=FG, selectcolor=PANEL,
            activebackground=PANEL, activeforeground=FG, font=FONT_BIG
        )
        self._rb_both = tk.Radiobutton(
            row, text="Both", value=StationMode.BOTH.value, variable=self._var,
            command=self._on_change, bg=PANEL, fg=BLUE, selectcolor=PANEL,
            activebackground=PANEL, activeforeground=BLUE, font=FONT_BIG
        )

        self._rb_s1.pack(side="left", expand=True, padx=18)
        self._rb_s2.pack(side="left", expand=True, padx=18)
        self._rb_both.pack(side="left", expand=True, padx=18)

        # init controller mode
        try:
            self.controller.set_station_mode(StationMode(self._var.get()))
        except Exception:
            pass

    def _on_change(self) -> None:
        try:
            self.controller.set_station_mode(StationMode(self._var.get()))
        except Exception as e:
            messagebox.showwarning("Not Allowed", str(e))
            st = self.controller.get_status()
            if st.station_mode is not None:
                self._var.set(st.station_mode.value)

    def sync(self, status) -> None:
        disabled = status.run_state != RunState.IDLE
        state = "disabled" if disabled else "normal"
        self._rb_s1.configure(state=state)
        self._rb_s2.configure(state=state)
        self._rb_both.configure(state=state)

        if status.station_mode is not None and self._var.get() != status.station_mode.value:
            self._var.set(status.station_mode.value)