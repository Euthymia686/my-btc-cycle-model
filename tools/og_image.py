"""Render the social share image (og-image.png, 1200x630) from the repo's own published data. Display only.
Reads data/history.json (weekly close + Cycle Heat Score), data/hero_bg.json (trend corridor + past cycle band),
data/hero_fwd.json (blue band ahead, past cycles scaled down) and pipeline/state.json (zone thresholds).
No network, no model code, nothing frozen is read or written. Regenerate with:  python tools/og_image.py"""
import json, os
import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates, matplotlib.ticker as mt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime, timezone

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
J = lambda p: json.load(open(os.path.join(R, p)))
H, BG, FW, ST = J("data/history.json"), J("data/hero_bg.json"), J("data/hero_fwd.json"), J("pipeline/state.json")
HOT, WARM = ST["score"]["hot_at"], ST["score"]["warm_at"]
D = lambda ts: np.array([datetime.fromtimestamp(t, timezone.utc).replace(tzinfo=None) for t in ts])
num = lambda a: np.array([np.nan if v is None else v for v in a], dtype=float)

t, c, s = D(H["t"]), num(H["close"]), num(H["score"])
keep = t >= datetime(2015, 1, 1); t, c, s = t[keep], c[keep], s[keep]
wk = np.arange(len(t)) % 7 == 0; wk[-1] = True; t, c, s = t[wk], c[wk], s[wk]       # weekly points, plus the last day
ok = np.isfinite(c); t, c, s = t[ok], c[ok], np.where(np.isfinite(s[ok]), s[ok], 50)

stops = [(0, "#1e40af"), (30, "#3b82f6"), (40, "#9ca3af"), (WARM, "#f59e0b"), (HOT, "#ef4444"), (100, "#991b1b")]
cmap = LinearSegmentedColormap.from_list("heat", [(v / 100, col) for v, col in stops])

fig = plt.figure(figsize=(12, 6.3), dpi=100); fig.patch.set_facecolor("white")
ax = fig.add_axes([0.04, 0.09, 0.86, 0.68])
bt = D(BG["t"]); fl, md, ce = num(BG["floor"]), num(BG["mid"]), num(BG["ceil"])
ax.fill_between(bt, fl, ce, color="#f1f2f5", lw=0, zorder=0)
ax.plot(bt, ce, color="#9ca3af", lw=1, ls=":", zorder=1); ax.plot(bt, md, color="#6b7280", lw=1, ls="--", zorder=1)
ax.plot(bt, fl, color="#d97706", lw=1.8, zorder=1)
blo, bhi, bmd = num(BG["band_lo"]), num(BG["band_hi"]), num(BG["band_md"]); past = bt <= t[-1]
ax.fill_between(bt[past], blo[past], bhi[past], color="#3b82f6", alpha=0.14, lw=0, zorder=1)
ft = D(FW["t"]); flo, fmd, fhi = num(FW["lo"]), num(FW["md"]), num(FW["hi"]); fa = ft >= t[-1]
ax.fill_between(ft[fa], flo[fa], fhi[fa], color="#3b82f6", alpha=0.14, lw=0, zorder=1)
ax.plot(ft[fa], fmd[fa], color="#3b82f6", lw=1, alpha=0.55, zorder=1)

x = mdates.date2num(t); segs = np.stack([np.column_stack([x[:-1], c[:-1]]), np.column_stack([x[1:], c[1:]])], axis=1)
lc = LineCollection(segs, cmap=cmap, norm=plt.Normalize(0, 100), linewidths=3, zorder=5, capstyle="round")
lc.set_array((s[:-1] + s[1:]) / 2); ax.add_collection(lc)
ax.scatter([t[-1]], [c[-1]], s=60, color=cmap(s[-1] / 100), edgecolor="#111827", lw=1.3, zorder=7)

ax.set_yscale("log"); ax.set_ylim(150, 3e6); ax.set_xlim(datetime(2015, 1, 1), datetime(2031, 1, 15))
ax.yaxis.set_major_locator(mt.FixedLocator([1000, 10000, 100000, 1000000]))
ax.yaxis.set_minor_locator(mt.NullLocator())
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v/1e6:.0f}M" if v >= 1e6 else f"${v/1e3:.0f}K" if v >= 1e3 else f"${v:.0f}"))
ax.yaxis.tick_right(); ax.tick_params(axis="both", labelsize=13, colors="#4b5563", length=0, pad=6)
ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
for k in ("top", "left"): ax.spines[k].set_visible(False)
for k in ("right", "bottom"): ax.spines[k].set_color("#d1d5db")
ax.grid(axis="y", color="#eef0f3", lw=1, zorder=0)

fig.text(0.04, 0.89, "My BTC Cycle Model", fontsize=40, fontweight="bold", color="#111827", va="center")
fig.text(0.04, 0.815, "Where Bitcoin is in its ~4-year cycle: locked rules, Bitcoin-timestamped, graded in public.", fontsize=17, color="#374151", va="center")
fig.text(0.04, 0.03, "euthymia686.github.io/my-btc-cycle-model", fontsize=15, color="#2563eb", va="center", fontweight="bold")
# small key: heat gradient + blue band
kx = fig.add_axes([0.70, 0.016, 0.12, 0.028]); kx.imshow(np.linspace(0, 1, 256)[None, :], aspect="auto", cmap=cmap); kx.axis("off")
fig.text(0.695, 0.03, "line color = Heat Score  cool", fontsize=11.5, color="#6b7280", ha="right", va="center")
fig.text(0.825, 0.03, "hot", fontsize=11.5, color="#6b7280", va="center")
fig.patches.append(plt.Rectangle((0.865, 0.017), 0.02, 0.026, transform=fig.transFigure, color="#3b82f6", alpha=0.25, figure=fig))
fig.text(0.89, 0.03, "past cycles", fontsize=11.5, color="#6b7280", va="center")
out = os.path.join(R, "og-image.png"); fig.savefig(out, facecolor="white", dpi=100)
print("wrote", out, os.path.getsize(out), "bytes")
