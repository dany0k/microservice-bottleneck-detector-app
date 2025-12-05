from typing import Dict, Tuple, List
from .models import NodeMetrics, EdgeMetrics


class GraphState:
    def __init__(self):
        self.nodes: Dict[str, NodeMetrics] = {}
        self.edges: Dict[Tuple[str, str], EdgeMetrics] = {}

        self.total_logs = 0
        self.recent_logs: List[str] = []
        self._max_logs = 50

    def _ensure_node(self, name: str) -> NodeMetrics:
        if name not in self.nodes:
            self.nodes[name] = NodeMetrics(name=name)
        return self.nodes[name]

    def _append_log(self, src: str, dst: str, lat: float):
        line = f"{src} → {dst}  {lat:.1f} ms"
        self.recent_logs.append(line)
        if len(self.recent_logs) > self._max_logs:
            self.recent_logs.pop(0)

    def update_from_log(self, src: str, dst: str, latency: float):
        self.total_logs += 1

        src_node = self._ensure_node(src)
        dst_node = self._ensure_node(dst)

        # узловые метрики
        src_node.total_calls += 1
        src_node.add_latency(latency)

        # ребро
        key = (src, dst)
        if key not in self.edges:
            self.edges[key] = EdgeMetrics()
        self.edges[key].update(latency)

        self._append_log(src, dst, latency)

    def export(self):
        """DTO для фронтенда."""
        return {
            "nodes": [
                {
                    "id": n.name,
                    "label": n.name,
                    "load": n.total_calls,
                    "avg_latency": n.avg_latency,
                    "status": n.status,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "id": f"{src}->{dst}",
                    "source": src,
                    "target": dst,
                    "latency": m.last_latency,
                    "avg_latency": m.avg_latency,
                    "trend": m.trend,
                }
                for (src, dst), m in self.edges.items()
            ],
        }

    def active_nodes_count(self):
        return len(self.nodes)
