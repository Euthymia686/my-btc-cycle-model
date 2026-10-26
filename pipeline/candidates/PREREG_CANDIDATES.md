# Shadow signal candidates: pre-registration (written 2026-10-26 10:15 UTC, before any forward data)

Research only. Nothing here feeds the Cycle Heat Score, v1, v2, v3, the scorecard, the blue band test or any graded result.
The frozen files (`pipeline/frozen/FROZEN_SHA256SUMS`, `pipeline/frozen/band/BAND_SHA256SUMS`) and the daily chain record
(`scripts/stamp_daily.py`, PREREG_BAND.md section 9) are unchanged.

This file and `candidates_spec.py` (the exact formulas and the review rule, as code) are hash-locked in
`CANDIDATES_SHA256SUMS`. That list is pinned in the workflow (the run fails if it changes) and timestamped in the Bitcoin
blockchain with OpenTimestamps: `CANDIDATES_SHA256SUMS.ots` (check with
`ots verify -f pipeline/candidates/CANDIDATES_SHA256SUMS pipeline/candidates/CANDIDATES_SHA256SUMS.ots`).
It is stamped on its own, not in the daily chain, because adding files to the chain record would change a pre-registered list.
Any later change is logged in `AMENDMENTS.md` with a new hash and stamp, or is a new pre-registration.
If this file and the code disagree, this file governs.

## 1. Honest starting point

- The author already knows the published history of these signals: the Puell Multiple was very high near the 2011, 2013 and
  2017 tops and lower at the 2021 top; futures leverage built up into 2021; liquidity is widely claimed to drive bitcoin.
  The history test below is therefore **in-sample** and weak evidence. It can rule a candidate out; it cannot prove one.
- There are only about 4 cycle tops (2013, 2017, 2021, 2025; 2011 is too early for every candidate). With so few
  events, any rule tuned to them will look good. To limit that: one formula per candidate, the same causal percentile and
  the same zones as v2, no tuning of windows, and the formulas were written before the backfill was computed.
- The forward year (2026-10-26 to 2027-10-24) will most likely contain no cycle top. So the forward test mostly checks that
  the data arrives reliably and that the candidate does not raise false alarms. That is why the bar to adopt is high and
  why an adopted candidate would only enter a new frozen v4, never v2 or v3.

## 2. The candidates

Heat for every scored candidate: percentile (0 to 100) of the day's raw value against the strictly prior 2,922 daily
values, needing at least 730 prior values (the frozen v2 `window_pct`, imported unchanged). Zones as v2: hot >= 80,
warm >= 65, neutral >= 40, cool < 40. Each candidate is its own family.

| # | Family | Raw value for close date d | Source and terms | Scored in shadow? |
|---|---|---|---|---|
| 1 | `miner_income` (Puell Multiple) | CoinMetrics `IssTotUSD` on d / mean of `IssTotUSD` over the 365 days ending d (needs all 365) | CoinMetrics Community API, free, CC BY-NC 4.0 (same terms as the existing CoinMetrics data). Subsidy only, no fees (fee revenue in USD is not in the free tier) | Yes |
| 2 | `leverage` (futures open interest vs market cap) | L = BTC-equivalent CME open interest / CoinMetrics `SplyCur`, where OI = 5 x CME Bitcoin (CFTC code 133741) + 0.1 x CME Micro Bitcoin (133742, 0 before 2021-05-04), from the latest weekly CFTC report dated <= d - 4 and at most 21 days old. Raw signal = L / median of L over the 365 days before d (needs >= 300 values) | CFTC Commitments of Traders (Legacy, futures only), public domain US government data, via publicreporting.cftc.gov | Yes |
| 3 | `liquidity` (skeptical test) | NL = WALCL - WTREGEN - 1000 x RRPONTSYD ($ millions; values usable from d - 2, d - 2, d - 1; max age 14, 14, 10 days; RRP = 0 when missing before 2013-09-23). Dollar = DTWEXBGS usable from d - 7 (max age 21 days). g_nl = ln(NL / NL 365 days earlier), g_usd = ln(dollar / dollar 365 days earlier). Heat = mean of the percentile of g_nl and the percentile of -g_usd (needs both) | FRED (St. Louis Fed) series from the Federal Reserve H.4.1 and H.10 and the New York Fed; public domain data, no API key | Yes |
| 4 | `etf_flows` (spot bitcoin ETF net flows) | Not computed: no free source found whose terms allow republishing (Farside: all rights reserved; SoSoValue: terms forbid redistribution and scraping; issuer files cover one fund each and restrict data use) | None yet | No, display only, and only if a terms-compliant source is found |
| - | `oi_crypto` (diagnostic) | OKX all-BTC-contracts open interest in USD (daily, last 180 days available) and a Deribit BTC futures/perpetual snapshot, / CoinMetrics market cap | OKX and Deribit public endpoints. Raw files stay private (Actions cache); only the derived ratio is published | No, diagnostic only |

Why "global" liquidity is US-only: a timely, free global M2 series does not exist (FRED's non-US money series are
discontinued or months late). Fed net liquidity plus the broad dollar index is the free, documented proxy. Hot means
liquidity is growing and the dollar falling. The common claim is that this drives bitcoin up; it does not obviously mark
tops. It is tested because it is popular, with the same bar as the others, and the expectation is that it fails.

