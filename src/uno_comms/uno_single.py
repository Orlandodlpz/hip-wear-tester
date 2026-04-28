import threading
import time
import serial


@property
def is_connected(self) -> bool:
    return self._ser is not None and self._ser.is_open

class UnoSingle:
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 0.05):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        if self._ser is not None and self._ser.is_open:
            return

        self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(2.0)  # Arduino resets on open
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    def disconnect(self) -> None:
        if self._ser is not None and self._ser.is_open:
            self._ser.close()
        self._ser = None

    def send_raw_command(self, cmd: str) -> None:
        if self._ser is None or not self._ser.is_open:
            raise RuntimeError(f"Lateral Arduino not connected on {self.port}")

        with self._lock:
            self._ser.write((cmd + "\n").encode("utf-8"))
            self._ser.flush()

    def start_cycles(self, cycles: int) -> None:
        self.send_raw_command(f"START:{cycles}")

    def stop(self) -> None:
        self.send_raw_command("STOP")

    def read_available_lines(self) -> list[str]:
        lines: list[str] = []

        if self._ser is None or not self._ser.is_open:
            return lines

        with self._lock:
            while self._ser.in_waiting > 0:
                raw = self._ser.readline().decode("utf-8", errors="ignore").strip()
                if raw:
                    lines.append(raw)

        return lines