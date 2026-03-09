import tkinter as tk
from .dashboard import Dashboard
from ..controller.tester_controller import TesterController

def run() -> None:
    root = tk.Tk()
    root.title("Hip Wear Tester Dashboard (Sim Mode)")
    root.geometry("1150x700")
    root.minsize(1050, 650)

    controller = TesterController() # defaults to SimMotorIO (safe / no hardware)
    dash = Dashboard(root, controller)
    dash.pack(fill="both", expand=True)

    root.mainloop()

if __name__ == "__main__":
    run()