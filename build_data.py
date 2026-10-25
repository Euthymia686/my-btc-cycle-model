"""Build data/*.json from pipeline/ (+ a few public REST pulls).
Run daily (after cycle_signals/signals.py). Everything the browser needs to recompute the signals live is written here.
Usage: python build_data.py [--cycle-dir pipeline]"""
import json, os, sys, time, datetime as dt, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
CYC = sys.argv[sys.argv.index("--cycle-dir") + 1] if "--cycle-dir" in sys.argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline")
CYC = os.path.abspath(CYC); sys.path.insert(0, CYC); os.chdir(CYC)
import lib, backtest, charts, robust, v2_spec, health
OUT = os.path.join(HERE, "data"); os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "my-btc-cycle-model/1.0 (build_data)"}

def g(v, n=6):
    if v is None: return None
    v = float(v); return None if not np.isfinite(v) else float(f"{v:.{n}g}")
def dump(name, obj):
    p = os.path.join(OUT, name); tmp = p + ".tmp"
    with open(tmp, "w") as f: json.dump(obj, f, separators=(",", ":"), default=str)
    os.replace(tmp, p); return os.path.getsize(p)
def ts(d): return int(pd.Timestamp(d).timestamp())

def bitstamp_daily():
    """Daily OHLC from Bitstamp public REST (2011-08 onward), paged 1000 bars at a time. Falls back to the last file."""
    rows, start = {}, ts("2011-08-18")
    try:
        if os.environ.get("OFFLINE") == "1": raise RuntimeError("OFFLINE=1, keeping the last file")
        while True:
            r = requests.get("https://www.bitstamp.net/api/v2/ohlc/btcusd/", params={"step": 86400, "limit": 1000, "start": start}, headers=UA, timeout=30)
            r.raise_for_status(); o = r.json()["data"]["ohlc"]
            if not o: break
            for b in o: rows[int(b["timestamp"])] = [int(b["timestamp"]), g(b["open"]), g(b["high"]), g(b["low"]), g(b["close"])]
            last = int(o[-1]["timestamp"])
            if last <= start or len(o) < 1000: break
            start = last + 86400; time.sleep(0.4)
        return {"source": "Bitstamp public REST, daily UTC bars", "bars": [rows[k] for k in sorted(rows)]}, None
    except Exception as e:
        return None, str(e)

