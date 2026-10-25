# v3 freeze (2026-10-25)

v3 is frozen as of 2026-10-25 and runs alongside v2. From this date both are scored only on new data, in public, in
`data/scorecard.csv`. Nothing in this folder may change. Any change means a new version (v4) with a new freeze date.
The workflow fails if any frozen file changes (see `pipeline/frozen/FROZEN_SHA256SUMS`). That list is timestamped in the
Bitcoin blockchain with OpenTimestamps: `pipeline/timestamps/FROZEN_SHA256SUMS.ots` (check with
`ots verify -f pipeline/frozen/FROZEN_SHA256SUMS pipeline/timestamps/FROZEN_SHA256SUMS.ots`).

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

Caveats, stated in advance: predictions made on consecutive days overlap heavily, so one year of daily rows is much less
evidence than its row count suggests, and one year covers a single phase of one cycle. The 365-day horizon only starts
to mature on 2027-10-25. A pass is evidence, not proof.
