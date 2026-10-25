"""FROZEN (band pre-registration). Size-law competitors S1 and S3 (2-parameter form, fitted on the BTC cycles 2013, 2017, 2021, 2025;
the 2011 cycle is excluded because its 'prior low' is the data start). Same arithmetic as height_laws/laws.py + laws2.py (study code).
  S1: log10(top / prior cycle low) = a + k * log10(market cap at the prior cycle low)      -> top price
  S3: log10(MVRV at top)          = a + k * log10(realized cap at the prior cycle low)   -> realized-price fit at the band peak date x MVRV
Range: +-w in log10, w = max(RMS leave-one-out error, RMS forward error) of the law's own top-price backtest.
x for the 2029 projection = the 2025 cycle's low = lowest weekly close in the 104 weeks after the 2025 top (2025-10-05), i.e. the
same definition the law is fitted on. Before 2027-10-03 that low is provisional (lowest so far)."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import lib, bandlib as B
cm = lib.coinmetrics(); S = B.S
TP_BACKTEST = {"2017": pd.Timestamp("2017-07-11"), "2021": pd.Timestamp("2021-11-10"), "2025": pd.Timestamp("2025-09-28")}  # band peak dates at halving origin (ensemble backtest)
TP_2029 = pd.Timestamp("2029-09-25")                       # frozen band peak date (band_freeze.json) - where S3's realized price is read
H_ = dict(zip(["2013", "2017", "2021", "2025"], S[1:5]))
SPEC = {"S1": ("mult_low", "prior_low_mcap"), "S3": ("mvrv_top", "rcap_start")}

def cycles(upto):
    """Cycle table from data strictly before `upto` (weekly closes = CoinMetrics close dated Sunday)."""
    c0 = cm.loc[: upto - pd.Timedelta(days=1)]
    Wb = c0[["price", "mcap", "mvrv"]].resample("W-SUN").last().dropna(subset=["price"]); RC = c0.mcap / c0.mvrv
    rows = []
    for j in range(5):
        w = Wb.loc[S[0]:S[1] - pd.Timedelta(days=1)] if j == 0 else Wb.loc[S[j] - pd.Timedelta(days=101):S[j] + pd.Timedelta(days=1084)]
        t = w.price.idxmax(); after = Wb.loc[t:t + pd.Timedelta(weeks=104)]; l = after.price.idxmin()
        rows.append(dict(cycle=["2011", "2013", "2017", "2021", "2025"][j], top_date=t, top=w.price[t], top_mvrv=w.mvrv[t],
                         low_date=l, low=after.price[l], low_mcap=after.mcap[l], low_complete=(t + pd.Timedelta(weeks=104)) <= Wb.index[-1]))
    c = pd.DataFrame(rows)
    c["prior_low"] = c.low.shift(); c["prior_low_mcap"] = c.low_mcap.shift(); c["prior_low_date"] = c.low_date.shift()
    c = c.iloc[1:].reset_index(drop=True)
    c["mult_low"] = np.log10(c.top / c.prior_low); c["mvrv_top"] = np.log10(c.top_mvrv)
    c["rcap_start"] = [float(RC.loc[:d].iloc[-1]) for d in c.prior_low_date]
    return c, RC

def pfit(ser, origin, since=None):
    q = ser.loc[since:origin - pd.Timedelta(days=1)].dropna(); q = q[q > 0]; b, a = np.polyfit(B.X(q.index), np.log10(q.values), 1)
    return lambda d: float(10 ** (a + b * B.X([d])[0]))
def fitA(x, y): k, a = np.polyfit(np.log10(x), y, 1); return a, k

def run(origin, low_override=None):
    """S1/S3 projections for the next top with data strictly before origin. low_override=(price) only for sensitivity tables."""
    C, RC = cycles(origin); out = {}
    def to_price(law, y, cyc, o, tp):
        if law == "S1": return float(C.set_index("cycle").prior_low[cyc]) * 10 ** y
        return pfit(cm.price / cm.mvrv, o, "2011-01-01")(tp) * 10 ** y
    cl = C.iloc[-1]
    for law, (yc, xc) in SPEC.items():
        loo, fwd = [], []
        for i in range(len(C)):
            c = C.cycle[i]
            if c != "2013":
                m = C.drop(i); a, k = fitA(m[xc], m[yc]); pr = to_price(law, a + k * np.log10(C[xc][i]), c, H_[c], TP_BACKTEST[c]); loo.append(np.log10(pr / C.top[i]))
            if i >= 2:
                m = C.iloc[:i]; a, k = fitA(m[xc], m[yc]); pr = to_price(law, a + k * np.log10(C[xc][i]), c, H_[c], TP_BACKTEST[c]); fwd.append(np.log10(pr / C.top[i]))
        w = max(float(np.sqrt(np.mean(np.square(loo)))), float(np.sqrt(np.mean(np.square(fwd)))))
        a, k = fitA(C[xc], C[yc])
        low, low_mcap = float(cl.low), float(cl.low_mcap)
        if low_override: low_mcap, low = low_mcap * low_override / low, float(low_override)
        x = low_mcap if law == "S1" else float(RC.loc[:cl.low_date].iloc[-1])
        y = a + k * np.log10(x)
        base = low if law == "S1" else pfit(cm.price / cm.mvrv, origin, "2011-01-01")(TP_2029)
        top = base * 10 ** y
        out[law] = dict(intercept=a, slope=k, x=x, multiple_log10=y, base=base, top=top, w=w, range=[top / 10 ** w, top * 10 ** w],
                        loo_err=loo, fwd_err=fwd, low_used=dict(date=str(cl.low_date.date()), price=float(cl.low), complete=bool(cl.low_complete)))
    return out

def lengthening_timing(halving=pd.Timestamp("2028-04-11")):
    """C4 timing competitor: halving + OLS-trend extrapolation of halving-to-top days (weekly-close tops) over all 4 completed cycles."""
    W = B.W; days = []
    for j in range(1, 5):
        w = W.loc[S[j] - pd.Timedelta(days=101): S[j] + pd.Timedelta(days=1084)]; days.append((w.idxmax() - S[j]).days)
    s, c = np.polyfit(np.arange(1, 5), days, 1); nxt = c + s * 5
    return dict(days=days, slope_per_cycle=s, next_days=nxt, date=str((halving + pd.Timedelta(days=round(nxt))).date()))
