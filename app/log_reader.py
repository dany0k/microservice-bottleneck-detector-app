import time
from datetime import datetime
from app.models import EdgeMetrics


class LogReader:
    def __init__(self, graph_state, alert_engine, log_file: str, interval: float):
        self._gs = graph_state
        self._ae = alert_engine
        self.log_file = log_file
        self.interval = interval

    def parse_line(self, line: str):
        try:
            parts = line.strip().split(",")

            if parts[0].startswith("traceId"):
                return None

            timestamp = datetime.fromisoformat(parts[3]).timestamp()

            src = f"{parts[4]}{parts[5]}"
            dst = f"{parts[6]}{parts[7]}"

            latency = float(parts[9])
            rps = float(parts[10])

            return timestamp, src, dst, rps, latency

        except Exception as e:
            print("PARSE ERROR:", e)
            return None

    def run_blocking(self):
        print("OPENING:", self.log_file)

        while True:
            try:
                with open(self.log_file, "r") as f:
                    while True:
                        line = f.readline()
                        if not line:
                            f.seek(0)
                            time.sleep(self.interval)
                            continue

                        parsed = self.parse_line(line)
                        if not parsed:
                            continue

                        ts, src, dst, rps, latency = parsed

                        key = (src, dst)
                        if key not in self._gs.edges:
                            self._gs.edges[key] = EdgeMetrics()

                        edge = self._gs.edges[key]
                        edge.update(ts, rps, latency)

                        self._ae.handle_log(src, dst)

                        time.sleep(self.interval)

            except Exception as e:
                print("LOG READER ERROR:", e)
                time.sleep(self.interval)
