"""FROZEN (band pre-registration). Implements SELECTION_RULE.md (written 2026-10-25T18:29Z) exactly; the code is corrected.py from the
height study with the same arithmetic, wrapped in functions so the one-time freeze and the daily log call the same lines.
Run from pipeline/ with PYTHONPATH=.:frozen/band (OFFLINE=1 for a rebuild from the cached CoinMetrics file)."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import lib, bandlib as B
cm = lib.coinmetrics(); P = B.P; W = B.W; S = B.S; X = B.X; H = S[1:]
MV = cm["mvrv"].dropna(); RP = (cm["price"] / cm["mvrv"]).dropna(); LAST = P.index[-1]
H_NEXT = pd.Timestamp("2028-04-11")                       # fixed halving estimate (calendar anchor, never updated)

def cyc_top(j, upto):
    w = W.loc[: upto - pd.Timedelta(days=1)]
    w = w.loc[S[0]: S[1] - pd.Timedelta(days=1)] if j == 0 else w.loc[S[j] - pd.Timedelta(days=101): S[j] + pd.Timedelta(days=1084)]
    return (w.idxmax(), float(w.max())) if len(w) else None
def cyc_low(j, upto, complete=True):
    t = cyc_top(j, upto); end = t[0] + pd.Timedelta(weeks=104)
    if complete and end >= upto: return None
    w = W.loc[t[0]: min(end, upto - pd.Timedelta(days=1))]; return (w.idxmin(), float(w.min()))
def loglin_next(v):
    if len(v) < 2: return np.nan
    i = np.arange(len(v)); s, c = np.polyfit(i, np.log(v), 1); return float(np.exp(c + s * len(v)))
def powerfit(ser, origin, since=None):
    q = ser.loc[since: origin - pd.Timedelta(days=1)]; q = q[q > 0]; b, a = np.polyfit(X(q.index), np.log10(q.values), 1)
    return (lambda d: float(10 ** (a + b * X([d])[0]))), pd.Series(np.log10(q.values) - (a + b * X(q.index)), index=q.index)
gm = lambda v: float(np.exp(np.mean(np.log(v))))

def estimate(k, origin, band_df=None, cap=True):
    tops = {j: cyc_top(j, origin) for j in range(k)}; lows = {j: cyc_low(j, origin) for j in range(k)}
    tr, res = powerfit(P, origin); q05, q50, q95 = (float(res.quantile(x)) for x in (.05, .5, .95))
    if band_df is None:
        try:
            bd, info = B.band(origin, min(LAST, H[k - 1] + pd.Timedelta(days=1084)), "damp", cap=cap)
            band_df = 10 ** bd if np.isfinite(info["rho"]) else None
        except Exception: band_df = None
    T, L = {}, {}
    if band_df is not None:
        nx = band_df.loc[H[k - 1] - pd.Timedelta(days=101):]; tp = nx.md.idxmax(); af = nx.loc[tp:]
        tl = af.md.idxmin() if len(af) > 30 else None
        T["T1_band"] = float(nx.md[tp]); L["L1_band"] = float(af.md[tl]) if tl is not None else np.nan
    else: tp = tl = None
    dts = [(tops[j][0] - S[j]).days for j in range(1, k) if tops[j]]; tl_ = [(lows[j][0] - tops[j][0]).days for j in range(k) if lows[j]]
    if tp is None: tp = H[k - 1] + pd.Timedelta(days=float(np.mean(dts[-2:])) if dts else 365)
    if tl is None: tl = tp + pd.Timedelta(days=float(np.mean(tl_[-2:])) if tl_ else 365)
    M = [np.log10(tops[j][1]) - np.log10(tr(tops[j][0])) for j in range(k) if tops[j]]
    m2 = loglin_next([m for m in M if m > 0]) if len(M) >= 2 else np.nan
    T["T2_trend_mult"] = tr(tp) * 10 ** m2 if np.isfinite(m2) else np.nan
    T["T3_ceiling95"] = tr(tp) * 10 ** q95
    mv = [float(MV.get(tops[j][0], np.nan)) for j in range(k) if tops[j]]
    rpf, _ = powerfit(RP, origin, since="2011-01-01")
    T["T4_mvrv"] = rpf(tp) * loglin_next(mv) if len(mv) >= 2 else np.nan
    R = [np.log10(tops[j][1] / tops[j - 1][1]) for j in range(1, k) if tops[j] and tops[j - 1]]
    T["T5_peak_ratio"] = tops[k - 1][1] * 10 ** loglin_next(R) if len(R) >= 2 and min(R) > 0 else np.nan
    trend_tp = tr(tp) * 10 ** q50
    inc = {m: v for m, v in T.items() if np.isfinite(v) and v >= trend_tp}                  # sanity (a),(b)
    ens_t = gm(list(inc.values())) if len(inc) >= 3 else np.nan
    dd = [1 - lows[j][1] / tops[j][1] for j in range(k) if lows[j]]; d2 = loglin_next(dd) if len(dd) >= 2 else np.nan
    L["L2_drawdown"] = ens_t * (1 - d2) if np.isfinite(d2) and np.isfinite(ens_t) else np.nan
    L["L3_floor05"] = tr(tl) * 10 ** q05
    lm = [float(MV.get(lows[j][0], np.nan)) for j in range(k) if lows[j]]
    L["L4_rp_mvrv"] = rpf(tl) * float(np.mean(lm)) if lm else np.nan
    Lr = [np.log10(lows[j][1]) - np.log10(tr(lows[j][0])) for j in range(k) if lows[j]]
    L["L5_low_resid"] = tr(tl) * 10 ** float(np.mean(Lr)) if Lr else np.nan
    incl = {m: v for m, v in L.items() if np.isfinite(v) and (not np.isfinite(ens_t) or v < ens_t)}   # sanity (a),(c)
    ens_l = gm(list(incl.values())) if len(incl) >= 3 and np.isfinite(ens_t) else np.nan
    sm = lambda d: float(np.std(np.log10(list(d.values())), ddof=1)) if len(d) >= 2 else np.nan
    return dict(T=T, L=L, inc_t=sorted(inc), inc_l=sorted(incl), ens_t=ens_t, ens_l=ens_l, sm_t=sm(inc), sm_l=sm(incl),
                tp=tp, tl=tl, trend_tp=trend_tp, band_df=band_df)

def backtest():
    rows = []
    for k, cyc in [(1, "2013"), (2, "2017"), (3, "2021"), (4, "2025")]:
        for lab, o in [("at halving", H[k - 1]), ("534 d before halving", H[k - 1] - pd.Timedelta(days=534))]:
            if o < pd.Timestamp("2012-01-01"): continue
            e = estimate(k, o); at = cyc_top(k, LAST + pd.Timedelta(days=1)); al = cyc_low(k, LAST + pd.Timedelta(days=1), complete=False)
            rows.append(dict(cycle=cyc, origin=lab, origin_date=o.date(), top_date_used=e["tp"].date(), included_top=",".join(e["inc_t"]),
                             ens_top=e["ens_t"], actual_top=at[1], top_err=np.log10(e["ens_t"] / at[1]), sm_t=e["sm_t"],
                             included_low=",".join(e["inc_l"]), ens_low=e["ens_l"], actual_low=al[1], low_err=np.log10(e["ens_l"] / al[1]), sm_l=e["sm_l"],
                             low_complete=(at[0] + pd.Timedelta(weeks=104)) <= LAST))
    bt = pd.DataFrame(rows); ok = bt[bt.top_err.notna()]; okl = bt[bt.low_err.notna() & bt.low_complete]
    return bt, float(np.sqrt(np.mean(ok.top_err ** 2))), float(np.sqrt(np.mean(okl.low_err ** 2)))

def interp(anchors, idx):
    out = np.zeros(len(idx))
    for i, d in enumerate(idx):
        if d <= anchors[0][0]: out[i] = anchors[0][1]; continue
        if d >= anchors[-1][0]: out[i] = anchors[-1][1]; continue
        for (d0, v0), (d1, v1) in zip(anchors[:-1], anchors[1:]):
            if d0 <= d <= d1: u = (d - d0) / (d1 - d0); out[i] = v0 + (v1 - v0) * (1 - np.cos(np.pi * u)) / 2; break
    return out

def corrected(bdf, origin):
    """bdf: uncorrected band in USD with columns lo, md, hi (daily index). Returns (corrected DataFrame, summary dict)."""
    bt, e_t, e_l = backtest(); e = estimate(5, origin, band_df=bdf)
    wt = float(np.sqrt(e["sm_t"] ** 2 + e_t ** 2)); wl = float(np.sqrt(e["sm_l"] ** 2 + e_l ** 2))
    lg = np.log10(bdf); tp, tl = e["tp"], e["tl"]
    c = interp([(H_NEXT, 0.0), (tp, np.log10(e["ens_t"]) - lg.md[tp]), (tl, np.log10(e["ens_l"]) - lg.md[tl])], lg.index)
    shi = interp([(H_NEXT, 1.0), (tp, wt / (lg.hi - lg.md)[tp]), (tl, wl / (lg.hi - lg.md)[tl])], lg.index)
    slo = interp([(H_NEXT, 1.0), (tp, wt / (lg.md - lg.lo)[tp]), (tl, wl / (lg.md - lg.lo)[tl])], lg.index)
    md2 = lg.md + c; cor = pd.DataFrame({"lo": 10 ** (md2 - slo * (lg.md - lg.lo)), "md": 10 ** md2, "hi": 10 ** (md2 + shi * (lg.hi - lg.md))}, index=lg.index)
    pk = cor.loc[H_NEXT:].md.idxmax(); lw = cor.loc[pk:].md.idxmin()
    summ = dict(origin=str(origin.date()), tp=str(tp.date()), tl=str(tl.date()), trend_at_tp=e["trend_tp"], T=e["T"], L=e["L"],
                included_top=e["inc_t"], included_low=e["inc_l"], ens_top=e["ens_t"], ens_low=e["ens_l"], sm_t=e["sm_t"], sm_l=e["sm_l"],
                e_h_top=e_t, e_h_low=e_l, w_top=wt, w_low=wl,
                top_range=[e["ens_t"] / 10 ** wt, e["ens_t"] * 10 ** wt], low_range=[e["ens_l"] / 10 ** wl, e["ens_l"] * 10 ** wl],
                corrected_peak=dict(date=str(pk.date()), **cor.loc[pk].to_dict()), corrected_low_after=dict(date=str(lw.date()), **cor.loc[lw].to_dict()),
                backtest=bt.astype(str).to_dict("records"))
    return cor, summ
