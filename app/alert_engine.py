import statistics
from typing import List, Dict, Any


class AlertEngine:
    def __init__(self, graph_state):
        self._gs = graph_state
        self._alerts: List[Dict[str, Any]] = []

    def get_alerts(self):
        return list(self._alerts)

    def _compute_adaptive_thresholds(self):
        edges = list(self._gs.edges.values())
        if len(edges) < 5:
            return 150, 250

        avg_latencies = [e.avg_latency for e in edges if e.avg_latency > 0]

        if len(avg_latencies) < 5:
            return 150, 250

        med = statistics.median(avg_latencies)
        std = statistics.pstdev(avg_latencies)

        warn = med + 1 * std
        crit = med + 2 * std

        return warn, crit

    def _latency_rps_slope(self, edge) -> float:
        samples = list(edge.samples)
        if len(samples) < 5:
            return 0.0

        rps_vals = [r for _, r, _ in samples]
        lat_vals = [l for _, _, l in samples]

        if len(set(rps_vals)) < 2:
            return 0.0

        mean_rps = statistics.mean(rps_vals)
        mean_lat = statistics.mean(lat_vals)

        num = sum(
            (r - mean_rps) * (l - mean_lat)
            for r, l in zip(rps_vals, lat_vals)
        )
        den = sum((r - mean_rps) ** 2 for r in rps_vals)

        return num / den if den != 0 else 0.0

    def process_edge(self, src: str, dst: str, edge):
        slope = self._latency_rps_slope(edge)

        RPS_MIN = 5
        SLOPE_CRIT = 2.0  # ms latency / 1 rps
        STABILITY = 3  # последних точек

        recent = list(edge.samples)[-STABILITY:]
        if len(recent) < STABILITY:
            return

        avg_rps = sum(r for _, r, _ in recent) / STABILITY
        avg_lat = sum(l for _, _, l in recent) / STABILITY

        if (
                slope > SLOPE_CRIT
                and avg_rps > RPS_MIN
                and avg_lat > self._compute_adaptive_thresholds()[0]
        ):
            self._gs.bottleneck_edges.add((src, dst))

            self._alerts.append({
                "type": "critical",
                "title": "Bottleneck detected",
                "message": (
                    f"{src} → {dst}: "
                    f"dLatency/dRPS={slope:.2f}, "
                    f"rps={avg_rps:.1f}, "
                    f"lat={avg_lat:.1f}"
                ),
                "route": f"{src}/{dst}",
                "meta": ""
            })

    def handle_log(self, src: str, dst: str):
        edge = self._gs.edges.get((src, dst))
        if edge:
            self.process_edge(src, dst, edge)

    def overall_status(self):
        crit_count = sum(1 for a in self._alerts if a["type"] == "critical")
        warn_count = sum(1 for a in self._alerts if a["type"] == "warning")

        if crit_count >= 3:
            return "critical"
        elif warn_count >= 3:
            return "warning"
        return "ok"
