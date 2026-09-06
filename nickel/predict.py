import datetime
import math


def _linreg(xs, ys):
    n = len(xs)
    if n == 0:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    slope = sxy / sxx
    intercept = my - slope * mx
    return slope, intercept


def forecast(history, days=30):
    points = [h for h in history if h.get("spot") is not None]
    if len(points) < 2:
        return None

    x0 = datetime.date.fromisoformat(points[0]["date"])
    xs = [(datetime.date.fromisoformat(h["date"]) - x0).days for h in points]
    ys = [h["spot"] for h in points]

    result = _linreg(xs, ys)
    if result is None:
        return None
    slope, intercept = result

    preds = []
    for i in range(1, days + 1):
        x = xs[-1] + i
        day = x0 + datetime.timedelta(days=x)
        y = slope * x + intercept
        preds.append({"date": day.isoformat(), "price": round(max(y, 0), 2)})

    diffs = [ys[i] - ys[i - 1] for i in range(1, len(ys))]
    volatility = (sum(d * d for d in diffs) / len(diffs)) ** 0.5 if diffs else 0.0

    last_price = ys[-1]
    last_x = xs[-1]
    trend_next = slope * (last_x + 30) + intercept
    pct_change_30d = ((trend_next - last_price) / last_price * 100) if last_price else 0.0

    return {
        "slope": round(slope, 2),
        "intercept": round(intercept, 2),
        "last_price": round(last_price, 2),
        "volatility": round(volatility, 2),
        "pct_change_30d": round(pct_change_30d, 2),
        "points": len(points),
        "forecast": preds,
    }
