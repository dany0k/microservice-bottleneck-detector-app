import os
import matplotlib.pyplot as plt
import numpy as np


class LatencyRpsPlotter:
    def __init__(self, graph_state, output_dir="output/latency_rps_scatter"):
        self.gs = graph_state
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _fname(self, src: str, dst: str) -> str:
        name = f"{src}__{dst}".replace("/", "_")
        return os.path.join(self.output_dir, f"{name}.png")

    def draw(self):
        for (src, dst), edge in self.gs.edges.items():
            if len(edge.samples) < 10:
                continue

            rps = np.array([r for _, r, _ in edge.samples])
            latency = np.array([l for _, _, l in edge.samples])

            plt.figure(figsize=(8, 5))
            plt.scatter(rps, latency, s=14, alpha=0.5)

            plt.xlabel("RPS")
            plt.ylabel("Latency (ms)")
            plt.title(f"Latency vs RPS\n{src} → {dst}")
            plt.grid(True)

            out = self._fname(src, dst)
            plt.tight_layout()
            plt.savefig(out, dpi=150)
            plt.close()
