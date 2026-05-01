from ..common.types import StationMode
from .uno_single import UnoSingle
from .uno_dual import UnoDual


class UnoManager:
    def __init__(self, lateral_port: str, top_port: str, baudrate: int = 9600):
        self.lateral_uno = UnoSingle(lateral_port, baudrate=baudrate)
        self.top_uno = UnoDual(top_port, baudrate=baudrate)

    def connect(self) -> None:
        """Try to open both serial ports. Either one may silently fail to
        connect (Arduino not plugged in, port busy, etc.) — the manager
        does NOT raise. Use lateral_connected() / top_connected() to check
        which Arduinos came up, and start_mode() will refuse cleanly if
        the requested mode needs a missing Arduino."""
        self.lateral_uno.connect()
        self.top_uno.connect()

    def disconnect(self) -> None:
        self.lateral_uno.disconnect()
        self.top_uno.disconnect()

    def lateral_connected(self) -> bool:
        return self.lateral_uno.is_connected()

    def top_connected(self) -> bool:
        return self.top_uno.is_connected()

    def start_mode(self, mode: StationMode, cycles: int) -> None:
        # Refuse modes that need an Arduino that isn't connected, with a
        # clear message instead of a serial-write exception deep in the
        # worker thread. Every supported mode currently uses BOTH Arduinos
        # (top for S1/S2/BOTH, lateral always), so both must be connected.
        missing: list[str] = []
        if not self.top_connected():
            missing.append("Top")
        if not self.lateral_connected():
            missing.append("Lateral")
        if missing:
            joined = " and ".join(missing)
            raise RuntimeError(
                f"Cannot start mode {mode.value}: {joined} Arduino not connected."
            )

        if mode == StationMode.S1:
            self.top_uno.start_station_1(cycles)
            self.lateral_uno.start_cycles(cycles)

        elif mode == StationMode.S2:
            self.top_uno.start_station_2(cycles)
            self.lateral_uno.start_cycles(cycles)

        elif mode == StationMode.BOTH:
            self.top_uno.start_both(cycles)
            self.lateral_uno.start_cycles(cycles)

        else:
            raise RuntimeError(f"Unsupported mode: {mode}")

    def stop_all(self) -> None:
        # Both wrapped in try/except — stop should always succeed even if
        # one (or both) Arduinos disconnected mid-run.
        try:
            self.top_uno.stop()
        except Exception:
            pass

        try:
            self.lateral_uno.stop()
        except Exception:
            pass

    def poll_lines(self) -> list[tuple[str, str]]:
        # read_available_lines() already returns [] if the port isn't open,
        # so disconnected Arduinos contribute zero messages — no special
        # case needed here.
        msgs: list[tuple[str, str]] = []

        for line in self.top_uno.read_available_lines():
            msgs.append(("TOP", line))

        for line in self.lateral_uno.read_available_lines():
            msgs.append(("LAT", line))

        return msgs