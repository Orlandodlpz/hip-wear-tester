from __future__ import annotations
import threading
import time
from .sensor import DS18B20


SENSOR_POLL_INTERVAL_S = 2.0


class SensorManager:

    def __init__(
        self,
        s1_address: str | None = None,
        s2_address: str | None = None,
    ) -> None:
        self._sensor_s1 = DS18B20(s1_address) if s1_address else None
        self._sensor_s2 = DS18B20(s2_address) if s2_address else None

        # If only one sensor is configured, mirror its value to the other
        # station. This is the supported single-sensor mode.
        self._mirror = (self._sensor_s1 is not None) and (self._sensor_s2 is None)

        # Cached readings written by the background thread, read by update().
        # Lock protects reads/writes since they're on different threads.
        self._lock = threading.Lock()
        self._cached_t1: float = 0.0
        self._cached_t2: float = 0.0

        # Start the polling thread. Daemon=True so it dies when the main
        # process exits. Only start if at least one sensor is configured —
        # if neither is set, update() always returns 0.0 anyway.
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        if self._sensor_s1 is not None or self._sensor_s2 is not None:
            self._thread = threading.Thread(
                target=self._poll_loop,
                name="DS18B20-poller",
                daemon=True,
            )
            self._thread.start()

    def _poll_loop(self) -> None:
        """Background thread: periodically read each sensor and cache the
        result. Failures (sensor disconnected, CRC error) leave the previous
        cached value in place rather than zeroing it — that gives a smoother
        graph during transient read errors. Only zero on init."""
        while not self._stop_event.is_set():
            t1 = None
            t2 = None
            if self._sensor_s1 is not None:
                t1 = self._sensor_s1.read_celsius()
            if self._sensor_s2 is not None:
                t2 = self._sensor_s2.read_celsius()

            with self._lock:
                if t1 is not None:
                    self._cached_t1 = t1
                if t2 is not None:
                    self._cached_t2 = t2

            # Wait, but interruptibly — Event.wait() returns immediately if
            # _stop_event is set, so shutdown is responsive.
            if self._stop_event.wait(SENSOR_POLL_INTERVAL_S):
                return

    def stop(self) -> None:
        """Signal the polling thread to exit. Optional — daemon thread dies
        on process exit anyway, but call this explicitly during clean shutdown
        to avoid a stale read in flight."""
        self._stop_event.set()

    def update(self, *, running: bool, active_s1: bool, active_s2: bool) -> dict:
        """Return the most recently cached {"S1": float, "S2": float}.
        Non-blocking: the background thread does the actual sensor reads.
        running / active_s1 / active_s2 are kept in the signature for
        compatibility with SimSensorManager but aren't used (the real sensor
        always reads regardless of station mode).
        """
        with self._lock:
            t1 = self._cached_t1
            t2 = self._cached_t2

        # Mirror after the lock so we always return a self-consistent pair.
        if self._mirror:
            t2 = t1

        return {"S1": t1, "S2": t2}
