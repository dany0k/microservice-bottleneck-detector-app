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

            if parts[0].startswith("traceId"):
                return None

            src = parts[4].strip()
            dst = parts[6].strip()
            latency = float(parts[8])

            return src, dst, latency

        except Exception as e:
            print("PARSE ERROR:", e)
            return None

    def parse_line_old(self, line: str):
        print("RAW:", line.strip())
        try:
            parts = line.strip().split(",")
            if len(parts) < 6:
                return None

            _, src, _, dst, _, latency = parts
            return src, dst, float(latency)
        except Exception:
            return None

    def run_blocking(self):
        print("OPENING:", self.log_file)
        while True:
            try:
                with open(self.log_file, "r") as f:
                    print("FILE OPENED:", self.log_file)
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
                        print("LOG:", src, dst, latency)

                        self._gs.update_from_log(src, dst, latency)
                        self._gs.recent_logs.append(f"{src} → {dst}  {latency} ms")

                        self._ae.handle_log(src, dst)

                        time.sleep(self.interval)
            except Exception:
                time.sleep(self.interval)
                continue
