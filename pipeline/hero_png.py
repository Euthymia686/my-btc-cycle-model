"""Render the one-figure 'My BTC Cycle Model' hero PNG (high resolution).
Weekly BTC price coloured by Cycle Heat Score (v1) over the trend corridor / floor / ceiling / trend line / cycle band. After now the
blue band continues in the same style (dampened forward cycle band, data/hero_fwd.json from forward_band.py, display only) as far as the
prior cycles' data reaches (late 2030), with light notes on its possible next top and the low after it, computed from the data each run.
The graded forecast range (the frozen fan) is NOT drawn here since 2026-10-25 (display change only); the site shows it in the scorecard
section. No model changes: uses charts.fits / cycle_band (same as chart a) and state.json. Model output, not predictions."""
import json, os, sys, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
import lib, charts

OUTS = [os.path.join(lib.HERE, "out", "hero_combined.png"), os.path.join(lib.HERE, "..", "hero_combined.png")]
st = json.load(open(os.path.join(lib.HERE, "state.json")))
HOT, WARM = st["score"]["hot_at"], st["score"]["warm_at"]

cm = lib.coinmetrics(); df, _ = lib.build_signals(cm, lib.google_trends())
p = df["price"].dropna(); a, b, res, q = charts.fits(p)
H = json.load(open(os.path.join(lib.HERE, "..", "data", "history.json")))
score = pd.Series(H["score"], index=pd.to_datetime(H["t"], unit="s"), dtype=float)

START, END = pd.Timestamp("2015-01-01"), pd.Timestamp("2031-01-20")
DISPLAY_END = pd.Timestamp("2030-12-31")   # display only
now = pd.Timestamp(st["date"]); px = st["btc"]["price"]; sc_now = st["score"]["value"]; zone_now = st["score"]["zone"]
# weekly price + weekly score (last value of each week), then the live point
wk = p.loc[START:].resample("W").last().dropna(); wk = wk[wk.index < now]
ws = score.reindex(p.index).ffill().loc[START:].resample("W").last().reindex(wk.index).ffill()
wk.loc[now] = px; ws.loc[now] = sc_now

# heat colour map, stops at the model's own zones (cool < 40, warm >= WARM, hot >= HOT)
stops = [(0, "#1e40af"), (30, "#3b82f6"), (40, "#9ca3af"), (WARM, "#f59e0b"), (HOT, "#ef4444"), (100, "#991b1b")]
cmap = LinearSegmentedColormap.from_list("heat", [(s / 100, c) for s, c in stops])

fig = plt.figure(figsize=(16, 9), dpi=200); fig.patch.set_facecolor("white")
ax = fig.add_axes([0.035, 0.115, 0.855, 0.775])

