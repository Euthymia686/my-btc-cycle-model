"""Statistical grading for the scorecard. The method is pre-registered in frozen/v3/FREEZE.md ("Grading method");
if this code and that note ever disagree, the note governs and the code is fixed.

- Baseline: plain power-law trend, log10(price) = a + b * log10(days since 2009-01-03), OLS on every daily close up to
  and including the forecast date, with a lognormal band of constant width: sd = standard deviation of that fit's
  residuals (log10), the same at every horizon.
- Coverage test: exact two-sided binomial test of hits vs the target rate (0.5 or 0.9) on NON-overlapping predictions only.
- Skill test: Diebold-Mariano test on the per-forecast log score difference, Newey-West (Bartlett) long-run variance,
  two-sided normal p-value.
"""
import math
import numpy as np, pandas as pd
from scipy import stats
import lib

Z = {"q5": -1.6448536, "q25": -0.6744898, "q50": 0.0, "q75": 0.6744898, "q95": 1.6448536}
MIN_EFF = 10

def baseline(p, d, horizons):
    """Baseline forecast made at close d: {h: {q5..q95, 'sd10': sd}} using closes <= d only."""
    q = p.loc[:d]; x = np.log10((q.index - lib.GENESIS).days.values.astype(float)); y = np.log10(q.values)
    b, a = np.polyfit(x, y, 1); sd = float(np.std(y - (a + b * x), ddof=1)); out = {}
    for h in horizons:
        m = a + b * math.log10((d + pd.Timedelta(days=h) - lib.GENESIS).days)
        out[h] = {k: 10 ** (m + z * sd) for k, z in Z.items()}; out[h]["sd10"] = sd
    return out

def baseline_log_score(q, x):
    """ln density of ln(x) under the baseline lognormal; sd recovered from the stored 5% and 95% levels."""
    s = (math.log(q["q95"]) - math.log(q["q5"])) / (2 * Z["q95"]); m = math.log(q["q50"]); y = math.log(x)
    return -0.5 * math.log(2 * math.pi) - math.log(s) - 0.5 * ((y - m) / s) ** 2

def nonoverlap(dates, h):
    """Pick dates (sorted) so each picked forecast starts at least h days after the previous one: the first available
    forecast, then the first on or after previous + h, and so on. Windows [d, d+h] then never overlap."""
    out, nxt = [], None
    for d in sorted(dates):
        if nxt is None or d >= nxt: out.append(d); nxt = d + pd.Timedelta(days=h)
    return out

def binom(hits, n, target):
    if n == 0: return None
    return float(stats.binomtest(int(hits), int(n), target, alternative="two-sided").pvalue)

def dm(d, lag):
    """Diebold-Mariano: mean of d, Newey-West variance with Bartlett weights up to `lag`, normal two-sided p."""
    d = np.asarray(d, float); n = len(d)
    if n < 2: return None
    e = d - d.mean(); v = e @ e / n
    for k in range(1, min(lag, n - 1) + 1): v += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    if v <= 0: return {"mean_diff": float(d.mean()), "n": n, "p": None}
    t = d.mean() / math.sqrt(v / n)
    return {"mean_diff": float(d.mean()), "n": n, "lag": int(lag), "stat": float(t), "p": float(2 * stats.norm.sf(abs(t)))}

def expected_date(start, h, k=MIN_EFF):
    """Date the k-th non-overlapping prediction matures if the job runs every day: start + k*h days."""
    return str((pd.Timestamp(start) + pd.Timedelta(days=k * h)).date())
