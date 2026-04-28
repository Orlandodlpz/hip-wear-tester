from __future__ import annotations
from pathlib import Path


W1_DEVICES_DIR = Path("/sys/bus/w1/devices")


class DS18B20:
    """Reads temperature from a single DS18B20 sensor via the 1-Wire
    filesystem on the Raspberry Pi.

    Each DS18B20 has a unique address like '28-0516a41a81ff'.  The kernel
    exposes readings at:
        /sys/bus/w1/devices/<address>/w1_slave
    """

    def __init__(self, address: str) -> None:
        self.address = address
        self._path = W1_DEVICES_DIR / address / "w1_slave"

    @staticmethod
    def discover() -> list[str]:
        """Return a list of DS18B20 addresses found on the 1-Wire bus."""
        if not W1_DEVICES_DIR.exists():
            return []
        return sorted(
            d.name for d in W1_DEVICES_DIR.iterdir() if d.name.startswith("28-")
        )

    def read_celsius(self) -> float | None:
        """Read the sensor and return temperature in Celsius, or None on
        failure (sensor disconnected, CRC error, etc.)."""
        try:
            text = self._path.read_text()
        except (OSError, IOError):
            return None

        lines = text.strip().splitlines()
        if len(lines) < 2:
            return None

        # Line 1 ends with "YES" if the CRC check passed
        if not lines[0].strip().endswith("YES"):
            return None

        # Line 2 contains "t=<millidegrees>"
        idx = lines[1].find("t=")
        if idx == -1:
            return None

        try:
            raw = int(lines[1][idx + 2:])
        except ValueError:
            return None

        return raw / 1000.0
