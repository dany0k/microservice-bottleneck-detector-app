class AlertEngine:

    WARN_LATENCY = 80
    CRIT_LATENCY = 150

    WARN_TREND = 2.0
    CRIT_TREND = 5.0

    def __init__(self, graph_state):
        self._gs = graph_state
        self._alerts = []

    def get_alerts(self):
        return list(self._alerts)

    def process_edge(self, src: str, dst: str, edge):

        status = "ok"
        level = None

        if edge.avg_latency >= self.CRIT_LATENCY:
            status = "critical"
            level = "critical"
        elif edge.avg_latency >= self.WARN_LATENCY:
            status = "warning"
            level = "warning"

        if edge.trend >= self.CRIT_TREND:
            status = "critical"
            level = "critical"
        elif edge.trend >= self.WARN_TREND and status != "critical":
            status = "warning"
            level = "warning"

        if level:
            self._gs.nodes[src].status = status
            self._gs.nodes[dst].status = status

            self._alerts.append({
                "type": level,
                "title": f"Latency {status}",
                "message": f"{src} → {dst} avg={edge.avg_latency:.1f}, trend={edge.trend:+.1f}",
                "route": f"{src}/{dst}",
                "meta": ""
            })

    # --------------------------------------

    def handle_log(self, src: str, dst: str):
        edge = self._gs.edges.get((src, dst))
        if edge:
            self.process_edge(src, dst, edge)

    # --------------------------------------

    def overall_status(self):
        if any(n.status == "critical" for n in self._gs.nodes.values()):
            return "critical"
        if any(n.status == "warning" for n in self._gs.nodes.values()):
            return "warning"
        return "ok"
