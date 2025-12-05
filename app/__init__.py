from flask import Flask
from flask_cors import CORS
from threading import Thread
from .config import LOG_FILE, SIMULATION_INTERVAL
from .graph_state import GraphState
from .log_reader import LogReader
from .alert_engine import AlertEngine
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    CORS(app)

    graph_state = GraphState()
    alert_engine = AlertEngine(graph_state)

    # фоновая симуляция логов из файла
    reader = LogReader(graph_state, alert_engine, LOG_FILE, SIMULATION_INTERVAL)
    t = Thread(target=reader.run_blocking, daemon=True)
    t.start()

    app.graph_state = graph_state
    app.alert_engine = alert_engine

    from .routes import bp

    app.register_blueprint(bp)

    return app
