import tkinter as tk
from tkinter import ttk
from ...controller.tester_controller import StationMode, RunState


class TempDisplayPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Temperature Readings (Sim)")

        self.s1_frame = ttk.Frame(self)
        self.s2_frame = ttk.Frame(self)

        self.s1_label = ttk.Label(self.s1_frame, text="Station 1: — °C", font=("Arial", 14))
        self.s2_label = ttk.Label(self.s2_frame, text="Station 2: — °C", font=("Arial", 14))

        self.s1_state = ttk.Label(self.s1_frame, text="Inactive", font=("Arial", 10))
        self.s2_state = ttk.Label(self.s2_frame, text="Inactive", font=("Arial", 10))

        self.s1_label.grid(row=0, column=0, sticky="w")
        self.s1_state.grid(row=1, column=0, sticky="w")
        self.s2_label.grid(row=0, column=0, sticky="w")
        self.s2_state.grid(row=1, column=0, sticky="w")

        self.s1_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=10)
        self.s2_frame.grid(row=0, column=1, sticky="ew", padx=12, pady=10)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def update(self, *, temps: dict, mode: StationMode, run_state: RunState) -> None:
        t1 = temps.get("S1", 0.0)
        t2 = temps.get("S2", 0.0)

        self.s1_label.configure(text=f"Station 1: {t1:.2f} °C")
        self.s2_label.configure(text=f"Station 2: {t2:.2f} °C")

        active_s1 = (mode == StationMode.S1) or (mode == StationMode.BOTH)
        active_s2 = (mode == StationMode.S2) or (mode == StationMode.BOTH)
        running = (run_state == RunState.RUNNING)

        self.s1_state.configure(text=("Running" if (running and active_s1) else "Inactive"))
        self.s2_state.configure(text=("Running" if (running and active_s2) else "Inactive"))