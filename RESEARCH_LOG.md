# Research log (forking paths)

Every model variant tried for this project, including the ones that were dropped, with when and why. The point is that
a reader can see how many paths were explored before the published versions were chosen, and discount the backtests
accordingly. Rules for this file: entries are only added, never removed or rewritten (corrections are new entries);
git history shows every change. All times are UTC on 2026-10-25 unless stated. Times marked "file time" come from the
modification time of the research file, not from a commit. Everything here is a model, not a prediction, and not
financial advice.

Sources for the entries below: `cycle_signals/REPORT.md` (v1 research, generated 04:13), `pipeline/v2_spec.py` (v2),
`pipeline/frozen/v3/PREREG.md`, `v3_spec.md`, `band_results.csv` and `fan_backtest_v3.json` (v3), `docs/ROBUSTNESS.md`,
and this repo's git history.

## 1. Cycle Heat Score (the 0-100 score)

| when | variant | result | decision |
|---|---|---|---|
| 04:13 (report time) | **v1**: 8 signals, each scored as a percentile against all prior days, equal-weight average (weights chosen before testing) | Walk-forward score at the top: 2013 92.9, 2017 92.0, 2021 64.8, 2025 62.1. Fell to 12-25 at every cycle low. | Kept as v1 and still shown, but its weak spot is public: percentiles against all history under-react as each cycle gets less extreme. |
| 04:13 (report time) | v1 with **fitted weights** (how much hotter each signal ran at prior tops, fitted on prior tops only) | Score at the top: 2013 92.9, 2017 91.3, 2021 63.8, 2025 63.0. No better than equal weights at the two tops it missed. | Dropped: more fitted parameters, no gain. |
| 04:13 (report time) | v1 **rule count** (how many signals were at their own "hot" level) | Max within 60 days of the top: 2017 4 of 6, 2021 1 of 8, 2025 1 of 8. | Dropped as a headline: it missed the last two tops. |
| 04:02 (file time) | **v2**: percentiles against the prior 8 years only (2,922 days, at least 730 needed), signals grouped into 5 families (price structure, on-chain valuation, network usage, attention, timing) and the families averaged | In-sample (hindsight) peaks: 80.0 (2013), 91.6 (2017), 69.8 (2021), 67.2 (2025); bottoms about 20-23. Still only "warm" at the last two tops. | Kept and frozen as v2 (hash 1ed15c4c). Not tuned further after seeing these numbers. |

## 2. Heat thresholds (what counts as "hot")

| when | variant | result | decision |
|---|---|---|---|
| 04:13 (report time) | v1 **calibrated** threshold: hot = lowest score within 30 days before or 7 after any prior top; warm = hot minus 15 | The hot level moved with each new top: 88 before 2021, 68 before 2025, 62 today. Fitted on 1 to 3 tops. | Kept for v1 display only, labelled as fitted on very few points. |
| 04:02 (file time) | v2 **fixed** zones set in advance: hot 80 or more, warm 65 or more, neutral 40 or more, cool below 40 | Not fitted to any top, so they do not drift; v2 would only have said "warm" at the 2021 and 2025 tops. | Kept and frozen in v2. |

## 3. Attention signal: Google Trends vs Wikipedia

| when | variant | result | decision |
|---|---|---|---|
| 04:02 (file time) | **Google Trends** (pytrends, monthly, lagged one month) as the attention input in v1 and v2 | It is a sampled, relative index from an unofficial library, resampled on each request (SOURCES.md). On the first CI runs the score history files changed a lot between runs on the same day; re-sampled Trends values are the likely cause. | Kept in both scores, because v1 and v2 were already pre-registered with it. Swapping it now would be an unlogged change to a frozen version. |
| 10:09 (commit 0e76671) | **Wikipedia pageviews** (Wikimedia API, English "Bitcoin" article, users only, since July 2015), heat = percentile of the 30-day average against the prior 8 years | Daily, official API, stable history. Only starts in mid-2015, so it covers fewer tops. | Added as **display only**, not part of any score. Any use in a score has to come as a new pre-registered version. |

## 4. Cycle band (path of past cycles mapped onto the current one)

Rules written at 08:24 before any test (`PREREG.md`), results at 08:25 to 08:27 (file times).

