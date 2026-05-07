from __future__ import annotations                                  
from dataclasses import dataclass, asdict                                                                                                                                                                           
from enum import Enum                                                                                                                                                                                               
from typing import Optional                                                                                                                                                                                         
import time                                                                                                                                                                                                         
import threading                                                                                                                                                                                                  

from ..uno_comms.uno_manager import UnoManager                                                                                                                                                                      
  
                                                                                                                                                                                                                      
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
    cycles: int
    completed_cycles: int

    side_motor: MotorState
    top_motor_station1: MotorState
    top_motor_station2: MotorState

    message: str = ""


class MotorIO:
    def start_test(self, mode: StationMode, cycles: int, *, is_resume: bool = False) -> None:
        raise NotImplementedError

    def stop_all(self) -> None:
        raise NotImplementedError

    def is_done(self) -> bool:
        raise NotImplementedError


class SimMotorIO(MotorIO):
    def __init__(self) -> None:
        self.side = MotorState.OFF
        self.top_s1 = MotorState.SLEEP
        self.top_s2 = MotorState.SLEEP
        self._running = False
        self.completed_cycles = 0                                                                                                                                                                                     
                                                                                                                                                                                                                      
    def start_test(self, mode: StationMode, cycles: int, *, is_resume: bool = False) -> None:
        self.side = MotorState.RUN
        if mode == StationMode.S1:
            self.top_s1 = MotorState.RUN
            self.top_s2 = MotorState.SLEEP
        elif mode == StationMode.S2:
            self.top_s1 = MotorState.SLEEP
            self.top_s2 = MotorState.RUN
        elif mode == StationMode.BOTH:
            self.top_s1 = MotorState.RUN
            self.top_s2 = MotorState.RUN
        self._running = True
   
    def stop_all(self) -> None:                                                                                                                                                                                     
        self.side = MotorState.OFF                                                                                                                                                                                
        self.top_s1 = MotorState.SLEEP
        self.top_s2 = MotorState.SLEEP                                                                                                                                                                              
        self._running = False
                                                                                                                                                                                                                      
    def is_done(self) -> bool:                                                                                                                                                                                    
        if self._running:
            self.stop_all()
            return True                                                                                                                                                                                             
        return False
                                                                                                                                                                                                                      
                                                                                                                                                                                                                    
