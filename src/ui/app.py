import tkinter as tk
from tkinter import ttk

from .dashboard import Dashboard
from ..controller.tester_controller import TesterController
from .theme import BG

def run() -> None:
    root = tk.Tk()
    root.title("Hip Wear Tester Dashboard (Sim Mode)")
    root.configure(bg=BG)
    root.attributes("-fullscreen", True)
    root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))

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