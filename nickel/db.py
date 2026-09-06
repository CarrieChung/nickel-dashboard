import datetime
import json
import os
import threading
import time

from . import config

_lock = threading.RLock()
_daily = {}
_logs = []
_dirty = False
_saver = None


def _save():
    try:
        with _lock:
            snapshot = {"daily": dict(_daily), "logs": list(_logs[-50:])}
        with open(config.STORE_PATH, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _saver_loop():
    global _dirty
    while True:
        time.sleep(3)
        if _dirty:
            _dirty = False
            _save()


def _load():
    try:
        if not os.path.exists(config.STORE_PATH):
            return
        with open(config.STORE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            _daily.update(data.get("daily") or {})
            _logs.extend(data.get("logs") or [])
    except Exception:
        pass


def init_db():
    global _saver
    with _lock:
        _load()
        if _saver is None:
            _saver = threading.Thread(target=_saver_loop, name="store-saver", daemon=True)
            _saver.start()


def get_daily_by_date(date_str):
    with _lock:
        return _daily.get(date_str)


def upsert_daily(record):
    global _dirty
    with _lock:
        _daily[record["date"]] = record
        _dirty = True


def list_daily():
    with _lock:
        return [record for _, record in sorted(_daily.items())]


def add_monitor_log(status, detail=""):
    global _dirty
    with _lock:
        _logs.append(
            {
                "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "status": status,
                "detail": detail,
            }
        )
        if len(_logs) > 50:
            del _logs[:-50]
        _dirty = True


def last_monitor_log():
    with _lock:
        return _logs[-1] if _logs else None