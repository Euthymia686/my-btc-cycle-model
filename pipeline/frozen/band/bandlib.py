"""FROZEN (band pre-registration, see PREREG_BAND.md). Causal re-implementation of the dampened cycle band (pipeline/forward_band.py at 307abb5),
parameterised by forecast origin. Used only by corrected_rule.py for the walk-forward backtest that sets e_h."""
import numpy as np, pandas as pd
import lib

P = lib.coinmetrics()["price"].dropna(); P = P[P > 0]
EST_2028 = pd.Timestamp("2028-04-11")                     # forward_band.py: pd.Timestamp(lib.HORIZON.year, 4, 11)
S = [P.index[0]] + lib.HALVINGS + [EST_2028]               # cycle starts: 0=data start, 1=2012, 2=2016, 3=2020, 4=2024, 5=2028(est)
W = P[P.index.day_of_week == 6]                            # weekly close = CoinMetrics close dated Sunday (as kill rule b)
X = lambda idx: np.log10((pd.DatetimeIndex(idx) - lib.GENESIS).days.values)

def fit(origin):
    """OLS power law on closes strictly before origin (data through origin-1 day)."""
    q = P.loc[: origin - pd.Timedelta(days=1)]; b, a = np.polyfit(X(q.index), np.log10(q.values), 1)
    r = pd.Series(np.log10(q.values) - (a + b * X(q.index)), index=q.index)
    return a, b, r

def rho_at(origin, r):
    done = [j for j in range(len(S) - 1) if S[j + 1] <= origin]
    E = [float(r.loc[S[j]: S[j + 1] - pd.Timedelta(days=1)].max()) for j in done]
    if len(E) < 2: return np.nan, E
    return float(np.exp(np.mean(np.log([E[j] / E[j - 1] for j in range(1, len(E))])))), E

def band(origin, end, model="damp", rho=None, cap=False):
    """Daily log10 lo/md/hi from origin to end. model: damp | base2 (rho=1) | last1 (cycle k-1 only, unscaled)."""
    a, b, r = fit(origin); rh, E = rho_at(origin, r)
    if rho is not None: rh = rho
    if model == "base2": rh = 1.0
    dates = pd.date_range(origin - pd.Timedelta(days=14), end, freq="D"); out = []
    for d in dates:
        k = max(i for i, h in enumerate(S) if h <= d); day = (d - S[k]).days
        prior = (k - 1,) if model == "last1" else (k - 2, k - 1); vals = []
        for i in prior:
            if i < 0: continue
            v = r.loc[S[i] + pd.Timedelta(days=day - 10): S[i] + pd.Timedelta(days=day + 10)]
            if cap and i + 1 < len(S): v = v[v.index < S[i + 1]]
            if len(v): vals.append(v * (1.0 if model == "last1" else rh ** (k - i)))
        ok = len(vals) == len(prior)
        out.append((min(v.min() for v in vals), max(v.max() for v in vals), np.mean([v.median() for v in vals])) if ok else (np.nan,) * 3)
    o = pd.DataFrame(out, index=dates, columns=["lo", "hi", "md"])
    o = o.rolling(15, center=True, min_periods=1).mean()
    t = a + b * X(dates)
    return o.add(t, axis=0).dropna().loc[origin:], dict(a=a, b=b, rho=rh, E=E, q50=float(r.median()), q05=float(r.quantile(.05)), q95=float(r.quantile(.95)), sd=float(r.std()))
