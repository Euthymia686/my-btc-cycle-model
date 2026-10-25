"""Robust projection fan (anti stock-to-flow). Plain-language write-up: ROBUSTNESS.md.

Idea: do not trust any single formula. Each day the power-law trend is refit on ALL data up to that day. The fan is built
from how wrong that daily-refit trend has actually been in the past, out of sample, at each horizon h:
    e(t, h) = log10 price(t+h) - trend_fit_made_at_t(t+h)          (error of a forecast made at t, using data <= t only)
    r0(t)   = log10 price(t)   - trend_fit_made_at_t(t)            (how far above/below trend we were when forecasting)
For each h:  e = alpha_h + beta_h * r0 + u,  OLS, then the empirical 5/25/50/75/95% quantiles of u (residual resampling,
no normality assumed). Fan at horizon h from today = trend_today(t+h) + alpha_h + beta_h * r0_today + q_u(h).
The errors include the trend's own drift as data arrived (the thing that broke stock-to-flow), so bands widen forward.
Beyond the longest horizon with >= MIN_SAMPLES forecast origins, spreads grow with sqrt(h) (stated assumption).
"""
import numpy as np, pandas as pd, lib
np.seterr(invalid="ignore", divide="ignore")

QS = (5, 25, 50, 75, 95)
ORIGIN_START = "2012-01-01"     # origins before this have < 3 years of data and a wildly unstable fit
MIN_SAMPLES = 365
STEP = 7
HALF_LIFE_DAYS = 4 * 365.25  # one halving cycle; chosen a priori (not tuned): recent forecast errors count more

def wquant(v, w, qs):
    o = np.argsort(v); v, w = v[o], w[o]; c = (np.cumsum(w) - 0.5 * w) / w.sum()
    return np.interp(np.array(qs) / 100, c, v)

def causal_fit(price):
    d = (price.index - lib.GENESIS).days.values.astype(float); x, y = np.log10(d), np.log10(price.values)
    n = np.arange(1, len(x) + 1); sx, sy = np.cumsum(x), np.cumsum(y); sxx, sxy = np.cumsum(x * x), np.cumsum(x * y)
    b = (n * sxy - sx * sy) / (n * sxx - sx ** 2); a = (sy - b * sx) / n
    return d, x, y, a, b

def fan_params(price, asof=None, hmax=1600, step=STEP, half_life=HALF_LIFE_DAYS):
    """Fan parameters using only data up to `asof` (inclusive)."""
    p = price.loc[:asof] if asof is not None else price
    d, x, y, a, b = causal_fit(p)
    ok = np.where(p.index >= pd.Timestamp(ORIGIN_START))[0]
    r0 = y - (a + b * x)
    H = np.arange(0, hmax + 1, step); al, be, qs, ns = [], [], [], []
    last = None
    for h in H:
        o = ok[ok + h < len(y)]
        if len(o) >= MIN_SAMPLES:
            xf = np.log10(d[o] + h); e = y[o + h] - (a[o] + b[o] * xf); X = r0[o]
            age = (len(y) - 1) - (o + h)          # days since this forecast error became known
            w = np.ones(len(o)) if not half_life else 0.5 ** (age / half_life)
            if h == 0: alpha, beta, u = 0.0, 1.0, np.zeros(len(o))
            else:
                beta, alpha = np.polyfit(X, e, 1, w=np.sqrt(w)); u = e - (alpha + beta * X)
            q = wquant(u, w, QS); last = (h, alpha, beta, q, len(o))
            al.append(alpha); be.append(beta); qs.append(q); ns.append(len(o))
        else:                         # extrapolate: hold alpha/beta, widen spread with sqrt(h)
            h0, alpha, beta, q0, _ = last; s = np.sqrt(h / h0)
            al.append(alpha); be.append(beta); qs.append(q0[2] + (q0 - q0[2]) * s); ns.append(0)
    qs = np.array(qs)
    # bands must not narrow with horizon (overlapping samples make the raw estimates a little noisy)
    med = qs[:, 2:3]; up = np.maximum.accumulate(qs[:, 3:] - med, axis=0); dn = np.minimum.accumulate(qs[:, :2] - med, axis=0)
    qs = np.hstack([med + dn, med, med + up])
    return {"asof": str(p.index[-1].date()), "a": float(a[-1]), "b": float(b[-1]), "r0": float(r0[-1]), "h": H.tolist(),
            "alpha": np.array(al).tolist(), "beta": np.array(be).tolist(), "q": qs.tolist(), "n": ns, "qs": list(QS)}

