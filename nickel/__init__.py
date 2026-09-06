from flask import Flask, render_template, jsonify, request

from . import config, db
from .analysis import annual_trend
from .fred import FredService
from .predict import forecast
from .scheduler import DailyMonitor
from .services import NickelService
from .sheet import NewsService, SheetService
from .static_data import RECENT, DRIVERS

service = NickelService()
monitor = DailyMonitor(service)
sheet_service = SheetService()
news_service = NewsService()
fred_service = FredService()


def create_app():
    app = Flask(__name__)

    db.init_db()
    monitor.start()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/nickel")
    def api_nickel():
        force = request.args.get("force") == "1"
        try:
            quote = service.get_latest(force_refresh=force)
            return jsonify({"success": True, "data": quote})
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/history")
    def api_history():
        return jsonify({"success": True, "data": service.get_history()})

    @app.route("/api/dashboard")
    def api_dashboard():
        force = request.args.get("force") == "1"
        payload = {"success": True}

        try:
            payload["sheet"] = sheet_service.summary(force=force)
        except Exception as exc:
            payload["sheet"] = {"ok": False, "error": str(exc)}

        try:
            payload["live"] = service.get_latest(force_refresh=force)
        except Exception as exc:
            payload["live"] = {"error": str(exc)}

        try:
            payload["annual"] = annual_trend(fred_service.annual_with_current())
        except Exception:
            payload["annual"] = annual_trend()

        try:
            payload["recent"] = fred_service.recent()
        except Exception:
            payload["recent"] = RECENT
        payload["drivers"] = DRIVERS

        try:
            payload["news"] = news_service.get_news(force=force)
        except Exception as exc:
            payload["news"] = {"error": str(exc)}

        history = service.get_history()
        payload["monitor"] = {
            "running": monitor._thread is not None and monitor._thread.is_alive(),
            "total_records": len(history),
            "recorded_today": bool(
                db.get_daily_by_date(__import__("datetime").date.today().isoformat())
            ),
            "last_log": db.last_monitor_log(),
        }
        return jsonify(payload)

    @app.route("/api/annual")
    def api_annual():
        try:
            return jsonify({"success": True, "data": annual_trend(fred_service.annual_with_current())})
        except Exception:
            return jsonify({"success": True, "data": annual_trend()})

    @app.route("/api/news")
    def api_news():
        try:
            return jsonify({"success": True, "data": news_service.get_news()})
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/predict")
    def api_predict():
        days = request.args.get("days", type=int) or config.PREDICT_DAYS
        history = service.get_history()
        result = forecast(history, days=days)
        if result is None:
            return jsonify({"success": False, "error": "歷史資料不足，無法預測"}), 400
        return jsonify({"success": True, "data": result})

    @app.route("/api/daily/run", methods=["POST"])
    def api_daily_run():
        try:
            record = service.capture_today()
            return jsonify({"success": True, "data": record})
        except Exception as exc:
            db.add_monitor_log("error", f"手動抓取失敗: {exc}")
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/monitor/status")
    def api_monitor_status():
        return jsonify({"success": True, "data": monitor_status()})

    def monitor_status():
        history = service.get_history()
        return {
            "running": monitor._thread is not None and monitor._thread.is_alive(),
            "total_records": len(history),
            "recorded_today": bool(
                db.get_daily_by_date(__import__("datetime").date.today().isoformat())
            ),
            "last_log": db.last_monitor_log(),
        }

    return app
