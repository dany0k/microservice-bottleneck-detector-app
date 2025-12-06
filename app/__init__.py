from flask import Flask
from flask_cors import CORS
from threading import Thread
import os

from .config import LOG_FILE, SIMULATION_INTERVAL
from .graph_state import GraphState
from .log_reader import LogReader
from .alert_engine import AlertEngine

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
    graph_state.alert_engine = alert_engine

    app.graph_state = graph_state
    app.alert_engine = alert_engine

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print(">>> Starting LogReader THREAD (MAIN PROCESS)")
        reader = LogReader(graph_state, alert_engine, LOG_FILE, SIMULATION_INTERVAL)
        t = Thread(target=reader.run_blocking, daemon=True)
        t.start()
    else:
        print(">>> SKIP LogReader THREAD (LOADER PROCESS)")

    from .routes import bp
    app.register_blueprint(bp)

    return app

