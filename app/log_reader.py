import time
from .alert_engine import AlertEngine


class LogReader:
    def __init__(self, graph_state, alert_engine: AlertEngine, log_file: str, interval: float):
        self._gs = graph_state
        self._ae = alert_engine
        self.log_file = log_file
        self.interval = interval

    def parse_line(self, line: str):
        try:
            parts = line.strip().split(",")
            if len(parts) < 6:
                return None

            _, src, _, dst, _, latency = parts
            return src, dst, float(latency)
        except Exception:
            return None

    def run_blocking(self):
        while True:
            try:
                with open(self.log_file, "r") as f:
                    while True:
                        line = f.readline()

                        if not line:
                            f.seek(0)
                            time.sleep(self.interval)
                            continue

                        if line.strip() == "":
                            continue

                        parsed = self.parse_line(line)
                        if not parsed:
                            continue

                        src, dst, latency = parsed

                        self._gs.update_from_log(src, dst, latency)
                        self._gs.recent_logs.append(f"{src} → {dst}  {latency} ms")

                        self._ae.handle_log(src, dst)

                        time.sleep(self.interval)
            except Exception:
                time.sleep(self.interval)
                continue
