"""Display-only "Crowd euphoria" gauge: how excited the crowd is, from two free public sources.
  (a) Crypto Fear & Greed Index, alternative.me API (daily, 0-100, since 2018-02-01).
  (b) BTC perpetual-futures funding rate (what leveraged longs pay shorts), annualized:
      Deribit BTC-PERPETUAL (hourly 8h-rate, since 2019-04-30) is the main source; OKX BTC-USDT-SWAP (8-hourly, last ~3 months)
      is the backup for recent days; BitMEX XBTUSD (8-hourly, since 2016) is tried for the longer history but is blocked from
      some networks (it is from this build machine, and may be from GitHub's runners).
Gauge (0-100) = average of the 7-day average Fear & Greed and a 0-100 funding score of the 7-day average annualized funding.
Funding score: piecewise linear through (-10%, 0), (0%, 20), (10%, 45), (20%, 65), (40%, 85), (80%, 100); about 11% a year is
the exchanges' default when the market is balanced. Zones: calm < 25 <= normal < 55 <= excited < 75 <= euphoric.
These cut-offs are display conventions chosen on 2026-10-25, not fitted or calibrated.
NOT an input of the Cycle Heat Score or of any graded version (v1, v2, v3). Writes data/crowd.json. The page recomputes the same gauge live from Deribit's public funding history
(BTCModel.crowdLive in js/model.js), using fng.window and curve from this file. Failure-tolerant: each
source falls back to its cache; on total failure the previous data/crowd.json stays. Not financial advice."""
import json, os, sys, time, datetime as dt
import numpy as np, pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__)); CD = os.path.join(HERE, "pipeline", "cache")
OUT = os.path.join(HERE, "data", "crowd.json")
UA = {"User-Agent": "my-btc-cycle-model/1.0 (https://euthymia686.github.io/my-btc-cycle-model/; display-only crowd gauge)"}
OFF = os.environ.get("OFFLINE") == "1"
FUND_X = [-0.10, 0.0, 0.10, 0.20, 0.40, 0.80]; FUND_Y = [0, 20, 45, 65, 85, 100]
ZONES = [(75, "euphoric"), (55, "excited"), (25, "normal"), (-1, "calm")]
now = lambda: dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

def cache_rw(name, fn):
    """Run fn(cached) -> new data; on failure keep the cache. Returns (data or None, error or None)."""
    p = os.path.join(CD, name); old = json.load(open(p)) if os.path.exists(p) else None
    if OFF: return old, "OFFLINE=1, using cache"
    try:
        new = fn(old); tmp = p + ".tmp"; json.dump(new, open(tmp, "w"), separators=(",", ":")); os.replace(tmp, p); return new, None
    except Exception as e: return old, f"{type(e).__name__}: {str(e)[:160]}"

def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=40, **kw); r.raise_for_status(); return r.json()

def f_fng(old):
    d = get("https://api.alternative.me/fng/", params={"limit": 0, "format": "json"})["data"]
    s = {dt.datetime.fromtimestamp(int(x["timestamp"]), dt.timezone.utc).strftime("%Y-%m-%d"): int(x["value"]) for x in d}
    if len(s) < 1000: raise RuntimeError(f"only {len(s)} days")
    return {"source": "alternative.me Crypto Fear & Greed Index", "fetched_utc": now().isoformat(timespec="seconds") + "Z", "daily": dict(sorted(s.items()))}

def merge_daily(old, rows, src):   # rows: list of (day, 8h-rate); daily mean, newer fetch replaces those days
    by = {}
    for d, v in rows: by.setdefault(d, []).append(v)
    daily = dict((old or {}).get("daily", {})); daily.update({d: float(np.mean(v)) for d, v in by.items()})
    return {"source": src, "fetched_utc": now().isoformat(timespec="seconds") + "Z", "unit": "mean 8-hour funding rate per day", "daily": dict(sorted(daily.items()))}