def fan_at(P, dates, r0=None, a=None, b=None):
    """Fan quantile prices for given future dates (DataFrame q5..q95)."""
    a = P["a"] if a is None else a; b = P["b"] if b is None else b; r0 = P["r0"] if r0 is None else r0
    t0 = pd.Timestamp(P["asof"]); H = np.array(P["h"]); dates = pd.DatetimeIndex(dates)
    hh = np.clip((dates - t0).days.values, 0, H[-1])
    al = np.interp(hh, H, P["alpha"]); be = np.interp(hh, H, P["beta"]); Q = np.array(P["q"])
    xf = np.log10((dates - lib.GENESIS).days.values.astype(float))
    base = a + b * xf + al + be * r0
    return pd.DataFrame({f"q{k}": 10 ** (base + np.interp(hh, H, Q[:, i])) for i, k in enumerate(P["qs"])}, index=dates)

def coverage(price, fan, end=None):
    """Share of daily closes inside the 90% (q5-q95) and 50% (q25-q75) bands, plus tails."""
    p = price.reindex(fan.index).dropna()
    if end is not None: p = p.loc[:end]
    if p.empty: return {"days": 0}
    f = fan.loc[p.index]
    return {"days": int(len(p)), "in90": float(((p >= f.q5) & (p <= f.q95)).mean()), "in50": float(((p >= f.q25) & (p <= f.q75)).mean()),
            "below5": float((p < f.q5).mean()), "above95": float((p > f.q95).mean())}

def fixed_corridor(price, asof, dates):
    """The 'single formula' alternative for comparison: fit at asof, fixed 5/95% residual corridor that never widens."""
    p = price.loc[:asof]; d, x, y, a, b = causal_fit(p); res = y - (a[-1] + b[-1] * x)
    xf = np.log10((pd.DatetimeIndex(dates) - lib.GENESIS).days.values.astype(float)); t = a[-1] + b[-1] * xf
    return pd.DataFrame({"q5": 10 ** (t + np.percentile(res, 5)), "q25": 10 ** (t + np.percentile(res, 25)),
                         "q75": 10 ** (t + np.percentile(res, 75)), "q95": 10 ** (t + np.percentile(res, 95))}, index=pd.DatetimeIndex(dates))

def coverage_backtest(price, horizon_days=1150, half_life=HALF_LIFE_DAYS):
    """Freeze the fan at past dates (data <= freeze only) and score it on what happened next."""
    last = price.index[-1]; rows = []
    freezes = [pd.Timestamp(f"{y}-{m}-01") for y in range(2015, 2026) for m in (1, 7) if pd.Timestamp(f"{y}-{m}-01") < last - pd.Timedelta(days=180)]
    pool = {k: [] for k in ("all", "0-1y", "1-2y", "2-3y")}; pool_fix = []
    for fz in freezes:
        P = fan_params(price, fz, half_life=half_life); dates = pd.date_range(fz + pd.Timedelta(days=1), min(last, fz + pd.Timedelta(days=horizon_days)))
        F = fan_at(P, dates); pr = price.reindex(dates)
        inside90 = (pr >= F.q5) & (pr <= F.q95); inside50 = (pr >= F.q25) & (pr <= F.q75)
        hz = (dates - fz).days
        for k, (lo, hi) in {"all": (0, 99999), "0-1y": (0, 365), "1-2y": (366, 730), "2-3y": (731, 1150)}.items():
            m = (hz >= lo) & (hz <= hi)
            if m.any(): pool[k].append((inside90[m].values, inside50[m].values))
        C = coverage(price, F); Fx = fixed_corridor(price, fz, dates); Cx = coverage(price, Fx)
        pool_fix.append(((pr >= Fx.q5) & (pr <= Fx.q95)).values)
        rows.append({"freeze": str(fz.date()), **{k: round(v, 3) if isinstance(v, float) else v for k, v in C.items()},
                     "fixed_corridor_in90": round(Cx["in90"], 3)})
    summ = {}
    for k, v in pool.items():
        if v: summ[k] = {"in90": round(float(np.mean(np.concatenate([a for a, _ in v]))), 3), "in50": round(float(np.mean(np.concatenate([b for _, b in v]))), 3),
                         "days": int(sum(len(a) for a, _ in v))}
    summ["fixed_corridor_all_in90"] = round(float(np.mean(np.concatenate(pool_fix))), 3)
    return {"freezes": rows, "summary": summ, "horizon_days": horizon_days,
            "note": "Each freeze uses only data up to that date. Overlapping windows (every 6 months), so the rows are not independent; "
                    "about 2.5 halving cycles of out-of-sample history in total."}
