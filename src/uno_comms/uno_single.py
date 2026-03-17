import time
import threading
import serial


class UnoSingle:

    # Raspberry Pi <-> Arduino communication class for the lateral/side motor Arduino.
    # This class ONLY sends serial commands. The Arduino does the real motor work.


    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser = None
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def connect(self) -> None:
        if self.is_connected:
            return

        self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(2.0)  # Arduino usually resets on serial open
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    def disconnect(self) -> None:
        if self.is_connected:
            self._ser.close()
        self._ser = None

    def send_raw_command(self, command: str) -> None:
        if not self.is_connected:
            raise RuntimeError(f"Lateral Arduino on {self.port} is not connected.")

        with self._lock:
            self._ser.write((command + "\n").encode("utf-8"))
            self._ser.flush()

    def read_line(self) -> str:
        if not self.is_connected:
            raise RuntimeError(f"Lateral Arduino on {self.port} is not connected.")

        with self._lock:
            return self._ser.readline().decode("utf-8", errors="ignore").strip()

    # -------------------------
    # Lateral motor commands
    # -------------------------
    def move_lateral(self, direction: int, steps: int) -> None:

        # direction: 1 = forward, 0 = backward
        # steps: number of steps

        if steps <= 0:
            raise ValueError("steps must be > 0")

        direction = 1 if direction else 0
        self.send_raw_command(f"LAT:{direction}:{steps}")

    def enable_lateral(self) -> None:
        self.send_raw_command("LAT:ENABLE")

    def disable_lateral(self) -> None:
        self.send_raw_command("LAT:DISABLE")

    def home_lateral(self) -> None:
        self.send_raw_command("LAT:HOME")

    def stop_lateral(self) -> None:
        self.send_raw_command("STOP")