def f_deribit(old):
    start = pd.Timestamp("2019-04-30") if not old or not old.get("daily") else pd.Timestamp(max(old["daily"])) - pd.Timedelta(days=2)
    end = pd.Timestamp(now()); rows = []; t = start
    while t < end:
        t2 = min(t + pd.Timedelta(hours=743), end)
        r = get("https://www.deribit.com/api/v2/public/get_funding_rate_history", params={"instrument_name": "BTC-PERPETUAL",
                "start_timestamp": int(t.timestamp() * 1000), "end_timestamp": int(t2.timestamp() * 1000)})["result"]
        rows += [(dt.datetime.fromtimestamp(x["timestamp"] / 1000, dt.timezone.utc).strftime("%Y-%m-%d"), float(x["interest_8h"])) for x in r]
        t = t2; time.sleep(0.15)
    if not rows: raise RuntimeError("no rows")
    return merge_daily(old, rows, "Deribit BTC-PERPETUAL funding (hourly interest_8h)")

def f_okx(old):
    rows, after = [], None
    for _ in range(6):   # up to ~3 months of 8-hourly rates
        p = {"instId": "BTC-USDT-SWAP", "limit": 100}; p.update({"after": after} if after else {})
        d = get("https://www.okx.com/api/v5/public/funding-rate-history", params=p)["data"]
        if not d: break
        rows += [(dt.datetime.fromtimestamp(int(x["fundingTime"]) / 1000, dt.timezone.utc).strftime("%Y-%m-%d"), float(x["realizedRate"] or x["fundingRate"])) for x in d]
        after = d[-1]["fundingTime"]; time.sleep(0.2)
    if not rows: raise RuntimeError("no rows")
    return merge_daily(old, rows, "OKX BTC-USDT-SWAP funding (8-hourly)")

