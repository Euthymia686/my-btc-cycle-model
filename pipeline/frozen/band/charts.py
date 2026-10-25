"""Render My BTC Cycle Model charts (PNGs + combined PDF) from state.json, out/score_history.csv and cached data."""
import json, os, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import lib

OUT = os.path.join(lib.HERE, "out")
C = {"price": "#111111", "trend": "#555555", "floor": "#d97706", "ceil": "#9ca3af", "band": "#3b82f6", "live": "#dc2626",
     "exp": "#b91c1c", "halv": "#6b7280", "cool": "#2563eb", "neutral": "#9ca3af", "warm": "#f59e0b", "hot": "#dc2626", "n/a": "#d1d5db"}
FOOT = ("Data: CoinMetrics Community API (daily BTC price, market cap, MVRV, supply, active addresses), CoinGecko (live price), "
        "Yahoo Finance (MSTR), Strategy.com / SEC EDGAR (BTC holdings), Google Trends, mempool.space (block height). "
        "All lines, bands and scores are my own fits to this data. Model output, not predictions; not financial advice.")
plt.rcParams.update({"text.parse_math": False, "font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e5e7eb", "grid.linewidth": 0.6})
usd = FuncFormatter(lambda v, _: f"${v/1e6:.1f}M" if v >= 1e6 else f"${v/1e3:.0f}K" if v >= 1e3 else f"${v:.0f}")

def foot(fig, extra=""):
    fig.text(0.01, 0.008, (extra + "  " if extra else "") + FOOT, fontsize=7, color="#6b7280", wrap=True, va="bottom")

def load():
    st = json.load(open(os.path.join(lib.HERE, "state.json")))
    cm = lib.coinmetrics(); df, _ = lib.build_signals(cm, lib.google_trends())
    return st, df

def fits(p):
    d = (p.index - lib.GENESIS).days.values; x = np.log10(d); y = np.log10(p.values)
    b, a = np.polyfit(x, y, 1); res = y - (a + b * x)
    q = {k: float(np.quantile(res, v)) for k, v in [("floor", 0.05), ("mid", 0.5), ("ceil", 0.95)]}
    return a, b, res, q

def trend_at(a, b, dates): return 10 ** (a + b * np.log10((pd.DatetimeIndex(dates) - lib.GENESIS).days.values))

def cycle_band(p, a, b, res, dates):
    """For each date: range of log-residuals of the two previous complete halving cycles at the same day-since-halving (+-10d)."""
    r = pd.Series(res, index=p.index); H = lib.HALVINGS + [pd.Timestamp(lib.HORIZON.year, 4, 11)]
    out = []
    for d in dates:
        hs = [h for h in H if h <= d]; h = hs[-1]; k = H.index(h); day = (d - h).days
        prev = [H[i] for i in (k - 2, k - 1) if i >= 0]
        vals = [r.loc[ph + pd.Timedelta(days=day - 10): ph + pd.Timedelta(days=day + 10)] for ph in prev]
        vals = [v for v in vals if len(v)]
        if len(vals) < 2: out.append((np.nan,) * 3); continue
        lo = min(v.min() for v in vals); hi = max(v.max() for v in vals); md = np.mean([v.median() for v in vals])
        out.append((lo, hi, md))
    o = pd.DataFrame(out, index=dates, columns=["lo", "hi", "md"]).rolling(15, center=True, min_periods=1).mean()
    t = trend_at(a, b, dates)
    return pd.DataFrame({"lo": t * 10 ** o.lo, "hi": t * 10 ** o.hi, "md": t * 10 ** o.md}, index=dates)

