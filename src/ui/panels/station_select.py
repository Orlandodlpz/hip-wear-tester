import tkinter as tk
from tkinter import ttk, messagebox

from ...controller.tester_controller import TesterController, StationMode, RunState


class StationSelectPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc, controller: TesterController) -> None:
        super().__init__(parent, text="Station Selection")
        self.controller = controller

        self._var = tk.StringVar(value=StationMode.S1.value)

        ttk.Label(self, text="Choose mode (only while IDLE):").grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))

        self._rb_s1 = ttk.Radiobutton(self, text="Station 1", value=StationMode.S1.value, variable=self._var, command=self._on_change)
        self._rb_s2 = ttk.Radiobutton(self, text="Station 2", value=StationMode.S2.value, variable=self._var, command=self._on_change)
        self._rb_both = ttk.Radiobutton(self, text="Both", value=StationMode.BOTH.value, variable=self._var, command=self._on_change)

        self._rb_s1.grid(row=1, column=0, sticky="w", padx=10, pady=2)
        self._rb_s2.grid(row=1, column=1, sticky="w", padx=10, pady=2)
        self._rb_both.grid(row=1, column=2, sticky="w", padx=10, pady=2)

        for c in range(3):
            self.columnconfigure(c, weight=1)

        # Initialize controller mode
        try:
            self.controller.set_station_mode(StationMode(self._var.get()))
        except Exception:
            pass

    def _on_change(self) -> None:
        try:
            self.controller.set_station_mode(StationMode(self._var.get()))
        except Exception as e:
            messagebox.showwarning("Not Allowed", str(e))
            # revert UI selection to controller’s current mode
            st = self.controller.get_status()
            if st.station_mode is not None:
                self._var.set(st.station_mode.value)

    def sync(self, status) -> None:
        # Disable selection while running/paused/error
        disabled = status.run_state != RunState.IDLE
        state = "disabled" if disabled else "normal"
        self._rb_s1.configure(state=state)
        self._rb_s2.configure(state=state)
        self._rb_both.configure(state=state)

        # Keep selection aligned with controller
        if status.station_mode is not None:
            if self._var.get() != status.station_mode.value:
                self._var.set(status.station_mode.value)