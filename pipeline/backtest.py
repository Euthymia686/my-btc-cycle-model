"""Walk-forward backtest of the Cycle Heat Score. Writes out/backtest.json, out/backtest.md, out/score_history.csv."""
import json, os, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, lib

FOLDS = [("2013", "2013-01-01", "2016-12-31"), ("2017", "2017-01-01", "2020-12-31"),
         ("2021", "2021-01-01", "2024-12-31"), ("2025", "2025-01-01", None)]
TOPWIN = (-30, 7)            # window around a top used for calibration "peak heat"
THRESH = [70, 80, 90]

def episodes(mask, gap=14, minlen=3):
    idx = mask[mask].index; eps = []
    for d in idx:
        if eps and (d - eps[-1][1]).days <= gap: eps[-1][1] = d
        else: eps.append([d, d])
    return [(a, b) for a, b in eps if (b - a).days + 1 >= minlen]

def calibrate(df, H_eq_unused, tops, cutoff):
    """Everything here uses only data strictly before `cutoff`."""
    cut = pd.Timestamp(cutoff)
    prior = {k: t for k, t in tops.items() if t + pd.Timedelta(days=TOPWIN[1]) < cut}
    top_days = [(t - lib.last_halving(t)).days for t in prior.values() if lib.last_halving(t) is not None]
    H = lib.heats(df, top_days)
    Hc = H[H.index < cut]
    peak = {}; weights = {}
    for s in lib.SIGNALS:
        vals = []
        for k, t in prior.items():
            w = Hc[s].loc[t + pd.Timedelta(days=TOPWIN[0]): t + pd.Timedelta(days=TOPWIN[1])]
            if s == "cycle_day":     # leave-one-out so timing is not graded on the top it was fitted to
                others = [(tt - lib.last_halving(tt)).days for kk, tt in prior.items() if kk != k and lib.last_halving(tt) is not None]
                if lib.last_halving(t) is None or not others: continue
                w = lib.cycle_heat(df["days_since_halving"], others).loc[w.index]
            if w.notna().any(): vals.append(float(w.max()))
        peak[s] = vals
        if vals:
            disc = np.mean(vals) - float(Hc[s].median())
            weights[s] = max(disc, 0.0)
    eq = {s: 1.0 for s in lib.SIGNALS if peak[s]}
    tot = sum(weights.values()) or 1
    fitted = {s: v / tot for s, v in weights.items() if v > 0}
    sc_eq = lib.score_from(H, eq, list(eq)); sc_fit = lib.score_from(H, fitted, list(fitted))
    hot = {}
    for name, sc in [("equal", sc_eq), ("fitted", sc_fit)]:
        pk = [float(sc.loc[t + pd.Timedelta(days=TOPWIN[0]): t + pd.Timedelta(days=TOPWIN[1])].max()) for t in prior.values()]
        pk = [x for x in pk if not np.isnan(x)]
        hot[name] = float(np.floor(min(pk))) if pk else None
    sig_hot = {s: float(np.clip(min(v), 70, 99)) for s, v in peak.items() if v}
    if sig_hot:
        nhot = sum((H[s] >= v).astype(float) for s, v in sig_hot.items())
        nhot[H[list(sig_hot)].notna().sum(1) < 3] = np.nan
    else:
        nhot = pd.Series(np.nan, index=H.index)
    return dict(cutoff=cutoff, prior_tops=[str(t.date()) for t in prior.values()], top_days=top_days,
                eq_signals=list(eq), fitted_weights=fitted, score_hot=hot, signal_hot=sig_hot), H, sc_eq, sc_fit, nhot

def evaluate(sc, p, top, bottom, start, end, hot):
    s = sc.loc[start:end]; out = {"top": str(top.date()), "top_price": round(float(p[top]))}
    out["score_at_top"] = round(float(s.get(top, np.nan)), 1)
    near = s.loc[top - pd.Timedelta(days=60): top + pd.Timedelta(days=60)]
    out["max_near_top"] = round(float(near.max()), 1); out["max_near_top_date"] = str(near.idxmax().date())
    out["max_in_window"] = round(float(s.max()), 1); out["max_in_window_date"] = str(s.idxmax().date())
    lvls = THRESH + ([hot] if hot else [])
    for T in lvls:
        key = f"T{int(T)}"
        pre = s.loc[top - pd.Timedelta(days=365): top + pd.Timedelta(days=30)]
        hit = pre[pre >= T]
        if len(hit):
            d = hit.index[0]; out[key] = {"first_cross": str(d.date()), "lead_days": (top - d).days,
                                          "price_pct_of_top": round(100 * float(p[d] / p[top]), 1)}
        else: out[key] = {"first_cross": None}
        eps = episodes(s >= T)
        false = [(a, b) for a, b in eps if not (top - pd.Timedelta(days=365) <= a <= top + pd.Timedelta(days=30))]
        out[key]["false_episodes"] = [f"{a.date()}..{b.date()}" for a, b in false]
    if bottom is not None:
        out["bottom"] = str(bottom.date()); out["bottom_price"] = round(float(p[bottom]))
        out["score_at_bottom"] = round(float(s.get(bottom, np.nan)), 1)
        nb = s.loc[bottom - pd.Timedelta(days=120): bottom + pd.Timedelta(days=120)]
        out["min_near_bottom"] = round(float(nb.min()), 1); out["min_near_bottom_date"] = str(nb.idxmin().date())
    return out

