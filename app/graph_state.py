from .models import NodeMetrics, EdgeMetrics


from collections import deque

class GraphState:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.total_logs = 0
        self.recent_logs = deque(maxlen=100)


    # --------------------------------------

    def _ensure_node(self, name: str) -> NodeMetrics:
        if name not in self.nodes:
            self.nodes[name] = NodeMetrics(name)
        return self.nodes[name]

    def _ensure_edge(self, src: str, dst: str) -> EdgeMetrics:
        key = (src, dst)
        if key not in self.edges:
            self.edges[key] = EdgeMetrics()
        return self.edges[key]

    # --------------------------------------

    def update_from_log(self, src: str, dst: str, latency_ms: float):
        """Обновляет граф по одной записи лога."""
        self.total_logs += 1

        src_node = self._ensure_node(src)
        dst_node = self._ensure_node(dst)

        src_node.update(latency_ms)
        dst_node.mark_touched()

        edge = self._ensure_edge(src, dst)
        edge.update(latency_ms)

        self.recent_logs.append(f"{src} → {dst}  {latency_ms:.1f} ms")

    # --------------------------------------

    def active_nodes_count(self) -> int:
        return len(self.nodes)

    # --------------------------------------

    def export(self) -> dict:
        """Формат данных для отправки в граф на фронт."""

        nodes = []
        for name, m in self.nodes.items():
            nodes.append({
                "id": name,
                "label": name,
                "load": m.total_calls,
                "avg_latency": m.avg_latency,
                "status": m.status
            })

        edges = []
        for (src, dst), m in self.edges.items():
            edges.append({
                "id": f"{src}->{dst}",
                "source": src,
                "target": dst,
                "latency": m.last_latency,
                "avg_latency": m.avg_latency,
                "trend": m.trend
            })

        return {"nodes": nodes, "edges": edges}
