# app/graph_state.py
from typing import Dict, Tuple
from collections import deque

from .models import NodeMetrics, EdgeMetrics


class GraphState:
    def __init__(self):
        self.nodes: Dict[str, NodeMetrics] = {}
        self.edges: Dict[Tuple[str, str], EdgeMetrics] = {}

        self.total_logs: int = 0
        self.recent_logs = deque(maxlen=200)

        self.bottleneck_edges = set()
        self.global_max_flow: float = 0.0

    def _ensure_node(self, name: str) -> NodeMetrics:
        if name not in self.nodes:
            self.nodes[name] = NodeMetrics(name=name)
        return self.nodes[name]

    def update_from_log(self, src: str, dst: str, latency: float) -> None:
        self.total_logs += 1

        self._ensure_node(src)
        self._ensure_node(dst)

        key = (src, dst)
        if key not in self.edges:
            self.edges[key] = EdgeMetrics()

        self.edges[key].update(latency)

    def _compute_incoming_edges(self):
        incoming = {name: [] for name in self.nodes}
        for (src, dst), m in self.edges.items():
            incoming[dst].append(m)
        return incoming

    def _compute_node_load(self, incoming_edges):
        load = {}
        for node, edges in incoming_edges.items():
            load[node] = sum(m.count for m in edges)
        return load

    def _compute_node_avg_latency(self, incoming_edges):
        avg = {}
        for node, edges in incoming_edges.items():
            if edges:
                total = sum(sum(m.latencies) for m in edges)
                count = sum(len(m.latencies) for m in edges)
                avg[node] = total / count if count > 0 else 0.0
            else:
                avg[node] = 0.0
        return avg

    def export(self) -> dict:
        incoming_edges = self._compute_incoming_edges()
        load = self._compute_node_load(incoming_edges)
        avg_latency = self._compute_node_avg_latency(incoming_edges)

        nodes_out = []
        for name in self.nodes:
            node = self.nodes[name]
            nodes_out.append(
                {
                    "id": name,
                    "label": name,
                    "load": load[name],
                    "avg_latency": avg_latency[name],
                    "status": node.status,
                    "bottleneck_score": node.bottleneck_score,
                }
            )

        edges_out = []
        for (src, dst), m in self.edges.items():
            edges_out.append(
                {
                    "id": f"{src}->{dst}",
                    "source": src,
                    "target": dst,
                    "latency": m.last_latency,
                    "avg_latency": m.avg_latency,
                    "capacity": round(1.0 / m.avg_latency, 4) if m.avg_latency else None,
                    "is_bottleneck": (src, dst) in self.bottleneck_edges,
                }
            )

        return {
            "nodes": nodes_out,
            "edges": edges_out,
            "max_flow": self.global_max_flow,
            "bottlenecks": [f"{u}->{v}" for (u, v) in self.bottleneck_edges],
        }

    def active_nodes_count(self) -> int:
        return len(self.nodes)
