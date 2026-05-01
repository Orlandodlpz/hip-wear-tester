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
    def start_test(self, mode: StationMode, cycles: int) -> None:
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
                                                                                                                                                                                                                      
    def start_test(self, mode: StationMode, cycles: int) -> None:                                                                                                                                                   
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

        # Per-Arduino cycle progress. The overall counter (completed_cycles)
        # advances only when BOTH Arduinos have reported the same cycle number
        # (i.e. both finished the current overall cycle). For S1/S2 modes the
        # top Arduino still reports CYCLE:n at the same rate as the lateral,
        # so the gating works the same way in all three modes.
        self._lat_last_cycle = 0
        self._top_last_cycle = 0

    def start_test(self, mode: StationMode, cycles: int) -> None:
        self._lat_done = False
        self._top_done = False
        self.completed_cycles = 0
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
            # Track per-Arduino cycle progress. The overall counter only
            # advances when BOTH Arduinos have crossed the same cycle number.
            if line.startswith("CYCLE:"):
                try:
                    n = int(line.split(":")[1])
                except (IndexError, ValueError):
                    n = None

                if n is not None:
                    if source == "LAT":
                        self._lat_last_cycle = n
                    elif source == "TOP":
                        self._top_last_cycle = n

                    overall = min(self._lat_last_cycle, self._top_last_cycle)
                    if overall > self.completed_cycles:
                        self.completed_cycles = overall

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
        if cycles > 10000:
            raise ValueError("Cycles must be <= 10000 (Arduino limit).")
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
        self._motor.stop_all()
        self._run_state = RunState.PAUSED                                                                                                                                                                           
        self._last_message = "Paused (motors sleeping)."                                                                                                                                                          
                                                                                                                                                                                                                      
    def resume_test(self) -> None:
        if self._run_state != RunState.PAUSED:                                                                                                                                                                      
            raise RuntimeError("Can only resume while PAUSED.")                                                                                                                                                     
        if self._station_mode is None:
            raise RuntimeError("No station mode set.")                                                                                                                                                              
                                                                                                                                                                                                                      
        assert self._pause_t is not None
        self._paused_total_s += time.time() - self._pause_t                                                                                                                                                         
        self._pause_t = None                                                                                                                                                                                      

        self._motor.start_test(self._station_mode, self._target_cycles)                                                                                                                                             
   
        self._run_state = RunState.RUNNING                                                                                                                                                                          
        self._last_message = "Resumed."                                                                                                                                                                           

        self._worker = threading.Thread(target=self._monitor_test, daemon=True)                                                                                                                                     
        self._worker.start()
                                                                                                                                                                                                                      
    def stop_test(self) -> None:                                                                                                                                                                                  
        if self._run_state == RunState.IDLE:
            return                                                                                                                                                                                                  
        self._motor.stop_all()
        self._run_state = RunState.IDLE                                                                                                                                                                             
        self._start_t = None                                                                                                                                                                                      
        self._pause_t = None                                                                                                                                                                                        
        self._paused_total_s = 0.0
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