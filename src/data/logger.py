from __future__ import annotations
from pathlib import Path
from datetime import datetime
import csv

class logger:
    # Creates ONE folder per test and outputs:
      # - data.csv
      # - graph.png
      
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir if base_dir is not None else (Path.cwd() / "data" / "runs")
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.run_dir: Path | None = None
        self.csv_path: Path | None = None
        self.graph_path: Path | None = None

        self._fp = None
        self._writer: csv.writer | None = None

        # For graphing
        self._t_sec: list[float] = []
        self._s1: list[float] = []
        self._s2: list[float] = []

        self.mode: str = "UNKNOWN"
        self.started_iso: str = ""
        self.ended_iso: str = ""

    def start(self, mode: str) -> Path:
        self.mode = mode
        self.started_iso = datetime.now().isoformat(timespec="seconds")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.base_dir / f"run_{ts}_{mode}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.csv_path = self.run_dir / "data.csv"
        self.graph_path = self.run_dir / "graph.png"

        self._fp = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fp)

        # Normal CSV header row
        self._writer.writerow([
            "timestamp",
            "elapsed_seconds",
            "elapsed_time",
            "station_mode",
            "test_state",
            "temp_station1_celsius",
            "temp_station2_celsius",
            "lateral_motor_state",
            "top_motor_station1_state",
            "top_motor_station2_state",
            "log_message",
        ])
        self._fp.flush()
        return self.run_dir

    def log(self, *, elapsed_s: float, elapsed_hhmmss: str, mode: str, run_state: str,
            t1: float, t2: float, side: str, top1: str, top2: str, message: str) -> None:
        if not self._writer or not self._fp:
            return

        wall_iso = datetime.now().isoformat(timespec="seconds")

        # store for graph
        self._t_sec.append(float(elapsed_s))
        self._s1.append(float(t1))
        self._s2.append(float(t2))

        self._writer.writerow([
            wall_iso,
            f"{elapsed_s:.2f}",
            elapsed_hhmmss,
            mode,
            run_state,
            f"{t1:.3f}",
            f"{t2:.3f}",
            side,
            top1,
            top2,
            message,
        ])
        self._fp.flush()

    def finalize(self, end_state: str) -> None:
        """Close CSV and generate graph.png."""
        self.ended_iso = datetime.now().isoformat(timespec="seconds")

        # write a final marker row (optional but useful)
        if self._writer and self._fp:
            self._writer.writerow([
                self.ended_iso,
                "",
                "",
                self.mode,
                f"END:{end_state}",
                "",
                "",
                "",
                "",
                "",
                "",
            ])
            self._fp.flush()
            self._fp.close()

        self._fp = None
        self._writer = None

        self._export_graph()

    def _export_graph(self) -> None:
        if self.graph_path is None:
            return

        try:
            import matplotlib
            matplotlib.use("Agg")  # headless safe
            import matplotlib.pyplot as plt
            from matplotlib.ticker import FuncFormatter, MaxNLocator
        except Exception:
            return

        def fmt_hhmm(x, _pos=None):
            x = int(max(0, x))
            h = x // 3600
            m = (x % 3600) // 60
            return f"{h:02d}:{m:02d}"

        fig = plt.figure(figsize=(12, 6), dpi=150)
        fig.patch.set_facecolor("black")
        ax = fig.add_subplot(111)
        ax.set_facecolor("black")

        if self._t_sec:
            ax.plot(self._t_sec, self._s1, label="Station 1", linewidth=2, color="#00ff6a")
            ax.plot(self._t_sec, self._s2, label="Station 2", linewidth=2, color="#2aa1ff", linestyle="--")

        ax.set_title(f"Hip Wear Tester — Temperature vs Time ({self.mode})", color="white")
        ax.set_xlabel("Time (HH:MM)", color="white")
        ax.set_ylabel("Temperature (°C)", color="white")

        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("#7a7a7a")

        ax.grid(True, which="major", color="#2b2b2b", linewidth=0.8)
        ax.xaxis.set_major_formatter(FuncFormatter(fmt_hhmm))
        ax.xaxis.set_major_locator(MaxNLocator(nbins=10))

        leg = ax.legend(facecolor="#0a0a0a", edgecolor="#2b2b2b")
        for txt in leg.get_texts():
            txt.set_color("white")

        fig.tight_layout()
        fig.savefig(self.graph_path, facecolor=fig.get_facecolor())
        plt.close(fig)