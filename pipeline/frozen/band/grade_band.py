"""FROZEN (band pre-registration). Grades the band and its competitors exactly as PREREG_BAND.md sections 4, 7, 11 and 12 say.
Usage (from pipeline/): PYTHONPATH=.:frozen/band python frozen/band/grade_band.py [frozen_dir] [out_json] [prices_csv]
Prices: data/band_prices.csv (first-print log). Writes data/band_grades.json for the scorecard. Interim results are labeled."""
import json, math, os, sys, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

WIN0, WIN1 = pd.Timestamp("2028-01-02"), pd.Timestamp("2031-03-30")       # top window (Sundays)
FINAL_TOP = pd.Timestamp("2031-04-06"); PATH0, PATH1 = pd.Timestamp("2026-11-01"), pd.Timestamp("2030-10-27")
EDGE_WEEKS = 26; TIE = 0.05; MIN_DM = 104; THIN = 13; MIN_THIN = 8; ALPHA = 0.05

def load(frozen, prices_csv):
    j = lambda f: json.load(open(os.path.join(frozen, f)))
    bf, cf = j("band_freeze.json"), j("competitors_freeze.json"); T0 = bf["origin_T0"]
    snap = pd.read_csv(os.path.join(frozen, f"band_snapshot_{T0}.csv"), parse_dates=["date"]).set_index("date")
    cor = pd.read_csv(os.path.join(frozen, f"corrected_band_snapshot_{T0}.csv"), parse_dates=["date"]).set_index("date")
    p = pd.read_csv(prices_csv, parse_dates=["date"]).set_index("date").close.astype(float)
    return bf, cf, snap, cor, p

def weekly(p): return p[p.index.day_of_week == 6]                          # close dated Sunday (end of Sunday UTC)

def dm_test(d, lag=26):
    """Diebold-Mariano with Newey-West (Bartlett) variance, lag 26, Harvey-Leybourne-Newbold correction; t(n-1) reference."""
    d = np.asarray(d, float); n = len(d); m = d.mean(); e = d - m
    g = [np.sum(e[k:] * e[:n - k]) / n for k in range(lag + 1)]
    v = (g[0] + 2 * sum((1 - k / (lag + 1)) * g[k] for k in range(1, lag + 1))) / n
    if v <= 0: return dict(n=n, mean_diff=m, stat=None, p=None)
    h = 1; stat = m / math.sqrt(v) * math.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    from scipy import stats
    return dict(n=n, mean_diff=float(m), stat=float(stat), p=float(2 * stats.t.sf(abs(stat), n - 1)))

def mcnemar(a, b):
    """Exact McNemar on paired hits (a, b boolean arrays)."""
    n01 = int(np.sum(~a & b)); n10 = int(np.sum(a & ~b)); n = n01 + n10
    if n == 0: return dict(n01=0, n10=0, p=1.0)
    k = min(n01, n10); p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return dict(n01=n01, n10=n10, p=p)

def holm(ps):
    """Holm step-down adjusted p-values, dict name -> p (None kept as None)."""
    items = sorted([(p, k) for k, p in ps.items() if p is not None]); m = len(items); out = {k: None for k in ps}; run = 0
    for i, (p, k) in enumerate(items): run = max(run, min(1.0, (m - i) * p)); out[k] = run
    return out

def lerr(pred, act): return float(math.log10(pred / act))

