import csv
import io
import time

import requests

from . import config

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


class FredService:
    def __init__(self, ttl=config.FRED_CACHE_SECONDS):
        self._cache = {}
        self._cache_time = {}
        self._ttl = ttl

    def fetch(self, series):
        cached = self._cache.get(series)
        if cached is not None and (time.time() - self._cache_time.get(series, 0)) < self._ttl:
            return cached
        resp = requests.get(config.FRED_CSV_BASE.format(series=series), headers=UA, timeout=(3.05, 8))
        resp.raise_for_status()
        points = []
        reader = csv.reader(io.StringIO(resp.text))
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                value = float(row[1])
            except (ValueError, TypeError):
                continue
            points.append((row[0], value))
        points.sort(key=lambda p: p[0])
        self._cache[series] = points
        self._cache_time[series] = time.time()
        return points

    def annual(self):
        rows = []
        for date, price in self.fetch(config.FRED_SERIES_ANNUAL):
            year = date[:4]
            if rows and rows[-1]["year"] == year:
                continue
            rows.append({"year": year, "price": round(price)})
        return rows

    def monthly(self):
        return [
            {"date": date, "price": round(price)}
            for date, price in self.fetch(config.FRED_SERIES_MONTHLY)
        ]

    def annual_with_current(self):
        annual = self.annual()
        if not annual:
            return annual
        monthly = self.monthly()
        current = monthly[-1]["date"][:4] if monthly else None
        if not current:
            return annual
        values = [p["price"] for p in monthly if p["date"][:4] == current]
        if values and not any(a["year"] == current for a in annual):
            annual.append({"year": f"{current}*", "price": round(sum(values) / len(values))})
        return annual

    def recent(self, months=None):
        if months is None:
            months = config.FRED_RECENT_MONTHS
        pts = self.monthly()[-months:]
        return [
            {"date": p["date"], "label": p["date"][:7], "price": p["price"]}
            for p in pts
        ]