# ---- background layers (subtle), as in chart (a)
dates = pd.date_range(START, DISPLAY_END, freq="D"); t = charts.trend_at(a, b, dates)
ax.fill_between(dates, t * 10 ** q["floor"], t * 10 ** q["ceil"], color="#f3f4f6", lw=0, zorder=0, label="Trend corridor (5-95% of history)")
ax.plot(dates, t * 10 ** q["ceil"], color="#9ca3af", lw=0.9, ls=":", zorder=1, label="Trend ceiling (95%)")
ax.plot(dates, t * 10 ** q["mid"], color="#6b7280", lw=1.0, ls="--", zorder=1, label="Trend line (power-law fit)")
ax.plot(dates, t * 10 ** q["floor"], color="#d97706", lw=1.4, alpha=0.8, zorder=1, label="Trend floor (5%)")
band = charts.cycle_band(p, a, b, res, pd.date_range("2016-07-15", DISPLAY_END, freq="D"))
nowp = pd.Timestamp(st["date"]); pb = band.loc[:nowp]
ax.fill_between(pb.index, pb.lo, pb.hi, color="#3b82f6", alpha=0.11, lw=0, zorder=1, label="Cycle band (prior 2 cycles, same day since halving)")
ax.plot(pb.index, pb.md, color="#3b82f6", lw=0.9, alpha=0.55, zorder=1, label="Cycle band middle")
fwinfo = None
# forward cycle band after now (display only): the dampened band from data/hero_fwd.json, blended in log space over the first
# 8 weeks from the past band, as on the live site. Ends where the prior cycles' data ends (no extrapolation).
try:
    FW = json.load(open(os.path.join(lib.HERE, "..", "data", "hero_fwd.json")))
    fw = pd.DataFrame({k: pd.to_numeric(pd.Series(FW[k]), errors="coerce").values for k in ("lo", "md", "hi")}, index=pd.to_datetime(FW["t"], unit="s"))
    fw = fw.loc[nowp:DISPLAY_END].dropna()
    w = np.clip((fw.index - nowp).days.values / 56.0, 0, 1)
    bref = band.reindex(fw.index)
    for k in ("lo", "md", "hi"):
        bk = bref[k].values; fw[k] = np.where(np.isfinite(bk), np.exp((1 - w) * np.log(np.where(np.isfinite(bk), bk, 1)) + w * np.log(fw[k].values)), fw[k].values)
    fw = pd.concat([pb.iloc[[-1]], fw])
    ax.fill_between(fw.index, fw.lo, fw.hi, color="#3b82f6", alpha=0.11, lw=0, zorder=1, label=f"Cycle band ahead (past cycles scaled down, rho {FW['rho']:.2f}): shape guide, not a forecast")
    ax.plot(fw.index, fw.md, color="#3b82f6", lw=0.9, alpha=0.55, zorder=1)
    # possible next top = highest band middle after the next (estimated) halving; low after it = lowest band middle after that top
    nh = pd.Timestamp(st["btc"]["next_halving_est"]); f2 = fw.loc[nh:]; ipk = f2.md.idxmax(); f3 = f2.loc[ipk:].iloc[1:]
    fwinfo = {"end": fw.index[-1], "peak": (ipk, f2.loc[ipk])}
    if len(f3): ilo = f3.md.idxmin(); fwinfo["low"] = (ilo, f3.loc[ilo])
    K = lambda v: f"${v/1e3:,.0f}K"
    for k, dy, dx, lab in (("peak", 1.75, -170, "possible next top"), ("low", 0.6, -280, "low after it")):
        if k not in fwinfo: continue
        d, v = fwinfo[k]; ax.scatter([d], [v.md], s=16, color="#2563eb", alpha=0.7, zorder=4)
        ax.annotate(f"{lab}: ~{d.strftime('%b %Y')}\nmiddle ~{K(v.md)} (band {K(v.lo)}-{K(v.hi)})", (d, v.md), xytext=(d + pd.Timedelta(days=dx), v.md * dy),
                    ha="center", va="center", fontsize=8.5, color="#1e3a8a", alpha=0.85, arrowprops=dict(arrowstyle="-", color="#93c5fd", lw=0.7),
                    bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.5), zorder=6)
except Exception as e:
    print("forward cycle path not drawn:", e)

# ---- heat-coloured weekly price line
x = mdates.date2num(wk.index.to_pydatetime()); y = wk.values
segs = np.stack([np.column_stack([x[:-1], y[:-1]]), np.column_stack([x[1:], y[1:]])], axis=1)
lc = LineCollection(segs, cmap=cmap, norm=plt.Normalize(0, 100), linewidths=2.4, zorder=5, capstyle="round")
lc.set_array(((ws.values[:-1] + ws.values[1:]) / 2)); ax.add_collection(lc)
ax.scatter([now], [px], s=110, color=cmap(sc_now / 100), edgecolor="#111827", lw=1.6, zorder=7)

# ---- halvings
for h in [pd.Timestamp(d) for d in ["2016-07-09", "2020-05-11", "2024-04-20"]] + [pd.Timestamp(st["btc"]["next_halving_est"])]:
    for A in (ax,): A.axvline(h, color="#6b7280", ls=":", lw=0.9, zorder=1)
    ax.text(h, 105, ("est. halving " if h.year == 2028 else " halving"), fontsize=8.5, color="#6b7280", va="bottom", ha=("right" if h.year == 2028 else "left"))

# ---- right price axis, dense plain-dollar ticks (live-site style) + tag pill for the live price
TICKS = [100, 170, 300, 500, 850, 1500, 2500, 4200, 7000, 12000, 20000, 35000, 60000, 100000, 170000, 300000, 500000, 850000, 1500000, 2500000]
tags = [px]
plain = lambda v: "" if any(abs(np.log10(v / t)) < 0.1 for t in tags) else (f"${v:,.0f}" if v >= 1000 else f"${v:,.2f}")
ax.set_yscale("log"); ax.set_ylim(100, 4e6); ax.set_xlim(START, END)
ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator(TICKS)); ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: plain(v)))
ax.yaxis.tick_right(); ax.yaxis.set_label_position("right"); ax.spines["right"].set_visible(True); ax.spines["left"].set_visible(False)
ax.spines["right"].set_color("#d1d5db"); ax.tick_params(axis="y", labelsize=9.5, colors="#4b5563", length=0, pad=6)
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
def pill(y, text, fc, tc="white"):
    ax.annotate(text, (1.0, y), xycoords=("axes fraction", "data"), xytext=(5, 0), textcoords="offset points", ha="left", va="center",
                fontsize=9.5, color=tc, fontweight="bold", annotation_clip=False, bbox=dict(boxstyle="round,pad=0.28,rounding_size=0.25", fc=fc, ec="none"))
