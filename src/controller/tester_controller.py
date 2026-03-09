# src/controller/tester_controller.py

from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional
import time


class StationMode(str, Enum):
    S1 = "S1"
    S2 = "S2"
    BOTH = "BOTH"


class RunState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class MotorState(str, Enum):
    OFF = "OFF"
    SLEEP = "SLEEP"
    RUN = "RUNNING"


@dataclass(frozen=True)
class TesterStatus:
    run_state: RunState
    station_mode: Optional[StationMode]
    elapsed_s: float

    # Motor states (what UI should show)
    side_motor: MotorState              # always ON during tests
    top_motor_station1: MotorState      # flex/extend motor for station 1
    top_motor_station2: MotorState      # flex/extend motor for station 2

    message: str = ""


class MotorIO:
    """
    Hardware abstraction.

    Today: Simulated/placeholder.
    Later: implement with serial commands to Arduino(s).
    """
    def start_side(self) -> None:
        raise NotImplementedError

    def stop_side(self) -> None:
        raise NotImplementedError

    def set_top_motors(self, *, s1_run: bool, s2_run: bool) -> None:
        """Enable/disable top motors by station."""
        raise NotImplementedError

    def stop_all(self) -> None:
        """Emergency stop / full shutdown."""
        raise NotImplementedError


class SimMotorIO(MotorIO):
    """Safe simulation backend so the controller works before hardware exists."""
    def __init__(self) -> None:
        self.side = MotorState.OFF
        self.top_s1 = MotorState.SLEEP
        self.top_s2 = MotorState.SLEEP

    def start_side(self) -> None:
        self.side = MotorState.RUN

    def stop_side(self) -> None:
        self.side = MotorState.OFF

    def set_top_motors(self, *, s1_run: bool, s2_run: bool) -> None:
        self.top_s1 = MotorState.RUN if s1_run else MotorState.SLEEP
        self.top_s2 = MotorState.RUN if s2_run else MotorState.SLEEP

    def stop_all(self) -> None:
        self.side = MotorState.OFF
        self.top_s1 = MotorState.SLEEP
        self.top_s2 = MotorState.SLEEP


class TesterController:
    """
    State machine + truth table.

    - Station mode selection allowed only in IDLE
    - Start/Stop/Pause/Resume control the motors via MotorIO
    - UI should call get_status() to render everything
    """
    def __init__(self, motor_io: Optional[MotorIO] = None) -> None:
        self._motor = motor_io if motor_io is not None else SimMotorIO()

        self._run_state: RunState = RunState.IDLE
        self._station_mode: Optional[StationMode] = None

        self._start_t: Optional[float] = None
        self._pause_t: Optional[float] = None
        self._paused_total_s: float = 0.0

        self._last_message: str = "Sleeping (IDLE)."

    # -------------------------
    # Public API for UI
    # -------------------------
    def set_station_mode(self, mode: StationMode) -> None:
        if self._run_state != RunState.IDLE:
            raise RuntimeError("Cannot change station mode while running/paused.")
        self._station_mode = mode
        self._last_message = f"Mode selected: {mode.value}."

    def start_test(self) -> None:
        if self._run_state != RunState.IDLE:
            raise RuntimeError("Test already running or paused.")
        if self._station_mode is None:
            raise RuntimeError("Select station mode (S1/S2/BOTH) before starting.")

        # Start session timer
        self._start_t = time.time()
        self._pause_t = None
        self._paused_total_s = 0.0

        # Apply motor truth-table
        self._apply_running_outputs(self._station_mode)

        self._run_state = RunState.RUNNING
        self._last_message = f"Test started ({self._station_mode.value})."

    def pause_test(self) -> None:
        if self._run_state != RunState.RUNNING:
            raise RuntimeError("Can only pause while RUNNING.")
        self._pause_t = time.time()

        # Pause behavior: sleep/stop everything
        self._motor.stop_all()

        self._run_state = RunState.PAUSED
        self._last_message = "Paused (motors sleeping)."

    def resume_test(self) -> None:
        if self._run_state != RunState.PAUSED:
            raise RuntimeError("Can only resume while PAUSED.")
        if self._station_mode is None:
            raise RuntimeError("No station mode set.")

        # Update paused time
        assert self._pause_t is not None
        self._paused_total_s += time.time() - self._pause_t
        self._pause_t = None

        # Re-apply truth-table outputs
        self._apply_running_outputs(self._station_mode)

        self._run_state = RunState.RUNNING
        self._last_message = "Resumed."

    def stop_test(self) -> None:
        if self._run_state == RunState.IDLE:
            return  # already stopped; no-op is fine
        # Shutdown everything
        self._motor.stop_all()

        self._run_state = RunState.IDLE
        self._start_t = None
        self._pause_t = None
        self._paused_total_s = 0.0

        self._last_message = "Stopped. Sleeping (IDLE)."

    def estop(self) -> None:
        """Hard stop: go to ERROR state."""
        self._motor.stop_all()
        self._run_state = RunState.ERROR
        self._last_message = "E-STOP triggered. Motors off. Reset required."

    def reset_error(self) -> None:
        if self._run_state != RunState.ERROR:
            return
        # After a fault, we go back to IDLE safely
        self._motor.stop_all()
        self._run_state = RunState.IDLE
        self._start_t = None
        self._pause_t = None
        self._paused_total_s = 0.0
        self._last_message = "Reset from ERROR. Sleeping (IDLE)."

    def get_status(self) -> TesterStatus:
        elapsed = self._compute_elapsed_s()

        # If using SimMotorIO, we can mirror its states for UI.
        side = getattr(self._motor, "side", MotorState.OFF)
        top1 = getattr(self._motor, "top_s1", MotorState.SLEEP)
        top2 = getattr(self._motor, "top_s2", MotorState.SLEEP)

        return TesterStatus(
            run_state=self._run_state,
            station_mode=self._station_mode,
            elapsed_s=elapsed,
            side_motor=side,
            top_motor_station1=top1,
            top_motor_station2=top2,
            message=self._last_message,
        )

    def get_status_dict(self) -> dict:
        """Handy if your UI likes plain dicts."""
        return asdict(self.get_status())

    # -------------------------
    # Internals
    # -------------------------
    def _apply_running_outputs(self, mode: StationMode) -> None:
        # Side motor always runs during tests
        self._motor.start_side()

        # Top motors depend on station mode
        if mode == StationMode.S1:
            self._motor.set_top_motors(s1_run=True, s2_run=False)
        elif mode == StationMode.S2:
            self._motor.set_top_motors(s1_run=False, s2_run=True)
        elif mode == StationMode.BOTH:
            self._motor.set_top_motors(s1_run=True, s2_run=True)
        else:
            # Safety default
            self._motor.set_top_motors(s1_run=False, s2_run=False)

    def _compute_elapsed_s(self) -> float:
        if self._start_t is None:
            return 0.0

        now = time.time()
        paused_total = self._paused_total_s

        # If currently paused, include the current pause duration too
        if self._run_state == RunState.PAUSED and self._pause_t is not None:
            paused_total += now - self._pause_t

        elapsed = (now - self._start_t) - paused_total
        return max(0.0, float(elapsed))