import sys, json, numpy as np, pandas as pd; sys.path.insert(0, "..")
import lib
cm = lib.coinmetrics(); p = cm["price"].dropna(); p = p[p > 0]
H = [p.index[0]] + lib.HALVINGS            # cycle starts: 0=data start,1=2012,2=2016,3=2020,4=2024
END = p.index[-1]
def fit_at(T):
    q = p.loc[:T]; x = np.log10((q.index - lib.GENESIS).days.values); y = np.log10(q.values)
    b, a = np.polyfit(x, y, 1); return a, b
def resid(a, b):
    return pd.Series(np.log10(p.values) - (a + b * np.log10((p.index - lib.GENESIS).days.values)), index=p.index)
def cyc(r, j):
    e = H[j + 1] if j + 1 < len(H) else END + pd.Timedelta(days=1)
    return r.loc[H[j]: e - pd.Timedelta(days=1)]
tops, _ = lib.find_tops_bottoms(p)
TOP = {2: tops["2017"], 3: tops["2021"], 4: tops["2025"]}
def band(k, scale, a, b, r):
    s = H[k]; e = (H[k + 1] - pd.Timedelta(days=1)) if k + 1 < len(H) else pd.Timestamp("2028-04-10")
    dates = pd.date_range(s, e); out = []
    for d in dates:
        day = (d - s).days; vs = []
        for j in (k - 2, k - 1):
            w = r.loc[H[j] + pd.Timedelta(days=day - 10): H[j] + pd.Timedelta(days=day + 10)]
            w = w[w.index < H[j + 1]]
            if len(w): vs.append(w * scale[j])
        if len(vs) < 2: out.append((np.nan,) * 3); continue
        out.append((min(v.min() for v in vs), max(v.max() for v in vs), np.mean([v.median() for v in vs])))
    o = pd.DataFrame(out, index=dates, columns=["lo", "hi", "md"]).rolling(15, center=True, min_periods=1).mean()
    xf = np.log10((dates - lib.GENESIS).days.values); t = a + b * xf
    return o.add(t, axis=0)            # log10 prices
rows = []; bands = {}
for k in (2, 3, 4):
    a, b = fit_at(H[k] - pd.Timedelta(days=1)); r = resid(a, b)
    E = [cyc(r, j).max() for j in range(k)]
    ratios = [E[j] / E[j - 1] for j in range(1, k)]
    rho = float(np.exp(np.mean(np.log(ratios))))
    sl, ic = np.polyfit(np.arange(k), E, 1); Ek = ic + sl * k
    sc = {"base": {j: 1.0 for j in range(k)}, "damp": {j: rho ** (k - j) for j in range(k)},
          "lin": {j: max(Ek, 0) / E[j] for j in range(k)}}
    pr = np.log10(p.loc[H[k]:]); pr = pr.loc[:(H[k + 1] - pd.Timedelta(days=1)) if k + 1 < len(H) else END]
    for name, s in sc.items():
        B = band(k, s, a, b, r); bands[(k, name)] = B
        m = B.loc[pr.index]
        tp = B.md.idxmax()
        rows.append({"cycle": f"{H[k].year}->{TOP[k].year} top", "model": name, "rho": round(rho, 3) if name == "damp" else None,
                     "E_prior": [round(x, 2) for x in E],
                     "top_actual": round(float(p[TOP[k]])), "top_date": str(TOP[k].date()),
                     "mid_peak": round(float(10 ** B.md.max())), "mid_peak_date": str(tp.date()),
                     "top_err_log10": round(float(B.md.max() - np.log10(p[TOP[k]])), 3),
                     "top_err_x": round(float(10 ** (B.md.max() - np.log10(p[TOP[k]]))), 2),
                     "timing_err_d": int((tp - TOP[k]).days),
                     "mae_log10": round(float((m.md - pr).abs().mean()), 3),
                     "in_band": round(float(((pr >= m.lo) & (pr <= m.hi)).mean()), 3), "days": len(pr)})
df = pd.DataFrame(rows); print(df.drop(columns=["E_prior"]).to_string()); print(df[df.model=="damp"][["cycle","E_prior","rho"]].to_string())
df.to_csv("band_results.csv", index=False)
pd.to_pickle(bands, "bands.pkl")