def fan(st, df):
    p = df["price"].dropna(); a, b, res, q = fits(p)
    dates = pd.date_range("2020-01-01", "2028-12-31", freq="D"); t = trend_at(a, b, dates)
    band = cycle_band(p, a, b, res, pd.date_range("2022-05-01", "2028-12-31", freq="D"))
    fig, ax = plt.subplots(figsize=(13, 7.2), dpi=130)
    ax.fill_between(dates, t * 10 ** q["floor"], t * 10 ** q["ceil"], color="#f3f4f6", zorder=0, label="Trend corridor (5%-95% of history)")
    ax.plot(dates, t * 10 ** q["ceil"], color=C["ceil"], lw=1, ls=":", label="Trend ceiling (95% fit)")
    ax.plot(dates, t * 10 ** q["mid"], color=C["trend"], lw=1.3, ls="--", label="Trend line (power-law fit, median)")
    ax.plot(dates, t * 10 ** q["floor"], color=C["floor"], lw=2, label="Trend floor (5% fit)")
    ax.fill_between(band.index, band.lo, band.hi, color=C["band"], alpha=0.16, lw=0, label="Cycle band (prior 2 cycles, same day since halving)")
    ax.plot(band.index, band.md, color=C["band"], lw=1.4, label="Cycle band middle")
    pp = p.loc["2020-01-01":]; ax.plot(pp.index, pp.values, color=C["price"], lw=1.1, label="BTC daily close")
    now = pd.Timestamp(st["date"]); px = st["btc"]["price"]
    ax.scatter([now], [px], s=70, color=C["live"], zorder=6, edgecolor="white", lw=1.5)
    ax.annotate(f"Now ${px:,.0f}\n{st['run_utc'][:16].replace('T',' ')} UTC", (now, px), xytext=(12, -32), textcoords="offset points",
                fontsize=9, color=C["live"], fontweight="bold")
    for h in lib.HALVINGS[2:] + [pd.Timestamp(st["btc"]["next_halving_est"])]:
        ax.axvline(h, color=C["halv"], ls=":", lw=1); ax.text(h, 3.3e3, " Halving" + (" (est.)" if h.year == 2028 else ""), fontsize=8, color=C["halv"], va="bottom")
    e = lib.HORIZON; te = trend_at(a, b, [e])[0]; be = band.loc[e]
    txt = (f"At end of 2028 (model values)\nTrend ceiling ${te*10**q['ceil']/1e3:,.0f}K\nTrend line ${te*10**q['mid']/1e3:,.0f}K\n"
           f"Cycle band ${be.lo/1e3:,.0f}K-${be.hi/1e3:,.0f}K\nTrend floor ${te*10**q['floor']/1e3:,.0f}K")
    ax.text(1.005, 0.62, txt, transform=ax.transAxes, fontsize=8.5, va="center", color="#374151")
    ax.set_yscale("log"); ax.yaxis.set_major_formatter(usd); ax.set_ylim(3e3, 4e6); ax.set_xlim(dates[0], pd.Timestamp("2029-01-15"))
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.text(0.07, 0.955, "My BTC Cycle Model: projection fan to Dec 2028", fontsize=15, fontweight="bold")
    fig.text(0.07, 0.925, "Model ranges, not predictions.  Log scale.  Shaded areas show where my fitted models put BTC, not where it will be.", fontsize=10, color=C["exp"], fontweight="bold")
    ax.legend(loc="upper left", fontsize=8, frameon=True, framealpha=0.95, ncol=2)
    fig.subplots_adjust(left=0.07, right=0.84, top=0.90, bottom=0.12)
    foot(fig, f"Trend fit: log10(price) = {a:.3f} + {b:.3f} x log10(days since 2009-01-03), OLS on {p.index[0].date()} to {p.index[-1].date()}; floor/ceiling = 5%/95% residual quantiles.")
    path = os.path.join(OUT, "a_projection_fan.png"); fig.savefig(path); plt.close(fig); return path

