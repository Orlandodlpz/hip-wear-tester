from __future__ import annotations
from .sensor import DS18B20


class SensorManager:
    """Manages two DS18B20 sensors — one per test station.

    On construction, provide the 1-Wire addresses for each station.
    If an address is None the reading for that station will always be 0.0.

    The update() method has the same signature as SimSensorManager so
    the dashboard can swap between them without changes.

    Usage:
        # Find connected sensors first:
        #   from .sensor import DS18B20
        #   print(DS18B20.discover())   # e.g. ['28-0516a41a81ff', '28-0516a41b92cc']
        #
        # Then pass the addresses:
        mgr = SensorManager(s1_address="28-xxxx", s2_address="28-yyyy")
    """

    def __init__(
        self,
        s1_address: str | None = None,
        s2_address: str | None = None,
    ) -> None:
        self._sensor_s1 = DS18B20(s1_address) if s1_address else None
        self._sensor_s2 = DS18B20(s2_address) if s2_address else None

    def update(self, *, running: bool, active_s1: bool, active_s2: bool) -> dict:
        """Read both sensors and return {"S1": float, "S2": float}.

        Returns 0.0 for a station if its sensor is not configured or if
        the read fails.
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

        return {"S1": t1, "S2": t2}
