from dataclasses import dataclass, field
import statistics


@dataclass
class NodeMetrics:
    name: str
    total_calls: int = 0
    latencies: list = field(default_factory=list)

    @property
    def avg_latency(self):
        return statistics.mean(self.latencies) if self.latencies else 0

    @property
    def status(self):
        """Логика статуса узла на основе среднего latency."""
        avg = self.avg_latency
        if avg > 150:
            return "critical"
        elif avg > 80:
            return "warning"
        return "normal"

    def add_latency(self, val: float):
        self.latencies.append(val)
        if len(self.latencies) > 100:
            self.latencies.pop(0)


@dataclass
class EdgeMetrics:
    latencies: list = field(default_factory=list)
    last_latency: float = 0

    @property
    def avg_latency(self):
        return statistics.mean(self.latencies) if self.latencies else 0

    @property
    def trend(self):
        """Возвращает изменение latency относительно последних значений."""
        if len(self.latencies) < 3:
            return 0
        return self.latencies[-1] - self.latencies[-3]

    def update(self, latency: float):
        self.last_latency = latency
        self.latencies.append(latency)
        if len(self.latencies) > 100:
            self.latencies.pop(0)
