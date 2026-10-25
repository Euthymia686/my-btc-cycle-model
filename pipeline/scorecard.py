"""Public forward scorecard: v2 fan vs v3 fan, scored only on data after the freeze. Rules: frozen/v3/FREEZE.md.

Each run (daily, after build_data.py):
  1. For the latest daily close (CoinMetrics), if it has no row yet, append one row per version (v2, v3) to
     data/scorecard.csv with the close, the scores and the predicted 5/25/50/75/95% levels 30, 90 and 365 days ahead.
     Idempotent: a close date that already has rows is never written again, so re-runs on the same data add nothing.
  2. For every earlier row whose target date now has a close, fill in the result: actual close, inside the 50% band,
     inside the 90% band, log score. Prediction columns of existing rows are never changed.
  3. Write data/scorecard.json, the summary shown on the site.
v2 = robust.fan_params on all data up to that close (the frozen code). v3 = the same fan with the 90% and 50% half-widths
multiplied by the frozen scales s90 / s50 (frozen/v3/v3_spec.md section B), median unchanged. base = the plain benchmark
(power-law trend with a constant-width lognormal band, scorestats.baseline). Statistical tests: scorestats.py."""
import csv, json, os, math, datetime as dt
import numpy as np, pandas as pd, lib, robust, scorestats as ST

ROOT = os.path.abspath(os.path.join(lib.HERE, ".."))
CSV = os.path.join(ROOT, "data", "scorecard.csv"); SUMMARY = os.path.join(ROOT, "data", "scorecard.json")
FZ3 = os.path.join(lib.HERE, "frozen", "v3")
START = pd.Timestamp("2026-10-24")      # last close known at the freeze (2026-10-25); earlier closes are never added
HORIZONS = (30, 90, 365); QK = ("q5", "q25", "q50", "q75", "q95"); VERSIONS = ("v2", "v3", "base")
COMPARE = (("v2", "base"), ("v3", "base"), ("v3", "v2"))   # skill tests: first minus second
S90, S50 = 0.712, 0.660                 # frozen v3 fan scales (frozen/v3/v3_spec.md, "Frozen parameters")
RES = ("actual", "in50", "in90", "log_score")
COLS = ["close_date", "run_utc", "version", "btc_close", "heat_score", "heat_score_v2"] + \
       [f"h{h}_{k}" for h in HORIZONS for k in ("target",) + QK + RES]

def v3_scale(q):
    """q: dict of prices q5..q95 (v2). Returns the v3 version (log10 space, median unchanged, 25-75 kept inside 5-95)."""
    L = {k: math.log10(v) for k, v in q.items()}; m = L["q50"]
    o = {"q5": m - (m - L["q5"]) * S90, "q95": m + (L["q95"] - m) * S90,
         "q25": m - min((m - L["q25"]) * S50, (m - L["q5"]) * S90), "q75": m + min((L["q75"] - m) * S50, (L["q95"] - m) * S90), "q50": m}
    return {k: 10 ** v for k, v in o.items()}

def log_score(q, x):
    """Natural log of the predictive density at ln(x), per unit of ln(price). The density is piecewise uniform between the
    five quantiles (20/25/25/20% of the mass) with exponential tails holding 5% each, continuous at q5 and q95."""
    l = [math.log(q[k]) for k in QK]; y = math.log(x); mass = (0.20, 0.25, 0.25, 0.20)
    if y < l[0]:
        lam = mass[0] / (0.05 * (l[1] - l[0])); return math.log(0.05 * lam) - lam * (l[0] - y)
    if y > l[4]:
        lam = mass[3] / (0.05 * (l[4] - l[3])); return math.log(0.05 * lam) - lam * (y - l[4])
    for i in range(4):
        if y <= l[i + 1]: return math.log(mass[i] / (l[i + 1] - l[i]))

def predictions(p, d):
    P = robust.fan_params(p.loc[:d]); F = robust.fan_at(P, [d + pd.Timedelta(days=h) for h in HORIZONS])
    v2 = {h: {k: float(F.iloc[i][k]) for k in QK} for i, h in enumerate(HORIZONS)}
    return {"v2": v2, "v3": {h: v3_scale(v2[h]) for h in HORIZONS}, "base": ST.baseline(p, d, HORIZONS)}

def score_one(version, q, x):
    return ST.baseline_log_score(q, x) if version == "base" else log_score(q, x)