class ArduinoMotorIO(MotorIO):
    def __init__(self, lateral_port: str, top_port: str, baudrate: int = 9600) -> None:
        self._uno = UnoManager(
            lateral_port=lateral_port,
            top_port=top_port,
            baudrate=baudrate,
        )
        self._uno.connect()

        self.side = MotorState.OFF
        self.top_s1 = MotorState.SLEEP
        self.top_s2 = MotorState.SLEEP

        self._lat_done = False
        self._top_done = False
        self.completed_cycles = 0

        # Per-Arduino cycle progress. The public completed_cycles counter is
        # driven by the LATERAL Arduino's CYCLE:n messages
        self._lat_last_cycle = 0
        self._top_last_cycle = 0
        self._resume_offset = 0

    def start_test(self, mode: StationMode, cycles: int, *, is_resume: bool = False) -> None:
        """Start a fresh run, OR resume a paused one.

        On a fresh start (is_resume=False, the default), all counters and
        state are reset to zero. On a resume (is_resume=True), the public
        counter and resume offset are PRESERVED — resume_test() in the
        controller will have set them already, and start_test must not
        clobber them.
        """
        # Drain any stale CYCLE/DONE/STOPPED lines that the previous run
        # might have left in the serial input buffer. If we don't drain, those
        # stale messages will be parsed by is_done() AFTER we send the new
        # START, and they can corrupt the fresh counter (e.g. stale CYCLE:42
        # from a prior run that was Stopped at 50 would set completed_cycles
        # to 42 before any real new CYCLE:1 arrives).
        try:
            self._uno.poll_lines()  # discard
        except Exception:
            pass

        self._lat_done = False
        self._top_done = False

        if not is_resume:
            self.completed_cycles = 0
            self._lat_last_cycle = 0
            self._top_last_cycle = 0
            self._resume_offset = 0
        else:
            # Resume: the firmware will count its NEW run starting from
            # CYCLE:1, so reset the per-Arduino raw counters. completed_cycles
            # and _resume_offset stay as resume_test() set them.
            self._lat_last_cycle = 0
            self._top_last_cycle = 0

        self.side = MotorState.RUN
        if mode == StationMode.S1:
            self.top_s1 = MotorState.RUN
            self.top_s2 = MotorState.SLEEP
        elif mode == StationMode.S2:
            self.top_s1 = MotorState.SLEEP
            self.top_s2 = MotorState.RUN
        elif mode == StationMode.BOTH:
            self.top_s1 = MotorState.RUN
            self.top_s2 = MotorState.RUN

        self._uno.start_mode(mode, cycles)

    def stop_all(self) -> None:
        self._uno.stop_all()
        self.side = MotorState.OFF
        self.top_s1 = MotorState.SLEEP
        self.top_s2 = MotorState.SLEEP
        self._lat_done = True
        self._top_done = True

    def is_done(self) -> bool:
        messages = self._uno.poll_lines()
        for source, line in messages:
            # Cycle counter is driven by the LATERAL Arduino only. The top
            # Arduino's CYCLE:n messages are still recorded for diagnostics
            # but they do NOT advance completed_cycles — the lateral runs
            # slightly slower per cycle (longer pulses, more steps) so its
            # count is the right ceiling for "how many overall cycles have
            # actually completed end-to-end."
            if line.startswith("CYCLE:"):
                try:
                    n = int(line.split(":")[1])
                except (IndexError, ValueError):
                    n = None

                if n is not None:
                    if source == "LAT":
                        self._lat_last_cycle = n
                        # Public counter = lateral's CYCLE:n + resume_offset.
                        # On a fresh start, _resume_offset is 0 so the GUI
                        # shows 1, 2, 3, ... as expected. After a resume,
                        # _resume_offset is set to the cycle count at pause
                        # so the counter continues from where it left off
                        # (e.g. paused at 387, resume sees CYCLE:1 from the
                        # firmware → public counter shows 388).
                        candidate = n + self._resume_offset
                        if candidate > self.completed_cycles:
                            self.completed_cycles = candidate
                    elif source == "TOP":
                        self._top_last_cycle = n

            if source == "LAT" and line.startswith("DONE:LAT"):
                self._lat_done = True
                self.side = MotorState.OFF
            elif source == "TOP" and line.startswith("DONE:TOP"):
                self._top_done = True
                self.top_s1 = MotorState.SLEEP
                self.top_s2 = MotorState.SLEEP

        return self._lat_done and self._top_done
                                                                                                                                                                                                                      
   
