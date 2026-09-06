from . import static_data


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


def annual_trend(annual=None):
    if not annual:
        annual = static_data.ANNUAL
    xs = list(range(len(annual)))
    ys = [a["price"] for a in annual]
    result = _linreg(xs, ys)
    if result is None:
        return None
    slope, intercept = result

    start_year = int(str(annual[0]["year"]).strip("*"))
    labels = [a["year"] for a in annual] + [f"{start_year + len(annual)}*", f"{start_year + len(annual) + 1}*"]
    actual_ys = [a["price"] for a in annual]
    trend_ys = []
    for i in range(len(labels)):
        trend_ys.append(round(max(intercept + slope * i, 0)))

    next_year = round(intercept + slope * len(xs))
    last_year = ys[-1]
    pct = (next_year - last_year) / last_year * 100 if last_year else 0
    return {
        "labels": labels,
        "actual": actual_ys,
        "trend": trend_ys,
        "slope": round(slope, 1),
        "next_year_projection": next_year,
        "pct_change": round(pct, 1),
    }
