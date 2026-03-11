import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import time

from ..controller.tester_controller import StationMode, RunState, TesterController
from ..sensors.sim_sensor_manager import SimSensorManager
from ..data.logger import logger

from .panels.station_select import StationSelectPanel
from .panels.status import StatusPanel
from .panels.buttons import ButtonsPanel
from .panels.temp_display import TempDisplayPanel
from .panels.temp_graph import TempGraphPanel

from .theme import BG, PANEL, FG, GREEN, FONT_TITLE, REFRESH_MS, LOG_EVERY_S


class Dashboard(tk.Frame):
    def __init__(self, parent: tk.Misc, controller: TesterController) -> None:
        super().__init__(parent, bg=BG)
        self.controller = controller
        self.sensors = SimSensorManager()

        self.logger: logger | None = None
        self._last_run_state = RunState.IDLE
        self._last_log_wall = 0.0

        # ========= Top header =========
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=14, pady=(14, 8))

        tk.Label(header, text="HIP WEAR TESTER", bg=BG, fg="white", font=FONT_TITLE).pack(side="left")

        # HOME + STATUS navigation buttons
        self.btn_home = tk.Button(
            header, text="HOME", font=("DejaVu Sans", 14, "bold"),
            bg="#3c2a7a", fg="white", activebackground="#3c2a7a",
            command=self._go_home, padx=14, pady=6
        )
        self.btn_status = tk.Button(
            header, text="STATUS", font=("DejaVu Sans", 14, "bold"),
            bg="#1f5cff", fg="white", activebackground="#1f5cff",
            command=self._go_status, padx=14, pady=6
        )

        self.btn_status.pack(side="right", padx=(8, 0))
        self.btn_home.pack(side="right")

        # Big running indicator (shows station mode clearly)
        self.header_state = tk.Label(
            header, text="IDLE — (select mode)", bg=BG, fg=FG, font=("DejaVu Sans", 16, "bold")
        )
        self.header_state.pack(side="right", padx=(12, 12))

        # ========= Notebook (tabs hidden by style in app.py) =========
        self.nb = ttk.Notebook(self, style="Dashboard.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.init_tab = tk.Frame(self.nb, bg=PANEL)
        self.run_tab = tk.Frame(self.nb, bg=PANEL)
        self.nb.add(self.init_tab, text="Initialize")
        self.nb.add(self.run_tab, text="Run")

        # ========= Initialize tab =========
        top_init = tk.Frame(self.init_tab, bg=PANEL)
        top_init.pack(fill="x", padx=12, pady=12)

        self.station_panel = StationSelectPanel(top_init, controller=self.controller)
        self.station_panel.pack(side="left", fill="x", expand=True)

        init_note = tk.Label(
            self.init_tab,
            text="Choose Station Mode in this screen.\nThen press START TEST to begin.",
            font=("DejaVu Sans", 28, "bold"),
            bg=PANEL, fg="#cfcfcf", justify="left"
        )
        init_note.pack(fill="x", padx=12, pady=(0, 12))

        self.btn_init_start = tk.Button(
            self.init_tab,
            text="START TEST",
            font=("DejaVu Sans", 20, "bold"),
            bg="#00ff6a", fg="black", activebackground="#00ff6a",
            padx=30, pady=18,
            command=self._start_from_home
        )
        self.btn_init_start.place(relx=0.5, rely=0.78, anchor="center")

        # ========= Run/Status tab =========
        top_row = tk.Frame(self.run_tab, bg=PANEL)
        top_row.pack(fill="x", padx=12, pady=(12, 6))

        self.status_panel = StatusPanel(top_row)
        self.status_panel.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.temp_display = TempDisplayPanel(top_row)
        self.temp_display.pack(side="left", fill="x", expand=True)

        self.temp_graph = TempGraphPanel(self.run_tab)
        self.temp_graph.pack(fill="both", expand=True, padx=12, pady=6)

        # Buttons: Pause/Stop/Reset/E-Stop
        self.buttons_panel = ButtonsPanel(
            self.run_tab,
            controller=self.controller,
            on_reset=self._reset_test_ui,
        )
        self.buttons_panel.pack(fill="x", padx=12, pady=(6, 12))

        self.after(REFRESH_MS, self._tick)

    # -----------------
    # Navigation actions
    # -----------------
    def _go_home(self) -> None:
        self.nb.select(self.init_tab)

    def _go_status(self) -> None:
        self.nb.select(self.run_tab)

    def _start_from_home(self) -> None:
        try:
            self.controller.start_test()
            self.nb.select(self.run_tab)
        except Exception as e:
            messagebox.showwarning("Start Failed", str(e))

    # -----------------
    # RESET button behavior
    # -----------------
    def _reset_test_ui(self) -> None:
        # Reset Test = stop the controller + clear the current run graph.
        # Keeps the selected station mode so you can start again quickly.
        if not messagebox.askyesno("Reset Test", "Reset will STOP the test and clear the graph.\nContinue?"):
            return

        try:
            self.controller.stop_test()
        except Exception:
            pass

        # Clear graph history + temp mini-graphs so UI looks fresh
        try:
            self.temp_graph.clear()
        except Exception:
            pass
        try:
            self.temp_display.clear_sparklines()
        except Exception:
            pass

        # If logger exists, close it
        if self.logger is not None:
            self.logger.finalize(end_state="RESET")
            self.status_panel.set_log_path(str(self.logger.run_dir))
            self.logger = None

    # -----------------
    # Main refresh loop
    # -----------------
    def _tick(self) -> None:
        try:
            status = self.controller.get_status()

            mode = status.station_mode or StationMode.S1
            active_s1 = (mode == StationMode.S1) or (mode == StationMode.BOTH)
            active_s2 = (mode == StationMode.S2) or (mode == StationMode.BOTH)
            running = (status.run_state == RunState.RUNNING)

            temps = self.sensors.update(running=running, active_s1=active_s1, active_s2=active_s2)

            self._update_header(status)

            self.station_panel.sync(status)
            self.status_panel.update(status)
            self.buttons_panel.sync(status)
            self.temp_display.update(temps=temps, mode=mode, run_state=status.run_state)
            self.temp_graph.update(elapsed_s=status.elapsed_s, temps=temps, mode=mode, run_state=status.run_state)

            self._handle_logging(status=status, temps=temps)

            self._last_run_state = status.run_state

        except Exception as e:
            messagebox.showerror("Dashboard Error", str(e))

        self.after(REFRESH_MS, self._tick)

    def _update_header(self, status) -> None:
        mode = status.station_mode.value if status.station_mode else "—"
        state = status.run_state.value

        if state == "RUNNING":
            self.header_state.configure(text=f"RUNNING — {mode}", fg=GREEN)
        elif state == "PAUSED":
            self.header_state.configure(text=f"PAUSED — {mode}", fg="#ffd000")
        elif state == "ERROR":
            self.header_state.configure(text=f"ERROR — {mode}", fg="#ff3b30")
        else:
            self.header_state.configure(text=f"IDLE — {mode}", fg=FG)

        self.btn_init_start.configure(state=("normal" if status.run_state == RunState.IDLE else "disabled"))

    def _handle_logging(self, status, temps: dict) -> None:
        now = time.time()

        if self._last_run_state != RunState.RUNNING and status.run_state == RunState.RUNNING:
            self.logger = logger()
            mode_str = status.station_mode.value if status.station_mode else "UNKNOWN"
            path = self.logger.start(mode_str)
            self._last_log_wall = 0.0
            self.status_panel.set_log_path(str(path))

        if status.run_state == RunState.RUNNING and self.logger is not None:
            if (now - self._last_log_wall) >= LOG_EVERY_S:
                self._last_log_wall = now
                wall_iso = datetime.now().isoformat(timespec="seconds")
                mode_str = status.station_mode.value if status.station_mode else "UNKNOWN"

                self.logger.log(
                    elapsed_s=status.elapsed_s,
                    elapsed_hhmmss=self._fmt_hhmmss(status.elapsed_s),
                    mode=(status.station_mode.value if status.station_mode else "UNKNOWN"),
                    run_state=status.run_state.value,
                    t1=float(temps.get("S1", 0.0)),
                    t2=float(temps.get("S2", 0.0)),
                    side=status.side_motor.value,
                    top1=status.top_motor_station1.value,
                    top2=status.top_motor_station2.value,
                    message=str(status.message),
                )

        if self.logger is not None and status.run_state in (RunState.IDLE, RunState.ERROR):
            if self._last_run_state in (RunState.RUNNING, RunState.PAUSED):
        # finalize creates graph.png and closes data.txt
                end_state = status.run_state.value
                self.logger.finalize(end_state=end_state)

        # show the folder on the UI (optional)
                if self.logger.run_dir is not None:
                    self.status_panel.set_log_path(str(self.logger.run_dir))

                self.logger = None

    @staticmethod
    def _fmt_hhmmss(seconds: float) -> str:
        s = int(seconds)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}"