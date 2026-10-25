"""Display-only: the DAMPENED cycle band (v3-candidate rule, pipeline/v3/v3_spec.md section A) for the hero chart's forward part.
Same construction as charts.cycle_band (same full-data trend fit, two prior cycles at the same day-since-halving +-10 d,
15-day smoothing); the only difference is that each prior cycle's log-residuals are scaled by rho^(k-j), where rho is the
geometric mean of the ratio of successive peak excesses over the COMPLETED cycles (data start, 2012, 2016, 2020 cycles).
Writes data/hero_fwd.json (weekly Mondays). Does not touch the model, the score, or any frozen file. A shape guide, not a forecast."""
import json, os, sys, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import lib, charts

cm = lib.coinmetrics(); p = cm["price"].dropna(); p = p[p > 0]
a, b, res, q = charts.fits(p); r = pd.Series(res, index=p.index)
H = lib.HALVINGS + [pd.Timestamp(lib.HORIZON.year, 4, 11)]
starts = [p.index[0]] + lib.HALVINGS                      # cycle starts; the cycle after the last halving is not complete
E = [float(r.loc[starts[j]: starts[j + 1] - pd.Timedelta(days=1)].max()) for j in range(len(starts) - 1)]
rho = float(np.exp(np.mean(np.log([E[j] / E[j - 1] for j in range(1, len(E))]))))

def damp_band(dates):
    out = []
    for d in dates:
        k = max(i for i, h in enumerate(H) if h <= d); day = (d - H[k]).days; vals = []
        for i in (k - 2, k - 1):
            if i < 0: continue
            v = r.loc[H[i] + pd.Timedelta(days=day - 10): H[i] + pd.Timedelta(days=day + 10)]
            if len(v): vals.append(v * rho ** (k - i))
        out.append((min(v.min() for v in vals), max(v.max() for v in vals), np.mean([v.median() for v in vals])) if len(vals) == 2 else (np.nan,) * 3)
    o = pd.DataFrame(out, index=dates, columns=["lo", "hi", "md"]).rolling(15, center=True, min_periods=1).mean()
    t = charts.trend_at(a, b, dates)
    return pd.DataFrame({"lo": t * 10 ** o.lo, "hi": t * 10 ** o.hi, "md": t * 10 ** o.md}, index=dates)

days = pd.date_range("2024-04-20", "2029-01-31", freq="D"); D = damp_band(days)
mon = pd.date_range("2024-04-22", "2029-01-15", freq="W-MON"); W = D.reindex(mon)
rd = lambda v: None if not np.isfinite(v) else round(float(v), 2)
out = {"t": [int(x.timestamp()) for x in mon], "lo": [rd(v) for v in W.lo], "md": [rd(v) for v in W.md], "hi": [rd(v) for v in W.hi],
       "rho": round(rho, 4), "peak_excess": {str(starts[j].date()): round(E[j], 4) for j in range(len(E))}, "data_to": str(p.index[-1].date()),
       "note": "display only; dampened cycle band (v3 candidate rule), full-data trend fit; shape guide, not a forecast"}
json.dump(out, open(os.path.join(lib.HERE, "..", "data", "hero_fwd.json"), "w"), separators=(",", ":"))
print("wrote data/hero_fwd.json", len(mon), "rho", round(rho, 3))
