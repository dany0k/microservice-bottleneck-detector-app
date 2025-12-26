import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.interpolate import griddata
from mpl_toolkits.mplot3d import Axes3D  # noqa


class Edge3DSurfacePlotter:
    def __init__(self, graph_state, save_dir: str = "plots"):
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
        bottlenecks = self.gs.bottleneck_edges

        for (src, dst), series in data.items():
            if len(series["t"]) < 10:
                continue

            t = np.array(series["t"], dtype=float)
            rps = np.array(series["rps"], dtype=float)
            latency = np.array(series["latency"], dtype=float)

            t = t - t.min()

            ti = np.linspace(t.min(), t.max(), 40)
            ri = np.linspace(rps.min(), rps.max(), 40)
            T, R = np.meshgrid(ti, ri)

            Z = griddata(
                points=(t, rps),
                values=latency,
                xi=(T, R),
                method="linear"
            )

            Z = np.nan_to_num(Z, nan=np.nanmean(latency))

            is_bottleneck = (src, dst) in bottlenecks

            fig = plt.figure(figsize=(11, 8))
            ax = fig.add_subplot(111, projection="3d")

            cmap = "coolwarm" if is_bottleneck else "inferno"

            surf = ax.plot_surface(
                T,
                R,
                Z,
                cmap=cmap,
                linewidth=0,
                antialiased=True,
                alpha=0.9
            )

            ax.set_title(
                f"{src} → {dst}"
                + ("  [BOTTLENECK]" if is_bottleneck else "")
            )
            ax.set_xlabel("t (relative seconds)")
            ax.set_ylabel("RPS")
            ax.set_zlabel("Latency (ms)")

            fig.colorbar(surf, ax=ax, label="Latency (ms)")

            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            fname = f"{ts}_surface"
            if is_bottleneck:
                fname += "_BOTTLENECK"
            fname += ".png"

            out_dir = self._endpoint_dir(src, dst)
            out_path = os.path.join(out_dir, fname)

            plt.tight_layout()
            plt.savefig(out_path, dpi=150)
            plt.close(fig)
