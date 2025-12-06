import networkx as nx
from typing import Dict, Tuple
from .models import EdgeMetrics, NodeMetrics


class FlowAnalyzer:
    def __init__(self, source_node: str = "api-gateway"):
        self.source_node = source_node

    @staticmethod
    def edge_capacity(metrics: EdgeMetrics) -> float:
        if metrics.avg_latency and metrics.avg_latency > 0:
            return 1.0 / metrics.avg_latency
        return 9999.0  # fallback

    def analyze(
        self,
        nodes: Dict[str, NodeMetrics],
        edges: Dict[Tuple[str, str], EdgeMetrics],
    ) -> tuple[float, set[Tuple[str, str]]]:

        print("\n================= ПЕРЕСЧЁТ ПОТОКОВ (MAX-FLOW / MIN-CUT) =================")

        G = nx.DiGraph()

        print("Добавляем рёбра в граф:")
        for (src, dst), metrics in edges.items():
            cap = self.edge_capacity(metrics)
            print(f"  {src} → {dst}: avg={metrics.avg_latency:.1f} ms, capacity={cap:.5f}, calls={metrics.count}")
            G.add_edge(src, dst, capacity=cap)

        sinks = [name for name in nodes if name.startswith("db")]
        if not sinks:
            sinks = list(nodes.keys())

        print("\nСтоки (targets):", sinks)

        total_flow = 0.0
        bottlenecks: set[Tuple[str, str]] = set()

        for target in sinks:
            if target == self.source_node:
                continue

            print(f"\n--- Анализ пути: {self.source_node} → {target} ---")

            try:
                flow_val, _ = nx.maximum_flow(G, self.source_node, target)
                total_flow += flow_val
                print(f"Максимальный поток = {flow_val:.5f}")

                cut = nx.minimum_edge_cut(G, self.source_node, target)

                if not cut:
                    print("Min-cut пустой — узких мест нет.")
                else:
                    print("Min-cut рёбра (узкие места):")
                    for u, v in cut:
                        m = edges.get((u, v))
                        if m:
                            avg = m.avg_latency
                            cap = self.edge_capacity(m)
                            cnt = m.count
                            print(
                                f"  {u} → {v}: avg={avg:.1f} ms, capacity={cap:.5f}, calls={cnt}"
                            )
                            print("    Причина: это ребро ограничивает поток и попало в min-cut.")
                        else:
                            print(f"  {u} → {v}: нет метрик, но ребро в min-cut.")
                        bottlenecks.add((u, v))

            except Exception as e:
                print(f"[ОШИБКА] Не удалось вычислить поток до {target}: {e}")
                continue

        print("\n================= ИТОГИ ПОТОКОВ =================")
        print(f"Глобальный максимальный поток: {round(total_flow, 4)}")
        print("Найденные бутылочные горлышки:", bottlenecks)
        print("=======================================================================\n")

        return round(total_flow, 4), bottlenecks
