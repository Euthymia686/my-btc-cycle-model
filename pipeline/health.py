"""Model health: v2 score + spec-hash check, frozen-fan forward coverage, historical fan coverage backtest, trend drift.
Writes out/health.json; signals.py calls today_fields() for journal.csv."""
import hashlib, json, os
import numpy as np, pandas as pd, lib, robust, v2_spec
FZ = os.path.join(lib.HERE, "frozen")
def sha(path): return hashlib.sha256(open(path, "rb").read()).hexdigest()

def freeze_record():
    p = os.path.join(FZ, "v2_freeze.json")
    return json.load(open(p)) if os.path.exists(p) else None

def integrity(rec):
    if not rec: return {"frozen": False}
    fan_path = os.path.join(FZ, rec["fan_file"])
    return {"frozen": True, "frozen_on": rec["frozen_on"],
            "v2_spec_ok": sha(os.path.join(lib.HERE, "v2_spec.py")) == rec["v2_spec_sha256"],
            "robust_ok": sha(os.path.join(lib.HERE, "robust.py")) == rec["robust_sha256"],
            "fan_ok": os.path.exists(fan_path) and sha(fan_path) == rec["fan_sha256"], "v2_spec_sha256": rec["v2_spec_sha256"]}

def frozen_fan(rec):
    f = json.load(open(os.path.join(FZ, rec["fan_file"])))
    return pd.DataFrame({k: f[k] for k in ("q5", "q25", "q50", "q75", "q95")}, index=pd.to_datetime(f["dates"]))

def forward(price, rec):
    F = frozen_fan(rec); after = price.loc[price.index > pd.Timestamp(rec["frozen_on"])]
    c = robust.coverage(after, F); c["since"] = rec["frozen_on"]
    if c["days"]:
        d = after.index[-1]; v = after.iloc[-1]; q = F.loc[d]
        c["last"] = {"date": str(d.date()), "close": float(v), "in90": bool(q.q5 <= v <= q.q95), "in50": bool(q.q25 <= v <= q.q75),
                     "position_pct": float(np.interp(np.log(v), np.log(q.values), [5, 25, 50, 75, 95], left=0, right=100))}
    return c

def trend_drift(price):
    """How much the trend's Dec-2028 value moved as data arrived (stock-to-flow's failure mode was a target that never moved)."""
    d, x, y, a, b = robust.causal_fit(price); xe = np.log10((lib.HORIZON - lib.GENESIS).days); out = []
    for back in (0, 365, 730, 1461, 2922):
        i = len(y) - 1 - back
        if i > 365: out.append({"fit_date": str(price.index[i].date()), "slope_b": round(float(b[i]), 3), "trend_at_horizon": round(float(10 ** (a[i] + b[i] * xe)), 0)})
    return out

def build(df=None, closes=None, write=True):
    """df: signal frame (may include today's provisional live row, used for v2 today).
    closes: finalized daily closes only (CoinMetrics), used for fan coverage and trend drift."""
    if df is None:
        df, _ = lib.build_signals(lib.coinmetrics(), lib.google_trends())
    p = (closes if closes is not None else lib.coinmetrics()["price"]).dropna(); rec = freeze_record(); integ = integrity(rec)
    sc, F, H = v2_spec.score(df); d = df.index.max()
    v2 = {"value": None if np.isnan(sc.get(d, np.nan)) else round(float(sc[d]), 1), "zone": v2_spec.zone(sc.get(d, np.nan)),
          "families": {k: (None if np.isnan(v) else round(float(v), 1)) for k, v in F.loc[d].items()}, "date": str(d.date())}
    bt = robust.coverage_backtest(p); P = robust.fan_params(p)
    out = {"integrity": integ, "v2_today": v2, "fan_backtest": bt, "forward": forward(p, rec) if rec else None,
           "trend_drift": trend_drift(p), "fan_today": {"asof": P["asof"], "at_horizon": {k: round(float(v), 0) for k, v in robust.fan_at(P, [lib.HORIZON]).iloc[0].items()}}}
    if write:
        os.makedirs(os.path.join(lib.HERE, "out"), exist_ok=True)
        with open(os.path.join(lib.HERE, "out", "health.json"), "w") as f: json.dump(out, f, indent=1, default=str)
    return out, sc, F

def today_fields(h):
    fw = h.get("forward") or {}; fz = h["integrity"]; s = h["fan_backtest"]["summary"]["all"]; last = fw.get("last") or {}
    return {"score_v2": h["v2_today"]["value"], "score_v2_zone": h["v2_today"]["zone"],
            **{f"v2_{k}": v for k, v in h["v2_today"]["families"].items()},
            "v2_spec_ok": fz.get("v2_spec_ok"), "fan_frozen_ok": fz.get("fan_ok"),
            "fan_fwd_days": fw.get("days", 0), "fan_fwd_in90": None if not fw.get("days") else round(fw["in90"], 3),
            "fan_fwd_in50": None if not fw.get("days") else round(fw["in50"], 3),
            "fan_last_in90": last.get("in90"), "fan_last_in50": last.get("in50"), "fan_last_pos_pct": None if not last else round(last["position_pct"], 1),
            "fan_bt_in90": s["in90"], "fan_bt_in50": s["in50"],
            "fan_h_q5": h["fan_today"]["at_horizon"]["q5"], "fan_h_q50": h["fan_today"]["at_horizon"]["q50"], "fan_h_q95": h["fan_today"]["at_horizon"]["q95"]}

if __name__ == "__main__":
    h, _, _ = build(); print(json.dumps({k: h[k] for k in ("integrity", "v2_today", "forward", "trend_drift", "fan_today")}, indent=1, default=str))
    print(json.dumps(h["fan_backtest"]["summary"]))