pill(px, f"${px:,.0f}", "#3b82f6")

h_, l_ = ax.get_legend_handles_labels()
ax.legend(h_, l_, loc="upper left", fontsize=8, ncol=2, frameon=True, framealpha=0.95, edgecolor="#e5e7eb")

# heat colour bar (small, lower right)
cax = ax.inset_axes([0.755, 0.10, 0.215, 0.022]); cb = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0, 100), cmap=cmap), cax=cax, orientation="horizontal")
cb.set_ticks([0, 40, WARM, HOT, 100]); cb.ax.tick_params(labelsize=7.5, length=2); cb.outline.set_edgecolor("#d1d5db")
cax.set_title("line colour = Cycle Heat Score", fontsize=8, color="#374151", pad=3)

# ---- titles, notes
fig.text(0.035, 0.955, "My BTC Cycle Model", fontsize=19, fontweight="bold")
fig.text(0.035, 0.922, f"BTC ${px:,.0f}  \u00b7  Cycle Heat Score {sc_now:.0f} ({zone_now})  \u00b7  day {st['btc']['days_since_halving']} since halving  \u00b7  "
         f"{st['btc']['days_since_peak']} days since the ${st['btc']['ath']/1e3:,.0f}K peak  \u00b7  {st['run_utc'][:16].replace('T', ' ')} UTC",
         fontsize=11, color="#374151")
fig.text(0.89, 0.945, "Model ranges, not predictions.\nNot financial advice.", fontsize=10, color="#b91c1c", fontweight="bold", ha="right", va="center")
import textwrap
note = ("Forward blue band: past cycles scaled down, a shape guide, not a forecast" + (f" (ends {fwinfo['end'].date()}, as far as the prior cycles' data reaches)" if fwinfo else "")
        + ". The graded forecast range (fan) is shown in the scorecard section, not on this chart.")
fig.text(0.035, 0.058, textwrap.fill(note, 200), fontsize=8.5, color="#4b5563", va="bottom")
fig.text(0.035, 0.042, f"Corridor/trend: log10(price) = {a:.3f} + {b:.3f} x log10(days since 2009-01-03), 5%/95% residuals. Price weekly; colour = Cycle Heat Score (v1) that week.", fontsize=7.5, color="#9ca3af")
fig.text(0.035, 0.008, textwrap.fill(charts.FOOT, 190), fontsize=7, color="#9ca3af", va="bottom")
for o in OUTS: fig.savefig(o, facecolor="white")
print("wrote", OUTS)

# ---- background layers for the live site hero (same fits as above), weekly on Mondays (matches hero.js weekStart)
mon = pd.date_range("2014-01-06", DISPLAY_END + pd.Timedelta(days=13), freq="W-MON"); tm = charts.trend_at(a, b, mon)
bm = band.reindex(mon)
r = lambda v: None if v is None or not np.isfinite(v) else round(float(v), 2)
bg = {"generated_from": "cycle_signals/hero_png.py (charts.fits + charts.cycle_band, same as chart a)",
      "fit": {"a": a, "b": b, "q_floor": q["floor"], "q_mid": q["mid"], "q_ceil": q["ceil"]},
      "t": [int(x.timestamp()) for x in mon], "floor": [r(v) for v in tm * 10 ** q["floor"]], "mid": [r(v) for v in tm * 10 ** q["mid"]],
      "ceil": [r(v) for v in tm * 10 ** q["ceil"]], "band_lo": [r(v) for v in bm.lo], "band_md": [r(v) for v in bm.md], "band_hi": [r(v) for v in bm.hi]}
json.dump(bg, open(os.path.join(lib.HERE, "..", "data", "hero_bg.json"), "w"), separators=(",", ":"))
print("wrote data/hero_bg.json", len(mon))