def run():
    cm = lib.coinmetrics(); tr = lib.google_trends()
    df, _ = lib.build_signals(cm, tr); p = df["price"]
    tops, bottoms = lib.find_tops_bottoms(p)
    res = {"tops": {k: str(v.date()) for k, v in tops.items()}, "bottoms": {k: str(v.date()) for k, v in bottoms.items()}, "folds": []}
    stitched = pd.DataFrame(index=df.index, columns=["score_eq", "score_fit", "hot_eq", "hot_fit", "fold"])
    for name, start, end in FOLDS:
        cal, H, se, sf, nh = calibrate(df, None, tops, start)
        r = {"fold": name, "calibration": cal,
             "equal": evaluate(se, p, tops[name], bottoms.get(name), start, end, cal["score_hot"]["equal"]),
             "fitted": evaluate(sf, p, tops[name], bottoms.get(name), start, end, cal["score_hot"]["fitted"])}
        sl = slice(start, end)
        stitched.loc[sl, "score_eq"] = se.loc[sl]; stitched.loc[sl, "score_fit"] = sf.loc[sl]
        stitched.loc[sl, "hot_eq"] = cal["score_hot"]["equal"]; stitched.loc[sl, "hot_fit"] = cal["score_hot"]["fitted"]
        s = nh.loc[start:end]; top = tops[name]; near = s.loc[top - pd.Timedelta(days=60): top + pd.Timedelta(days=60)]
        if s.isna().all():
            r["rules"] = None; res["folds"].append(r); stitched.loc[sl, "fold"] = name; continue
        rc = {"n_signals": len(cal["signal_hot"]), "max_near_top": int(near.max()), "at_top": int(s[top])}
        for N in (3, 4, 5):
            pre = s.loc[top - pd.Timedelta(days=365): top + pd.Timedelta(days=30)]; hit = pre[pre >= N]
            rc[f"N{N}"] = {"first": str(hit.index[0].date()), "lead_days": (top - hit.index[0]).days,
                           "price_pct_of_top": round(100 * float(p[hit.index[0]] / p[top]), 1)} if len(hit) else None
            rc[f"N{N}"] = rc[f"N{N}"] or {}
            rc[f"N{N}"]["false_episodes"] = [f"{a.date()}..{b.date()}" for a, b in episodes(s >= N) if not (top - pd.Timedelta(days=365) <= a <= top + pd.Timedelta(days=30))]
        r["rules"] = rc
        stitched.loc[start:end, "rules_hot"] = s
        res["folds"].append(r)
        sl = slice(start, end)
        stitched.loc[sl, "score_eq"] = se.loc[sl]; stitched.loc[sl, "score_fit"] = sf.loc[sl]
        stitched.loc[sl, "hot_eq"] = cal["score_hot"]["equal"]; stitched.loc[sl, "hot_fit"] = cal["score_hot"]["fitted"]
        stitched.loc[sl, "fold"] = name
    # pre-2013 (in-sample only; no walk-forward possible): equal weight, timing excluded
    H0 = lib.heats(df, []); s0 = lib.score_from(H0, {s: 1 for s in lib.SIGNALS if s != "cycle_day"}, [s for s in lib.SIGNALS if s != "cycle_day"])
    stitched.loc[:"2012-12-31", "score_eq"] = s0.loc[:"2012-12-31"]; stitched.loc[:"2012-12-31", "fold"] = "pre-2013 (no calibration)"
    stitched["price"] = p
    os.makedirs(os.path.join(lib.HERE, "out"), exist_ok=True)
    stitched.to_csv(os.path.join(lib.HERE, "out", "score_history.csv"), index_label="date")
    with open(os.path.join(lib.HERE, "out", "backtest.json"), "w") as f: json.dump(res, f, indent=1, default=str)
    return res

if __name__ == "__main__":
    r = run(); print(json.dumps(r, indent=1, default=str))
