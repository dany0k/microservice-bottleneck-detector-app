import csv
import time
from typing import IO
from .graph_state import GraphState
from .alert_engine import AlertEngine


class LogReader:
    """
    Читает live_logs.csv по кругу и "проигрывает" его как поток логов.
    Формат строки:
    timestamp, src_service, src_endpoint, dst_service, dst_endpoint, latency_ms
    """

    def __init__(
        self,
        graph_state: GraphState,
        alert_engine: AlertEngine,
        log_file: str,
        interval: float,
    ) -> None:
        self.graph_state = graph_state
        self.alert_engine = alert_engine
        self.log_file = log_file
        self.interval = interval

    def _iter_logs(self):
        while True:
            with open(self.log_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row or len(row) < 6:
                        continue
                    # timestamp = row[0]
                    src_service = row[1].strip()
                    # src_endpoint = row[2].strip()
                    dst_service = row[3].strip()
                    # dst_endpoint = row[4].strip()
                    try:
                        latency_ms = float(row[5])
                    except ValueError:
                        continue
                    yield src_service, dst_service, latency_ms
            # по окончании файла начинаем заново

    def run_blocking(self) -> None:
        for src, dst, latency_ms in self._iter_logs():
            self.graph_state.update_from_log(src, dst, latency_ms)
            self.alert_engine.process_observation(src, dst, latency_ms)
            time.sleep(self.interval)
