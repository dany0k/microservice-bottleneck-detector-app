from typing import List, Optional
from collections import deque
import time
import statistics
from dataclasses import dataclass, field
from typing import List

@dataclass
class NodeMetrics:
    name: str

    outgoing_calls: int = 0
    outgoing_latencies: List[float] = field(default_factory=list)

    incoming_calls: int = 0
    incoming_latencies: List[float] = field(default_factory=list)

    bottleneck_score: float = 0.0

    _forced_status: Optional[str] = None

    def add_outgoing_latency(self, val: float) -> None:
        self.outgoing_latencies.append(val)
        if len(self.outgoing_latencies) > 200:
            self.outgoing_latencies.pop(0)

    def add_incoming_latency(self, val: float) -> None:
        self.incoming_latencies.append(val)
        if len(self.incoming_latencies) > 200:
            self.incoming_latencies.pop(0)

    @property
    def outgoing_avg_latency(self) -> float:
        return (
            statistics.mean(self.outgoing_latencies)
            if self.outgoing_latencies
            else 0.0
        )

    @property
    def incoming_avg_latency(self) -> float:
        return (
            statistics.mean(self.incoming_latencies)
            if self.incoming_latencies
            else 0.0
        )

    @property
    def total_calls(self) -> int:
        return self.incoming_calls + self.outgoing_calls

    @property
    def total_avg_latency(self) -> float:
        vals: List[float] = []
        vals.extend(self.incoming_latencies)
        vals.extend(self.outgoing_latencies)
        return statistics.mean(vals) if vals else 0.0

    @property
    def max_observed_latency(self) -> float:
        vals: List[float] = []
        vals.extend(self.incoming_latencies)
        vals.extend(self.outgoing_latencies)
        return max(vals) if vals else 0.0

    # ---------- Статус узла ----------

    @property
    def status(self) -> str:
        if self._forced_status is not None:
            return self._forced_status

        base_avg = self.incoming_avg_latency or self.total_avg_latency

        if base_avg > 200:
            return "critical"
        elif base_avg > 100:
            return "warning"
        return "normal"

    @status.setter
    def status(self, value: str) -> None:
        self._forced_status = value

@dataclass
class EdgeMetrics:
    latencies: List[float] = field(default_factory=list)
    last_latency: float = 0.0
    count: int = 0

    samples: deque = field(default_factory=lambda: deque(maxlen=50))

    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0.0

    @property
    def trend(self) -> float:
        if len(self.latencies) < 3:
            return 0.0
        return self.latencies[-1] - self.latencies[-3]

    def update(self, latency: float, rps: int):
        now = int(time.time())

        self.last_latency = latency
        self.latencies.append(latency)
        self.count += 1

        if len(self.latencies) > 200:
            self.latencies.pop(0)

        # сохраняем точку
        self.samples.append((now, rps, latency))

