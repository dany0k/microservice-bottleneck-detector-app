import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# путь к твоему CSV с логами
LOG_FILE = os.path.join(BASE_DIR, "live_logs.csv")

# интервал между "логами" при симуляции (секунды)
SIMULATION_INTERVAL = 0.3
