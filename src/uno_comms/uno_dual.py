import time
import threading
import serial


class UnoDual:

    # Raspberry Pi <-> Arduino communication class for the top-motors Arduino.
    # This Arduino controls:
    #   - top-left motor
    #   - top-right motor


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
            raise RuntimeError(f"Top Arduino on {self.port} is not connected.")

        with self._lock:
            self._ser.write((command + "\n").encode("utf-8"))
            self._ser.flush()

    def read_line(self) -> str:
        if not self.is_connected:
            raise RuntimeError(f"Top Arduino on {self.port} is not connected.")

        with self._lock:
            return self._ser.readline().decode("utf-8", errors="ignore").strip()

    # -------------------------
    # Top motor commands
    # -------------------------
    def move_top_left(self, direction: int, steps: int) -> None:
        if steps <= 0:
            raise ValueError("steps must be > 0")

        direction = 1 if direction else 0
        self.send_raw_command(f"TL:{direction}:{steps}")

    def move_top_right(self, direction: int, steps: int) -> None:
        if steps <= 0:
            raise ValueError("steps must be > 0")

        direction = 1 if direction else 0
        self.send_raw_command(f"TR:{direction}:{steps}")

    def move_top_both(self, direction: int, steps: int) -> None:

        # Sends one command to the top Arduino telling it to move both top motors.
        # This is best when both top motors should start together.

        if steps <= 0:
            raise ValueError("steps must be > 0")

        direction = 1 if direction else 0
        self.send_raw_command(f"TOP_BOTH:{direction}:{steps}")

    def enable_top_left(self) -> None:
        self.send_raw_command("TL:ENABLE")

    def disable_top_left(self) -> None:
        self.send_raw_command("TL:DISABLE")

    def enable_top_right(self) -> None:
        self.send_raw_command("TR:ENABLE")

    def disable_top_right(self) -> None:
        self.send_raw_command("TR:DISABLE")

    def enable_all_top(self) -> None:
        self.send_raw_command("TOP:ENABLE_ALL")

    def disable_all_top(self) -> None:
        self.send_raw_command("TOP:DISABLE_ALL")

    def home_top_left(self) -> None:
        self.send_raw_command("TL:HOME")

    def home_top_right(self) -> None:
        self.send_raw_command("TR:HOME")

    def home_all_top(self) -> None:
        self.send_raw_command("TOP:HOME_ALL")

    def stop_top(self) -> None:
        self.send_raw_command("STOP")