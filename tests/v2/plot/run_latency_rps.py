import os
import threading
import time

from app.graph_state import GraphState
from app.alert_engine import AlertEngine
from app.log_reader import LogReader
from app.plot.plot_latency_rps import LatencyRpsPlotter
from app.plot.plot_latency_rps_binned import LatencyRpsBinnedPlotter
from app.plot.plot_latency_surface import LatencySurfacePlotter
from app.plot.plot_latency_surface_smooth import LatencySurfaceSmoothPlotter
from app.plot.plot_time_series import TimeSeriesPlotter


# ---------- util ----------

def wait_for_data(gs, min_samples=10, timeout=30):
    """
    Ждём, пока у хотя бы одного edge накопится min_samples.
    Это важно, иначе output будет пустой.
    """
    start = time.time()
    while time.time() - start < timeout:
        for edge in gs.edges.values():
            if len(edge.samples) >= min_samples:
                return True
        print("Waiting for data...")
        time.sleep(1)
    return False


# ---------- main ----------

def main():
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    LOG_FILE = os.path.join(
        BASE_DIR,
        # "resources/microservice_logs_10000_extended.csv"
        "resources/one_service_logs.csv"
    )

    # --- core state ---
    gs = GraphState()
    ae = AlertEngine(gs)

    # --- log reader ---
    reader = LogReader(
        graph_state=gs,
        alert_engine=ae,
        log_file=LOG_FILE,
        interval=0.05
    )

    threading.Thread(
        target=reader.run_blocking,
        daemon=True
    ).start()

    print("LogReader started")

    # --- ждём первые данные ---
    if not wait_for_data(gs, min_samples=15):
        print("No data collected, exiting")
        return

    print("Data collected, starting plotters")

    # --- plotters ---
    scatter_plotter = LatencyRpsPlotter(gs)
    binned_plotter = LatencyRpsBinnedPlotter(gs, bin_size=5)
    time_series_plotter = TimeSeriesPlotter(gs)
    surface_plotter = LatencySurfacePlotter(gs)
    surface_plotter_smooth = LatencySurfaceSmoothPlotter(gs)

    # --- main loop ---
    while True:
        scatter_plotter.draw()
        binned_plotter.draw()
        time_series_plotter.draw()
        surface_plotter.draw()
        surface_plotter_smooth.draw()

        print("Plots saved to output/")
        time.sleep(15)


if __name__ == "__main__":
    main()
