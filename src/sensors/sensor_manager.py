from __future__ import annotations
import threading
import time
from .sensor import DS18B20


# How often the background thread re-reads each DS18B20. The sensor's
# kernel-side conversion takes ~750 ms internally regardless of how often
# we poll, so reading more than once per second wastes CPU and (more
# importantly) blocks the calling thread for ~750 ms each time. Temperatures
# in a wear-test rig don't change fast enough for sub-second resolution to
# matter — the previous unthreaded code blocked the GUI for ~750 ms every
# 200 ms refresh.
SENSOR_POLL_INTERVAL_S = 2.0


class SensorManager:
    """Manages DS18B20 sensors for the two test stations.

    On construction, provide the 1-Wire address(es) for each station.

    SHARED-SENSOR MODE:
        If only s1_address is provided (s2_address=None), the single sensor's
        reading is mirrored to BOTH stations. This is the current rig setup —
        we have one working DS18B20 and the second station's reading uses
        the same value. Once a second sensor is added, pass its address as
        s2_address and each station will get its own reading.

    THREADING:
        A background daemon thread polls the configured sensor(s) every
        SENSOR_POLL_INTERVAL_S seconds. The kernel's 1-Wire read blocks for
        ~750 ms per sensor (DS18B20 intrinsic conversion time), so reading
        synchronously from the GUI thread freezes the UI. update() now just
        returns the most recent cached value — non-blocking, instant return.

    The update() method has the same signature as SimSensorManager so the
    dashboard can swap between them without changes.

    Usage:
        # Find connected sensors first:
        #   from .sensor import DS18B20
        #   print(DS18B20.discover())   # e.g. ['28-000000b9f30a']
        #
        # Single-sensor (mirrored) configuration:
        mgr = SensorManager(s1_address="28-000000b9f30a")
        # Two-sensor configuration:
        mgr = SensorManager(s1_address="28-xxxx", s2_address="28-yyyy")
    """

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

        Non-blocking — the background thread does the actual sensor reads.
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
