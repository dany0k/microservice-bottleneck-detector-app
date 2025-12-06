from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set
from collections import deque, defaultdict
from datetime import datetime, timedelta
import statistics

import networkx as nx  # <-- добавили для max-flow / min-cut

# ------------------------------
#   НАСТРОЙКИ ОКНА И ПОРОГОВ
# ------------------------------

MAX_WINDOW_EVENTS = 200
MAX_WINDOW_SECONDS = 60

LATENCY_WARN = 120.0   # ms
LATENCY_CRIT = 200.0   # ms


# ------------------------------
#   МОДЕЛИ ДАННЫХ
# ------------------------------

@dataclass
class LogEntry:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    timestamp: datetime
    src_service: str
    src_route: str
    dst_service: str
    dst_route: str
    latency_ms: float


@dataclass
class EdgeMetrics:
    latencies: List[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.latencies)

    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0.0

    @property
    def trend(self) -> float:
        if len(self.latencies) < 3:
            return 0.0
        return self.latencies[-1] - self.latencies[0]

    @property
    def best_latency(self) -> float:
        return min(self.latencies) if self.latencies else 0.0

    @property
    def capacity_rps(self) -> float:
        """
        Оценка максимальной пропускной способности по лучшей (минимальной) latency:
        capacity ≈ 1000 ms / best_latency.
        """
        if not self.latencies:
            return 0.0

        best_ms = self.best_latency
        if best_ms <= 0:
            return 0.0

        return 1000.0 / best_ms

    def add(self, latency: float) -> None:
        self.latencies.append(latency)


@dataclass
class NodeMetrics:
    name: str
    bottleneck_score_struct: int = 0   # суммарно: trace + max-flow
    bottleneck_score_degrad: int = 0   # по latency


# ------------------------------
#   ГРАФ В СКОЛЬЗЯЩЕМ ОКНЕ
# ------------------------------

class SlidingWindowGraph:
    def __init__(
        self,
        max_events: int = MAX_WINDOW_EVENTS,
        max_seconds: int = MAX_WINDOW_SECONDS,
        source_node: str = "api-gateway",
    ):
        self.max_events = max_events
        self.max_seconds = max_seconds
        self.source_node = source_node

        self.window: deque[LogEntry] = deque()

        self.nodes: Dict[str, NodeMetrics] = {}
        self.edges: Dict[Tuple[str, str], EdgeMetrics] = {}

    def add_log(self, entry: LogEntry) -> None:
        self.window.append(entry)

        # ограничение по количеству событий
        while len(self.window) > self.max_events:
            self.window.popleft()

        # ограничение по времени
        self._shrink_by_time(entry.timestamp)

        # пересборка агрегированных метрик
        self._rebuild_graph_from_window()

    def _shrink_by_time(self, current_ts: datetime) -> None:
        if self.max_seconds <= 0:
            return

        threshold = current_ts - timedelta(seconds=self.max_seconds)
        while self.window and self.window[0].timestamp < threshold:
            self.window.popleft()

    def _rebuild_graph_from_window(self) -> None:
        self.nodes.clear()
        self.edges.clear()

        for e in self.window:
            if e.src_service not in self.nodes:
                self.nodes[e.src_service] = NodeMetrics(name=e.src_service)
            if e.dst_service not in self.nodes:
                self.nodes[e.dst_service] = NodeMetrics(name=e.dst_service)

            key = (e.src_service, e.dst_service)
            if key not in self.edges:
                self.edges[key] = EdgeMetrics()
            self.edges[key].add(e.latency_ms)

    def sinks(self) -> List[str]:
        sinks = [n for n in self.nodes if n.lower().startswith("db")]
        if not sinks:
            sinks = list(self.nodes.keys())
        return sinks

    def traces(self) -> Dict[str, List[LogEntry]]:
        traces: Dict[str, List[LogEntry]] = {}
        for e in self.window:
            traces.setdefault(e.trace_id, []).append(e)
        for tid in traces:
            traces[tid].sort(key=lambda x: x.timestamp)
        return traces


# ------------------------------
#   АНАЛИЗАТОР ПОТОКОВ
# ------------------------------

