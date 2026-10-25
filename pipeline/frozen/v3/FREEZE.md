# v3 freeze (2026-10-25)

v3 is frozen as of 2026-10-25 and runs alongside v2. From this date both are scored only on new data, in public, in
`data/scorecard.csv`. Nothing in this folder may change. Any change means a new version (v4) with a new freeze date.
The workflow fails if any frozen file changes (see `pipeline/frozen/FROZEN_SHA256SUMS`). That list is timestamped in the
Bitcoin blockchain with OpenTimestamps: `pipeline/timestamps/FROZEN_SHA256SUMS.ots` (check with
`ots verify -f pipeline/frozen/FROZEN_SHA256SUMS pipeline/timestamps/FROZEN_SHA256SUMS.ots`). Three earlier lists stamped the same day,
before any forecast matured, are kept with their own proofs: `pipeline/timestamps/FROZEN_SHA256SUMS.first.txt` (before the
grading method below was added) `FROZEN_SHA256SUMS.second.txt` (before the kill criteria were added) and `FROZEN_SHA256SUMS.third.txt` (kill rule (b) at 8
weeks, before it was changed to 26), each with its `.ots`.

## What is frozen

| File | What it is |
|---|---|
| `PREREG.md` | Rules for the v3 research tests, written 2026-10-25 08:24 UTC before any test was run |
| `v3_spec.md` | The same rules plus the frozen v3 parameters |
| `band_test.py` | Walk-forward test of the dampened cycle band (section A) |
| `band_results.csv` | Its output |
| `fan_backtest_v3.json` | Summary of the walk-forward test of the fan width rule (section B), copied from the research output |
| `v3_hashes.txt` | SHA-256 of the files above; `cd pipeline/frozen/v3 && sha256sum -c v3_hashes.txt` |
| `withheld_sha256.txt` | SHA-256 of two research files that are not published (see below) |
| `FREEZE.md` | This note, including the promotion rule |

The v2 frozen files are `pipeline/v2_spec.py`, `pipeline/robust.py`, `pipeline/frozen/v2_freeze.json` and
`pipeline/frozen/fan_2026-10-25.json` (frozen the same day, 04:03 UTC).

Withheld files: `fan_test.py` (the fan width test script) and `v3_candidate_band.png` (a research plot) were listed in the
original hash list but are kept private because they also contain notes unrelated to this model. Their SHA-256 values are
committed in `withheld_sha256.txt` and covered by the timestamp proof, so their content is fixed as of today and can be
checked if they are ever published. The numbers they produced are in `v3_spec.md` and `fan_backtest_v3.json`.

The scripts were written to run from a folder one level below `pipeline/` (originally `pipeline/v3/`). To re-run one,
copy it to such a folder first, so the frozen outputs here are not overwritten.

## What v3 changes versus v2

v3 does not change the Cycle Heat Score or the v2 score. Both scorecard rows for a day carry the same scores.

1. **Fan width (scored).** Same fan as v2 (same frozen code, same median), but the distance from the median to the 5% and
   95% levels is multiplied by s90 = 0.712 and the distance to the 25% and 75% levels by s50 = 0.660 (the 25-75% band is
   kept inside the 5-95% band). In the backtest the v2 fan was too wide: about 99% of later prices fell inside its 90%
   band. The scales were estimated only from past forecast errors (split-conformal recalibration, PREREG section B).
2. **Cycle band (display only, not scored).** Each prior cycle's path above or below the trend is scaled down by
   rho per cycle back (rho = 0.777 at the freeze, the average shrink of successive cycle peaks above trend). The site already
   uses this dampened rule for the forward cycle path, as a shape guide. It is not part of the promotion rule.

## How the scorecard works

- Each daily run takes the latest CoinMetrics daily close (date d). If d has no rows yet, it appends one row for v2 and
  one for v3. Re-running on the same data adds nothing.
- v2 prediction: `robust.fan_params` on all closes up to d (the frozen code, refit daily as on the site), read at
  d + 30, d + 90 and d + 365 days: the 5, 25, 50, 75 and 95% levels. v3 prediction: the same, scaled as above.
- A prediction matures when the close for its target date exists. It is then scored once:
  - inside the 50% band: 25% level <= close <= 75% level;
  - inside the 90% band: 5% level <= close <= 95% level;
  - log score: natural log of the predicted density at ln(close). The density is spread evenly between the five levels
    (20%, 25%, 25%, 20% of the probability) with exponential tails holding 5% on each side, joined smoothly at the 5% and
    95% levels. Higher is better. It rewards bands that are narrow but still contain the price.
- Days the job did not run get no row. Rows are never back-filled or edited, except to fill in results.
- Target coverage: 50% inside the 50% band, 90% inside the 90% band.

## Promotion rule (set 2026-10-25, before any forward data)

`PREREG.md` only has win rules for the backtests. v3 passed both: the dampened band had lower error than the old band in
3 of 3 testable cycles (but not lower than the plain trend line), and the scaled fan's coverage was closer to 90% and 50%
with no horizon below 80% (still too wide at 98.6% inside the 90% band). `PREREG.md` has no rule for live data, so this
rule was set today, before any forward prediction matured.

v3 replaces v2 as the main fan on the site only if, at a check made no earlier than **2027-10-25** (12 months of forward
data), using every matured scorecard prediction at all three horizons:

