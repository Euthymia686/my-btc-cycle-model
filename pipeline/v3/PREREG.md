# v3 candidate - pre-registered rules (written 2026-10-25 08:24 UTC, before running any test)

Research only. v2, robust.py, frozen/* and the published hero are unchanged.

## A. Dampened cycle band
- Trend: power law log10 p = a + b log10(days since 2009-01-03), fitted ONLY on data up to the halving H_k that starts the projected cycle k.
- Residual r(t) = log10 p - trend (that fit). Cycle j = [H_j, H_{j+1}); cycle 0 = data start (2010-07-18) .. 2012-11-28.
- Peak excess E_j = max r(t) in cycle j (completed cycles only, all before H_k).
- Decay rho_k = geometric mean of successive ratios E_j / E_{j-1} over all completed pairs before H_k  (ONE parameter, re-estimated per cycle).
- Dampened path of prior cycle j mapped to cycle k: rho_k^(k-j) * r_j(same day since halving). Whole path scaled (amplitude dampening).
- Band = same construction as baseline (two prior cycles, +-10 d window, mid = mean of medians, lo/hi = min/max, 15-day centred smoothing).
- Baseline = identical except no scaling (rho = 1).
- Sensitivity only (not the candidate): linear regression of E_j on j, predicted E_k / E_j as the scale.
- Testable cycles: 2016->(2017 top), 2020->(2021 top), 2024->(2025 top). 2013 is NOT testable: it needs two prior full cycles.
- Metrics per cycle: top price error (log10 band-mid peak vs actual top), top timing error (days), MAE of log10(mid) vs log10(price) over the cycle, share of days inside lo-hi.
- Win rule: candidate wins only if MAE is lower in at least 2 of 3 cycles AND lower on average, and top price error is lower on average.

## B. Fan width rule (walk-forward split-conformal recalibration)
- Base fan = robust.fan_params frozen at each 1 Jan / 1 Jul 2015-2025 (unchanged code).
- For each realised (freeze, day) pair, normalised error z = (log p - median) / (side-specific half-width of the 90% [or 50%] band).
- At freeze F, scale s90 = 90th percentile of |z90| over pairs whose day <= F (only past information); s50 likewise with 50%. Requires >= 365 pairs, else s = 1.
- Calibrated fan: median unchanged, 90% / 50% half-widths multiplied by s90 / s50 (25-75 also clipped to stay inside 5-95).
- Scored on freezes from 2017 on (where s is estimable) vs the raw fan on the same freezes: pooled in90/in50, by horizon year, worst freeze, tail breaches.
- Win rule: closer to 90/50 pooled, AND no horizon bucket with in90 < 80%.