def main():
    status = {}
    cm = lib.coinmetrics(); tr = lib.google_trends()
    df, (a_exp, b_exp) = lib.build_signals(cm, tr); p = df["price"]; last = df.index.max()
    tops, bottoms = lib.find_tops_bottoms(p)
    cal, H, se, sf, nh = backtest.calibrate(df, None, tops, str((last + pd.Timedelta(days=2)).date()))
    top_days = cal["top_days"]; mu = float(np.mean(top_days)); sd = max(60.0, float(np.std(top_days)))
    hot = cal["score_hot"]["equal"]
    # ---- history (CoinMetrics daily reference price + score history with today's calibration + walk-forward score)
    wf = pd.read_csv(os.path.join(CYC, "out", "score_history.csv"), index_col=0, parse_dates=True)["score_eq"].reindex(df.index)
    hist = {"source": "CoinMetrics Community API (daily reference price, UTC)", "start": str(df.index[0].date()),
            "t": [ts(d) for d in df.index], "close": [g(v) for v in p.values],
            "score": [g(v, 4) for v in se.reindex(df.index).values], "score_wf": [g(v, 4) for v in wf.values]}
    sc2, F2, H2 = v2_spec.score(df)
    hist["score_v2"] = [g(v, 4) for v in sc2.reindex(df.index).values]
    # ---- running sums so the browser can add today's live price exactly
    d = (df.index - lib.GENESIS).days.values.astype(float); x, y = np.log10(d), np.log10(p.values)
    mc = df["mcap"].dropna()
    rcap = float(df["mcap"].iloc[-1] / df["mvrv"].iloc[-1])
    a_f, b_f, res, q = charts.fits(p)
    dist = {}
    for s in ["mayer", "p200w", "trend_mult", "mvrv_z", "pi_ratio"]:
        v = np.sort(df[s].dropna().values); dist[s] = [g(z, 5) for z in v]
    fixed = {}
    for s in ["activity", "trends"]:
        sv = df[s].dropna(); hv = H[s].dropna()
        fixed[s] = {"value": g(sv.iloc[-1], 4), "heat": g(hv.iloc[-1], 4), "asof": str(sv.index[-1].date())}
    if tr and tr.get("monthly"):
        mk = sorted(tr["monthly"]); fixed["trends"]["month"] = mk[-2] if len(mk) > 1 else mk[-1]
        fixed["trends"]["note"] = "Google Trends monthly index (0-100 relative); month M is used from the 1st of M+1"
    fixed["activity"]["note"] = "CoinMetrics AdrActCnt, 30-day avg / 365-day avg; published daily with ~1 day lag"
    model = {
        "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "last_daily": str(last.date()),
        "genesis": "2009-01-03", "halvings": [str(h.date()) for h in lib.HALVINGS], "next_halving_block": lib.NEXT_HALVING_BLOCK,
        "signals": lib.SIGNALS, "labels": lib.LABELS, "short": lib.SHORT,
        "calibration": {"top_days": top_days, "timing_mu": mu, "timing_sd": sd, "signal_hot": cal["signal_hot"],
                        "score_hot": hot, "score_warm": hot - 15, "prior_tops": cal["prior_tops"]},
        "trend_expanding_sums": {"n": int(len(x)), "sx": float(x.sum()), "sy": float(y.sum()), "sxx": float((x * x).sum()), "sxy": float((x * y).sum())},
        "trend_full_fit": {"a": a_f, "b": b_f, "q_floor": q["floor"], "q_mid": q["mid"], "q_ceil": q["ceil"], "fit_range": [str(p.index[0].date()), str(last.date())]},
        "mcap_moments": {"n": int(len(mc)), "mean": float(mc.mean()), "m2": float(((mc - mc.mean()) ** 2).sum())},
        "realized_cap": rcap, "realized_cap_asof": str(last.date()), "supply": float(df["supply"].iloc[-1]),
        "fixed": fixed, "distributions": dist,
        "tops": {k: str(v.date()) for k, v in tops.items()}, "bottoms": {k: str(v.date()) for k, v in bottoms.items()},
    }
    # ---- v2 (pre-registered): sliding-window distributions so the browser can compute v2 live
    P2 = v2_spec.PARAMS; W = P2["window_days"]; rec = health.freeze_record(); integ = health.integrity(rec)
    v2d = {}
    for s in ["mayer", "p200w", "trend_mult", "mvrv_z", "pi_ratio"]:
        v2d[s] = [g(z, 5) for z in np.sort(df[s].dropna().values[-W:])]
    model["v2"] = {"params": P2, "frozen_on": v2_spec.FROZEN_ON, "integrity": integ, "distributions": v2d,
                   "fixed_heat": {"activity": g(H2["activity"].dropna().iloc[-1], 4), "trends": g(H2["trends"].dropna().iloc[-1], 4)},
                   "today_daily": g(sc2.dropna().iloc[-1], 4)}
    # ---- robust fan (decay-weighted forecast-error fan, refit daily) + frozen fan + model health
    hl, _, _ = health.build(df, closes=p, write=True)
    P = robust.fan_params(p)
    fz = None
    if rec:
        ff = json.load(open(os.path.join(CYC, "frozen", rec["fan_file"])))
        idx = list(range(0, len(ff["dates"]), 7))
        fz = {"frozen_on": rec["frozen_on"], "t": [ts(ff["dates"][i]) for i in idx], **{k: [ff[k][i] for i in idx] for k in ("q5", "q25", "q50", "q75", "q95")},
              "today": {"t": [ts(x) for x in ff["dates"][:7]], **{k: ff[k][:7] for k in ("q5", "q25", "q50", "q75", "q95")}}}
    fan2 = {"params": P, "frozen": fz, "end": str(lib.HORIZON.date()),
            "next_halving_est": str((pd.Timestamp("2028-04-15")).date())}
    health_out = {k: hl[k] for k in ("integrity", "v2_today", "fan_backtest", "forward", "trend_drift", "fan_today")}
    # ---- fan: weekly points, 2020 -> 2029
    dates = pd.date_range("2020-01-05", "2029-01-07", freq="7D"); t = charts.trend_at(a_f, b_f, dates)
    band = charts.cycle_band(p, a_f, b_f, res, pd.date_range("2022-05-01", "2029-01-07", freq="D")).reindex(dates)
    fan = {"t": [ts(z) for z in dates], "floor": [g(v) for v in t * 10 ** q["floor"]], "mid": [g(v) for v in t * 10 ** q["mid"]],
           "ceil": [g(v) for v in t * 10 ** q["ceil"]], "band_lo": [g(v) for v in band.lo.values], "band_hi": [g(v) for v in band.hi.values],
           "band_md": [g(v) for v in band.md.values], "end": str(lib.HORIZON.date())}
    # ---- MSTR context (price, holdings, mNAV inputs)
    stg = lib.strategy_kpis() or {}; sh = (lib.shares_outstanding() or {}).get("shares")
    ym = lib.yahoo_mstr()
    mstr = {"price": stg.get("mstr_close") or (ym["close"][-1] if ym else None), "price_time": stg.get("mstr_time"),
            "price_source": "Strategy.com KPI feed (last close)", "shares": sh, "shares_source": "Yahoo impliedSharesOutstanding",
            "btc_holdings": stg.get("holdings"), "holdings_source": "Strategy.com / SEC 8-K", "mnav_strategy_ev_based": stg.get("mnav_strategy"),
            "edgar_latest_8k": lib.edgar_latest_8k()}
    ohlc, err = bitstamp_daily()
    status["bitstamp_daily"] = {"ok": ohlc is not None, "error": err}
    if ohlc is None and os.path.exists(os.path.join(OUT, "ohlc_daily.json")): status["bitstamp_daily"]["from"] = "previous file"
    status.update({k: v for k, v in lib.STATUS.items()})
    sizes = {"history.json": dump("history.json", hist), "model.json": dump("model.json", model), "fan.json": dump("fan.json", fan),
             "mstr.json": dump("mstr.json", mstr), "fan2.json": dump("fan2.json", fan2), "health.json": dump("health.json", health_out)}
    if ohlc: sizes["ohlc_daily.json"] = dump("ohlc_daily.json", ohlc)
    sizes["meta.json"] = dump("meta.json", {"built_utc": model["built_utc"], "last_daily": model["last_daily"], "sources": status})
    for k, v in sizes.items(): print(f"  data/{k:<16} {v/1024:8.1f} KB")
    print("  calibration: hot", hot, "| timing mu/sd", round(mu), round(sd), "| last daily", model["last_daily"])

if __name__ == "__main__":
    main()
