import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter


class LatencySurfaceSmoothPlotter:
    """
    Сглаженная 3D surface:
      X — time (minutes, binned)
      Y — RPS (binned)
      Z — median latency (smoothed)

    Под bottleneck:
    - фиксированный RPS
    - рост latency во времени
    """

    def __init__(self, graph_state, output_dir="output/surface_smooth"):
        self.gs = graph_state
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _fname(self, src: str, dst: str) -> str:
        name = f"{src}__{dst}".replace("/", "_")
        return os.path.join(self.output_dir, f"{name}.png")

    def draw(self):
        for (src, dst), edge in self.gs.edges.items():
            if len(edge.samples) < 20:
                continue

            # unpack
            times = np.array([ts for ts, _, _ in edge.samples], dtype=float)
            rps = np.array([r for _, r, _ in edge.samples], dtype=float)
            latency = np.array([l for _, _, l in edge.samples], dtype=float)

            # --- TIME → minutes ---
            t0 = times.min()
            time_min = (times - t0) / 60.0

            # --- BINNING ---
            time_bins = np.arange(0, time_min.max() + 1, 0.5)   # 30 сек
            rps_bins = np.arange(rps.min() - 1, rps.max() + 1, 2)

            T, R = np.meshgrid(time_bins, rps_bins)
            Z = np.full_like(T, np.nan, dtype=float)

            # aggregate median latency
            for i in range(len(time_bins) - 1):
                for j in range(len(rps_bins) - 1):
                    mask = (
                        (time_min >= time_bins[i]) &
                        (time_min < time_bins[i + 1]) &
                        (rps >= rps_bins[j]) &
                        (rps < rps_bins[j + 1])
                    )
                    if np.any(mask):
                        Z[j, i] = np.median(latency[mask])

            # fill gaps
            nan_mask = np.isnan(Z)
            Z[nan_mask] = np.nanmedian(Z)

            # --- SMOOTH ---
            Z_smooth = gaussian_filter(Z, sigma=(1.0, 1.2))

            # --- PLOT ---
            fig = plt.figure(figsize=(13, 9))
            ax = fig.add_subplot(111, projection="3d")

            surf = ax.plot_surface(
                T, R, Z_smooth,
                cmap="viridis",
                linewidth=0,
                antialiased=True,
                alpha=0.95
            )

            ax.set_xlabel("Time (minutes)")
            ax.set_ylabel("RPS")
            ax.set_zlabel("Latency (ms)")
            ax.set_title(
                "Smoothed latency surface\n"
                f"{src} → {dst}",
                pad=18
            )

            # camera — ВИД ИЗ УГЛА
            ax.view_init(elev=40, azim=-60)
            ax.set_proj_type("ortho")
            ax.set_box_aspect((3, 1.5, 2))

            cbar = fig.colorbar(surf, ax=ax, shrink=0.6, pad=0.08)
            cbar.set_label("Latency (ms)")

            plt.tight_layout()
            plt.savefig(self._fname(src, dst), dpi=160)
            plt.close(fig)
