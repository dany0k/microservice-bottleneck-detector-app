import os

from app.graph_state import GraphState
from app.alert_engine import AlertEngine
from app.log_reader import LogReader
from app.plot_3d_edges import Edge3DSurfacePlotter
import threading
import time

from app.plot_contour_bottleneck import EdgeContourBottleneckPlotter
from app.plot_contour_edges import EdgeContourPlotter


def main():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    LOG_FILE = os.path.join(BASE_DIR, "resources/microservice_logs_10000_extended.csv")

    gs = GraphState()
    ae = AlertEngine(gs)

    reader = LogReader(
        graph_state=gs,
        alert_engine=ae,
        log_file=LOG_FILE,
        interval=0.05
    )

    # plotter = Edge3DSurfacePlotter(gs)
    # plotter = EdgeContourPlotter(gs)
    plotter = EdgeContourBottleneckPlotter(gs)

    threading.Thread(
        target=reader.run_blocking,
        daemon=True
    ).start()
    print("LogReader thread started")

    i = 0
    while True:
        i += 1
        plotter.draw()
        time.sleep(10)
        if i == 1000:
            break

if __name__ == "__main__":
    main()
