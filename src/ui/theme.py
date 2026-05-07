BG = "#0b0b0b"
PANEL = "#121212"
FG = "#e8e8e8"
MUTED = "#a8a8a8"

GREEN = "#00ff6a"
BLUE = "#2aa1ff"
YELLOW = "#ffd000"
RED = "#ff3b30"
GRID = "#2b2b2b"
AXIS = "#7a7a7a"

FONT_TITLE = ("DejaVu Sans", 18, "bold")
FONT_HUGE = ("DejaVu Sans", 20, "bold")
FONT_BIG = ("DejaVu Sans", 16, "bold")
FONT_MED = ("DejaVu Sans", 12)
FONT_SMALL = ("DejaVu Sans", 10)

REFRESH_MS = 500          # UI refresh (Pi 4 2GB: 500 ms balances responsiveness and CPU)
LOG_EVERY_S = 1.0         # log rate (1 Hz = good for multi-hour runs)
GRAPH_MAX_POINTS = 600    # cap graph history per series (10 min at 1 Hz log rate)