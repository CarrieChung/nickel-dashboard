import time
from concurrent.futures import ThreadPoolExecutor, wait

from flask import Flask, render_template, jsonify, request

from . import config, db
from .analysis import annual_trend
from .fred import FredService
from .predict import forecast
from .scheduler import DailyMonitor
from .services import NickelService
from .sheet import NewsService, SheetService
from .static_data import RECENT, DRIVERS

sheet_service = SheetService()
service = NickelService(sheet_service=sheet_service)
monitor = DailyMonitor(service)
news_service = NewsService()
fred_service = FredService()

DASHBOARD_BUDGET_SECONDS = 45


def _call_with_timeout(fn, timeout):
    """Run fn with a hard wall-clock cap, even if DNS/connect stalls."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(fn).result(timeout=timeout)
    except BaseException:
        return None
    finally:
        pool.shutdown(wait=False)


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
        quote = _call_with_timeout(lambda: service.get_latest(force_refresh=force), 15)
        if quote is None:
            return jsonify({"success": False, "error": "資料來源回應逾時，請稍後再試"}), 502
        return jsonify({"success": True, "data": quote})

    @app.route("/api/history")
    def api_history():
        return jsonify({"success": True, "data": service.get_history()})

    @app.route("/api/dashboard")
    def api_dashboard():
        force = request.args.get("force") == "1"
        payload = {
            "success": True,
            "sheet": {"ok": False, "error": "來源逾時"},
            "live": {"error": "來源逾時"},
            "annual": annual_trend(),
            "recent": RECENT,
            "news": {"error": "來源逾時"},
        }

        def load_sheet():
            return sheet_service.summary(force=force)

        def load_live():
            return service.get_latest(force_refresh=force)

        def load_annual():
            return {
                "annual": annual_trend(fred_service.annual_with_current()),
                "recent": fred_service.recent(),
            }

        def load_news():
            return news_service.get_news(force=force)

        tasks = {
            "sheet": load_sheet,
            "live": load_live,
            "annual": load_annual,
            "news": load_news,
        }

        pool = ThreadPoolExecutor(max_workers=len(tasks))
        future_map = {pool.submit(fn): key for key, fn in tasks.items()}
        started = time.monotonic()
        pending = set(future_map)
        try:
            while pending:
                remaining = DASHBOARD_BUDGET_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    break
                done, pending = wait(pending, timeout=min(remaining, 10))
                for future in done:
                    key = future_map[future]
                    try:
                        data = future.result()
                    except BaseException:
                        data = None
                    if data is None:
                        continue
                    if key == "annual":
                        payload["annual"] = data.get("annual", payload["annual"])
                        payload["recent"] = data.get("recent", payload["recent"])
                    else:
                        payload[key] = data
        finally:
            pool.shutdown(wait=False)

        payload["drivers"] = DRIVERS

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
        data = _call_with_timeout(lambda: annual_trend(fred_service.annual_with_current()), 30)
        if data is None:
            data = _call_with_timeout(annual_trend, 5)
        return jsonify({"success": True, "data": data or annual_trend()})

    @app.route("/api/news")
    def api_news():
        data = _call_with_timeout(news_service.get_news, 18)
        if data is None:
            return jsonify({"success": False, "error": "來源逾時，請稍後再試"}), 502
        return jsonify({"success": True, "data": data})

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
        record = _call_with_timeout(service.capture_today, 20)
        if record is None:
            return jsonify({"success": False, "error": "抓取逾時，請稍後再試"}), 502
        return jsonify({"success": True, "data": record})

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