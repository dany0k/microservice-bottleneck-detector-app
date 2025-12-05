from flask import Blueprint, jsonify, render_template, current_app

bp = Blueprint("main", __name__)


@bp.route("/")
def index_page():
    return render_template("index.html")


@bp.route("/api/graph")
def api_graph():
    gs = current_app.graph_state
    return jsonify(gs.export())


@bp.route("/api/logs")
def api_logs():
    gs = current_app.graph_state
    return jsonify({"logs": gs.recent_logs})


@bp.route("/api/alerts")
def api_alerts():
    ae = current_app.alert_engine
    return jsonify({"alerts": ae.get_alerts()})


@bp.route("/api/stats")
def api_stats():
    gs = current_app.graph_state
    ae = current_app.alert_engine

    return jsonify({
        "total_logs": gs.total_logs,
        "active_nodes": gs.active_nodes_count(),
        "status": ae.overall_status(),
    })
