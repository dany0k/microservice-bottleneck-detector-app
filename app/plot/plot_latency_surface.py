import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from mpl_toolkits.mplot3d import Axes3D  # noqa


class LatencySurfacePlotter:
    """
    3D surface:
        X — time (minutes)
        Y — RPS
        Z — latency (ms)

    Оптимизировано для детекции bottleneck:
    - почти фиксированный RPS
    - latency растёт со временем
    """

    def __init__(self, graph_state, output_dir="output/surface"):
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

            # unpack samples
            times = np.array([ts for ts, _, _ in edge.samples], dtype=float)
            rps = np.array([r for _, r, _ in edge.samples], dtype=float)
            latency = np.array([l for _, _, l in edge.samples], dtype=float)

            # --- TIME NORMALIZATION ---
            # переводим в минуты от начала
            t0 = times.min()
            time_minutes = (times - t0) / 60.0

            # если RPS почти константа — чуть "раздвигаем" для визуализации
            if np.std(rps) < 1e-3:
                rps = rps + np.random.uniform(-0.15, 0.15, size=len(rps))

            # --- PLOT ---
            fig = plt.figure(figsize=(13, 9))
            ax = fig.add_subplot(111, projection="3d")

            surf = ax.plot_trisurf(
                time_minutes,
                rps,
                latency,
                cmap="viridis",
                linewidth=0.25,
                edgecolor="black",
                alpha=0.95,
                antialiased=True,
            )

            # labels
            ax.set_xlabel("Time (minutes)")
            ax.set_ylabel("RPS")
            ax.set_zlabel("Latency (ms)")

            ax.set_title(
                "Latency surface (minute-scale)\n"
                f"{src} → {dst}",
                pad=18
            )

            # --- CRITICAL PART: CAMERA & PROJECTION ---
            ax.set_proj_type("ortho")
            ax.view_init(elev=40, azim=-60)
            ax.set_box_aspect((3, 1, 2))  # time, rps, latency

            # colorbar
            cbar = fig.colorbar(surf, ax=ax, pad=0.1, shrink=0.6)
            cbar.set_label("Latency (ms)")

            plt.tight_layout()
            plt.savefig(self._fname(src, dst), dpi=160)
            plt.close(fig)
