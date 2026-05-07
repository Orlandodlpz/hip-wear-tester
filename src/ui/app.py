import os
import sys
import tkinter as tk
from tkinter import ttk

from .dashboard import Dashboard
from ..controller.tester_controller import TesterController
from .theme import BG


# Default window size when launched windowed (not fullscreen). Picked to fit
# comfortably on a typical 1080p monitor while still leaving room for the
# title bar and dock. The window is resizable.
DEFAULT_WIDTH  = 1280
DEFAULT_HEIGHT = 720


def _is_fullscreen_requested() -> bool:
    """Return True if the user wants to launch fullscreen.

    Sources, in order of priority:
      1. CLI flag --fullscreen (or -f).
      2. Environment variable HIP_WEAR_FULLSCREEN=1.

    Default: False (launch as a regular window). To make the Pi launch
    fullscreen, edit scripts/launch.sh to export HIP_WEAR_FULLSCREEN=1
    before exec'ing python3.
    """
    if any(arg in ("--fullscreen", "-f") for arg in sys.argv[1:]):
        return True
    if os.environ.get("HIP_WEAR_FULLSCREEN") in ("1", "true", "yes"):
        return True
    return False


def run() -> None:
    root = tk.Tk()
    root.title("Hip Wear Tester Dashboard")
    root.configure(bg=BG)

    fullscreen = _is_fullscreen_requested()
    if fullscreen:
        root.attributes("-fullscreen", True)
    else:
        # Windowed: pick a reasonable default size and let the user resize.
        root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")
        root.minsize(800, 480)  # don't let it shrink so small the layout breaks

    # F11 toggles fullscreen on the fly. Escape exits fullscreen back to a
    # window (does NOT quit the app). These work whether you started in
    # fullscreen or windowed mode.
    def toggle_fullscreen(_event=None):
        is_full = bool(root.attributes("-fullscreen"))
        root.attributes("-fullscreen", not is_full)

    def exit_fullscreen(_event=None):
        root.attributes("-fullscreen", False)

    root.bind("<F11>", toggle_fullscreen)
    root.bind("<Escape>", exit_fullscreen)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Hide notebook tabs (we'll navigate with buttons)
    style.layout("Dashboard.TNotebook.Tab", [])
    style.configure("Dashboard.TNotebook", background=BG, borderwidth=0)
    style.configure("Dashboard.TNotebook.Tab", padding=0)

    controller = TesterController()
    dash = Dashboard(root, controller)
    dash.pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    run()
