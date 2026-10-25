"""PRE-REGISTERED Cycle Heat Score v2 ("cycle-relative, family-balanced"). FROZEN 2026-10-25.

DO NOT EDIT. The SHA-256 of this file is recorded in frozen/v2_freeze.json; signals.py checks it every run and logs
v2_spec_ok=False to journal.csv if the file was changed. Any change must become a new version (v3) with a new freeze date,
so v2 can only be judged on data that arrived AFTER it was frozen.

Definition
1. Same 8 raw signals as v1 (lib.build_signals).
2. Heat of each signal = percentile of today's value vs the PRIOR 2,922 days only (about two 4-year halving cycles),
   needing >= 730 prior observations. v1 compares against all history since 2010, so its peaks shrink each cycle
   (diminishing returns); v2 asks "how stretched is this vs the last two cycles".
   Timing heat = 100 * exp(-0.5 * ((day since halving - 494) / 71.4)^2), parameters frozen from the 2026-10-25 calibration.
3. Signals are grouped into 5 independent families, each family = mean of its members' heats:
      price_structure: mayer, p200w, trend_mult, pi_ratio      (all derived from price: they count as ONE vote)
      onchain_valuation: mvrv_z                                 (cost basis of all coins)
      network_usage: activity                                   (active addresses)
      attention: trends                                         (search interest)
      timing: cycle_day                                         (halving clock)
4. Score v2 = plain mean of the available family heats (needs >= 3 families).
5. Zones are fixed in advance, NOT fitted to past tops: hot >= 80, warm >= 65, neutral >= 40, cool < 40.
"""
import bisect
import numpy as np, pandas as pd

VERSION = "v2"
FROZEN_ON = "2026-10-25"
PARAMS = {
    "window_days": 2922, "min_obs": 730, "timing_mu": 494.0, "timing_sd": 71.4, "min_families": 3,
    "families": {"price_structure": ["mayer", "p200w", "trend_mult", "pi_ratio"], "onchain_valuation": ["mvrv_z"],
                 "network_usage": ["activity"], "attention": ["trends"], "timing": ["cycle_day"]},
    "zones": {"hot": 80, "warm": 65, "neutral": 40},
}

def window_pct(s, window, min_obs):
    """Percentile (0-100) of each value vs the previous `window` observed values (strictly prior, causal)."""
    out = np.full(len(s), np.nan); hist = []; q = []
    for i, v in enumerate(s.values):
        if np.isnan(v): continue
        if len(hist) >= min_obs:
            lo = bisect.bisect_left(hist, v); hi = bisect.bisect_right(hist, v); out[i] = 100.0 * (lo + hi) / 2 / len(hist)
        bisect.insort(hist, v); q.append(v)
        if len(q) > window: old = q.pop(0); del hist[bisect.bisect_left(hist, old)]
    return pd.Series(out, index=s.index)

def heats(df):
    P = PARAMS; H = pd.DataFrame(index=df.index)
    for fam, members in P["families"].items():
        for s in members:
            if s == "cycle_day": H[s] = 100 * np.exp(-0.5 * ((df["days_since_halving"] - P["timing_mu"]) / P["timing_sd"]) ** 2)
            else: H[s] = window_pct(df[s], P["window_days"], P["min_obs"])
    return H

def families(H):
    return pd.DataFrame({fam: H[m].mean(axis=1, skipna=True) for fam, m in PARAMS["families"].items()}, index=H.index)

def score(df):
    H = heats(df); F = families(H)
    sc = F.mean(axis=1, skipna=True); sc[F.notna().sum(axis=1) < PARAMS["min_families"]] = np.nan
    return sc, F, H

def zone(x):
    z = PARAMS["zones"]
    if x is None or not np.isfinite(x): return "n/a"
    return "hot" if x >= z["hot"] else "warm" if x >= z["warm"] else "neutral" if x >= z["neutral"] else "cool"
