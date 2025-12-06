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

    def process_edge(self, src: str, dst: str, edge):
        warn, crit = self._compute_adaptive_thresholds()

        status = None

        if edge.avg_latency >= crit:
            status = "critical"
        elif edge.avg_latency >= warn:
            status = "warning"

        if edge.trend > 0 and status != "critical":
            if edge.trend > (crit * 0.1):
                status = "warning"

        if not status:
            return

        self._alerts.append({
            "type": status,
            "title": f"Latency {status.upper()}",
            "message": f"{src} → {dst} "
                       f"avg={edge.avg_latency:.1f} ms "
                       f"(warn={warn:.1f}, crit={crit:.1f})",
            "route": f"{src}/{dst}",
            "meta": ""
        })

        if len(self._alerts) > 200:
            self._alerts.pop(0)

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
