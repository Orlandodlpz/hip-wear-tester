from ..common.types import StationMode
from .uno_single import UnoSingle
from .uno_dual import UnoDual


class UnoManager:
    def __init__(self, lateral_port: str, top_port: str, baudrate: int = 9600):
        self.lateral_uno = UnoSingle(lateral_port, baudrate=baudrate)
        self.top_uno = UnoDual(top_port, baudrate=baudrate)

    def connect(self) -> None:
        self.lateral_uno.connect()
        self.top_uno.connect()

    def disconnect(self) -> None:
        self.lateral_uno.disconnect()
        self.top_uno.disconnect()

    def start_mode(self, mode: StationMode, cycles: int) -> None:
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
        try:
            self.top_uno.stop()
        except Exception:
            pass

        try:
            self.lateral_uno.stop()
        except Exception:
            pass

    def poll_lines(self) -> list[tuple[str, str]]:
        msgs: list[tuple[str, str]] = []

        for line in self.top_uno.read_available_lines():
            msgs.append(("TOP", line))

        for line in self.lateral_uno.read_available_lines():
            msgs.append(("LAT", line))

        return msgs