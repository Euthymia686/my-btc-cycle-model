# Height-correction selection rule (DRAFT): written 2026-10-25T18:29Z

**Disclosure.** This rule text was written at 2026-10-25T18:29Z, after the owner's instruction (t54u). Before that, the walk-forward height study had already been run once (height_study.py, three variants: main, no2011 and lastpair, about 18:20–18:27Z), and its error tables had been seen.
- To limit selection after the fact, the rule below follows the owner's own wording: an equal-weight geometric mean of **all** estimators, with exclusions only by sanity check.
- The estimator list is exactly the one already coded in `height_study.py` before this rule was written. Nothing is added, dropped or reweighted because of backtest errors.
- The "main" variant (decay = log-linear fit over all prior cycles, including the 2010–12 data-start cycle) is the one coded first. It is used as is. The other two variants are reported as sensitivity only.

## Estimators (fixed list)
Each estimator uses data strictly before the origin (closes through origin − 1 day).

**Top:**
- **T1 band:** middle of the dampened band (live rule) at its peak.
- **T2 trend multiple:** trend × 10^M, where M = the log10 multiple of each prior top over the causal trend, projected by log-linear decay in cycle number.
- **T3 ceiling:** trend × 10^q95 of residuals.
- **T4 on-chain:** realized price (its own power-law fit, data since 2011) × MVRV at prior price tops, projected by log-linear decay.
- **T5 peak ratio:** previous top × 10^R, where R = log10 of successive top ratios, projected by log-linear decay.

**Low:**
- **L1 band:** band middle low after the band peak.
- **L2 drawdown decay:** ensemble top × (1 − d), where d = prior drawdown depths (completed cycles only), projected by log-linear decay.
- **L3 floor:** trend × 10^q05.
- **L4 realized price:** projected realized price × the mean MVRV at prior lows.
- **L5 low residual:** trend × 10^(mean residual of prior lows).

**Benchmarks only (never in the ensemble):** the previous top unchanged, and the trend line.

**Dates.** The top estimators are evaluated at the band's own peak date and the low estimators at the band's own post-peak low date. Timing stays with the band. If the band cannot be computed, the timing-rule dates are used instead: halving + mean of the last two halving-to-top gaps, and top + mean of the last two top-to-low gaps.

## Sanity checks (the only exclusions)
- (a) The estimate cannot be computed (missing data, fewer than 2 prior points for a decay fit).
- (b) **Top only:** the estimate is below the causal trend line at the band peak date.
- (c) **Low only:** the estimate is at or above the ensemble top.

The ensemble needs at least 3 included estimators. With fewer, there is no corrected band and the uncorrected band is shown, labeled as uncorrected.

## Combination
- ensemble top = geometric mean (equal weights) of the included T-estimators;
- ensemble low = geometric mean of the included L-estimators. L2 uses the ensemble top.

## Range (stated in advance)
- w = sqrt(s_m² + e_h²), in log10, where:
  - s_m = the sample SD (ddof = 1) of log10 of the included estimates;
  - e_h = the RMS of the ensemble's walk-forward log10 errors over all completed backtest cases (cycles 2017 onward, both origins) available at the origin. Lows count only once top + 104 weeks has passed.
- Range = ensemble × 10^(±w).
- The min–max of the included estimates is also shown, but it is not graded.

## Corrected band (shape and timing kept, height rescaled)
Work in log10. The uncorrected band is lo, md, hi. Anchors are the band's peak date tp and post-peak low date tl.
- **Offset c(t):**
  - 0 before the next halving H (2028-04-11);
  - log10(ensemble top) − md(tp) at tp;
  - log10(ensemble low) − md(tl) at tl;
  - stays at the tl value after tl.
- **Interpolation:** between consecutive anchors (H → tp → tl), use half-cosine interpolation: f(u) = (1 − cos(πu))/2, where u is the fraction of the time elapsed.
- **Width factors:**
  - s_hi(tp) = w_top / (hi − md)(tp) and s_lo(tp) = w_top / (md − lo)(tp);
  - the same at tl with w_low;
  - both are 1 before H, and interpolated the same way as c.
- **Corrected band:**
  - md' = md + c
  - hi' = md' + s_hi·(hi − md)
  - lo' = md' − s_lo·(md − lo)
- So at tp the corrected band is exactly ensemble top × 10^(±w_top), and at tl it is exactly ensemble low × 10^(±w_low).

## Update rule (locked; no human changes)
Every daily run recomputes everything above, with the same code, from data through yesterday:
- the trend refit;
- rho;
- the band shape;
- the realized-price fit;
- the MVRV values;
- prior tops (highest weekly close in each cycle's window so far);
- prior lows (completed cycles only);
- the sanity checks, the ensemble, w (e_h changes only when a backtest case completes) and the corrected band.

The only inputs are the CoinMetrics daily data and the fixed 2028-04-11 halving estimate. No parameter can be set by hand.

## Grading
Three versions are graded side by side under PREREG_BAND.md outcomes (a)–(d):
1. the frozen corrected snapshot at the freeze day;
2. the rule-driven live corrected band (daily append-only log);
3. the uncorrected band snapshot.

The ensemble's competing components (T1–T5, L1–L5) and the benchmarks are logged and graded as separate claims. None is promoted after the fact.