| variant | mean abs error of the band middle (log10), cycles 2017 / 2021 / 2025 | decision |
|---|---|---|
| **v1 band, undampened** (each prior cycle's path at full size, rho = 1) | 0.325 / 0.152 / 0.250, mean 0.242. Middle peak 0.91x, 1.46x and 3.20x the actual top. | Dropped: overshot the last top more than 3 times. |
| **Dampened band** (paths scaled by rho = geometric mean of past peak-excess ratios, re-estimated at each halving; one parameter) | 0.292 / 0.139 / 0.190, mean 0.207. Won under the pre-registered rule (lower in 3 of 3 cycles). | Kept as v3's band and the site's forward cycle path (display only, commit f2311b3 at 10:45). But it does not beat the plain trend line (mean 0.189), and it made the 2017 top worse, so it is a shape and timing guide, not a calibrated range. |
| Linear decay of peak excess (sensitivity check only, never a candidate) | 0.289 / 0.138 / 0.165, but 2025 top timing off by +880 days | Dropped, as planned in advance. |

- 2026-10-25, 18:20 to 19:00 (file times): **Forward band pre-registration study.** The blue band (dampened rule, rho about 0.78) was re-implemented independently and reproduced the live band to within 3e-8 log10. A height-estimator study (`height_study`) and a size-law study (`height_laws`: three laws tried, S2 dropped as redundant with S1, the 2011 cycle excluded after it was seen to break the forward fits) were run before the competitors were chosen. All of their backtests are in-sample. The ensemble selection rule (SELECTION_RULE.md, 18:29) was written after the component errors were seen. The full order of events is in `pipeline/frozen/band/PREREG_BAND.md` section 13.
- 2026-10-25, about 19:15: **Band locked and pre-registered** with the author's approval (`pipeline/frozen/band/`, hash list BAND_SHA256SUMS, timestamped with OpenTimestamps). Main claim: today's blue band, next top about 2029-09-25 (hit if within 91 days) at $355K to $653K (point $481K), then a low about 2030-06-04 at $227K to $337K (point $276K). Secondary competitors frozen the same day: C1 ensemble-corrected band (top $261K to $1,210K, low $135K to $266K), C2 size law S1 (top $189K to $571K), C3 on-chain size law S3 (top $194K to $966K), C4 lengthening-cycle timing (top 2029-12-27). Benchmarks: the trend line ($291K at 2029-09-25), the unscaled past cycles, the last cycle alone. Graded by `grade_band.py` on a first-print daily price log; results pending until the top is confirmed (window opens 2028-01-02). No existing frozen file, score or fan was changed.

## 5. Fan width (the 5-95% and 25-75% bands)

| when | variant | result | decision |
|---|---|---|---|
| 04:02 (file time) | **Fixed corridor**: one formula with a constant 5-95% band | 90.2% inside overall, but only 20.8% and 43.2% after the 2015 freezes. | Dropped: it broke in the regime change where it mattered most. |
| 04:02 (file time) | **v2 robust fan**: width from the model's own past forecast errors, regressed on distance from trend, recent cycles weighted more (half-life 4 years, set before looking at results) | Too wide: 98.2% inside the 90% band, 70.7% inside the 50% band (22 freezes 2015-2025). | Kept and frozen as v2 (robust.py hash d03a0e5a). |
| 08:24 rule, 08:25 result | **v3 split-conformal scale** on the v2 fan (90% and 50% half-widths times s90 and s50, estimated only from past errors, at least 365 pairs) | Freezes 2017-2025: 50% band 70.2% to 55.8%; 90% band 99.4% to 98.6% (still too wide); no horizon bucket below 80% (rule met). Today s90 = 0.712, s50 = 0.660. | Kept and frozen as v3, scored next to v2. Not swapped into the hero chart. |

## 6. Grading and kill rules (no model change)

| when | what | decision |
|---|---|---|
| 13:14 (commit 6448540) | Forward scorecard with the promotion rule (v3 replaces v2 only after 2027-10-25 and only if it wins on all three conditions) | Frozen in `pipeline/frozen/v3/FREEZE.md`. |
| 13:26 (commit 025f759) | Statistical grading: exact binomial coverage tests, Diebold-Mariano vs a plain power-law benchmark, minimum 10 independent results | Frozen in FREEZE.md before any result. |
| this entry's commit | Kill criteria (a) coverage p below 0.01 on at least 10, (b) 8 or more weekly closes below the floor, (c) behind the benchmark with p below 0.05 on at least 12 | Frozen in FREEZE.md before any result. Checked on past data before freezing: (b) would have fired 4 times (2012, twice in 2015, late 2022), so it is strict. Kept as written at first; see the next row. |
| 2026-10-25 (this entry's commit) | Kill rule (b) changed from 8 to 26 consecutive weekly closes below the floor, both versions | Changed from 8 to 26 weeks after seeing that 8 would have fired 4 times in past bear markets (2012, 2015 x2, 2022). This choice was informed by historical data, so it is mildly in-sample; locked before any live weekly close counted. At 26 weeks it would never have fired on the 773 weekly closes since 2012 (longest run 17 weeks, from 2012-02-19). The 8-week list is kept as `FROZEN_SHA256SUMS.third.txt`. |
| 2026-10-25, about 19:15 | Blue band pre-registration: weekly-close top/low grading, path MAE vs the trend line (Diebold-Mariano, HAC lag 26), secondary comparisons Holm-adjusted, verdict PASS/PARTIAL/FAIL, append-only price and band logs, daily hash chain stamped with OpenTimestamps | Frozen in `pipeline/frozen/band/PREREG_BAND.md` before any outcome. The coverage binomial test from an earlier draft was dropped before the freeze (the band has no nominal coverage level). |

## 7. Display-only changes (no effect on any score or forecast)

- 11:26 (commit 756b74d): fan shading and forward path cut off at the floor line on the chart, for readability.
- 12:49 (commit 8ecf210): plain-language labels and (i) explainers.
- 2026-10-25 (commit with the crowd gauge): chart time axis, power-law corridor and dampened forward cycle path extended to the end of 2030 (the cycle path stops where the prior cycles' data ends, late 2030 for now); the locked fan still ends Dec 31 2028, marked by a dashed line. The live-price header block was removed (the live price stays on the chart, with a small status indicator), and the MSTR premium (mNAV) tile was removed from the site (the pipeline still writes `data/mstr.json`). New display-only "Crowd euphoria" tile (`crowd.py`, `data/crowd.json`): Fear & Greed plus annualized BTC perpetual funding. No score, fan or locked file changed.
- 2026-10-25: Wikipedia attention indicator removed from the site (display only, superseded by the crowd euphoria gauge). Data still collected for the yearly signal review (`attention.py` still writes `pipeline/cache/wiki_bitcoin.json` and `data/wiki.json`; the site no longer loads them).
- 2026-10-25: Display change only: the projection fan (the graded forecast range) was moved from the main chart to the scorecard section at the author's request, for clarity. The main chart and the README image now show the price, the trend corridor and the blue cycle band, which continues after now in the same style (past cycles scaled down; a shape guide, not a forecast) with light notes on its possible next top and the low after it, found from the data each day. The scorecard section shows the locked fan as a table (5/25/50/75/95% at Dec 31 2027 and Dec 31 2028, v2 from the frozen file `fan_2026-10-25.json` and v3 with the frozen scales; written by `pipeline/fan_locked.py` to `data/fan_locked.json`). No model change: no frozen file, score, scorecard or fan computation was changed.

## 8. Idea log (candidates for the next yearly review, 2027-10-25)

Dated ideas only; nothing here changes v1, v2 or v3. An adopted idea becomes a new locked version (v4) at the review.
The same entries are kept in `IDEAS.md`.

- 2026-10-25: Crowd-euphoria signal (funding rates + Fear & Greed) added as display only. Proposed as a v4 candidate. A shadow candidate score will be pre-registered and tracked live until the 2027-10-25 review.
- 2026-10-25: Signal review for v4 candidate. Price-stretch family (Mayer, 200W, trend multiple, Pi Cycle) is largely redundant; family averaging already limits its weight. Candidates for the 2027-10-25 review: add crowd euphoria (funding rates + Fear & Greed); consider dropping or down-weighting Pi Cycle ratio (did not fire at the 2025 top) and active addresses (weakened by ETF/exchange custody and off-chain activity); add a long-term-holder selling signal if a free, reliable data source exists. No change to v2/v3.

## How to add an entry

Write the idea and the rule for judging it here first, with the date, before running the test. Then add the result,
whether it was kept or dropped, and why. A kept idea that changes a forecast or a score becomes a new frozen version
(v4 and so on); it never edits v2 or v3.