def scores_for(d):
    h = json.load(open(os.path.join(ROOT, "data", "history.json")))
    ix = {pd.Timestamp(t, unit="s").normalize(): i for i, t in enumerate(h["t"])}; i = ix.get(d)
    g = lambda k: None if i is None or h[k][i] is None else round(float(h[k][i]), 1)
    return g("score"), g("score_v2")

def read():
    if not os.path.exists(CSV): return []
    with open(CSV, newline="") as f: rows = list(csv.DictReader(f))
    return rows

def write(rows):
    tmp = CSV + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    os.replace(tmp, CSV)

def main(p=None, now=None):
    p = (lib.coinmetrics()["price"] if p is None else p).dropna(); p = p[p > 0]
    rows = read(); PRED = [c for c in COLS if not any(c.endswith("_" + x) for x in RES)]; before = [{k: r[k] for k in PRED} for r in rows]
    last = p.index[-1]; have = {(r["close_date"], r["version"]) for r in rows}; added = 0
    missing = [v for v in VERSIONS if (str(last.date()), v) not in have]
    if last >= START and missing:      # per version, so a version added later starts on the current close only
        pr = predictions(p, last); hs, hs2 = scores_for(last)
        run = (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds")
        for v in missing:
            r = {c: "" for c in COLS}
            r.update({"close_date": str(last.date()), "run_utc": run, "version": v, "btc_close": f"{p[last]:.2f}",
                      "heat_score": "" if hs is None else f"{hs:.1f}", "heat_score_v2": "" if hs2 is None else f"{hs2:.1f}"})
            for h in HORIZONS:
                r[f"h{h}_target"] = str((last + pd.Timedelta(days=h)).date())
                for k in QK: r[f"h{h}_{k}"] = f"{pr[v][h][k]:.0f}"
            rows.append(r); added += 1
    scored = 0
    for r in rows:                       # fill results for matured horizons (only empty result cells are written)
        for h in HORIZONS:
            if r[f"h{h}_actual"]: continue
            t = pd.Timestamp(r[f"h{h}_target"])
            if t not in p.index: continue
            x = float(p[t]); q = {k: float(r[f"h{h}_{k}"]) for k in QK}
            r[f"h{h}_actual"] = f"{x:.2f}"; r[f"h{h}_in50"] = str(int(q["q25"] <= x <= q["q75"]))
            r[f"h{h}_in90"] = str(int(q["q5"] <= x <= q["q95"])); r[f"h{h}_log_score"] = f"{score_one(r['version'], q, x):.4f}"; scored += 1
    after = [{k: r[k] for k in PRED} for r in rows[:len(before)]]
    assert after == before, "refusing to change prediction columns of existing rows"
    if added or scored or not os.path.exists(CSV): write(rows)
    summary(rows, last)
    print(f"scorecard: data through {last.date()}, rows +{added}, results +{scored}, total {len(rows)}")

def summary(rows, last):
    out = {"updated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "data_through": str(last.date()),
           "live_since": "2026-10-25", "targets": {"in50": 0.5, "in90": 0.9}, "horizons": list(HORIZONS), "versions": {}}
    pending = [r[f"h{h}_target"] for r in rows for h in HORIZONS if not r[f"h{h}_actual"]]
    out["next_result"] = str((pd.Timestamp(min(pending)) + pd.Timedelta(days=1)).date()) if pending else None
    out["next_result_horizon"] = None
    if pending:
        t = min(pending); out["next_result_horizon"] = min(h for r in rows for h in HORIZONS if r[f"h{h}_target"] == t and not r[f"h{h}_actual"])
    for v in VERSIONS:
        R = [r for r in rows if r["version"] == v]; o = {"forecast_days": len(R), "by_horizon": {}}
        allm = []
        for h in HORIZONS:
            m = [r for r in R if r[f"h{h}_actual"]]; allm += [(h, r) for r in m]
            o["by_horizon"][str(h)] = {"matured": len(m), **({} if not m else {
                "in50": round(sum(int(r[f"h{h}_in50"]) for r in m) / len(m), 3), "in90": round(sum(int(r[f"h{h}_in90"]) for r in m) / len(m), 3),
                "log_score": round(sum(float(r[f"h{h}_log_score"]) for r in m) / len(m), 3)})}
        o["all"] = {"matured": len(allm), **({} if not allm else {
            "in50": round(sum(int(r[f"h{h}_in50"]) for h, r in allm) / len(allm), 3), "in90": round(sum(int(r[f"h{h}_in90"]) for h, r in allm) / len(allm), 3),
            "log_score": round(sum(float(r[f"h{h}_log_score"]) for h, r in allm) / len(allm), 3)})}
        if R:
            L = R[-1]; o["latest"] = {"close_date": L["close_date"], "btc_close": float(L["btc_close"]),
                                      **{str(h): {"target": L[f"h{h}_target"], **{k: float(L[f"h{h}_{k}"]) for k in QK}} for h in HORIZONS}}
        out["versions"][v] = o
    try:
        hb = json.load(open(os.path.join(ROOT, "data", "health.json")))["fan_backtest"]["summary"]["all"]
        out["backtest_v2_all"] = {"in90": hb["in90"], "in50": hb["in50"], "days": hb["days"], "freezes": "every 1 Jan and 1 Jul, 2015-2025"}
    except Exception: out["backtest_v2_all"] = None
    b3 = json.load(open(os.path.join(FZ3, "fan_backtest_v3.json")))
    out["backtest_2017on"] = {"freezes": "every 1 Jan and 1 Jul, 2017-2025", "days": b3["pooled_2017on"]["days"],
                              "v2": {"in90": b3["pooled_2017on"]["in90_raw"], "in50": b3["pooled_2017on"]["in50_raw"]},
                              "v3": {"in90": b3["pooled_2017on"]["in90_cal"], "in50": b3["pooled_2017on"]["in50_cal"]},
                              "first_year": {"v2": {"in90": b3["by_horizon"]["0-1y"]["in90_raw"], "in50": b3["by_horizon"]["0-1y"]["in50_raw"]},
                                             "v3": {"in90": b3["by_horizon"]["0-1y"]["in90_cal"], "in50": b3["by_horizon"]["0-1y"]["in50_cal"]}}}
    out["promotion_check_earliest"] = "2027-10-25"
    out["tests_live"] = tests(rows)
    bt = os.path.join(ROOT, "data", "scorecard_backtest.json")
    out["tests_backtest"] = json.load(open(bt)) if os.path.exists(bt) else None
    tmp = SUMMARY + ".tmp"
    with open(tmp, "w") as f: json.dump(out, f, indent=1)
    os.replace(tmp, SUMMARY)

def tests(rows, lag_days=True):
    """Coverage (exact binomial, non-overlapping predictions) and skill (Diebold-Mariano) per horizon.
    Rows: dicts with close_date, version and h{h}_* fields (matured when h{h}_actual is set). Daily origins: lag = h - 1."""
    out = {"min_eff": ST.MIN_EFF, "coverage": {}, "skill": {}}
    by = {v: sorted([r for r in rows if r["version"] == v], key=lambda r: r["close_date"]) for v in VERSIONS}
    start = min((r["close_date"] for r in rows), default=str(START.date()))
    for h in HORIZONS:
        c = out["coverage"][str(h)] = {"expected": ST.expected_date(start, h)}
        for v in VERSIONS:
            R = by[v]; pick = set(ST.nonoverlap([pd.Timestamp(r["close_date"]) for r in R], h))
            M = [r for r in R if pd.Timestamp(r["close_date"]) in pick and r[f"h{h}_actual"]]; n = len(M); o = {"eff_n": n}
            for b, tgt in (("in50", 0.5), ("in90", 0.9)):
                k = sum(int(r[f"h{h}_{b}"]) for r in M)
                o[b] = {"hits": k, "rate": None if not n else k / n, "p": ST.binom(k, n, tgt) if n >= ST.MIN_EFF else None}
            c[v] = o
        s = out["skill"][str(h)] = {"expected": ST.expected_date(start, h)}
        for a, b in COMPARE:
            A = {r["close_date"]: float(r[f"h{h}_log_score"]) for r in by[a] if r[f"h{h}_actual"]}
            B = {r["close_date"]: float(r[f"h{h}_log_score"]) for r in by[b] if r[f"h{h}_actual"]}
            ds = sorted(set(A) & set(B)); eff = len(ST.nonoverlap([pd.Timestamp(x) for x in ds], h))
            o = {"n": len(ds), "eff_n": eff}
            if eff >= ST.MIN_EFF: o.update(ST.dm([A[x] - B[x] for x in ds], h - 1))
            elif ds: o["mean_diff"] = float(np.mean([A[x] - B[x] for x in ds]))
            s[f"{a}_vs_{b}"] = o
    return out

if __name__ == "__main__": main()