class FlowAnalyzer:
    """
    Комбинированный анализатор "узких мест":

    1) Трейсовый структурный анализ:
       - разбираем трейсы в пути от входа до БД;
       - на каждом пути ищем самый медленный шаг (узкое место пути);
       - считаем, по каким рёбрам это происходит чаще всего.

    2) Графовый max-flow / min-cut:
       - строим граф сервисов с capacity по оценке пропускной способности;
       - для источника и всех db-* стоков считаем max-flow и min-cut;
       - рёбра, часто попадающие в min-cut, считаем структурными бутылочными
         горлышками с точки зрения глобальной пропускной способности.

    3) Деградационный анализ:
       - по средней latency в окне, с уровнями warning / critical.

    4) Гибридный рейтинг:
       - комбинируем счётчики из (1) и (2) + среднюю latency + capacity_rps.
    """

    def __init__(self, source_node: str = "api-gateway"):
        self.source_node = source_node

    @staticmethod
    def _is_db_service(name: str) -> bool:
        return name.lower().startswith("db")

    @staticmethod
    def _edge_capacity(m: EdgeMetrics) -> float:
        if m.capacity_rps > 0:
            return m.capacity_rps
        if m.avg_latency > 0:
            return 1000.0 / m.avg_latency
        return 0.0

    # ТРЕЙСОВЫЙ АНАЛИЗ
    def _build_paths_for_trace(self, entries: List[LogEntry]) -> List[List[LogEntry]]:
        span_by_id: Dict[str, LogEntry] = {}
        children: Dict[str, List[LogEntry]] = defaultdict(list)

        for e in entries:
            span_by_id[e.span_id] = e

        # строим дерево (parent -> [children...])
        for e in entries:
            parent = (e.parent_span_id or "").strip()
            if parent:
                children[parent].append(e)

        roots: List[LogEntry] = []
        for e in entries:
            parent = (e.parent_span_id or "").strip()
            if not parent or parent not in span_by_id:
                roots.append(e)

        paths: List[List[LogEntry]] = []

        def dfs(current: LogEntry, path: List[LogEntry]) -> None:
            new_path = path + [current]

            if self._is_db_service(current.dst_service):
                paths.append(new_path)

            for child in children.get(current.span_id, []):
                dfs(child, new_path)

        for r in roots:
            dfs(r, [])

        return paths

    def _trace_structural_phase(
        self,
        graph: SlidingWindowGraph,
    ) -> Tuple[Set[Tuple[str, str]], Dict[Tuple[str, str], int]]:
        traces = graph.traces()

        structural_edges: Set[Tuple[str, str]] = set()
        structural_count: Dict[Tuple[str, str], int] = defaultdict(int)

        print("\n================= СТРУКТУРНЫЙ АНАЛИЗ ПО ТРЕЙСАМ =================")
        print(f"Трейсов в окне: {len(traces)}")

        for trace_id, entries in traces.items():
            print(f"\n--- Трейс {trace_id} ---")

            paths = self._build_paths_for_trace(entries)
            if not paths:
                print("  Нет полных путей до БД (db-*).")
                continue

            for idx, path in enumerate(paths, start=1):
                total_latency = sum(e.latency_ms for e in path)
                print(f"  Путь #{idx}: шагов={len(path)}, "
                      f"суммарная латентность={total_latency:.1f} ms")
                for step in path:
                    print(
                        f"    {step.src_service} → {step.dst_service} "
                        f"({step.latency_ms:.1f} ms)"
                    )

                bottleneck = max(path, key=lambda e: e.latency_ms)
                edge_key = (bottleneck.src_service, bottleneck.dst_service)
                structural_edges.add(edge_key)
                structural_count[edge_key] += 1

                print(
                    f"    → Структурное узкое место на пути: "
                    f"{bottleneck.src_service} → {bottleneck.dst_service} "
                    f"(latency={bottleneck.latency_ms:.1f} ms)"
                )

        print("\n================= ИТОГ СТРУКТУРНОГО АНАЛИЗА (ТРЕЙСЫ) =================")
        if not structural_edges:
            print("Структурные бутылочные горлышки по трейсам не обнаружены.")
        else:
            print("Структурные бутылочные горлышки по трейсам:")
            for (u, v), cnt in sorted(
                structural_count.items(),
                key=lambda kv: kv[1],
                reverse=True,
            ):
                print(f"  {u} → {v}: {cnt} раз(а)")

        return structural_edges, structural_count

    # ГРАФОВЫЙ АНАЛИЗ (MAX-FLOW / MIN-CUT)
    def _flow_structural_phase(
        self,
        graph: SlidingWindowGraph,
    ) -> Tuple[Set[Tuple[str, str]], Dict[Tuple[str, str], int], float]:
        nodes = graph.nodes
        edges = graph.edges
        src_node = graph.source_node
        sinks = graph.sinks()

        G = nx.DiGraph()
        for (u, v), m in edges.items():
            cap = self._edge_capacity(m)
            G.add_edge(u, v, capacity=cap)

        structural_edges: Set[Tuple[str, str]] = set()
        structural_count: Dict[Tuple[str, str], int] = defaultdict(int)
        total_flow = 0.0

        print("\n================= ГРАФОВЫЙ АНАЛИЗ (MAX-FLOW / MIN-CUT) =================")
        print("Рёбра графа:")
        for (u, v), m in edges.items():
            print(
                f"  {u} → {v}: avg={m.avg_latency:.1f} ms, "
                f"best={m.best_latency:.1f} ms, "
                f"capacity≈{m.capacity_rps:.2f} rps, calls={m.count}"
            )

        print("\nСтоки (БД):", sinks)

        for target in sinks:
            if target == src_node:
                continue

            if src_node not in nodes or target not in nodes:
                continue

            try:
                print(f"\n--- Путь {src_node} → {target} (max-flow/min-cut) ---")
                flow_val, _ = nx.maximum_flow(G, src_node, target)
                total_flow += flow_val
                print(f"Максимальный поток до {target}: {flow_val:.2f}")

                cut_edges = nx.minimum_edge_cut(G, src_node, target)
                if not cut_edges:
                    print("  Min-cut пустой, ограничивающих рёбер не найдено.")
                    continue

                print("  Рёбра в min-cut (структурные узкие места для этого стока):")
                for (u, v) in cut_edges:
                    structural_edges.add((u, v))
                    structural_count[(u, v)] += 1
                    m = edges.get((u, v))
                    if m:
                        print(
                            f"    {u} → {v}: avg={m.avg_latency:.1f} ms, "
                            f"capacity≈{m.capacity_rps:.2f} rps, calls={m.count}"
                        )
                    else:
                        print(f"    {u} → {v}: (нет метрик, но попало в min-cut)")
            except Exception as ex:
                print(f"  [WARN] Не удалось посчитать max-flow до {target}: {ex}")
                continue

        print("\n=========== ИТОГ ГРАФОВОГО АНАЛИЗА (MAX-FLOW / MIN-CUT) ===========")
        print(f"Суммарный максимальный поток по всем стокам: {total_flow:.2f}")
        if not structural_edges:
            print("Структурные узкие места по max-flow/min-cut не обнаружены.")
        else:
            print("Структурные бутылочные горлышки по max-flow/min-cut:")
            for (u, v), cnt in sorted(
                structural_count.items(),
                key=lambda kv: kv[1],
                reverse=True,
            ):
                print(f"  {u} → {v}: в min-cut для {cnt} сток(ов)")

        return structural_edges, structural_count, total_flow

    def _degradation_phase(
        self,
        graph: SlidingWindowGraph,
    ) -> Dict[Tuple[str, str], str]:
        nodes = graph.nodes
        edges = graph.edges

        degradation_edges: Dict[Tuple[str, str], str] = {}

        for (u, v), m in edges.items():
            if m.avg_latency >= LATENCY_CRIT:
                degradation_edges[(u, v)] = "critical"
            elif m.avg_latency >= LATENCY_WARN:
                degradation_edges[(u, v)] = "warning"

        for n in nodes.values():
            n.bottleneck_score_degrad = 0

        for (u, v), level in degradation_edges.items():
            if u in nodes:
                nodes[u].bottleneck_score_degrad += 1
            if v in nodes:
                nodes[v].bottleneck_score_degrad += 1

        print("\n================= ДЕГРАДАЦИОННЫЕ УЗКИЕ МЕСТА (LATENCY) =================")
        if not degradation_edges:
            print("Деградационных бутылочных горлышек по latency не найдено.")
        else:
            for (u, v), lvl in sorted(
                degradation_edges.items(),
                key=lambda kv: graph.edges[kv[0]].avg_latency,
                reverse=True,
            ):
                m = edges[(u, v)]
                print(
                    f"  [{lvl.upper()}] {u} → {v}: avg={m.avg_latency:.1f} ms, "
                    f"calls={m.count}"
                )
        print("=======================================================================")

        return degradation_edges

    def _hybrid_phase(
        self,
        graph: SlidingWindowGraph,
        trace_struct_count: Dict[Tuple[str, str], int],
        flow_struct_count: Dict[Tuple[str, str], int],
        degradation_edges: Dict[Tuple[str, str], str],
    ) -> Dict[Tuple[str, str], float]:
        edges = graph.edges

        combined_struct_count: Dict[Tuple[str, str], int] = defaultdict(int)
        for k, v in trace_struct_count.items():
            combined_struct_count[k] += v
        for k, v in flow_struct_count.items():
            combined_struct_count[k] += v

        max_struct = max(combined_struct_count.values()) if combined_struct_count else 0

        max_capacity = max((m.capacity_rps for m in edges.values()), default=0.0)

        hybrid_scores: Dict[Tuple[str, str], float] = {}

        W_STRUCT = 0.5
        W_LAT = 0.25
        W_CAP = 0.25

        print("\n================= ГИБРИДНЫЙ РЕЙТИНГ БУТЫЛОЧНЫХ ГОРЛЫШЕК =================")

        if not edges:
            print("Рёбер нет, гибридный рейтинг не считается.")
            print("=======================================================================")
            return hybrid_scores

        for key, m in edges.items():
            s_raw = combined_struct_count.get(key, 0)
            s_norm = (s_raw / max_struct) if max_struct > 0 else 0.0

            lat_norm = min(m.avg_latency / LATENCY_CRIT, 1.0) if m.avg_latency > 0 else 0.0

            if max_capacity > 0 and m.capacity_rps > 0:
                cap_penalty = 1.0 - (m.capacity_rps / max_capacity)
                cap_penalty = max(0.0, min(cap_penalty, 1.0))
            else:
                cap_penalty = 0.0

            score = W_STRUCT * s_norm + W_LAT * lat_norm + W_CAP * cap_penalty
            hybrid_scores[key] = score

        sorted_edges = sorted(
            hybrid_scores.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
        for (u, v), score in sorted_edges:
            m = edges[(u, v)]
            trace_c = trace_struct_count.get((u, v), 0)
            flow_c = flow_struct_count.get((u, v), 0)
            degr = degradation_edges.get((u, v), "none")
            print(
                f"  {u} → {v}: hybrid_score={score:.3f}, "
                f"trace_struct={trace_c}, flow_struct={flow_c}, "
                f"avg={m.avg_latency:.1f} ms, best={m.best_latency:.1f} ms, "
                f"capacity≈{m.capacity_rps:.1f} rps, "
                f"lat_lvl={degr}, calls={m.count}"
            )
        print("=======================================================================")

        for n in graph.nodes.values():
            n.bottleneck_score_struct = 0
        for (u, v), cnt in combined_struct_count.items():
            if u in graph.nodes:
                graph.nodes[u].bottleneck_score_struct += cnt
            if v in graph.nodes:
                graph.nodes[v].bottleneck_score_struct += cnt

        return hybrid_scores

    def analyze(self, graph: SlidingWindowGraph) -> Dict[str, object]:
        trace_struct_edges, trace_struct_count = self._trace_structural_phase(graph)
        flow_struct_edges, flow_struct_count, total_flow = self._flow_structural_phase(graph)
        degradation_edges = self._degradation_phase(graph)
        hybrid_scores = self._hybrid_phase(
            graph,
            trace_struct_count,
            flow_struct_count,
            degradation_edges,
        )

        return {
            "trace_struct_edges": trace_struct_edges,
            "trace_struct_count": trace_struct_count,
            "flow_struct_edges": flow_struct_edges,
            "flow_struct_count": flow_struct_count,
            "total_flow": total_flow,
            "degradation_edges": degradation_edges,
            "hybrid_scores": hybrid_scores,
            "nodes": graph.nodes,
        }


def parse_timestamp(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def parse_log_line(line: str) -> LogEntry | None:
    line = line.strip()
    if not line:
        return None

    if line.lower().startswith("traceid"):
        return None

    parts = line.split(",")
    if len(parts) < 9:
        return None

    trace_id, span_id, parent_span_id, ts_s, src_s, src_route, dst_s, dst_route, latency_s = parts[:9]

    try:
        ts = parse_timestamp(ts_s.strip())
        latency = float(latency_s.strip())
    except Exception:
        return None

    parent_span_id = parent_span_id.strip() or None

    return LogEntry(
        trace_id=trace_id.strip(),
        span_id=span_id.strip(),
        parent_span_id=parent_span_id,
        timestamp=ts,
        src_service=src_s.strip(),
        src_route=src_route.strip(),
        dst_service=dst_s.strip(),
        dst_route=dst_route.strip(),
        latency_ms=latency,
    )


def load_logs_from_file(path: str) -> List[LogEntry]:
    result: List[LogEntry] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = parse_log_line(line)
            if entry:
                result.append(entry)
    result.sort(key=lambda e: e.timestamp)
    return result


def main():
    if len(sys.argv) < 2:
        print("Использование: python bottleneck_cli.py path/to/logs.csv")
        sys.exit(1)

    log_path = sys.argv[1]
    print(f"Читаем логи из: {log_path}")

    logs = load_logs_from_file(log_path)
    print(f"Загружено {len(logs)} строк логов.")

    graph = SlidingWindowGraph()
    analyzer = FlowAnalyzer(source_node="api-gateway")

    for i, entry in enumerate(logs, start=1):
        graph.add_log(entry)

        if i % 50 == 0 or i == len(logs):
            print(f"\n================ ОКНО ПОСЛЕ {i} ЗАПИСЕЙ =================")
            print(f"Размер окна: {len(graph.window)} записей")
            print(f"Узлов в графе: {len(graph.nodes)}, рёбер: {len(graph.edges)}")

            analyzer.analyze(graph)

    print("\nГотово.")


if __name__ == "__main__":
    main()
