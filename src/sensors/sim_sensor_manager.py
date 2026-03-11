import random
import time

class SimSensorManager:
    # Generates believable temps for Station 1 and Station 2.
    # - IDLE drifts toward room temp.
    # - RUNNING drifts toward a warm operating temp.
    
    def __init__(self) -> None:
        self._last_t = time.time()
        self._t_s1 = 24.5
        self._t_s2 = 24.7

    def update(self, *, running: bool, active_s1: bool, active_s2: bool) -> dict:
        now = time.time()
        dt = max(0.001, now - self._last_t)
        self._last_t = now

        room = 24.0
        warm = 36.5

    # Targets depend on whether the station is active during RUNNING
        target_s1 = warm if (running and active_s1) else room
        target_s2 = warm if (running and active_s2) else room

    # Simple first-order drift + noise
        k = 0.35 # responsiveness
        noise = 0.06

        self._t_s1 += (target_s1 - self._t_s1) * (1 - pow(2.71828, -k * dt)) + random.uniform(-noise, noise)
        self._t_s2 += (target_s2 - self._t_s2) * (1 - pow(2.71828, -k * dt)) + random.uniform(-noise, noise)

        return {"S1": float(self._t_s1), "S2": float(self._t_s2)}