import os
import matplotlib.pyplot as plt
import numpy as np


class LatencyRpsBinnedPlotter:
    def __init__(self, graph_state, bin_size=5, output_dir="output/latency_rps_binned"):
        self.gs = graph_state
        self.bin_size = bin_size
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _fname(self, src: str, dst: str) -> str:
        name = f"{src}__{dst}".replace("/", "_")
        return os.path.join(self.output_dir, f"{name}.png")

    def draw(self):
        for (src, dst), edge in self.gs.edges.items():
            samples = list(edge.samples)
            if len(samples) < 20:
                continue

            rps = np.array([r for _, r, _ in samples])
            latency = np.array([l for _, _, l in samples])

            bins = np.arange(rps.min(), rps.max() + self.bin_size, self.bin_size)

            xs = []
            ys = []

            for i in range(len(bins) - 1):
                mask = (rps >= bins[i]) & (rps < bins[i + 1])
                if mask.sum() < 3:
                    continue

                xs.append((bins[i] + bins[i + 1]) / 2)
                ys.append(np.median(latency[mask]))

            if not xs:
                continue

            plt.figure(figsize=(8, 5))
            plt.plot(xs, ys, marker="o")

            plt.xlabel("RPS")
            plt.ylabel("Median latency (ms)")
            plt.title(f"Latency(RPS)\n{src} → {dst}")
            plt.grid(True)

            out = self._fname(src, dst)
            plt.tight_layout()
            plt.savefig(out, dpi=150)
            plt.close()
