import time
from .alert_engine import AlertEngine

class LogReader:
    """
    Читает файл логов циклически.
    SIMULATION_INTERVAL — задержка между логами.
    """

    def __init__(self, graph_state, alert_engine: AlertEngine, log_file: str, interval: float):
        self._gs = graph_state
        self._ae = alert_engine
        self.log_file = log_file
        self.interval = interval

    # --------------------------------------

    def parse_line(self, line: str):
        """
        Формат строки:
        timestamp,src,src_route,dst,dst_route,latency
        """
        try:
            _, src, _, dst, _, latency = line.strip().split(",")
            return src, dst, float(latency)
        except Exception:
            return None

    # --------------------------------------

    def run_blocking(self):
        """Бесконечное чтение файла + возврат в начало."""
        while True:
            with open(self.log_file, "r") as f:
                while True:
                    line = f.readline()

                    if not line or line.strip() == "":
                        f.seek(0)
                        continue

                    parsed = self.parse_line(line)
                    if not parsed:
                        continue

                    src, dst, latency = parsed

                    # обновляем граф
                    self._gs.update_from_log(src, dst, latency)

                    # записываем лог в очередь для UI
                    self._gs.recent_logs.append(f"{src} → {dst}  {latency} ms")
                    if len(self._gs.recent_logs) > 100:
                        self._gs.recent_logs.pop(0)

                    # анализ для определения деградаций
                    self._ae.handle_log(src, dst)

                    time.sleep(self.interval)
