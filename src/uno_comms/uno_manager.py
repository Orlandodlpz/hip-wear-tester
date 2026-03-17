from enum import Enum
from threading import Thread
from typing import Callable, Iterable, Tuple

from .uno_single import UnoSingle
from .uno_dual import UnoDual


class StationMode(str, Enum):
    STATION_1 = "station_1"
    STATION_2 = "station_2"
    BOTH = "both"


class UnoManager:

    # Main Raspberry Pi communication manager.

    # Responsibilities:
    # - Hold both Arduino communication objects
    # - Keep track of selected station mode
    # - Send the correct command set for station 1 / station 2 / both


    def __init__(
        self,
        lateral_port: str,
        top_port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
    ):
        self.lateral_uno = UnoSingle(lateral_port, baudrate, timeout)
        self.top_uno = UnoDual(top_port, baudrate, timeout)
        self._station_mode: StationMode | None = None

    # -------------------------
    # Connection management
    # -------------------------
    def connect(self) -> None:
        self.lateral_uno.connect()
        self.top_uno.connect()

    def disconnect(self) -> None:
        self.lateral_uno.disconnect()
        self.top_uno.disconnect()

    # -------------------------
    # Station mode management
    # -------------------------
    def set_station_mode(self, mode: StationMode | str) -> None:
        if isinstance(mode, str):
            mode = StationMode(mode)
        self._station_mode = mode

    def get_station_mode(self) -> StationMode | None:
        return self._station_mode

    # -------------------------
    # Basic hardware helpers
    # -------------------------
    def enable_all(self) -> None:
        self.lateral_uno.enable_lateral()
        self.top_uno.enable_all_top()

    def disable_all(self) -> None:
        self.lateral_uno.disable_lateral()
        self.top_uno.disable_all_top()

    def stop_all(self) -> None:
        self.lateral_uno.stop_lateral()
        self.top_uno.stop_top()

    def home_all(self) -> None:
        self.lateral_uno.home_lateral()
        self.top_uno.home_all_top()

    # -------------------------
    # Internal helper for near-simultaneous dispatch
    # -------------------------
    def _run_parallel(
        self,
        actions: Iterable[Tuple[Callable, tuple]],
    ) -> None:

        # Sends commands to multiple Arduinos nearly at the same time.
        # Useful when the lateral motor and top motors should start together.

        threads = []

        for func, args in actions:
            t = Thread(target=func, args=args, daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    # -------------------------
    # Station-specific runs
    # -------------------------
    def run_station_1(
        self,
        top_direction: int,
        top_steps: int,
        lateral_direction: int,
        lateral_steps: int,
    ) -> None:

        # Station 1:
        # - top-left motor runs
        # - lateral motor runs at the same time

        self._run_parallel(
            [
                (self.top_uno.move_top_left, (top_direction, top_steps)),
                (self.lateral_uno.move_lateral, (lateral_direction, lateral_steps)),
            ]
        )

    def run_station_2(
        self,
        top_direction: int,
        top_steps: int,
        lateral_direction: int,
        lateral_steps: int,
    ) -> None:

        # Station 2:
        # - top-right motor runs
        # - lateral motor runs at the same time

        self._run_parallel(
            [
                (self.top_uno.move_top_right, (top_direction, top_steps)),
                (self.lateral_uno.move_lateral, (lateral_direction, lateral_steps)),
            ]
        )

    def run_both(
        self,
        top_direction: int,
        top_steps: int,
        lateral_direction: int,
        lateral_steps: int,
    ) -> None:
        # BOTH mode:
        # - both top motors run
        # - lateral motor runs at the same time
        
        self._run_parallel(
            [
                (self.top_uno.move_top_both, (top_direction, top_steps)),
                (self.lateral_uno.move_lateral, (lateral_direction, lateral_steps)),
            ]
        )

    def run_selected_mode(
        self,
        top_direction: int,
        top_steps: int,
        lateral_direction: int,
        lateral_steps: int,
    ) -> None:

        # Uses the chosen station mode.

        if self._station_mode is None:
            raise RuntimeError("No station mode has been selected.")

        if self._station_mode == StationMode.STATION_1:
            self.run_station_1(top_direction, top_steps, lateral_direction, lateral_steps)

        elif self._station_mode == StationMode.STATION_2:
            self.run_station_2(top_direction, top_steps, lateral_direction, lateral_steps)

        elif self._station_mode == StationMode.BOTH:
            self.run_both(top_direction, top_steps, lateral_direction, lateral_steps)

        else:
            raise RuntimeError(f"Unsupported station mode: {self._station_mode}")