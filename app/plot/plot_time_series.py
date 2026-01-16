import os
import matplotlib.pyplot as plt
from datetime import datetime


class TimeSeriesPlotter:
    def __init__(self, graph_state, output_dir="output/time_series"):
        self.gs = graph_state
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _fname(self, src: str, dst: str) -> str:
        name = f"{src}__{dst}".replace("/", "_")
        return os.path.join(self.output_dir, f"{name}.png")

    def draw(self):
        for (src, dst), edge in self.gs.edges.items():
            if len(edge.samples) < 5:
                continue

            # unpack samples
            times = [ts for ts, _, _ in edge.samples]
            rps = [r for _, r, _ in edge.samples]
            latency = [l for _, _, l in edge.samples]

            # convert unix → datetime
            times_dt = [datetime.fromtimestamp(t) for t in times]

            fig, (ax1, ax2) = plt.subplots(
                2, 1,
                figsize=(11, 6),
                sharex=True
            )

            # ----- RPS -----
            ax1.plot(times_dt, rps, color="tab:blue", linewidth=2)
            ax1.set_ylabel("RPS")
            ax1.set_title(f"RPS and Latency over time\n{src} → {dst}")
            ax1.grid(True, alpha=0.3)

            # ----- Latency -----
            ax2.plot(times_dt, latency, color="tab:red", linewidth=2)
            ax2.set_ylabel("Latency (ms)")
            ax2.set_xlabel("Time")
            ax2.grid(True, alpha=0.3)

            fig.autofmt_xdate()
            plt.tight_layout()
            plt.savefig(self._fname(src, dst), dpi=150)
            plt.close(fig)
