import tkinter as tk
from tkinter import messagebox

from ..controller.tester_controller import StationMode, RunState, TesterController
from ..sensors.sim_sensor_manager import SimSensorManager

from .panels.station_select import StationSelectPanel
from .panels.status import StatusPanel
from .panels.buttons import ButtonsPanel
from .panels.temp_display import TempDisplayPanel
from .panels.temp_graph import TempGraphPanel


class Dashboard(tk.Frame):
    def __init__(self, parent: tk.Misc, controller: TesterController) -> None:
        super().__init__(parent)
        self.controller = controller
        self.sensors = SimSensorManager()

        # Panels
        self.station_panel = StationSelectPanel(self, controller=self.controller)
        self.status_panel = StatusPanel(self)
        self.temp_display = TempDisplayPanel(self)
        self.temp_graph = TempGraphPanel(self)
        self.buttons_panel = ButtonsPanel(self, controller=self.controller)

        # Layout (grid)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.rowconfigure(0, weight=0)  # station + status
        self.rowconfigure(1, weight=0)  # temp cards
        self.rowconfigure(2, weight=1)  # graph
        self.rowconfigure(3, weight=0)  # buttons

        self.station_panel.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        self.status_panel.grid(row=0, column=1, sticky="ew", padx=12, pady=(12, 6))

        self.temp_display.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=6)
        self.temp_graph.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=12, pady=6)

        self.buttons_panel.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(6, 12))

        # Start periodic UI updates
        self.after(200, self._tick)

    def _tick(self) -> None:
        try:
            status = self.controller.get_status()

            # Determine which stations are active for sim + display
            mode = status.station_mode
            active_s1 = (mode == StationMode.S1) or (mode == StationMode.BOTH)
            active_s2 = (mode == StationMode.S2) or (mode == StationMode.BOTH)
            running = (status.run_state == RunState.RUNNING)

            temps = self.sensors.update(running=running, active_s1=active_s1, active_s2=active_s2)

            # Sync panels
            self.station_panel.sync(status)
            self.status_panel.update(status)
            self.buttons_panel.sync(status)
            self.temp_display.update(temps=temps, mode=mode, run_state=status.run_state)
            self.temp_graph.update(temps=temps, mode=mode, run_state=status.run_state)

        except Exception as e:
            # If something unexpected happens, surface it instead of silently dying
            messagebox.showerror("Dashboard Error", str(e))

        # schedule next refresh
        self.after(200, self._tick)