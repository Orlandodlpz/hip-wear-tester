from __future__ import annotations
from .sensor import DS18B20


class SensorManager:
    """Manages DS18B20 sensors for the two test stations.

    On construction, provide the 1-Wire address(es) for each station.

    SHARED-SENSOR MODE:
        If only s1_address is provided (s2_address=None), the single sensor's
        reading is mirrored to BOTH stations. This is the current rig setup —
        we have one working DS18B20 and the second station's reading uses
        the same value. Once a second sensor is added, pass its address as
        s2_address and each station will get its own reading.

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

    def update(self, *, running: bool, active_s1: bool, active_s2: bool) -> dict:
        """Read sensor(s) and return {"S1": float, "S2": float}.

        Returns 0.0 for a station if the sensor read fails or no sensor is
        configured (and mirroring isn't active for that station).
        """
        t1 = 0.0
        t2 = 0.0

        if self._sensor_s1 is not None:
            reading = self._sensor_s1.read_celsius()
            if reading is not None:
                t1 = reading

        if self._sensor_s2 is not None:
            reading = self._sensor_s2.read_celsius()
            if reading is not None:
                t2 = reading
        elif self._mirror:
            # Single-sensor rig: station 2's value mirrors station 1's.
            t2 = t1

        return {"S1": t1, "S2": t2}