def grade(frozen, prices_csv, asof=None, halving_json=None, rerun_json=None):
    bf, cf, snap, cor, p = load(frozen, prices_csv)
    if asof is not None: p = p.loc[:asof]
    W = weekly(p); last = W.index[-1] if len(W) else None
    G = dict(asof=str(p.index[-1].date()) if len(p) else None, status={}, events={}, claims={}, comparisons={}, notes=[])
    pk_d = pd.Timestamp(bf["band_peak"]["date"]); lo_d = pd.Timestamp(bf["band_low_after_peak"]["date"])
    c1 = cf["C1_corrected"]; S1, S3, C4 = cf["C2_S1"], cf["C3_S3"], cf["C4_lengthening_timing"]
    rer = json.load(open(rerun_json)) if rerun_json and os.path.exists(rerun_json) else None
    _x = np.log10((snap.index - pd.Timestamp("2009-01-03")).days.values); _b, _a = np.polyfit(_x, np.log10(snap.trend_line.values), 1)
    trend = lambda d: float(10 ** (_a + _b * math.log10((pd.Timestamp(d) - pd.Timestamp("2009-01-03")).days)))   # snapshot trend line (power law; extends past 2030-11-01)

    # ---- events that can occur any time: floor breaks, K1 ----
    fl = snap.trend_floor_5.reindex(W.index).dropna(); below = (W.reindex(fl.index) < fl)
    runs, cur = [], None
    for d, b in below.items():
        if b and cur is None: cur = [d, d]
        elif b: cur[1] = d
        elif cur is not None: runs.append(cur); cur = None
    if cur is not None: runs.append(cur)
    G["events"]["floor_breaks"] = [dict(start=str(a.date()), end=str(b.date()), weeks=int(((b - a).days) // 7 + 1)) for a, b in runs]
    k1 = W.loc[:pd.Timestamp("2029-12-25")]; k1 = k1[k1 > bf["band_peak"]["hi"]]
    G["events"]["K1_close_above_band_high"] = str(k1.index[0].date()) if len(k1) else None

    # ---- top T*, outcome class ----
    Ww = W.loc[WIN0:WIN1]; final_top = last is not None and last >= WIN1
    if len(Ww):
        Ts = Ww.idxmax(); top = float(Ww.max()); aft = W.loc[Ts + pd.Timedelta(days=1):]
        conf = None
        for d in aft.index:
            seg = W.loc[Ts + pd.Timedelta(days=1): d]
            if (d - Ts).days >= 364 and seg.max() <= top and seg.min() <= 0.5 * top: conf = d; break
        edge = Ts > WIN1 - pd.Timedelta(weeks=EDGE_WEEKS); no_boom = top < trend(Ts)
        cls = ("top identified and confirmed (52 weeks, 50% drawdown)" if conf is not None and not edge
               else "no cycle top identified: highest close in the last 26 weeks of the window (supercycle or still rising)" if edge
               else "top identified, not confirmed (shallow cycle: no 50% drawdown within the record)") if final_top else "provisional (window still open)"
        if no_boom and final_top: cls += "; no boom: top below the trend line"
        G["status"]["top"] = dict(T_star=str(Ts.date()), close=top, final=final_top, confirmed_on=str(conf.date()) if conf is not None else None, outcome_class=cls)
    else:
        Ts = None; G["status"]["top"] = dict(final=False, outcome_class="pending (window opens 2028-01-02)")
    # ---- low L* ----
    if Ts is not None:
        endL = Ts + pd.Timedelta(weeks=104); WL = W.loc[Ts + pd.Timedelta(days=1): endL]
        finalL = final_top and last >= endL
        Ls = (WL.idxmin(), float(WL.min())) if len(WL) else (None, None)
        G["status"]["low"] = dict(L_star=str(Ls[0].date()) if Ls[0] is not None else None, close=Ls[1], final=bool(finalL), final_on=str(endL.date()))
    else: Ls, finalL = (None, None), False; G["status"]["low"] = dict(final=False)

    hal = json.load(open(halving_json)) if halving_json and os.path.exists(halving_json) else None
    def timing(name, date, src):
        r = dict(predicted=str(pd.Timestamp(date).date()), source=src)
        if Ts is not None:
            e = (Ts - pd.Timestamp(date)).days; r.update(error_days=e, hit=abs(e) <= 91, final=final_top)
            if final_top and "no cycle top identified" in G["status"]["top"]["outcome_class"]: r["hit"] = False; r["note"] = "no cycle top identified in the window: graded as a miss"
            if hal: r["halving_relative_error_days"] = (Ts - pd.Timestamp(hal["date"])).days - (pd.Timestamp(date) - pd.Timestamp("2028-04-11")).days
        return r
    def height(name, pt, lo, hi, src):
        r = dict(point=pt, range=[lo, hi], width_log10=lerr(hi, lo) if lo and hi else None, source=src)
        if Ts is not None:
            r.update(log10_err=lerr(pt, top), hit=(lo <= top <= hi) if lo else None, final=final_top)
            if final_top and "no cycle top identified" in G["status"]["top"]["outcome_class"]: r["note"] = "top at window edge: the true top may be higher; graded on T* as defined"
        if K1 and name == "band": r["K1"] = K1
        return r
    def low(name, pt, lo, hi, d, src):
        r = dict(point=pt, range=[lo, hi], date=str(pd.Timestamp(d).date()) if d is not None else None, source=src)
        if Ls[0] is not None:
            r.update(log10_err=lerr(pt, Ls[1]), hit=(lo <= Ls[1] <= hi) if lo else None, final=bool(finalL))
            if d is not None and Ts is not None and Ts > pd.Timestamp(d): r.update(hit=False if lo else None, note="top came after the predicted low date: ordering wrong, miss")
            if final_top and "no cycle top identified" in G["status"]["top"]["outcome_class"] and lo: r.update(hit=False, note="no cycle top identified: low not observed, graded as a miss")
        return r
    K1 = G["events"]["K1_close_above_band_high"]

    # ---- claims ----
    C = G["claims"]
    C["band"] = dict(label="Main claim: today's blue band (frozen snapshot)",
                     timing=timing("band", pk_d, "band peak date"), height=height("band", bf["band_peak"]["mid"], bf["band_peak"]["lo"], bf["band_peak"]["hi"], "band at peak date"),
                     low=low("band", bf["band_low_after_peak"]["mid"], bf["band_low_after_peak"]["lo"], bf["band_low_after_peak"]["hi"], lo_d, "band at its post-peak low date"))
    C["C1"] = dict(label="Competitor 1: ensemble-corrected band (frozen snapshot)",
                   timing=timing("C1", c1["tp"], "same peak date as the band (not an independent timing claim)"),
                   height=height("C1", c1["ens_top"], *c1["top_range"], "equal-weight ensemble"), low=low("C1", c1["ens_low"], *c1["low_range"], c1["tl"], "equal-weight ensemble"))
    C["C2"] = dict(label="Competitor 2: S1 size law (frozen snapshot value)", height=height("C2", S1["top"], *S1["range"], "S1 at freeze, provisional 2025-cycle low"))
    C["C3"] = dict(label="Competitor 3: S3 on-chain size law (frozen snapshot value)", height=height("C3", S3["top"], *S3["range"], "S3 at freeze, provisional 2025-cycle low"))
    if rer:
        C["C2R"] = dict(label="S1-R: S1 re-run once with the final 2025-cycle low (secondary)", height=height("C2R", rer["S1-R"]["top"], *rer["S1-R"]["range"], "rerun " + rer["origin"]))
        C["C3R"] = dict(label="S3-R: S3 re-run once with the final 2025-cycle low (secondary)", height=height("C3R", rer["S3-R"]["top"], *rer["S3-R"]["range"], "rerun " + rer["origin"]))
    C["C4"] = dict(label="Competitor 4: lengthening-cycle timing", timing=timing("C4", C4["date"], f"halving + {round(C4['next_days'])} d (linear trend in halving-to-top days)"))
    # benchmarks
    s_pk = snap.loc[pk_d]; Bm = G["benchmarks"] = {}
    Bm["trend"] = dict(height=height("trend", trend(pk_d), None, None, "trend line at the band peak date"),
                       low=low("trend", float(snap.trend_floor_5.get(lo_d)), None, None, None, "5% trend floor at the band low date"))
    up = snap.unscaled2_mid.loc["2028-04-11":]; up_d = up.idxmax(); upl = snap.unscaled2_mid.loc[up_d:].idxmin()
    Bm["unscaled2"] = dict(timing=timing("u2", up_d, "rho = 1 band peak"), height=height("u2", float(up.max()), None, None, "rho = 1 band peak"),
                           low=low("u2", float(snap.unscaled2_mid[upl]), None, None, None, "rho = 1 band low"))
    lc = snap.lastcycle_mid.loc["2028-04-11":]; lc_d = lc.idxmax(); lcl = snap.lastcycle_mid.loc[lc_d:].idxmin()
    Bm["last_cycle"] = dict(timing=timing("lc", lc_d, "last cycle unscaled peak"), height=height("lc", float(lc.max()), None, None, "last cycle unscaled"),
                            low=low("lc", float(snap.lastcycle_mid[lcl]), None, None, None, "last cycle unscaled low"))
    Bm["timing_rule"] = dict(timing=timing("tr", bf["timing_rule_benchmark"]["date"], "halving + mean of last two halving-to-top gaps"))
    if Ts is not None:
        dd = np.mean([1 - 3195 / 19250, 1 - 16247 / 65032])                                # mean of the last two completed drawdowns (weekly closes)
        Bm["drawdown_rule"] = dict(low=low("dd", top * (1 - dd), None, None, None, "actual top x (1 - mean of last two completed drawdowns)"))

    # ---- path (H4) ----
    Wp = W.loc[PATH0:PATH1]; s = snap.reindex(Wp.index); cr = cor.reindex(Wp.index); lp = np.log10(Wp.values)
    if len(Wp):
        L = {"band": np.abs(lp - np.log10(s.band_mid.values)), "C1": np.abs(lp - np.log10(cr.corr_mid.values)), "trend": np.abs(lp - np.log10(s.trend_line.values)),
             "unscaled2": np.abs(lp - np.log10(s.unscaled2_mid.values)), "last_cycle": np.abs(lp - np.log10(s.lastcycle_mid.values))}
        inb = (Wp.values >= s.band_lo.values) & (Wp.values <= s.band_hi.values); inc = (Wp.values >= s.constw_lo.values) & (Wp.values <= s.constw_hi.values)
        inC = (Wp.values >= cr.corr_lo.values) & (Wp.values <= cr.corr_hi.values)
        n = len(Wp); allowed = n >= MIN_DM; th = slice(THIN - 1, None, THIN)
        dm_main = dm_test(L["band"] - L["trend"]) if n > 30 else None
        dm_sec = {"C1_vs_trend": dm_test(L["C1"] - L["trend"]) if n > 30 else None, "C1_vs_band": dm_test(L["C1"] - L["band"]) if n > 30 else None}
        hp = holm({k: (v or {}).get("p") for k, v in dm_sec.items()})
        G["path"] = dict(weeks=n, final=bool(last >= PATH1), formal_results_allowed=allowed, mae={k: float(v.mean()) for k, v in L.items()},
                         coverage=dict(band=float(inb.mean()), constant_width=float(inc.mean()), C1=float(inC.mean())),
                         H4_primary_DM_band_vs_trend=dm_main, secondary_DM_holm=dict(raw=dm_sec, holm_p=hp),
                         mcnemar_thinned=mcnemar(inb[th], inc[th]) if len(inb[th]) >= MIN_THIN else dict(note=f"needs {MIN_THIN} thinned points, have {len(inb[th])}"))
        C["band"]["path_mae"] = float(L["band"].mean()); C["C1"]["path_mae"] = float(L["C1"].mean())
    k2w = W.loc[pd.Timestamp(bf["timing_window"][0]):pd.Timestamp(bf["timing_window"][1])]
    if last is not None and last >= pd.Timestamp(bf["timing_window"][1]) - pd.Timedelta(days=6):
        G["events"]["K2_no_close_reaches_band_low_in_window"] = bool(k2w.max() < bf["band_peak"]["lo"]) if len(k2w) else True
    if "path" in G and G["path"]["weeks"] >= MIN_DM:
        d = G["path"]["H4_primary_DM_band_vs_trend"]; G["events"]["K3_band_significantly_worse_than_trend"] = bool(d and d["p"] is not None and d["p"] < ALPHA and d["mean_diff"] > 0)
    hz = {}
    for wk in (26, 52, 104, 156, 208):
        dd = PATH0 - pd.Timedelta(days=7) + pd.Timedelta(weeks=wk)
        if dd in W.index: hz[f"{wk}w_{dd.date()}"] = dict(band=abs(lerr(snap.band_mid[dd], W[dd])), trend=abs(lerr(snap.trend_line[dd], W[dd])), C1=abs(lerr(cor.corr_mid[dd], W[dd])))
    if "path" in G: G["path"]["fixed_horizons_abs_log10"] = hz
    # ---- verdict for the main claim ----
    b = C["band"]; v = "pending"
    if final_top and finalL and G.get("path", {}).get("final"):
        h1, h2, h3 = b["timing"].get("hit"), b["height"].get("hit"), b["low"].get("hit"); dmw = (G["path"]["H4_primary_DM_band_vs_trend"] or {})
        worse = dmw.get("p") is not None and dmw["p"] < ALPHA and dmw["mean_diff"] > 0
        if not h1 or worse: v = "FAIL"
        elif h1 and h2 and h3 and G["path"]["mae"]["band"] <= G["path"]["mae"]["trend"]: v = "PASS"
        else: v = "PARTIAL"
    G["verdict_main"] = v
    if Ts is not None and final_top and top < bf["band_peak"]["lo"]: G["events"]["K4_repeat_overshoot"] = True
    # ---- comparisons (winner rule, section 12.3) ----
    def rank(kind, entries):
        e = {k: abs(x) for k, x in entries.items() if x is not None}
        if not e: return None
        best = min(e, key=e.get); second = min([x for k, x in e.items() if k != best], default=None)
        return dict(abs_errors=e, best=best, decisive=second is None or second - e[best] >= (TIE if kind != "timing" else 30),
                    rule=f"lowest absolute error; a lead under {'30 days' if kind == 'timing' else str(TIE) + ' log10 (about 12%)'} is a tie")
    allc = {**C, **{f"bench_{k}": v for k, v in Bm.items()}}
    G["comparisons"] = {kind: rank(kind, {k: c[kind].get("error_days" if kind == "timing" else "log10_err") for k, c in allc.items()
                                          if kind in c and not (kind == "timing" and k == "C1") and not k.endswith("R")})   # C1 timing = band timing; S1-R/S3-R are readouts, not ranked
                        for kind in ("timing", "height", "low")}
    if "path" in G: G["comparisons"]["path"] = dict(mae=G["path"]["mae"], best=min(G["path"]["mae"], key=G["path"]["mae"].get), final=G["path"]["final"])
    return G

if __name__ == "__main__":
    fr = sys.argv[1] if len(sys.argv) > 1 else "frozen/band"; out = sys.argv[2] if len(sys.argv) > 2 else "../data/band_grades.json"
    pc = sys.argv[3] if len(sys.argv) > 3 else "../data/band_prices.csv"
    G = grade(fr, pc, halving_json="../data/halving_2028.json", rerun_json="../data/band_rerun.json")
    json.dump(G, open(out, "w"), indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x))
