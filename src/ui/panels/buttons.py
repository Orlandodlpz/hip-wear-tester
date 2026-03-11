import tkinter as tk
from tkinter import messagebox

from ...controller.tester_controller import TesterController, RunState
from ..theme import PANEL, FG, YELLOW, RED


class ButtonsPanel(tk.LabelFrame):
    def __init__(self, parent: tk.Misc, controller: TesterController, on_reset) -> None:
        super().__init__(parent, text="Controls", bg=PANEL, fg=FG, font=("DejaVu Sans", 11, "bold"))
        self.controller = controller
        self.on_reset = on_reset

        row = tk.Frame(self, bg=PANEL)
        row.pack(fill="x", padx=10, pady=10)

        self.btn_pause = tk.Button(
            row, text="PAUSE", font=("DejaVu Sans", 22, "bold"),
            bg=YELLOW, fg="black", activebackground=YELLOW,
            height=2, command=self._pause_or_resume
        )
        self.btn_stop = tk.Button(
            row, text="STOP", font=("DejaVu Sans", 22, "bold"),
            bg=YELLOW, fg="black", activebackground=YELLOW,
            height=2, command=self._stop
        )
        self.btn_reset = tk.Button(
            row, text="RESET TEST", font=("DejaVu Sans", 22, "bold"),
            bg="#2aa1ff", fg="black", activebackground="#2aa1ff",
            height=2, command=self._reset
        )
        self.btn_estop = tk.Button(
            row, text="EMERGENCY STOP", font=("DejaVu Sans", 22, "bold"),
            bg=RED, fg="white", activebackground=RED,
            height=2, command=self._estop
        )

        self.btn_pause.pack(side="left", fill="x", expand=True, padx=6)
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=6)
        self.btn_reset.pack(side="left", fill="x", expand=True, padx=6)
        self.btn_estop.pack(side="left", fill="x", expand=True, padx=6)

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

    def _reset(self) -> None:
        try:
            self.on_reset()
        except Exception as e:
            messagebox.showwarning("Reset Failed", str(e))

    def _estop(self) -> None:
        try:
            self.controller.estop()
        except Exception as e:
            messagebox.showwarning("E-STOP Failed", str(e))

    def sync(self, status) -> None:
        if status.run_state == RunState.PAUSED:
            self.btn_pause.configure(text="RESUME")
        else:
            self.btn_pause.configure(text="PAUSE")

        enabled = status.run_state in (RunState.RUNNING, RunState.PAUSED)
        self.btn_pause.configure(state=("normal" if enabled else "disabled"))
        self.btn_stop.configure(state=("normal" if enabled else "disabled"))
        self.btn_reset.configure(state="normal")