1. v3's mean log score is higher than v2's, **and**
2. v3's share inside the 90% band is closer to 90% than v2's, **and**
3. v3's share inside the 90% band is at least 80% at every horizon with at least 30 matured predictions.

If any condition fails, v2 stays. The same rule is re-checked every 6 months after that. The rule does not change.

## Grading method (pre-registered 2026-10-25, before any result)

Added the same day as the freeze, before any forecast matured, so the way the results are graded is fixed in advance too.
The code is `pipeline/scorestats.py` and `pipeline/scorecard.py`; if the code and this note disagree, this note governs.
These tests are reported next to the promotion rule above; they do not change it.

1. **Benchmark ("base").** A plain power-law trend: log10(price) = a + b * log10(days since 2009-01-03), ordinary least
   squares on every daily close up to and including the forecast date (none after it). The band is lognormal with a
   constant width: its standard deviation is the standard deviation of that fit's residuals (log10), the same at every
   horizon. Its 5/25/50/75/95% levels are logged in `data/scorecard.csv` each day as version `base`, from the
   2026-10-24 close on, and graded like v2 and v3, except that its log score is the exact lognormal log density of
   ln(close).
2. **Coverage test.** For each version, horizon (30, 90, 365 days) and band (50%, 90%): an exact two-sided binomial test
   of the number of hits against the target rate (0.5 or 0.9). Only non-overlapping predictions count, so outcomes are
   independent: in date order, take the first logged forecast, then the first one made at least h days later, and so on.
   The number of such matured predictions is the effective sample size.
3. **Skill test.** For each horizon, a Diebold-Mariano test of the per-forecast log score difference for v2 minus base,
   v3 minus base and v3 minus v2, on all matured daily forecasts that both versions have. The variance is Newey-West
   (Bartlett weights) with lag h - 1 days, because forecasts made up to h - 1 days apart overlap. Two-sided p-value from
   the normal distribution. Reported: mean score difference (positive means the first version did better) and p-value.
4. **Minimum data.** A test is shown only when its effective sample size is at least 10. Before that the site shows "not
   enough data yet" and the date the 10th non-overlapping prediction matures if the job runs every day: 2027-08-20 (30
   days), 2029-04-11 (90 days), 2036-10-21 (365 days).
5. **Reading the results.** p below 0.05 on a coverage test means the band is probably mis-sized. A high p means no
   evidence it is wrong yet, not proof it is right. No correction is made for running many tests; with 18 coverage tests
   and 9 skill tests, about one p below 0.05 is expected by chance alone.
6. **Backtest (past data).** The same tests on one forecast per day from 2015-01-01, each using only closes up to its own
   date (`pipeline/scorecard_backtest.py`, output `data/scorecard_backtest.json`), labelled "backtest (past data)". These
   p-values are optimistic: both models were designed, and the v3 scales estimated, after seeing that history.

Caveats, stated in advance: predictions made on consecutive days overlap heavily, so one year of daily rows is much less
evidence than its row count suggests, and one year covers a single phase of one cycle. The 365-day horizon only starts
to mature on 2027-10-25. A pass is evidence, not proof.

## Kill criteria (pre-registered 2026-10-25, before any result)

Added the same day, before any forecast matured. A version (v2 or v3) is declared broken and retired in public if any one
of these happens on live data (forecasts logged from 2026-10-24 on). Retired means: the site says so next to the version,
it is never restored or re-tuned, and it keeps being logged and graded so its record stays complete. A replacement is a
new version with its own freeze date. Code: `kill()` in `pipeline/scorecard.py`, `floor_level` and `floor_weeks` in
`pipeline/scorestats.py`; if the code and this note disagree, this note governs.

- **(a) Coverage fails.** At any horizon (30, 90 or 365 days), the exact two-sided binomial test of the 90% band (method
  item 2 above) gives p < 0.01 on at least 10 independent (non-overlapping) matured forecasts.
- **(b) Price breaks the floor.** 26 or more consecutive weekly closes below the power-law floor. Weekly close = the daily
  CoinMetrics close dated each Sunday (UTC), from 2026-10-25 on. Floor at that date = the benchmark's trend (method item 1,
  OLS on closes up to and including that date) shifted down by the 5% quantile of that fit's log10 residuals, the orange
  floor line on the site. Both versions use this trend, so (b) retires v2 and v3 together.
- **(c) Loses to the benchmark.** At any horizon, the Diebold-Mariano test of version minus base (method item 3) has a
  negative mean log score difference with p < 0.05 over at least 12 independent forecasts (effective sample size as in
  item 2).

The site shows each criterion's live status ("not triggered" or "triggered") and, for context only, whether it would have
fired on past data. Checked on 2026-10-25 before freezing, with the same code: on the 773 weekly closes from 2012-01-01,
(b) at 26 weeks would never have fired; the longest run below the floor was 17 weeks (from 2012-02-19).

Amendment (2026-10-25, before any live weekly close counted): (b) was first frozen at 8 weeks. On past data 8 weeks would
have fired 4 times (17 weeks from 2012-02-19, 16 from 2015-03-22, 15 from 2015-07-19, 9 from 2022-11-13), so it was changed
to 26 weeks. This choice was informed by historical data, so it is mildly in-sample. The 8-week version stays on record in
`pipeline/timestamps/FROZEN_SHA256SUMS.third.txt`. On the backtest (one forecast per day from 2015), (a) and (c) would not
have fired; the closest case is v2 at 365 days, behind the benchmark with p 0.0002 but only 11 independent forecasts.
