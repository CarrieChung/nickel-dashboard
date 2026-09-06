import datetime
import time

import requests

from . import config, db


class NickelService:
    def __init__(self, sheet_service=None, cache_ttl=config.CACHE_TTL_SECONDS):
        from .sheet import SheetService

        self._sheet = sheet_service or SheetService()
        self._latest_cache = None
        self._cache_time = 0.0
        self._cache_ttl = cache_ttl

    @staticmethod
    def _today_str():
        return datetime.date.today().isoformat()

    def fetch_latest(self):
        rows = self._sheet.get_rows()
        valid = [r for r in rows if r.get("_price") is not None]
        if not valid:
            raise ValueError("Google Sheet 中沒有有效的鎳價資料")

        today = valid[-1]
        return {
            "spot": today["_price"],
            "lme": today["_price"],
            "currency": "USD",
            "unit": "mt",
            "timestamp": today["date"],
        }

    def capture_today(self):
        today = self._today_str()
        existing = db.get_daily_by_date(today)
        if existing:
            return existing

        quote = self.fetch_latest()
        record = {
            "date": today,
            "spot": quote["spot"],
            "lme": quote["lme"],
            "currency": quote["currency"],
            "unit": quote["unit"],
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        db.upsert_daily(record)
        db.add_monitor_log("success", f"已記錄 {today} 鎳價: spot={record['spot']} lme={record['lme']}")
        self._latest_cache = quote
        self._cache_time = time.time()
        return record

    def get_latest(self, force_refresh=False):
        if (
            not force_refresh
            and self._latest_cache
            and (time.time() - self._cache_time) < self._cache_ttl
        ):
            return self._latest_cache
        quote = self.fetch_latest()
        self._latest_cache = quote
        self._cache_time = time.time()

        today = self._today_str()
        if not db.get_daily_by_date(today):
            record = {
                "date": today,
                "spot": quote["spot"],
                "lme": quote["lme"],
                "currency": quote["currency"],
                "unit": quote["unit"],
                "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
            }
            db.upsert_daily(record)
            db.add_monitor_log("success", f"已記錄 {today} 鎳價: spot={record['spot']} lme={record['lme']}")
        return quote

    def get_history(self):
        return db.list_daily()
