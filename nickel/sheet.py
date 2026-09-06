import re
import time
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import requests

from . import config

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def _parse_number(raw):
    if raw is None:
        return None
    try:
        return float(str(raw).replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


class SheetService:
    def __init__(self):
        self._cache = None
        self._cache_time = 0.0
        self._cache_ttl = 300

    def get_rows(self, force=False):
        if (
            not force
            and self._cache is not None
            and (time.time() - self._cache_time) < self._cache_ttl
        ):
            return self._cache
        url = f"{config.SHEET_PROXY}/{config.SHEET_ID}/{config.SHEET_TAB}"
        resp = requests.get(url, headers=UA, timeout=(3.05, 6))
        resp.raise_for_status()
        raw = resp.json()
        rows = [r for r in raw if r.get("date")]
        for r in rows:
            r["_price"] = _parse_number(r.get("price_usd_per_ton"))
            r["_change"] = _parse_number(r.get("change_pct"))
        rows.sort(key=lambda r: r["date"])
        self._cache = rows
        self._cache_time = time.time()
        return rows

    def summary(self, force=False):
        rows = self.get_rows(force=force)
        valid = [r for r in rows if r["_price"] is not None]
        if not valid:
            return {"ok": False, "rows": 0}
        today = valid[-1]
        prev = valid[-2] if len(valid) > 1 else None
        delta_pct = today["_change"]
        if delta_pct is None and prev and prev["_price"]:
            delta_pct = (today["_price"] - prev["_price"]) / prev["_price"] * 100
        prices = [r["_price"] for r in valid]
        return {
            "ok": True,
            "rows": len(valid),
            "today": {
                "date": today["date"],
                "price": today["_price"],
                "change_pct": delta_pct,
                "note": today.get("note", ""),
            },
            "range": {"min": min(prices), "max": max(prices)},
            "log": [
                {
                    "date": r["date"],
                    "label": r["date"][5:],
                    "price": r["_price"],
                    "change": r.get("_change"),
                }
                for r in valid
            ],
        }


def _news_sort_key(entry):
    try:
        return parsedate_to_datetime(entry["published"])
    except (TypeError, ValueError):
        return None


class NewsService:
    def __init__(self):
        self._cache = None
        self._cache_time = 0.0

    def get_news(self, force=False):
        if (
            not force
            and self._cache is not None
            and (time.time() - self._cache_time) < config.NEWS_CACHE_SECONDS
        ):
            return self._cache
        query = quote(config.NEWS_QUERY)
        url = (
            f"https://news.google.com/rss/search?q={query}"
            "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        )
        resp = requests.get(url, headers=UA, timeout=(3.05, 10))
        resp.raise_for_status()
        items = self._parse_rss(resp.text)
        self._cache = items
        self._cache_time = time.time()
        return items

    @staticmethod
    def _parse_rss(xml):
        entries = []
        blocks = re.findall(r"<item>(.*?)</item>", xml, re.S)
        for b in blocks:
            title = re.search(r"<title>(.*?)</title>", b, re.S)
            link = re.search(r"<link>(.*?)</link>", b, re.S)
            pub = re.search(r"<pubDate>(.*?)</pubDate>", b, re.S)
            source = re.search(r"<source[^>]*>(.*?)</source>", b, re.S)
            if not title:
                continue
            entries.append(
                {
                    "title": title.group(1).strip(),
                    "link": link.group(1).strip() if link else None,
                    "source": source.group(1).strip() if source else None,
                    "published": pub.group(1).strip() if pub else None,
                }
            )
        entries.sort(key=_news_sort_key, reverse=True)
        return entries[: config.NEWS_MAX]
