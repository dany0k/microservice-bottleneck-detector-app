import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.interpolate import griddata
import statistics


class EdgeContourBottleneckPlotter:
    def __init__(self, graph_state, save_dir="plots_contour"):
        self.gs = graph_state
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def _endpoint_dir(self, src: str, dst: str) -> str:
        name = f"{src}__{dst}".replace("/", "_")
        path = os.path.join(self.save_dir, name)
        os.makedirs(path, exist_ok=True)
        return path

    def draw(self):
        data = self.gs.export_edge_timeseries()

        for (src, dst), series in data.items():
            if len(series["t"]) < 15:
                continue

            t = np.array(series["t"], dtype=float)
            rps = np.array(series["rps"], dtype=float)
            latency = np.array(series["latency"], dtype=float)

            t = t - t.min()

            L_med = statistics.median(latency)
            L_std = statistics.pstdev(latency)
            L_crit = L_med + 1.5 * L_std
            RPS_min = max(3, np.percentile(rps, 30))

            ti = np.linspace(t.min(), t.max(), 80)
            ri = np.linspace(rps.min(), rps.max(), 80)
            T, R = np.meshgrid(ti, ri)

            Z = griddata(
                points=(t, rps),
                values=latency,
                xi=(T, R),
                method="linear"
            )

            Z = np.nan_to_num(Z, nan=L_med)

            bottleneck_mask = (Z >= L_crit) & (R >= RPS_min)

            cell_area = (ti[1] - ti[0]) * (ri[1] - ri[0])
            bottleneck_area = np.sum(bottleneck_mask) * cell_area
            total_area = T.size * cell_area

            bottleneck_ratio = bottleneck_area / total_area

            fig, ax = plt.subplots(figsize=(11, 6))

            cf = ax.contourf(
                T, R, Z,
                levels=20,
                cmap="inferno"
            )

            ax.contour(
                T, R, bottleneck_mask.astype(int),
                levels=[0.5],
                colors="cyan",
                linewidths=2
            )

            ax.set_title(
                f"{src} → {dst}\n"
                f"Lcrit={L_crit:.1f} ms, "
                f"Bottleneck area={bottleneck_ratio:.2%}"
            )
            ax.set_xlabel("t (relative seconds)")
            ax.set_ylabel("RPS")

            cbar = fig.colorbar(cf, ax=ax)
            cbar.set_label("Latency (ms)")

            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            fname = f"{ts}_contour_bottleneck.png"

            out_dir = self._endpoint_dir(src, dst)
            out_path = os.path.join(out_dir, fname)

            plt.tight_layout()
            plt.savefig(out_path, dpi=150)
            plt.close(fig)