def score_hist(st, df):
    sh = pd.read_csv(os.path.join(OUT, "score_history.csv"), index_col=0, parse_dates=True)
    bt = json.load(open(os.path.join(OUT, "backtest.json")))
    tops = {k: pd.Timestamp(v) for k, v in bt["tops"].items()}; bots = {k: pd.Timestamp(v) for k, v in bt["bottoms"].items()}
    s = sh["score_eq"].astype(float).loc["2012-01-01":]; p = df["price"].loc["2012-01-01":]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 8), dpi=130, sharex=True, gridspec_kw={"height_ratios": [1, 1.25]})
    a1.plot(p.index, p.values, color=C["price"], lw=1); a1.set_yscale("log"); a1.yaxis.set_major_formatter(usd); a1.set_ylabel("BTC price")
    for k, t in tops.items():
        if t >= p.index[0]:
            a1.scatter([t], [df["price"][t]], marker="v", color=C["hot"], s=60, zorder=5); a1.annotate(f"top {t:%b %Y}", (t, df["price"][t]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8, color=C["hot"])
    for k, t in bots.items():
        if t >= p.index[0]:
            a1.scatter([t], [df["price"][t]], marker="^", color=C["cool"], s=60, zorder=5); a1.annotate(f"low {t:%b %Y}", (t, df["price"][t]), xytext=(0, -14), textcoords="offset points", ha="center", fontsize=8, color=C["cool"])
    a1.set_title("My Cycle Heat Score, 2012 to now (walk-forward, equal-weight)", loc="left", fontsize=15, fontweight="bold")
    for lo, hi, col in [(0, 40, C["cool"]), (40, 70, C["neutral"]), (70, 80, C["warm"]), (80, 100, C["hot"])]:
        a2.axhspan(lo, hi, color=col, alpha=0.07, lw=0)
    a2.plot(s.index, s.values, color="#111827", lw=1.1, label="Cycle Heat Score (0-100)")
    hot = sh["hot_eq"].astype(float).loc["2012-01-01":]
    a2.plot(hot.index, hot.values, color=C["hot"], lw=1.2, ls="--", drawstyle="steps-post", label="'Hot' level calibrated on prior tops only")
    for T in (70, 80, 90): a2.axhline(T, color="#9ca3af", lw=0.8, ls=":"); a2.text(s.index[0], T + 0.8, f" {T}", fontsize=8, color="#6b7280")
    for t in tops.values():
        if t >= s.index[0]: a1.axvline(t, color=C["hot"], lw=0.7, alpha=0.4); a2.axvline(t, color=C["hot"], lw=0.7, alpha=0.4)
    for t in bots.values():
        if t >= s.index[0]: a2.axvline(t, color=C["cool"], lw=0.7, alpha=0.4)
    for f in bt["folds"]:
        x = pd.Timestamp(f["calibration"]["cutoff"]); a2.axvline(x, color="#6b7280", lw=0.6)
        a2.text(x, 2, f" test {f['fold']}\n calibrated < {x:%Y}", fontsize=7.5, color="#4b5563", va="bottom")
    now = pd.Timestamp(st["date"]); a2.scatter([now], [st["score"]["value"]], color=C["live"], zorder=6, s=40)
    a2.annotate(f"now {st['score']['value']:.0f}", (now, st["score"]["value"]), xytext=(6, 6), textcoords="offset points", color=C["live"], fontsize=9, fontweight="bold")
    a2.set_ylim(0, 100); a2.set_ylabel("score"); a2.legend(loc="upper right", fontsize=8)
    a2.xaxis.set_major_locator(mdates.YearLocator()); a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.subplots_adjust(left=0.07, right=0.98, top=0.94, bottom=0.11, hspace=0.06)
    foot(fig, "Before 2013 nothing could be calibrated (score shown uncalibrated). Each signal's heat = percentile vs all PRIOR days; score = mean of available heats.")
    path = os.path.join(OUT, "b_heat_score_history.png"); fig.savefig(path); plt.close(fig); return path

def tiles(st, df):
    fig = plt.figure(figsize=(13, 8.2), dpi=130); fig.patch.set_facecolor("#f9fafb")
    fig.text(0.02, 0.955, "My BTC Cycle Model: signal dashboard", fontsize=17, fontweight="bold")
    fig.text(0.02, 0.925, f"Run {st['run_utc'][:16].replace('T',' ')} UTC.  BTC ${st['btc']['price']:,.0f} ({st['btc']['source']}).  "
             f"On-chain data as of {st['btc']['onchain_asof']}.  Zones are model readings, not signals to act.", fontsize=9.5, color="#4b5563")
    def tile(x, y, w, h, title, value, sub, z):
        ax = fig.add_axes([x, y, w, h]); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for s in ax.spines.values(): s.set_visible(True); s.set_color("#e5e7eb")
        ax.set_facecolor("white"); ax.add_patch(plt.Rectangle((0, 0), 0.025, 1, color=C.get(z, "#d1d5db"), transform=ax.transAxes))
        ax.text(0.06, 0.80, title, fontsize=9, color="#4b5563", transform=ax.transAxes)
        ax.text(0.06, 0.42, value, fontsize=17, fontweight="bold", transform=ax.transAxes)
        ax.text(0.06, 0.12, sub, fontsize=7.8, color="#6b7280", transform=ax.transAxes)
        if z: ax.text(0.95, 0.80, z.upper(), fontsize=8.5, fontweight="bold", color=C.get(z, "#6b7280"), ha="right", transform=ax.transAxes)
    sc = st["score"]
    tile(0.02, 0.70, 0.30, 0.19, "Cycle Heat Score (0-100)", f"{sc['value']:.0f}", f"hot >= {sc['hot_at']:.0f} (calibrated), warm >= {sc['warm_at']:.0f}; {sc['signals_hot']}/{sc['n_signals']} signals hot", sc["zone"])
    b = st["btc"]
    tile(0.34, 0.70, 0.205, 0.19, "BTC price", f"${b['price']:,.0f}", f"{b['drawdown_pct']}% from ${b['ath']:,.0f} peak", None)
    tile(0.555, 0.70, 0.205, 0.19, "Days since halving / peak", f"{b['days_since_halving']} / {b['days_since_peak']}", f"peak {b['ath_date']}; next halving ~{b['next_halving_est']}", None)
    tile(0.77, 0.70, 0.21, 0.19, "Trend line / realized price", f"${b['trend_line']/1e3:,.0f}K / ${b['realized_price']/1e3:,.0f}K", "my trend fit; realized = cap / MVRV", None)
    fmt = {"cycle_day": lambda v: f"day {v:.0f}", "mayer": lambda v: f"{v:.2f}x", "p200w": lambda v: f"{v:.2f}x", "trend_mult": lambda v: f"{v:.2f}x",
           "mvrv_z": lambda v: f"{v:.2f}", "pi_ratio": lambda v: f"{v:.2f}", "trends": lambda v: f"{v:.0f}/100", "activity": lambda v: f"{v:.2f}x"}
    for i, (k, s) in enumerate(st["signals"].items()):
        r, c = divmod(i, 4); x = 0.02 + c * 0.245; y = 0.47 - r * 0.215
        thr = s.get("thresholds_today"); sub = f"heat {s['heat']:.0f}" if s["heat"] is not None else "heat n/a"
        if thr: sub += f"; warm >= {thr['warm_at']:.2f}, hot >= {thr['hot_at']:.2f}" if k != "trends" else f"; warm >= {thr['warm_at']:.0f}, hot >= {thr['hot_at']:.0f}"
        if k == "cycle_day": sub += "; peaks came on day 371-546"
        tile(x, y, 0.235, 0.19, lib.SHORT[k], fmt[k](s["value"]) if s["value"] is not None else "n/a", sub, s["zone"])
    m = st["mstr"]
    tile(0.02, 0.04, 0.30, 0.19, "MSTR", f"${m['price']:.2f}  |  mNAV {m['mnav_simple']:.2f}x",
         f"{m['btc_holdings']:,} BTC, {m['shares']/1e6:,.1f}M shares; Strategy EV-based mNAV {m['mnav_strategy_ev_based']}", m["mnav_zone"])
    fig.text(0.02, 0.006, "Zones: cool < 40 heat, neutral 40+, warm/hot set from each signal's level at past tops. Heat = percentile vs all prior days. mNAV bands are judgement, not backtested.\nData: CoinMetrics Community, CoinGecko, Yahoo Finance, Strategy.com / SEC EDGAR, Google Trends, mempool.space. My own fits; not predictions, not financial advice.", fontsize=7, color="#6b7280")
    path = os.path.join(OUT, "c_indicator_dashboard.png"); fig.savefig(path, facecolor=fig.get_facecolor()); plt.close(fig); return path

def overlays(st, df):
    p = df["price"].dropna(); fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6.4), dpi=130)
    cols = ["#9ca3af", "#60a5fa", "#f59e0b", "#dc2626"]
    for h, col in zip(lib.HALVINGS, cols):
        s = p.loc[h: h + pd.Timedelta(days=1460)]; x = (s.index - h).days
        a1.plot(x, s / s.iloc[0], color=col, lw=1.6 if h.year == 2024 else 1.1, label=f"{h.year} halving cycle")
        pk = s.idxmax(); a1.scatter([(pk - h).days], [s.max() / s.iloc[0]], color=col, s=25)
    a1.axvline(st["btc"]["days_since_halving"], color=C["live"], lw=1, ls="--"); a1.text(st["btc"]["days_since_halving"], 1.05, " today", color=C["live"], fontsize=8)
    a1.set_yscale("log"); a1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}x")); a1.set_xlabel("days since halving"); a1.set_ylabel("price / price on halving day")
    a1.set_title("Halving overlay", loc="left", fontsize=13, fontweight="bold"); a1.legend(fontsize=8)
    bt = json.load(open(os.path.join(OUT, "backtest.json"))); tops = [pd.Timestamp(v) for k, v in bt["tops"].items() if k != "2011"]
    for t, col in zip(tops, cols):
        s = p.loc[t: t + pd.Timedelta(days=1100)]; x = (s.index - t).days; dd = 100 * (s / s.iloc[0] - 1)
        a2.plot(x, dd, color=col, lw=1.6 if t.year == 2025 else 1.1, label=f"{t:%b %Y} peak (low {dd.min():.0f}% on day {x[dd.argmin()]})")
    a2.axvline(st["btc"]["days_since_peak"], color=C["live"], lw=1, ls="--"); a2.text(st["btc"]["days_since_peak"], -3, " today", color=C["live"], fontsize=8)
    a2.set_ylim(-95, 5); a2.set_xlabel("days since cycle peak"); a2.set_ylabel("% below cycle peak")
    a2.set_title("Drawdown overlay", loc="left", fontsize=13, fontweight="bold"); a2.legend(fontsize=8, loc="lower right")
    fig.suptitle("My BTC Cycle Model: past cycles lined up", x=0.01, ha="left", fontsize=15, fontweight="bold")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.86, bottom=0.17, wspace=0.18)
    foot(fig, "Daily closes. Past patterns, not forecasts.")
    path = os.path.join(OUT, "d_cycle_overlays.png"); fig.savefig(path); plt.close(fig); return path

def pdf(paths):
    from matplotlib.backends.backend_pdf import PdfPages
    from PIL import Image
    out = os.path.join(OUT, "my_btc_cycle_model.pdf")
    with PdfPages(out) as pp:
        rp = os.path.join(lib.HERE, "REPORT.md")
        if os.path.exists(rp):
            lines = open(rp).read().splitlines(); per = 62
            for i in range(0, len(lines), per):
                fig = plt.figure(figsize=(8.5, 11)); fig.text(0.06, 0.96, "\n".join(lines[i:i + per]), family="DejaVu Sans Mono", fontsize=7.2, va="top")
                pp.savefig(fig); plt.close(fig)
        for p in paths:
            im = Image.open(p); w, h = im.size; fig = plt.figure(figsize=(11, 11 * h / w)); ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(im); ax.axis("off")
            pp.savefig(fig, dpi=150); plt.close(fig)
    return out

if __name__ == "__main__":
    st, df = load(); ps = [fan(st, df), score_hist(st, df), tiles(st, df), overlays(st, df)]
    print("\n".join(ps)); print(pdf(ps))