def f_bitmex(old):
    start = "2016-05-14" if not old or not old.get("daily") else (pd.Timestamp(max(old["daily"])) - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    rows = []
    for _ in range(40):
        d = get("https://www.bitmex.com/api/v1/funding", params={"symbol": "XBTUSD", "count": 500, "startTime": start, "reverse": "false"})
        if not d: break
        rows += [(x["timestamp"][:10], float(x["fundingRate"])) for x in d]
        if len(d) < 500: break
        start = d[-1]["timestamp"]; time.sleep(1.1)
    if not rows: raise RuntimeError("no rows")
    return merge_daily(old, rows, "BitMEX XBTUSD funding (8-hourly)")

def zone(g): return None if g is None or not np.isfinite(g) else next(z for c, z in ZONES if g >= c)
def fund_score(a): return float(np.interp(a, FUND_X, FUND_Y))

def main():
    fng, e_fng = cache_rw("crowd_fng.json", f_fng)
    srcs = {}
    for k, name, fn in [("deribit", "crowd_deribit.json", f_deribit), ("okx", "crowd_okx.json", f_okx), ("bitmex", "crowd_bitmex.json", f_bitmex)]:
        d, e = cache_rw(name, fn); srcs[k] = {"data": d, "error": e}
    ser = lambda d: (pd.Series(d["daily"], dtype=float).rename(index=pd.Timestamp).sort_index() if d and d.get("daily") else pd.Series(dtype=float))
    # one daily funding series: Deribit, gaps filled by OKX, then BitMEX (BitMEX also supplies 2016-2019 when reachable)
    fund = ser(srcs["deribit"]["data"]); used = {"deribit": int(fund.notna().sum())}
    for k in ("okx", "bitmex"):
        s = ser(srcs[k]["data"]); add = s[~s.index.isin(fund.index)]; used[k] = int(len(add)); fund = pd.concat([fund, add]).sort_index()
    if fund.empty and not fng: print("crowd: no data at all, previous file kept"); return 0
    today = pd.Timestamp(now().date())
    idx = pd.date_range(min([x for x in [fund.index.min() if len(fund) else None, pd.Timestamp(min(fng["daily"])) if fng else None] if x is not None]), today, freq="D")
    fund = fund.reindex(idx); ann = fund * 3 * 365
    f7 = ann.rolling(7, min_periods=5).mean(); f30 = ann.rolling(30, min_periods=20).mean()
    g = ser(fng).reindex(idx) if fng else pd.Series(np.nan, index=idx); g7 = g.rolling(7, min_periods=5).mean()
    fs = f7.apply(lambda a: fund_score(a) if np.isfinite(a) else np.nan)
    gauge = pd.concat([g7, fs], axis=1).mean(axis=1, skipna=False)
    lv = lambda s: s.last_valid_index()
    r = lambda x, n=1: None if x is None or not np.isfinite(x) else round(float(x), n)
    gl, fl, ffl = lv(gauge), lv(g), lv(f7)
    if gl is None:   # one source missing: still show the other, gauge from what is there
        gauge = pd.concat([g7, fs], axis=1).mean(axis=1); gl = lv(gauge)
    out = {"display_only": True, "not_in_score": "Not part of the Cycle Heat Score or of any graded version (v1, v2, v3). Any future use in a score would be a new locked version.",
           "method": "gauge = mean(7-day avg Fear & Greed, funding score of the 7-day avg annualized funding rate); funding score piecewise linear through " +
                     ", ".join(f"({int(x*100)}%, {y})" for x, y in zip(FUND_X, FUND_Y)) + "; zones calm < 25 <= normal < 55 <= excited < 75 <= euphoric (display conventions, not calibrated)",
           "asof": gl.strftime("%Y-%m-%d") if gl is not None else None, "gauge": r(gauge[gl]) if gl is not None else None, "zone": zone(gauge[gl]) if gl is not None else None,
           "fng": {"asof": fl.strftime("%Y-%m-%d") if fl is not None else None, "value": r(g[fl], 0) if fl is not None else None, "avg7": r(g7[lv(g7)]) if lv(g7) is not None else None,
                   "source": "alternative.me Crypto Fear & Greed Index", "error": e_fng, "first": min(fng["daily"]) if fng else None,
                   "window": {d.strftime("%Y-%m-%d"): int(v) for d, v in g.iloc[-8:].items() if np.isfinite(v)}},   # raw daily values, so the page can recompute g7 for a live funding reading
           "funding": {"asof": ffl.strftime("%Y-%m-%d") if ffl is not None else None, "ann7": r(100 * f7[ffl], 1) if ffl is not None else None,
                       "ann30": r(100 * f30[lv(f30)], 1) if lv(f30) is not None else None, "score": r(fs[lv(fs)]) if lv(fs) is not None else None,
                       "unit": "percent a year (mean 8-hour rate x 3 x 365)", "days_used": used,
                       "sources": {k: {"source": (v["data"] or {}).get("source"), "fetched_utc": (v["data"] or {}).get("fetched_utc"), "error": v["error"],
                                       "first": min(v["data"]["daily"]) if v["data"] and v["data"].get("daily") else None,
                                       "last": max(v["data"]["daily"]) if v["data"] and v["data"].get("daily") else None} for k, v in srcs.items()}},
           "curve": {"funding_x": FUND_X, "funding_y": FUND_Y, "zones": [[c, z] for c, z in ZONES], "fng_min_days": 5, "funding_min_days": 5, "ann_factor": 3 * 365},   # the page's live recompute reads these (one source of truth)
           "t0": idx[0].strftime("%Y-%m-%d"), "gauge_daily": [r(x) for x in gauge.to_numpy()]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True); tmp = OUT + ".tmp"; json.dump(out, open(tmp, "w"), separators=(",", ":")); os.replace(tmp, OUT)
    print(f"crowd: asof {out['asof']} gauge {out['gauge']} ({out['zone']}) · F&G {out['fng']['value']} (7d {out['fng']['avg7']}) · funding 7d {out['funding']['ann7']}%/yr, 30d {out['funding']['ann30']}%/yr · days {used}"
          + "".join(f" · {k}: {v['error']}" for k, v in srcs.items() if v["error"]) + (f" · fng: {e_fng}" if e_fng else ""))
    return 0

if __name__ == "__main__": sys.exit(main())
