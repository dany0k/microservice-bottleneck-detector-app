from dataclasses import dataclass, field
from collections import deque
from typing import Literal


#  Метрики узла (сервиса)
@dataclass
class NodeMetrics:
    name: str
    total_calls: int = 0
    total_latency: float = 0.0
    avg_latency: float = 0.0
    status: Literal["ok", "warning", "critical"] = "ok"

    def update(self, latency_ms: float) -> None:
        self.total_calls += 1
        self.total_latency += latency_ms
        self.avg_latency = self.total_latency / self.total_calls

    def mark_touched(self) -> None:
        if self.total_calls == 0:
            self.total_calls = 1
            self.avg_latency = 0.0


#  Метрики ребра (вызова)
@dataclass
class EdgeMetrics:
    last_latency: float = 0.0
    total_latency: float = 0.0
    count: int = 0
    avg_latency: float = 0.0
    history: deque = field(default_factory=lambda: deque(maxlen=20))

    @property
    def trend(self) -> float:
        if len(self.history) < 2:
            return 0.0
        return (self.history[-1] - self.history[0]) / (len(self.history) - 1)

    def update(self, latency_ms: float):
        self.last_latency = latency_ms
        self.total_latency += latency_ms
        self.count += 1
        self.avg_latency = self.total_latency / self.count
        self.history.append(latency_ms)
