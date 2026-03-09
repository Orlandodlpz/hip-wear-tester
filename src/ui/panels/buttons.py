import tkinter as tk
from tkinter import ttk, messagebox

from ...controller.tester_controller import TesterController, RunState


class ButtonsPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc, controller: TesterController) -> None:
        super().__init__(parent, text="Controls")
        self.controller = controller

        self.btn_start = ttk.Button(self, text="Start Test", command=self._start)
        self.btn_pause = ttk.Button(self, text="Pause", command=self._pause_or_resume)
        self.btn_stop = ttk.Button(self, text="Stop Test", command=self._stop)
        self.btn_estop = ttk.Button(self, text="E-STOP", command=self._estop)
        self.btn_reset = ttk.Button(self, text="Reset Error", command=self._reset)

        self.btn_start.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.btn_pause.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.btn_stop.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        self.btn_estop.grid(row=0, column=3, padx=10, pady=10, sticky="ew")
        self.btn_reset.grid(row=0, column=4, padx=10, pady=10, sticky="ew")

        for c in range(5):
            self.columnconfigure(c, weight=1)

    def _start(self) -> None:
        try:
            self.controller.start_test()
        except Exception as e:
            messagebox.showwarning("Start Failed", str(e))

    def _pause_or_resume(self) -> None:
        try:
            st = self.controller.get_status()
            if st.run_state == RunState.RUNNING:
                self.controller.pause_test()
            elif st.run_state == RunState.PAUSED:
                self.controller.resume_test()
        except Exception as e:
            messagebox.showwarning("Action Failed", str(e))

    def _stop(self) -> None:
        try:
            self.controller.stop_test()
        except Exception as e:
            messagebox.showwarning("Stop Failed", str(e))

    def _estop(self) -> None:
        try:
            self.controller.estop()
        except Exception as e:
            messagebox.showwarning("E-STOP Failed", str(e))

    def _reset(self) -> None:
        try:
            self.controller.reset_error()
        except Exception as e:
            messagebox.showwarning("Reset Failed", str(e))

    def sync(self, status) -> None:
        # Pause button label depends on state
        if status.run_state == RunState.PAUSED:
            self.btn_pause.configure(text="Resume")
        else:
            self.btn_pause.configure(text="Pause")

        # Button enable/disable rules
        self.btn_start.configure(state=("normal" if status.run_state == RunState.IDLE else "disabled"))
        self.btn_stop.configure(state=("normal" if status.run_state in (RunState.RUNNING, RunState.PAUSED) else "disabled"))
        self.btn_pause.configure(state=("normal" if status.run_state in (RunState.RUNNING, RunState.PAUSED) else "disabled"))
        self.btn_reset.configure(state=("normal" if status.run_state == RunState.ERROR else "disabled"))
        self.btn_estop.configure(state=("normal" if status.run_state != RunState.IDLE else "normal"))