class TesterController:                                                                                                                                                                                             
    def __init__(self, motor_io: Optional[MotorIO] = None) -> None:                                                                                                                                               
        self._motor = motor_io if motor_io is not None else ArduinoMotorIO(
            # for testing with rp 4, use these ports:                                                                                                                                                               
            # lateral_port="/dev/ttyACM0",                                                                                                                                                                          
            # top_port="/dev/ttyACM1",                                                                                                                                                                              
            # for testing with macbook, use these ports:                                                                                                                                                            
            lateral_port="/dev/cu.usbmodem11301",
            top_port="/dev/cu.usbmodem11401",
            baudrate=9600,
        )                                                                                                                                                                                                         
                                                                                                                                                                                                                      
        self._target_cycles: int = 5000000  # number of cycles sent to Arduino                                                                                                                                            
        self._worker: Optional[threading.Thread] = None
                                                                                                                                                                                                                      
        self._run_state: RunState = RunState.IDLE                                                                                                                                                                   
        self._station_mode: Optional[StationMode] = None
                                                                                                                                                                                                                      
        self._start_t: Optional[float] = None                                                                                                                                                                       
        self._pause_t: Optional[float] = None
        self._paused_total_s: float = 0.0                                                                                                                                                                           
                                                                                                                                                                                                                    
        self._last_message: str = "Sleeping (IDLE)."

        # Snapshot of completed_cycles taken at pause_test() time. resume_test()
        # uses it to (a) tell the Arduinos to only run the REMAINING cycles, and
        # (b) restore the GUI counter so it picks up where it left off.
        self._cycles_at_pause: int = 0

        # If the motor backend exposes connection state, surface a warning
        # at startup when one or both Arduinos didn't connect. The app stays
        # IDLE so the operator can plug in the missing board and try START
        # — start_test() will refuse cleanly until both are available.
        uno = getattr(self._motor, "_uno", None)
        if uno is not None:
            lat_ok = uno.lateral_connected() if hasattr(uno, "lateral_connected") else True
            top_ok = uno.top_connected() if hasattr(uno, "top_connected") else True
            missing: list[str] = []
            if not lat_ok:
                missing.append("Lateral")
            if not top_ok:
                missing.append("Top")
            if missing:
                self._last_message = (
                    f"{' and '.join(missing)} Arduino not connected. "
                    "Plug in and restart, or run with the simulator backend."
                )                                                                                                                                                                
   
    # -------------------------                                                                                                                                                                                     
    # Public API for UI                                                                                                                                                                                           
    # -------------------------                                                                                                                                                                                     
    def set_station_mode(self, mode: StationMode) -> None:                                                                                                                                                        
        if self._run_state != RunState.IDLE:                                                                                                                                                                        
            raise RuntimeError("Cannot change station mode while running/paused.")
        self._station_mode = mode                                                                                                                                                                                   
        self._last_message = f"Mode selected: {mode.value}."                                                                                                                                                        
   
    def set_cycles(self, cycles: int) -> None:                                                                                                                                                                      
        """Set the number of cycles to send to the Arduino. Each cycle runs                                                                                                                                       
        the hardcoded back-and-forth steps defined on the Arduino."""                                                                                                                                               
        if self._run_state != RunState.IDLE:                                                                                                                                                                        
            raise RuntimeError("Cannot change cycles while running/paused.")                                                                                                                                        
        if cycles < 1:                                                                                                                                                                                              
            raise ValueError("Cycles must be >= 1.")                                                                                                                                                              
        if cycles > 5000000:
            raise ValueError("Cycles must be <= 5,000,000 (Arduino MAX_CYCLES limit).")
        self._target_cycles = cycles                                                                                                                                                                                
        self._last_message = f"Cycles set to {cycles}."                                                                                                                                                             
   
    def start_test(self) -> None:                                                                                                                                                                                   
        if self._run_state != RunState.IDLE:                                                                                                                                                                      
            raise RuntimeError("Test already running or paused.")
        if self._station_mode is None:                                                                                                                                                                              
            raise RuntimeError("Select station mode (S1/S2/BOTH) before starting.")
                                                                                                                                                                                                                      
        self._start_t = time.time()                                                                                                                                                                               
        self._pause_t = None                                                                                                                                                                                        
        self._paused_total_s = 0.0                                                                                                                                                                                

        self._run_state = RunState.RUNNING                                                                                                                                                                          
        self._last_message = f"Test started ({self._station_mode.value}, {self._target_cycles} cycles)."
                                                                                                                                                                                                                      
        self._motor.start_test(self._station_mode, self._target_cycles)                                                                                                                                           
                                                                                                                                                                                                                      
        self._worker = threading.Thread(target=self._monitor_test, daemon=True)                                                                                                                                     
        self._worker.start()
                                                                                                                                                                                                                      
    def _monitor_test(self) -> None:
        try:
            while self._run_state == RunState.RUNNING:
                if self._motor.is_done():
                    self._run_state = RunState.IDLE
                    self._last_message = "Test complete."
                    break
                time.sleep(0.05)
        except Exception as exc:
            self._run_state = RunState.ERROR
            self._last_message = f"Hardware error: {exc}"
            self._motor.stop_all()
                                                                                                                                                                                                                      
    def pause_test(self) -> None:
        if self._run_state != RunState.RUNNING:
            raise RuntimeError("Can only pause while RUNNING.")
        self._pause_t = time.time()

        # Snapshot the cycle count BEFORE stopping the motors. We need this so
        # resume_test() can ask the Arduinos for the remaining cycles only and
        # restore the GUI counter on top of the snapshot.
        self._cycles_at_pause = getattr(self._motor, "completed_cycles", 0)

        self._motor.stop_all()
        self._run_state = RunState.PAUSED
        self._last_message = (
            f"Paused at cycle {self._cycles_at_pause} of {self._target_cycles}."
        )

    def resume_test(self) -> None:
        if self._run_state != RunState.PAUSED:
            raise RuntimeError("Can only resume while PAUSED.")
        if self._station_mode is None:
            raise RuntimeError("No station mode set.")

        assert self._pause_t is not None
        self._paused_total_s += time.time() - self._pause_t
        self._pause_t = None

        # Compute remaining cycles. If we already finished the target before
        # pause (edge case), there's nothing to do.
        remaining = max(0, self._target_cycles - self._cycles_at_pause)
        if remaining == 0:
            self._run_state = RunState.IDLE
            self._last_message = "Already complete; nothing to resume."
            return

        # IMPORTANT: prime completed_cycles and _resume_offset BEFORE calling
        # start_test(is_resume=True). is_resume=True tells the motor backend
        # NOT to clobber these fields. After this, when the Arduinos send
        # CYCLE:1 (their fresh post-resume count), is_done() will compute
        # candidate = 1 + _cycles_at_pause = _cycles_at_pause + 1 and the
        # public counter continues from where it left off.
        if hasattr(self._motor, "completed_cycles"):
            self._motor.completed_cycles = self._cycles_at_pause
        if hasattr(self._motor, "_resume_offset"):
            self._motor._resume_offset = self._cycles_at_pause

        self._motor.start_test(self._station_mode, remaining, is_resume=True)

        self._run_state = RunState.RUNNING
        self._last_message = (
            f"Resumed from cycle {self._cycles_at_pause}; "
            f"{remaining} cycles remaining."
        )

        self._worker = threading.Thread(target=self._monitor_test, daemon=True)
        self._worker.start()

    def stop_test(self) -> None:
        if self._run_state == RunState.IDLE:
            # Already idle, but reset the counter anyway so the GUI shows 0
            # cleanly when the operator looks at it before the next start.
            if hasattr(self._motor, "completed_cycles"):
                self._motor.completed_cycles = 0
            if hasattr(self._motor, "_lat_last_cycle"):
                self._motor._lat_last_cycle = 0
            if hasattr(self._motor, "_top_last_cycle"):
                self._motor._top_last_cycle = 0
            if hasattr(self._motor, "_resume_offset"):
                self._motor._resume_offset = 0
            self._cycles_at_pause = 0
            return
        self._motor.stop_all()
        self._run_state = RunState.IDLE
        self._start_t = None
        self._pause_t = None
        self._paused_total_s = 0.0
        self._cycles_at_pause = 0

        # Reset the cycle counter immediately so the GUI shows 0 right after
        # Stop, not the count from the previous run. (start_test() also resets
        # this when a new run begins, but doing it here gives clean visual
        # feedback the moment the user hits Stop.)
        if hasattr(self._motor, "completed_cycles"):
            self._motor.completed_cycles = 0
        if hasattr(self._motor, "_lat_last_cycle"):
            self._motor._lat_last_cycle = 0
        if hasattr(self._motor, "_top_last_cycle"):
            self._motor._top_last_cycle = 0
        if hasattr(self._motor, "_resume_offset"):
            self._motor._resume_offset = 0

        self._last_message = "Stopped. Sleeping (IDLE)."
                                                                                                                                                                                                                    
    def estop(self) -> None:                                                                                                                                                                                        
        self._motor.stop_all()
        self._run_state = RunState.ERROR                                                                                                                                                                            
        self._last_message = "E-STOP triggered. Motors off. Reset required."                                                                                                                                      
                                                                                                                                                                                                                      
    def reset_error(self) -> None:
        if self._run_state != RunState.ERROR:                                                                                                                                                                       
            return                                                                                                                                                                                                
        self._motor.stop_all()                                                                                                                                                                                      
        self._run_state = RunState.IDLE
        self._start_t = None                                                                                                                                                                                        
        self._pause_t = None                                                                                                                                                                                      
        self._paused_total_s = 0.0
        self._last_message = "Reset from ERROR. Sleeping (IDLE)."                                                                                                                                                   
   
    def get_status(self) -> TesterStatus:
        elapsed = self._compute_elapsed_s()
        side = getattr(self._motor, "side", MotorState.OFF)
        top1 = getattr(self._motor, "top_s1", MotorState.SLEEP)
        top2 = getattr(self._motor, "top_s2", MotorState.SLEEP)

        completed = getattr(self._motor, "completed_cycles", 0)

        return TesterStatus(
            run_state=self._run_state,
            station_mode=self._station_mode,
            elapsed_s=elapsed,
            cycles=self._target_cycles,
            completed_cycles=completed,
            side_motor=side,
            top_motor_station1=top1,
            top_motor_station2=top2,
            message=self._last_message,
        )
   
    def get_status_dict(self) -> dict:                                                                                                                                                                              
        return asdict(self.get_status())                                                                                                                                                                          

    # -------------------------
    # Internals
    # -------------------------                                                                                                                                                                                     
    def _compute_elapsed_s(self) -> float:
        if self._start_t is None:                                                                                                                                                                                   
            return 0.0                                                                                                                                                                                            
        now = time.time()
        paused_total = self._paused_total_s
        if self._run_state == RunState.PAUSED and self._pause_t is not None:                                                                                                                                        
            paused_total += now - self._pause_t
        elapsed = (now - self._start_t) - paused_total                                                                                                                                                              
        return max(0.0, float(elapsed))    