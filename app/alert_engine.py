from typing import List, Dict, Any, Tuple
from .graph_state import GraphState


class AlertEngine:
    """
    Простейший механизм алертинга:
    - WARNING: латентность растёт (+ тренд) и выше средней
    - CRITICAL: латентность сильно выше средней и тренд положительный
    """

    def __init__(self, graph_state: GraphState) -> None:
        self.graph_state = graph_state
        self.alerts: List[Dict[str, Any]] = []
        self.max_alerts = 50

    def _push_alert(self, severity: str, title: str, message: str, route: str) -> None:
        alert = {
            "type": severity,  # "critical" | "warning" | "info"
            "title": title,
            "message": message,
            "route": route,
            "meta": "Just now",
        }
        self.alerts.insert(0, alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[: self.max_alerts]

    def process_observation(self, src: str, dst: str, latency_ms: float) -> None:
        key: Tuple[str, str] = (src, dst)
        edge = self.graph_state.edges.get(key)
        if not edge or len(edge.latencies) < 6:
            # мало данных – ничего не делаем
            return

        avg = edge.avg_latency
        trend = edge.trend
        route = f"{src} → {dst}"

        # WARNING
        if latency_ms > avg * 1.2 and trend > 1:
            self._push_alert(
                "warning",
                f"Latency creeping on {dst}",
                f"Latency {latency_ms:.1f}ms (avg {avg:.1f}ms, trend +{trend:.1f}ms)",
                route,
            )

        # CRITICAL
        if latency_ms > avg * 1.5 and trend > 3:
            self._push_alert(
                "critical",
                f"Rapid degradation on {dst}",
                f"Latency {latency_ms:.1f}ms (avg {avg:.1f}ms, trend +{trend:.1f}ms)",
                route,
            )

    def get_alerts(self) -> List[Dict[str, Any]]:
        return self.alerts

    def overall_status(self) -> str:
        """Возвращает общий статус системы для дашборда."""
        for a in self.alerts:
            if a["type"] == "critical":
                return "critical"
        for a in self.alerts:
            if a["type"] == "warning":
                return "warning"
        return "normal"
