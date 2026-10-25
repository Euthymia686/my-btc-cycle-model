"""FROZEN (band pre-registration, see PREREG_BAND.md). One-time, on the freeze day: writes the locked forward-band snapshot that PREREG_BAND.md grades.
The band rule is copied verbatim from pipeline/forward_band.py at commit 307abb5 (function damp_band), with rho passed in so the
benchmarks (rho = 1, last cycle only) come from the same code. Usage (from pipeline/): OFFLINE=1 PYTHONPATH=.:frozen/band python frozen/band/band_freeze.py frozen/band
Output: frozen/band/band_snapshot_<T0>.csv (daily) and band_freeze.json (parameters, input hashes, derived peak/low)."""
import json, os, sys, hashlib, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import lib, charts

OUT = sys.argv[1] if len(sys.argv) > 1 else "frozen_band_draft"; os.makedirs(OUT, exist_ok=True)
cm = lib.coinmetrics(); p = cm["price"].dropna(); p = p[p > 0]
T0 = p.index[-1] + pd.Timedelta(days=1)                   # forecast origin: the day after the last close
a, b, res, q = charts.fits(p); r = pd.Series(res, index=p.index)
H = lib.HALVINGS + [pd.Timestamp(lib.HORIZON.year, 4, 11)]   # 2028 halving: fixed estimate 2028-04-11 (calendar-anchored)
starts = [p.index[0]] + lib.HALVINGS
E = [float(r.loc[starts[j]: starts[j + 1] - pd.Timedelta(days=1)].max()) for j in range(len(starts) - 1)]
RHO = float(np.exp(np.mean(np.log([E[j] / E[j - 1] for j in range(1, len(E))]))))

def damp_band(dates, rho, prior=(2, 1)):                  # verbatim rule; prior=(2,1): cycles k-2 and k-1; (1,): k-1 only
    out = []
    for d in dates:
        k = max(i for i, h in enumerate(H) if h <= d); day = (d - H[k]).days; vals = []
        for i in (k - j for j in prior):
            if i < 0: continue
            v = r.loc[H[i] + pd.Timedelta(days=day - 10): H[i] + pd.Timedelta(days=day + 10)]
            if len(v): vals.append(v * rho ** (k - i))
        out.append((min(v.min() for v in vals), max(v.max() for v in vals), np.mean([v.median() for v in vals])) if len(vals) == len(prior) else (np.nan,) * 3)
    o = pd.DataFrame(out, index=dates, columns=["lo", "hi", "md"]).rolling(15, center=True, min_periods=1).mean()
    t = charts.trend_at(a, b, dates)
    return pd.DataFrame({"lo": t * 10 ** o.lo, "hi": t * 10 ** o.hi, "md": t * 10 ** o.md}, index=dates)

days = pd.date_range("2024-04-20", "2031-01-31", freq="D")
Dm, Db, Dl = damp_band(days, RHO), damp_band(days, 1.0), damp_band(days, 1.0, prior=(1,))
keep = Dm.md.notna() & (days >= T0); Dm, Db, Dl = Dm[keep], Db[keep], Dl[keep]
t = charts.trend_at(a, b, Dm.index)
snap = pd.DataFrame({"date": Dm.index.date, "band_lo": Dm.lo, "band_mid": Dm.md, "band_hi": Dm.hi,
                     "unscaled2_lo": Db.lo, "unscaled2_mid": Db.md, "unscaled2_hi": Db.hi, "lastcycle_mid": Dl.md,
                     "trend_line": t * 10 ** q["mid"], "trend_floor_5": t * 10 ** q["floor"], "trend_ceiling_95": t * 10 ** q["ceil"]}).round(2)
# constant-width benchmark: trend line +- the band's average half-width in log10 over the snapshot
hw = float(np.mean(np.log10(Dm.hi / Dm.lo)) / 2)
snap["constw_lo"] = (snap.trend_line / 10 ** hw).round(2); snap["constw_hi"] = (snap.trend_line * 10 ** hw).round(2)
f = os.path.join(OUT, f"band_snapshot_{T0.date()}.csv"); snap.to_csv(f, index=False)
nx = Dm.loc[H[-1]:]; pk = nx.md.idxmax(); lo = nx.loc[pk:].md.idxmin()
tops = [(W := p[p.index.day_of_week == 6]).loc[h - pd.Timedelta(days=101): h + pd.Timedelta(days=1084)].idxmax() for h in lib.HALVINGS[-2:]]
rule = H[-1] + pd.Timedelta(days=float(np.mean([(t_ - h).days for t_, h in zip(tops, lib.HALVINGS[-2:])])))
sha = lambda fn: hashlib.sha256(open(fn, "rb").read()).hexdigest()
meta = {"origin_T0": str(T0.date()), "data_through": str(p.index[-1].date()), "rho": RHO, "peak_excess": E, "trend_a": a, "trend_b": b,
        "resid_q05_q50_q95": [q["floor"], q["mid"], q["ceil"]], "halving_2028_assumed": "2028-04-11", "window_days": 10, "smooth_days": 15,
        "constw_half_width_log10": hw, "snapshot_last_date": str(Dm.index[-1].date()),
        "band_peak": {"date": str(pk.date()), "mid": Dm.md[pk], "lo": Dm.lo[pk], "hi": Dm.hi[pk]},
        "band_low_after_peak": {"date": str(lo.date()), "mid": Dm.md[lo], "lo": Dm.lo[lo], "hi": Dm.hi[lo]},
        "timing_window": [str((pk - pd.Timedelta(days=91)).date()), str((pk + pd.Timedelta(days=91)).date())],
        "timing_rule_benchmark": {"date": str(rule.date()), "prior_tops": [str(x.date()) for x in tops]},
        "inputs_sha256": {"pipeline/cache/coinmetrics.json": sha(os.path.join(lib.CACHE, "coinmetrics.json"))},
        "code_sha256": {"lib.py": sha("lib.py"), "charts.py": sha("charts.py"), "band_freeze.py": sha(os.path.abspath(__file__))},
        "snapshot_sha256": sha(f)}
json.dump(meta, open(os.path.join(OUT, "band_freeze.json"), "w"), indent=1, default=float)
print(json.dumps({k: meta[k] for k in ("origin_T0", "rho", "band_peak", "band_low_after_peak", "timing_window", "timing_rule_benchmark", "constw_half_width_log10", "snapshot_last_date")}, default=float, indent=1))
