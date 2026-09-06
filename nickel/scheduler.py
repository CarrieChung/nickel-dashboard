import datetime
import threading
import time

from . import config, db

CHECK_INTERVAL_SECONDS = 3600


class DailyMonitor:
    def __init__(self, service):
        self._service = service
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(
            target=self._run, name="daily-monitor", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _is_due(self):
        today = datetime.date.today().isoformat()
        return db.get_daily_by_date(today) is None

    def _run(self):
        while not self._stop.is_set():
            try:
                if self._is_due():
                    self._service.capture_today()
            except Exception as exc:
                db.add_monitor_log("error", f"自動監控失敗: {exc}")
            self._stop.wait(CHECK_INTERVAL_SECONDS)