Why leverage uses CME and not exchange perpetuals: CME (via the CFTC) is the only free open-interest history long enough
for the 2,922/730-day percentile (from 2018-04). Heat first exists in early 2021, so only the 2021 and 2025 tops and the
2022 low are testable. Exchange open interest (OKX, Deribit) has only ~180 days of free history; it is logged as a
diagnostic from today, so a future pre-registration could test it.

Revisions: FRED and CoinMetrics revise history. The backfill uses today's vintage (revised data), which flatters it. The
forward log keeps the first value printed each day.

## 3. Shadow Heat Score variants

Each is the plain mean of the available family heats, needing >= 3 families, like v2. The five v2 family heats come from
`pipeline/out/score_v2_history.csv` (frozen v2 code).

- `shadow_all` = v2's five families + miner_income + leverage + liquidity (8 families).
- `shadow_puell`, `shadow_lev`, `shadow_liq` = v2 + that one candidate (6 families).

ETF flows and exchange open interest are never in any shadow score.

## 4. Daily log (forward, from close date 2026-10-26)

- `data/candidates/shadow_log.csv`: one row per CoinMetrics close date, append-only, never edited (enforced by
  `scripts/check_append_only.py`). The row for close d is written once: when all three scored candidates have a value, or at
  the daily-run deadline (12:00 UTC on d + 1, the same deadline as the scorecard gate) with the missing ones left empty and
  named in the `missing` column. Columns: raw values, heats, v2 score and family heats as read that day, the four shadow
  scores, and the source dates used.
- `data/candidates/shadow_backfill.csv`: history computed once on 2026-10-26 from today's data, every row flagged
  `in_sample = 1`. Written once.
- Each day `scripts/stamp_candidates.py` writes a separate chain record (`pipeline/timestamps/candidates/`) with the
  SHA-256 of the log, the backfill and this pre-registration, and stamps it with OpenTimestamps.
- A candidate feed failing never blocks or changes the official run, the scorecard or the daily chain.

## 5. What counts as "present" on a forward day

A candidate is present on close date d if its heat is in the row for d in `shadow_log.csv`. A day with no row, or with an
empty heat, counts as missing. Coverage = present days / all calendar days from 2026-10-26 to 2027-10-24.

## 6. Review on 2027-10-25 (or later; then every 6 months, as v3 FREEZE.md)

Run `candidates_spec.evaluate` on: all heats (backfill + forward), the forward log, the v2 score and families from
`score_v2_history.csv`, and the cycle tops and lows from `pipeline/lib.find_tops_bottoms` on the CoinMetrics close.
A top counts if the candidate has a heat on that day and 60 days have passed after it; a low counts likewise with 30 days.

Checks, for each scored candidate:

- **A. Reliable:** forward coverage (section 5).
- **B. History (in-sample):** at least 2 tops count; at every counted top the highest heat within 60 days either side is
  hot (>= 80); at every counted low the average heat within 30 days either side is cool (<= 40).
- **C. Not a copy:** Spearman rank correlation with the v2 price_structure family heat, over all common days, below 0.80 in
  absolute value.
- **D. Helps the score:** the score with the candidate added (shadow_puell / _lev / _liq) reaches at least as high as v2
  around the counted tops (average of the 60-day-window maxima), and is no more than 2 points warmer than v2 around the
  counted lows (average of the 30-day-window means).
- **E. No forward false alarm:** in the forward year, no run of 30 or more consecutive days where the candidate is hot
  (>= 80) while the v2 score is cool (< 40).
- **F. Terms:** the source still exists and its terms still allow this use (checked by hand and written in the review).

Verdict:

- **DROP** if coverage is below 75%, or B fails, or C fails, or F fails. A dropped candidate is not re-tested with a
  tweaked formula unless that is a new pre-registration that says so.
- **ADOPT INTO A v4 CANDIDATE** only if all of these pass: coverage >= 90%, B, C, D, E and F. This does not change v2 or v3.
  It means the candidate may be included in a new v4, frozen on its own date with its own hash and stamp, which is then
  scored only on data after that freeze. If a confirmed cycle top falls inside the forward year, the candidate must also
  have been at least warm (>= 65) within the 60 days before it, or it cannot be adopted.
- **KEEP TRACKING** otherwise. Re-checked every 6 months with the same rules on the longer forward log.
- `shadow_all` is reported but is not separately accepted or rejected; it follows the individual verdicts.
- ETF flows: no scoring decision is possible at this review (history starts 2024-01, less than one cycle). The review only
  records whether a terms-compliant source was found. Scoring could be considered no earlier than after a full cycle,
  through a separate pre-registration.

When in doubt, the status quo stays: v2 and v3 continue unchanged.

## 7. Files

| File | What it is |
|---|---|
| `PREREG_CANDIDATES.md` | This document |
| `candidates_spec.py` | The formulas and the review rule as code |
| `CANDIDATES_SHA256SUMS` | SHA-256 of the two files above; `cd pipeline/candidates && sha256sum -c CANDIDATES_SHA256SUMS` |
| `CANDIDATES_SHA256SUMS.ots` | OpenTimestamps proof of that list |

Not locked (operational, may change without changing the rules): `candidates.py` (fetching, caching, writing the log),
`scripts/stamp_candidates.py`, and the site display.
