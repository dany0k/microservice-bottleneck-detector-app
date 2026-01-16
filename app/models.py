from typing import List, Optional, Deque, Tuple
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
    samples: Deque[Tuple[float, float, float]] = field(
        default_factory=lambda: deque(maxlen=1000)
    )

    def update(self, timestamp: float, rps: float, latency: float):
        self.samples.append((timestamp, rps, latency))

    @property
    def avg_latency(self) -> float:
        if not self.samples:
            return 0.0
        return statistics.mean(lat for _, _, lat in self.samples)

    @property
    def avg_rps(self) -> float:
        if not self.samples:
            return 0.0
        return statistics.mean(rps for _, rps, _ in self.samples)

