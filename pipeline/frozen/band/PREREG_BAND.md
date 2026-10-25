# PREREG_BAND: pre-registered public test of the blue cycle band, with three graded competitors

**Status: FINAL TEXT FOR THE OWNER'S APPROVAL. Not yet committed, frozen, timestamped or published.**
It locks nothing until the owner approves it. On approval, the freeze is run on the approval day (section 15.1). This file, the frozen code and the snapshots are then committed together with `BAND_SHA256SUMS`, and that list is stamped (section 9).
Drafted 2026-10-25 from commit 307abb5. Lock-prep revision on 2026-10-25, about 19:00Z: sections 11 to 16 were added, and earlier sections were edited where those decisions touch them. The live site, the existing frozen files and the graded fan are not touched.
Not financial advice: the band is a historical shape guide, not a price target.

---

## 0. One-paragraph version

On a freeze day (proposed: 2026-10-25, data through 2026-10-24) we save one copy of the blue band's forward path in a file. The band is a low, middle and high value for every calendar day up to 2030-11-01. We hash that file and anchor it to Bitcoin with OpenTimestamps. That locked copy is what gets graded. We then check four things:

1. **Timing:** did the next cycle top land within ±13 weeks of the band's peak date (2029-09-25)?
2. **Height:** was the top inside the band's range at that peak ($355K–$653K)?
3. **Low:** was the low after the top inside the band's low range ($227K–$337K on 2030-06-04)?
4. **Path:** over the whole path, did the band beat the plain power-law trend and the other simple benchmarks?

There is only one cycle to judge, so items 1–3 are pass/fail evidence and not statistics. Only the path test gets p-values. Everything about how it is graded is fixed now and cannot change.

**Competitors.** Three other forecasts are frozen on the same day and graded with the same rules (section 12). They are secondary claims. The blue band stays the main claim.
- **C1:** the equal-weight ensemble-corrected band.
- **C2:** the S1 size law.
- **C3:** the S3 on-chain size law.

A fourth, **C4**, is a simple "lengthening cycle" timing rule (section 11.4). The main claim is graded first, and the competitors cannot rescue or replace it after the fact.

---

## 1. What the band is (as live at 307abb5)

The source is `pipeline/forward_band.py`, which writes `data/hero_fwd.json` (weekly, Mondays). The site draws it from there (`hero.js`, and `hero_png.py` for the PNG). It is labeled "display only, not scored".

1. **Trend:** a power-law OLS fit, log10(price) on log10(days since genesis). It uses **all** data and is refit every day. Today a = −16.3413 and b = 5.6384.
2. **Residual:** r(t) = log10(price) − trend.
3. **Cycle starts:** 2012-11-28, 2016-07-09, 2020-05-11 and 2024-04-20, plus an assumed **2028-04-11** (`HORIZON.year`-04-11). The pseudo-cycle that starts at the data start (2010-07-18) counts only for rho.
4. **Dampening:** E_j is the peak residual of each completed cycle (data start, 2012, 2016 and 2020 cycles). rho is the geometric mean of E_j/E_(j−1). Today **rho = 0.77725**. It is recomputed every day.
5. **Daily values:** for each date in cycle k, take the residuals of cycles k−2 and k−1 at the same day-since-halving, ±10 days. Scale them by rho^(k−i). Then:
   - low = min, high = max;
   - middle = mean of the two medians;
   - apply a 15-day centered rolling mean (min_periods=1), then add the trend back.
   There is **no cap** on the ±10-day window at a cycle boundary.
6. **Display only:** the site blends the band into the fan over the first 8 weeks after "now". It also finds the peak and the low again on every page load.

**Hash coverage (step 1 finding).** The band is **not** covered by either frozen list.
- `FROZEN_SHA256SUMS` (sha 96f83fc4…, checked in the workflow env `FROZEN_LIST_SHA256`) covers only these: v2_spec.py, robust.py, v2_freeze.json, fan_2026-10-25.json and the v3 files (PREREG.md, v3_spec.md, band_test.py, band_results.csv, fan_backtest_v3.json, FREEZE.md, v3_hashes.txt, withheld_sha256.txt).
- `v3_hashes.txt` covers the v3 files only.
- `forward_band.py`, `charts.py`, `lib.py`, `hero.js`, `hero_png.py` and `hero_fwd.json` are not hashed anywhere.

`v3_spec.md` section A describes the dampened rule in words, with rho = 0.777, and `band_test.py` scored it causally in 2026. The live code differs from that description in three ways:
- (i) the trend is a full-data daily refit, not a fit through each halving;
- (ii) there is no window cap (band_test uses `w.index < H[j+1]`);
- (iii) rho moves a little every day.

**So the live band drifts every day, and none of it is locked.** At the same 2029 peak date the forward peak value moved like this:

| Run date | Band peak |
|---|---|
| 2025-10-25 | $497K |
| 2026-04-25 | $491K |
| 2026-07-25 | $486K |
| 2026-10-25 | $481K |

The "low after the peak" also moved, from $343K (2030-04-16, as of 2026-04-25) to $276K (2030-06-04, today), because the band's end moves forward by one day each day.

**Freeze decision (proposed).** Freeze a verbatim copy of the live rule plus one snapshot it produced. Leave the live code unchanged.
- The cap is left out. It changes the live path by at most 0.014 log10, and only between 2028-02-04 and 2028-04-17. It does not affect the 2029 peak or the 2030 low.

---

## 2. Exactly what gets frozen

The files go in a new folder, `pipeline/frozen/band/`. Their hashes go in a new `BAND_SHA256SUMS`, which gets its own .ots. Its own sha is pinned in the workflow env exactly as `FROZEN_LIST_SHA256` is.

| File | Content | sha256 (dry run 2026-10-25; final values in BAND_SHA256SUMS) |
|---|---|---|
| `PREREG_BAND.md` | this document | in BAND_SHA256SUMS |
| `SELECTION_RULE.md` | the ensemble rule for C1, copied verbatim. Its "Grading" section is superseded by section 12.4 here | 1ca54a5d…23db (unchanged) |
| `band_freeze.py` | the one-time generator of the band snapshot. The rule is copied verbatim from `forward_band.py::damp_band` | in BAND_SHA256SUMS |
| `bandlib.py` | an independent implementation of the same rule. It reproduces the snapshot to within 2e-8 log10. Used for the live band in the daily log and for C1 | in BAND_SHA256SUMS |
| `corrected_rule.py` | C1: the ensemble-corrected band, implementing SELECTION_RULE.md | in BAND_SHA256SUMS |
| `laws_rule.py` | C2/C3: the S1/S3 size laws; C4: the lengthening timing rule | in BAND_SHA256SUMS |
| `competitors_freeze.py` | one-time generator of the C1 snapshot and `competitors_freeze.json` | in BAND_SHA256SUMS |
| `band_log_daily.py` | daily append-only records: price log, band log, the one-time S1-R/S3-R re-run, the halving date | in BAND_SHA256SUMS |
| `grade_band.py` | all grading in sections 4–7 and 11–12, writing `data/band_grades.json` | in BAND_SHA256SUMS |
| `band_snapshot_<T0>.csv` | band and benchmark rows, daily from T0 to 2030-11-01. Columns: band_lo/mid/hi, unscaled2_lo/mid/hi, lastcycle_mid, trend_line, trend_floor_5, trend_ceiling_95, constw_lo/hi | dry run 2026-10-25: f33d31a0e65becb471b1a85fbc21f5c9761c13242c1cf329cabb98d19aa0a26d |
| `band_freeze.json` | parameters, derived peak/low/windows, and hashes of the input and the code (relative paths) | in BAND_SHA256SUMS |
| `corrected_band_snapshot_<T0>.csv` | C1 rows (corr_lo/mid/hi), daily T0 to 2030-11-01 | in BAND_SHA256SUMS |
| `competitors_freeze.json` | C1–C4 locked values, the S1 sensitivity table, and hashes of the input and the code | in BAND_SHA256SUMS |
| `lib.py`, `charts.py` copies | the helpers the rule calls (trend fit, halving dates, data loader) | in BAND_SHA256SUMS |
| input data hash | sha256 of `pipeline/cache/coinmetrics.json` on the freeze day, recorded in both JSON files. The full file is archived by `snapshots/` and MANIFEST.csv | recorded at freeze |

`BAND_SHA256SUMS` lists every file above. Its own sha256 is pinned in the workflow env as `BAND_LIST_SHA256`, the same way `FROZEN_LIST_SHA256` pins the existing list, so any change fails CI.

**Frozen parameters** (from the dry run, data through 2026-10-24):
- rho = 0.777252
- trend a = −16.3413, b = 5.6384
- residual quantiles q05/q50/q95 from the same fit
- window ±10 d, smoothing 15 d centered
- assumed 2028 halving 2028-04-11
- constant-width half-width 0.09477 log10

**Derived and locked:**

| Item | Value |
|---|---|
| Band peak (middle) | **2029-09-25: $481,434 (range $355,061–$653,032)** |
| Band low after peak | **2030-06-04: $276,258 (range $226,609–$336,640)** |
| Implied drawdown | 42.6% |
| Timing window | **2029-06-26 to 2029-12-25** |
| Rest of the current cycle | middle bottoms at $93.6K on 2026-11-07, then rises to $218K by 2028-03-12 |

The snapshot regenerated from `band_freeze.py` matches the earlier independent build (`bandlib.py`) exactly. The earlier build itself matches the live `hero_fwd.json` to within 3e-8 log10.

---

## 3. Hypotheses (stated before any outcome data)

- **H1, timing:** the cycle-4 top (highest weekly close, defined in 4a) falls within ±91 days of the band's peak date, 2029-09-25.
- **H2, height:** that top's weekly close lies inside [band_lo, band_hi] on the band peak date, $355K–$653K.
- **H3, low:** the lowest weekly close in the 104 weeks after the top lies inside [band_lo, band_hi] on the band-low date, $227K–$337K.
- **H4, path:** from 2026-11-01 to 2030-10-27, the band middle has a lower mean absolute log10 error on weekly closes than the power-law trend line (primary). A secondary check: the band holds a larger share of weekly closes than a trend-centered band of the same average width.

**Null for H1–H3:** the band carries no information beyond the benchmarks in section 5.
**Null for H4:** equal predictive accuracy.

---

## 4. Recorded predictions and outcomes

**Primary prediction record:** the frozen snapshot (section 2). It is graded as it is, forever.

**Secondary record: a daily append-only log, `data/band_log.csv`.** This is new. One row per run with:
- run_utc and data_to;
- rho, a and b;
- band peak date, mid, lo and hi;
- band low date, mid, lo and hi;
- band lo/mid/hi at fixed target dates: every quarter-end from 2027-03-31 to 2030-09-30, plus 2029-09-25 and 2030-06-04.

Rows are never edited. The log is stamped daily (section 9). It measures **drift** (how much the live band moved) and allows a secondary, fully causal grading of each day's forecast. It never replaces the primary grade.

**Price used:** the first-print daily close log `data/band_prices.csv` (section 11.1). Its primary source is the CoinMetrics community `PriceUSD`, with a fixed fallback.

A **"weekly close"** is the daily close dated Sunday. Under the CoinMetrics convention, that is the price at **Monday 00:00 UTC** (the end of Sunday UTC). This is the same rule as the fan's kill rule (b) and every backtest here.

### 4a. Top timing (primary)
- **Top T\*** = the date of the highest weekly close in the window **2028-01-02 to 2031-03-30**. That is 101 days before to 1,084 days after the assumed halving, the same window used in the backtest.
- **Final call:** the run on 2031-04-06, using data through 2031-03-30. This is a fixed date, so there is no judgment call.
- **Provisional notice (not a grade):** post "top provisionally confirmed" when 52 weeks have passed with no higher weekly close *and* some weekly close has been at least 50% below it. Applied to past cycles, this rule confirmed 2013-12, 2017-12, 2021-11 and 2025-10 (on 2026-10-04) with no false calls. A looser rule (−40% and 26 weeks) falsely confirmed 2013-04 and 2021-04.
- **Hit:** |T\* − 2029-09-25| ≤ 91 days. Also reported: the signed error in days, and the error measured from the *actual* halving date (the halving-relative readout, secondary; section 11.3).
- **No-cycle outcomes** are classified and graded as set out in section 11.5. T\* is always defined, so there is no "void" result.

### 4b. Top height (primary)
- **Hit:** the weekly close at T\* lies within $355,061–$653,032.
- **Score:** log10(actual top / $481,434).

### 4c. Post-top low (primary)
- **L\*** = the lowest weekly close in the 104 weeks after T\*. Final at T\* + 104 weeks.
- **Hit:** L\* lies within $226,609–$336,640.
- **Also reported:** log10 error against $276,258, and predicted vs actual drawdown (42.6% predicted).
- If T\* falls after 2030-06-04 (after the band's low date), H3 is recorded as a **miss**. The band's ordering was wrong.

### 4d. Path fit (primary H4 plus secondary measures)
- **Sample:** every weekly close from 2026-11-01 to 2030-10-27, 209 weeks, compared with the snapshot value for that date.
- **Primary measure:** mean |log10(close) − log10(band_mid)| vs the same for trend_line.
- **Coverage:** share of closes inside [band_lo, band_hi] vs inside [constw_lo, constw_hi].
- **Fixed horizons:** absolute log10 error at 26, 52, 104, 156 and 208 weeks:

| Weeks | Date | Band (lo – mid – hi) | Trend line |
|---|---|---|---|
| 26 | 2027-04-25 | $115K – $158K – $232K | $144K |
| 52 | 2027-10-24 | $145K – $162K – $186K | $168K |
| 104 | 2028-10-22 | $242K – $272K – $309K | $225K |
| 156 | 2029-10-21 | $333K – $465K – $651K | $297K |
| 208 | 2030-10-20 | $276K – $288K – $312K | $386K |

---

## 5. Benchmarks (all locked in the same snapshot file)

| Benchmark | What it is | Locked values |
|---|---|---|
| Power-law trend alone | trend_line (median residual), plus the 5% floor and 95% ceiling | $290,860 at 2029-09-25; floor at the low date $181,411 |
| Repeat last cycle, unscaled | lastcycle_mid: the 2024 cycle's residual path, no dampening | peak 2029-07-13 at $397K; low 2030-06-20 at $198K |
| Unscaled two-cycle band (rho = 1) | the old undampened rule | peak 2029-09-25 at $595K; low 2030-08-02 at $232K |
| Constant-width band | trend_line × 10^(±0.09477), the same average log width as the band | covers weeks 2026-11 to 2030-10 |
| Halving + ~540 d timing rule | assumed halving + the mean of the last two cycles' halving-to-top days (552 and 533) | **2029-10-05** (the window is ±91 d around it, for comparison) |
| Drawdown rule (for the low) | actual top × (1 − mean prior drawdown) | computed once T\* is known |

---

## 6. Statistical tests, alpha and minimum samples

- **Alpha = 0.05, two-sided**, for the two formal tests below. No other test is used for any primary verdict.
- **Diebold-Mariano (H4):**
  - loss = weekly absolute log10 error;
  - d_t = band loss − trend loss;
  - HAC (Newey-West) variance with lag 26 weeks, Harvey-Leybourne-Newbold small-sample correction.
  - **Minimum 104 weekly closes** before any DM result is called significant. Interim values are shown, clearly labeled.
- **Coverage (secondary):**
  - weekly closes are heavily autocorrelated, so use effective n: thin to every 13th week, giving about 16 points over the full sample;
  - test band vs constant-width band with an exact McNemar test;
  - each band's coverage share is **reported descriptively only**. *(Amended before the freeze: the earlier draft promised a binomial test against "the share implied by its own range width". The band is the min/max of two scaled cycles and has no nominal coverage level, so that test has no defined null. It is dropped rather than invented later.)*
  - **Minimum 8 thinned points**, about 2 years.
- **Timing (H1), permutation/random-phase:** if the top were uniformly random within the 1,186-day top window, a ±91-day window would catch it with probability **p0 ≈ 183/1,186 ≈ 0.154**. A single hit therefore has p ≈ 0.154. **It cannot reach 0.05 on one cycle by design**, and that is stated up front.
  - Across cycles: a binomial test on the pass record, combining the 3 hindsight cycles with the 1 live cycle as separate lines (never pooled into one p-value).
- **Honest note on n = 1.** There is one top and one low per cycle. H1–H3 are **pass/fail evidence that adds up across cycles**, not significance tests. A pass in 2029 is one data point. Only the path test (H4) has enough within-cycle data for p-values, and even that is autocorrelated, hence the HAC/effective-n corrections.

---

## 7. Verdict, kill and replace rules

**Verdict per cycle (pre-registered):**

| Verdict | Condition |
|---|---|
| **PASS** | H1, H2 and H3 all hit, and the band's path MAE ≤ the trend's |
| **PARTIAL** | H1 hits but H2 or H3 misses (the shape is right, the size is wrong) |
| **FAIL** | H1 misses, or DM shows the band is *significantly worse* than the trend (p < 0.05, ≥ 104 weeks) |

FAIL takes precedence. If H1, H2 and H3 all hit but the band's path MAE is above the trend's, the verdict is PARTIAL. The verdict is computed by `grade_band.py`, not by hand.

**Early kill signals.** These are dated, and each one is a public label, not a deletion.
- **K1, height falsified:** any weekly close above $653,032 before 2029-12-25 means the top is above the range, so H2 fails. Declared immediately.
- **K2, timing/height:** if no weekly close from 2029-06-26 to 2029-12-25 reaches $355,061, then H1 or H2 has failed. Declared on 2029-12-25.
- **K3, path:** at any yearly checkpoint with ≥ 104 weeks, if DM says the band is significantly worse than the trend, label the band on the site "**failed its pre-registered test; shown for reference**".
- **K4, repeat overshoot:** if the cycle-4 top is below band_lo (a second consecutive overshoot after 2025), the dampening rule is declared insufficient. The band is no longer drawn as a forward guide.

**Replace:** any new band rule is a new version (band v2) with its own pre-registration, freeze date and stamp. Its predictions start from its own freeze day. v1 is still graded to the end and is never re-tuned.

**What cannot change after the freeze:**
- the snapshot CSV, band_freeze.py/json, the parameters and the benchmark columns;
- the outcome definitions (4a–4d), windows, evaluation dates, the price source and the weekly-close rule;
- the tests, alpha, minimum samples, verdict and kill rules.

What may change: display code, typo fixes in prose outside the hashed files, and adding new benchmarks clearly labeled "post-hoc". Any change to a hashed file is caught by the workflow guard and must fail CI.

---

## 8. Dates of first results

| Date | What gets reported |
|---|---|
| Freeze day (proposed 2026-10-25) | snapshot hashed and stamped. The first graded weekly close is 2026-11-01 |
| 2027-05-02 | 26-week checkpoint: horizon-26 error, interim path MAE (no p-values) |
| 2027-10-31 | 52-week checkpoint (yearly report) |
| 2028-10-29 | 104-week checkpoint: **first DM and McNemar results allowed** |
| 2029-10-28 | 156-week checkpoint |
| first run after 2027-10-03 | the 2025-cycle low becomes final (104 weeks after the 2025 top). The **S1-R/S3-R** re-run is written once to `data/band_rerun.json` (section 11.2) |
| block 1,050,000 (est. mid-March to mid-April 2028) | actual halving date recorded once in `data/halving_2028.json` (section 11.3) |
| 2029-12-25 | timing window closes: K2 check |
| 2030-10-27 | path sample complete: **final H4** |
| 2031-04-06 | **final top call (H1, H2)** |
| T\* + 104 weeks (latest 2033-03-27) | **final low call (H3)** and overall verdict |

---

## 9. Bitcoin-anchored record

### What the repo already does (no change needed)
- **OTS proofs for the frozen hash list.** `pipeline/timestamps/FROZEN_SHA256SUMS.ots`, plus `.first/.second/.third.txt.ots`, were stamped once.
- **Daily upgrade.** The workflow runs `ots upgrade` on `pipeline/timestamps/*.ots` every day (opentimestamps-client 0.7.2). It is failure-tolerant: it posts a notice and carries on.
- **Frozen-hash guard.** Frozen hashes are checked before and after every run. The list's own sha is pinned in the workflow env.
- **Daily raw-data snapshots.** `scripts/snapshot.sh` writes daily tarballs to `snapshots/YYYY/` (weekly for the large files) and `snapshots/MANIFEST.csv` (date, file, bytes, sha256).
- **Offline rebuild.** `OFFLINE=1 bash scripts/update.sh` rebuilds from the cache without fetching. The README has a "Reproduce a past day" section.
- **Pinned environment.** `requirements.txt` pins versions; Python 3.12.15 on ubuntu-24.04.
- **Zenodo.** Concept DOI 10.5281/zenodo.23643772; release v3-freeze-2026-10-25 is 10.5281/zenodo.23643773.
- **Append-only scorecard.** `data/scorecard.csv` is append-only by code (idempotent, from 2026-10-24).

### Added at the lock
1. **Daily hash chain and stamp of every prediction record.** Script: `scripts/stamp_daily.py`. Each day it writes `pipeline/timestamps/chain/YYYY-MM-DD.txt` containing:
   - the date;
   - the **previous day's record hash**;
   - sha256 of `data/scorecard.csv`, `data/band_log.csv`, `data/band_prices.csv`, `data/band_price_revisions.csv`, `data/band_grades.json`, `data/band_rerun.json` and `data/halving_2028.json` (once they exist), `snapshots/MANIFEST.csv`, `FROZEN_SHA256SUMS`, `BAND_SHA256SUMS`, `competitors_freeze.json`, `AMENDMENTS.md` (if any), `data/hero_fwd.json` and `data/fan.json`.

   The date is the UTC date. The script is `scripts/stamp_daily.py`, and it always exits 0. It appends one line to `pipeline/timestamps/chain.csv` (date, record_sha256, prev_record_sha256) and runs `ots stamp` on the day's record. Because each record contains the previous hash, one Bitcoin attestation proves the whole history up to that day.
2. **Upgrade the new proofs.** Extend the existing upgrade loop to `pipeline/timestamps/chain/*.ots`, and commit the `.ots` files (they are already in the `git add` path).
3. **Append-only guard in CI** (`scripts/check_append_only.py`; today this is enforced only by code). The run fails if:
   - any earlier `band_log.csv` row is not byte-identical to the previous commit;
   - any earlier `scorecard.csv` row differs in its prediction columns (only the `*_actual/in50/in90/log_score` cells may be filled in later);
   - any earlier `chain.csv`, `band_prices.csv` or `band_price_revisions.csv` line has changed;
   - a write-once file (`band_rerun.json`, `halving_2028.json`) has changed.
4. **Hash-pinned environment.** Generate `requirements.lock` with `pip-compile --generate-hashes` and install with `pip install --require-hashes`. Optionally also publish a container image pinned by digest. Today's versions are pinned but the hashes are not.
5. **One-command rebuild-and-compare.** Add `scripts/rebuild.sh YYYY-MM-DD`. It:
   - (a) creates the pinned environment;
   - (b) unpacks that day's snapshot tarballs and checks them against MANIFEST.csv;
   - (c) runs `OFFLINE=1 bash scripts/update.sh`;
   - (d) compares the sha256 of the rebuilt CSV/JSON outputs with the values in that day's chain record and prints MATCH or DIFF per file.

   PNGs are **not** expected to be byte-identical (fonts and renderer), so they are excluded. CSV/JSON should match exactly. If they don't, that is a bug to fix, for example by pinning float formatting.
6. **Periodic Zenodo archives.** Make an automatic GitHub release (and so a Zenodo version under the same concept DOI) **monthly**, plus one at every checkpoint in section 8. Each archive includes the repo, `snapshots/`, `chain/` and all `.ots` files, so the record survives even if GitHub does not. Today only manual releases exist.
7. **Verify guide.** `VERIFY.md` is in the lock package. The short form is below.

**Scope of this lock.** Items 1–3 and 7 ship with the lock. Items 4–6 (the hash-pinned environment, rebuild.sh and the monthly Zenodo archive) are recommended follow-ups. They are not required for the claim to be verifiable, and they do not change any frozen file.

**Cost:** OpenTimestamps is **free**. Public calendar servers batch many hashes into one Bitcoin transaction and pay its fee, so there is no wallet and no fee for us. Repo growth is a few KB per day (.txt plus .ots).

**Failure handling:**
- `ots stamp` and `ots upgrade` run with a timeout and **never fail the update job**. They warn and continue.
- If the calendar servers are down, the day's chain record is still written and committed without its `.ots`. **The next day's run retries** stamping every record that still lacks an `.ots`.
- Because of the chain, a missed day is also covered by the next successful stamp. That day's proof then shows "existed by day N+1" instead of day N.
- Upgrades that are still pending stay pending and are retried daily.

### VERIFY.md, short form (full text: `VERIFY.md` at the repo root)
```
pip install opentimestamps-client==0.7.2
git clone <repo> && cd <repo>

# 1. Are the frozen files unchanged?
sha256sum -c pipeline/frozen/FROZEN_SHA256SUMS
sha256sum -c pipeline/frozen/band/BAND_SHA256SUMS
#   expect: every line ends in ": OK"

# 2. Was the hash list anchored in Bitcoin on the freeze day?
ots verify pipeline/frozen/band/BAND_SHA256SUMS.ots
#   with a local Bitcoin Core node, expect:
#   "Success! Bitcoin block NNNNNN attests existence as of 2026-10-2x"
#   without a node:  ots info pipeline/frozen/band/BAND_SHA256SUMS.ots
#   shows "BitcoinBlockHeaderAttestation(NNNNNN)". Look that block up on any
#   explorer and check its date. Or drag both files onto opentimestamps.org.
#   "Pending confirmation" only means the proof is under ~a day old and not yet upgraded.

# 3. Is the daily chain intact, and does each day point to the day before?
python scripts/verify_chain.py
#   expect: "chain OK: N days, first 2026-10-2x, last <today>, 0 breaks"

# 4. Did today's prediction files exist on the date claimed?
ots verify pipeline/timestamps/chain/2027-01-15.txt.ots
grep scorecard pipeline/timestamps/chain/2027-01-15.txt   # then compare to:
git show <commit of that day>:data/scorecard.csv | sha256sum

# 5. (once the rebuild.sh follow-up ships) Rebuild a past day from the archive, offline
bash scripts/rebuild.sh 2027-01-15
#   expect: "MATCH" for every CSV/JSON; PNGs are listed as "not compared"
```
`scripts/verify_chain.py` is new. It rechecks each record's sha, its `prev` link, and that each file hash matches git history.

---

## 10. Historical backtest (HINDSIGHT, in-sample). Competitor backtests: `height_study/` and `height_laws/` (not frozen; disclosed in section 13)

**Read this first:** the dampening rule (rho) was designed in 2026, *after* the 2025 cycle had overshot. Each cycle's band below uses only data before its origin (a causal trend fit, causal rho, the cycle-boundary cap as in band_test). The *choice of rule*, however, saw all of it. **This is not out-of-sample evidence.** The live test in sections 3–8 is the only clean test.

Code is in `band_prereg/backtest.py`, and the outputs are `backtest_outcomes_cap.csv` (headline) and `backtest_outcomes.csv` (no cap, for comparison). Two origins are used:
- **at halving;**
- **live phase:** 534 days before the halving, the same position the live freeze is in today.

The live-phase dampened band does not exist for 2017, because rho needs 2 completed cycles.

### Top timing and height
Timing error is actual top minus the band peak. A hit is within ±91 days.

| Cycle | Origin | Model | Band peak (mid; range) | Actual top (weekly close) | Timing | Height | log10 err |
|---|---|---|---|---|---|---|---|
| 2017 | halving | **damped** | 2017-07-11: $12.0K ($7.8–19.4K) | 2017-12-17: $19,250 | +159 d ✗ | ✓ | −0.20 |
| 2017 | halving | unscaled2 | 2017-07-11: $17.9K | | ✗ | ✓ | −0.03 |
| 2021 | halving | **damped** | 2021-11-10: $68.5K ($50.8–95.9K) | 2021-11-14: $65,032 | +4 d ✓ | ✓ | +0.02 |
| 2021 | live phase | **damped** | 2021-11-11: $79.0K ($60.9–107.4K) | | +3 d ✓ | ✓ | +0.09 |
| 2021 | halving / live | unscaled2 | $98.6K / $106.2K | | ✓ / ✓ | ✗ / ✗ | +0.18 / +0.21 |
| 2025 | halving | **damped** | 2025-09-28: $252K ($207–321K) | 2025-10-05: $123,524 | +7 d ✓ | **✗ (2.0× too high)** | +0.31 |
| 2025 | live phase | **damped** | 2025-09-28: $288K ($226–386K) | | +7 d ✓ | **✗ (2.3× too high)** | +0.37 |
| 2025 | halving / live | unscaled2 | $399K / $424K | | ✓ / ✓ | ✗ / ✗ | +0.51 / +0.54 |
| all | | last cycle unscaled | | | halving ✗/✓/✓ (+156/+28/−12 d); live ✗/✓/✗ (2025 +200 d) | ✗ in 2021 and 2025 | +0.29 to +0.39 |
| all | | halving + mean days rule | 2017-07-12 / 2021-08-01 / 2025-10-11 | | ✗ +158 / ✗ +105 / ✓ −6 | n/a | |
| all | | trend line at actual top | | | n/a | | −0.94 / −0.51 / −0.15 (halving) |
| all | | 95% ceiling at actual top | | | n/a | | +0.04 / +0.30 / +0.57 |

**Damped-band record:** timing 2 of 3 (p ≈ 0.064 against p0 = 0.154, hindsight), height 2 of 3.

**The honest finding: it overshot 2025 badly.** The top was half the band middle and below the band's low edge. The timing hits mostly repeat the prior cycles' timing; a plain timing rule did about as well in 2025.

### Post-top low (all misses, always too high)

| Cycle | Origin | Band low (mid; range) | Actual low | log10 err | Predicted / actual drawdown |
|---|---|---|---|---|---|
| 2017 | halving | 2018-12-05: $3,382 ($3,319–3,710)\* | 2018-12-16: $3,195 | +0.03 ✗ | 72% / 83% |
| 2021 | halving | 2022-11-25: $25.6K ($24.6–27.3K) | 2022-11-20: $16,247 | +0.20 ✗ | 63% / 75% |
| 2021 | live phase | 2022-10-08: $30.1K\* | | +0.27 ✗ | 62% / 75% |
| 2025 | halving | $103.2K\* | 2026-06-28: $59,517 (provisional) | +0.24 ✗ | 59% / 52% so far |
| 2025 | live phase | $114.4K\* | | +0.28 ✗ | 60% / 52% so far |

\* The band ended at or near this point, so its low is partly an edge effect.

Benchmarks: the 5% trend floor at the actual low date had errors of −0.14, +0.03 and +0.01 (halving origins). That makes it the **better low predictor in every cycle**. The mean-drawdown rule came out −0.11 and −0.36.

### Path fit (weekly closes, origin to band end)

| Case | Share in band | Share in const-width band | MAE band | MAE trend | DM p (band vs trend) |
|---|---|---|---|---|---|
| 2017, halving | 0.29 | 0.47 | 0.293 | 0.300 | 0.94 |
| 2021, halving | 0.43 | 0.34 | 0.139 | 0.226 | 0.06 |
| 2021, live phase | 0.31 | 0.49 | 0.153 | 0.188 | 0.05 |
| 2025, halving | 0.28 | 0.42 | 0.191 | 0.117 | 0.08 (band worse) |
| 2025, live phase | 0.18 | 0.44 | 0.205 | 0.153 | 0.27 (band worse) |

McNemar p ranged from 0.13 to 1 everywhere. The damped band beat the undamped band on MAE in every case. In 4 of 5 cases, a trend band of the same width held more weekly closes than the cycle band did.

**Bottom line of the hindsight test:**
- the band's *timing* has looked right;
- its *height* was right twice and then badly wrong in 2025;
- its *lows* were always too shallow;
- as a path it did not reliably beat the plain trend.

That is the reason for testing it publicly, with benchmarks, instead of promoting it.

---

## 11. Protocol decisions resolved at lock prep (2026-10-25, about 19:00Z)

### 11.1 Grading price source
- **Primary:** the CoinMetrics community API `PriceUSD`. The close dated D is CoinMetrics' fixed close at 00:00 UTC on D+1, i.e. the end of UTC day D. This is the same series every backtest and the fan's kill rule use.
- **First print, never overwritten.** `band_log_daily.py` appends each new date's close to `data/band_prices.csv` (date, close, source, logged_utc) the first time it is seen.
  - Later changes at the source go to `data/band_price_revisions.csv` and are shown, but they are never applied. Grading uses only `band_prices.csv`.
  - The file is append-only, enforced by CI, and stamped daily. Anyone can therefore check that the graded price was on record before it was used.
- **Fallback:** used only if CoinMetrics still has not published date D after 7 days.
  - The value is the **median of the UTC daily candle closes** from Coinbase Exchange (BTC-USD), Kraken (XBTUSD) and Bitstamp (btcusd). The candle for day D closes at 00:00 UTC on D+1, the same convention.
  - At least 2 of the 3 sources are required. Otherwise nothing is written that day and the run retries the next day.
  - The source tag records each exchange's value.
  - Check on 2026-10-18, 10-20 and 10-24: the fallback median was within 0.05–0.09% of CoinMetrics.
- **Weekly close:** the close dated **Sunday**, i.e. the price at **Monday 00:00 UTC**, the end of Sunday UTC. *(Note for the owner: the shorthand "Sunday 00:00 UTC" would mean Saturday's close. This protocol keeps the end-of-Sunday close because the fan's kill rule (b), the band backtests and the competitor fits all use it. See the decision list.)*
- **Weekly price:** no intraday highs. The top and low are weekly closes only.

### 11.2 The unconfirmed 2025-cycle low (S1/S3 input)
S1 and S3 are fitted with x = the prior cycle's low, defined as the lowest weekly close in the 104 weeks after that cycle's top. For 2025 that window ends on **2027-10-03**. Today's value, $59,517 on 2026-06-28, is the lowest so far and is provisional.

Options considered:

| Option | Description | Assessment |
|---|---|---|
| a | grade the frozen value only | clean, but if the low later goes deeper, the law is graded on an input its own definition rejects |
| b | wait for the final low before freezing S1/S3 | not a pre-registration of today's forecast |
| c | the owner's suggested rule (52 weeks + a 2× rise) | fails to fire in a shallow cycle, so a low may never be "confirmed" |
| **d (adopted)** | **both**, below | |

Option d:
- **C2 = S1 and C3 = S3, frozen today.** These are the competitor claims ranked in section 12.3.
- **S1-R and S3-R:** the same frozen code is run **once**, on the first daily run after 2027-10-03, when the low is final by the law's own definition.
  - The coefficients come from the same fit. Only x changes; S3 also refits its realized-price trend through that date, which is part of the rule.
  - The result is written once to `data/band_rerun.json`. That file is write-once and stamped, and it lands about 2 years before the top window.
  - S1-R and S3-R are graded and shown as **secondary readouts**. They are not ranked against the other claims, so S1 and S3 do not get two chances to win.
- Sensitivity, locked now: if the final low is $50,000, S1 = $296,748; at $40,000, S1 = $260,001.

### 11.3 Halving date
- **Every frozen forecast uses the assumed date 2028-04-11.** It is not re-frozen when the real date is known.
- mempool.space on 2026-10-25 showed height 973,109, with 76,891 blocks to go to block 1,050,000:
  - at 600 s per block that gives about 2028-04-11;
  - at the recent 572.7 s average it gives about 2028-03-18.
  - The plausible range is mid-March to mid-April 2028.
- **Primary grading is by calendar date** and is unchanged whatever the actual date turns out to be.
- **Secondary readout:** the UTC date of block 1,050,000 is recorded once in `data/halving_2028.json`. Each timing claim also reports its halving-relative error: (T\* − actual halving) − (predicted date − 2028-04-11).
- If the actual date differs from 2028-04-11 by **more than 30 days**, the scorecard says so next to the timing grades. That is the only consequence.

### 11.4 Timing drift and the C4 competitor
Halving-to-top days, measured to the weekly-close top (daily-close top in brackets):

| Cycle | Halving | Top | Days |
|---|---|---|---|
| 2013 | 2012-11-28 | 2013-12-01 | 368 (371) |
| 2017 | 2016-07-09 | 2017-12-17 | 526 (525) |
| 2021 | 2020-05-11 | 2021-11-14 | 552 (546) |
| 2025 | 2024-04-20 | 2025-10-05 | 533 (534) |

- A straight-line fit gives +52 days per cycle, so the next gap would be 625 days: **C4 = 2029-12-27**, graded with the same ±91-day hit rule.
- **The evidence for lengthening is weak.** The trend comes almost entirely from 2013. The last three gaps (526, 552, 533) are flat, with a mean of about 537 days, which is what the band (532 days) and the timing-rule benchmark (2029-10-05) already assume.
- C4 is included because it is simple, fixed now, and the obvious alternative people will cite. Its weakness is disclosed here. It is a timing-only claim.

### 11.5 "No cycle" outcomes
T\* and L\* are always defined (4a, 4c), so every claim gets a grade. Each outcome is labelled with one of these classes; all are computed by `grade_band.py` on the final top run, 2031-04-06:

| Class | Definition | Grading consequence |
|---|---|---|
| **Top identified and confirmed** | T\* is followed within the record by 52 weeks with no higher close and a close at least 50% below it | normal grading |
| **Top identified, not confirmed** (a shallow or flat cycle) | no 50% drawdown (the band itself implies only 42.6%) | normal grading on T\*. The label is shown |
| **No cycle top identified** (supercycle or still rising) | T\* falls in the last 26 weeks of the window (after 2030-09-29) | every timing claim is a **miss**. Height is graded on T\* and labelled "the true top may be higher". Every low claim is a **miss** (no post-top low was observed in the window's terms) |
| **No boom** (an added label) | the close at T\* is below the snapshot trend line at T\* | normal grading. Label shown |
| **Floor break** (an event, any time) | runs of weekly closes below the snapshot's 5% trend floor | each run is logged with its dates and shown. It does not change any grade by itself |

These classes do not change the verdict rules in section 7. They make sure "it never really topped" or "it went sideways" cannot be argued after the fact into a void result.

## 12. Claims, multiple comparisons, and how a winner is declared

### 12.1 What is graded
| Claim | Kind | Timing | Height (top close at T\*) | Low (L\*) | Path |
|---|---|---|---|---|---|
| **Main: blue band** (frozen snapshot) | primary | 2029-09-25 ±91 d | $481,434 ($355,061–$653,032) | $276,258 ($226,609–$336,640) on 2030-06-04 | H4 |
| **C1: ensemble-corrected band** (frozen snapshot) | secondary | the same date as the band; **not counted as a separate timing claim** | $562,145 ($261,057–$1,210,493) | $189,256 ($134,754–$265,802) on 2030-06-04 | MAE, DM |
| **C2: S1 size law** | secondary | none | $329,017 ($189,445–$571,416) | none | none |
| **C3: S3 on-chain size law** | secondary | none | $432,862 ($193,973–$965,961) | none | none |
| **C4: lengthening timing** | secondary | 2029-12-27 ±91 d | none | none | none |
| S1-R / S3-R (11.2) | readouts | none | written 2027-10 | none | none |
| Benchmarks (section 5) | reference | timing rule 2029-10-05; unscaled2; last cycle | trend $290,860; unscaled2 $595K; last cycle $397K | 5% trend floor $181,411; unscaled2; last cycle; drawdown rule (79.2%, the mean of the 2017 and 2021 weekly-close drawdowns) | trend line, constant width |

All numbers are from the 2026-10-25 dry run. The approval-day regeneration replaces them (15.1).

**Disclosed dependence between claims:**
- C1 contains the band as one of its components.
- C2 and C3 share the same x input.
- Their results will be correlated and must not be counted as independent confirmations.

### 12.2 Multiple comparisons
- **Primary:** the band's verdict (section 7). It has one formal test, H4 DM band vs trend, at α = 0.05 with no adjustment because it is the single pre-declared primary test.
- **Secondary formal tests:** DM C1 vs trend and DM C1 vs band, Holm-adjusted together at family-wise α = 0.05. McNemar (band vs constant width) stays as in section 6.
- **Hits are pass/fail evidence, not tests.**
  - A single timing hit has chance probability about 0.154 under a uniform top (section 6).
  - With several height ranges of different widths, at least one range is likely to contain the top by luck. Wide ranges hit more often: C1's range is 0.67 log10 wide, C3's 0.70, S1's 0.48 and the band's 0.27.
  - So every hit is shown with its range width, and **no claim is called validated** because its range contained the outcome.

### 12.3 Winner rule (per target, descriptive)
- For each target (timing, height, low, path), the **winner** is the claim with the lowest absolute error:
  - log10 error for height and low;
  - days for timing;
  - MAE for path.
- Eligible: the main claim, C1–C4 where they make that kind of prediction, and the section 5 benchmarks. S1-R and S3-R are not eligible.
- A lead smaller than **0.05 log10** (about 12%), or **30 days** for timing, is reported as a **tie**.
- The result is a one-cycle label ("closest this cycle"). It is not a claim that a method is better. A method is only called better if it wins the same target again in a later, separately pre-registered cycle.
- The **main claim's verdict does not depend on the competitors**. A competitor beating the band is reported plainly, and the band is not replaced mid-test (section 7, Replace).

### 12.4 SELECTION_RULE.md grading, superseded
SELECTION_RULE.md (copied verbatim, hash unchanged) says that the ensemble components T1–T5 and L1–L5 are "graded as separate claims", and that the live corrected band is graded too.

This protocol supersedes that section:
- only the **frozen C1 snapshot** is a graded claim;
- the components and the live corrected band are **logged daily** in `band_log.csv` and shown descriptively, never ranked.

This avoids ten more weakly distinct claims that would make a lucky "winner" almost certain. SELECTION_RULE.md itself is not edited.

## 13. Disclosure: order of events (what was known when)
Times are UTC on 2026-10-25 unless stated, taken from file times in the study folder.

1. **Before this study:** the band's live code (`forward_band.py`) already existed at commit 307abb5. It was displayed as "not scored".
2. **During 2026, after the 2025 top:** the **dampening rule rho was designed** (v3_spec, band_test). It was designed knowing that 2025 overshot the undampened band. The band's hindsight record (section 10) is therefore in-sample.
3. **By 18:32 at the latest:** the band's independent code, the snapshot and the draft of this protocol were written. Today's band values were seen before this protocol was written.
4. **About 18:20 to 18:27:** the height-estimator study ran (`height_study.py`). Every component's backtest errors were **seen before** the selection rule was written.
5. **18:29:** SELECTION_RULE.md (the equal-weight ensemble with sanity exclusions) was written, after step 4. The rule was chosen to be simple (equal weights, no fitting to the backtest), but it was not blind.
6. **About 18:40 to 18:43:** the size laws were studied (`height_laws/`). The **2011 cycle was excluded after it was seen** to break the forward fits; the stated reason is that its "prior low" is the data start. Three laws were tried, and S2 (top / trend vs market cap at the prior low) was dropped as largely redundant with S1.
7. **About 18:50:** the competitors C1–C3 were chosen by the owner, with their backtests and today's projections known.
8. **About 19:00 (lock prep):** C4 (lengthening timing) was added. Its fit was computed at the same moment it was proposed, and it is disclosed as weak evidence (11.4).
9. Nothing about cycle 4 (2028 onwards) is known to anyone. That forward test is the only clean evidence.

## 14. Site display plan (as a patch, applied only on approval)
- **The chart is unchanged:** the same blue band, drawn from the live `hero_fwd.json`. The owner's preference: no purple fans and no new lines.
- **The scorecard gets a new section, "Cycle band and its competitors".** It is rendered from `data/band_grades.json` in plain English:
  - each claim: what it says, its locked numbers, its status ("waiting: grading starts 2028-01-02", then hit, miss or provisional);
  - the winner per target and the tie rule;
  - the outcome class and any floor-break or kill (K1–K4) labels;
  - a link to this protocol and to VERIFY.md.
- **Text fixes:** the hero subtitle, the method bullet and the explain.js "chart" text currently say the band is "not scored" or "not part of the scorecard". They become "pre-registered on <freeze day>; graded in the scorecard".
- **Caption:** "The chart shows the band as recomputed daily. The locked, graded version is in the scorecard." The live band drifts a little; the frozen snapshot does not.
- **Every new block carries:** "Historical pattern test, not a price target. Not financial advice."
- No trading language and nothing about any individual's positions.

## 15. Freeze day, amendments, publication
### 15.1 Freeze day
- **The freeze day T0 is the approval day.** On that day, `band_freeze.py` and then `competitors_freeze.py` are run with data through T0 − 1.
- Values move slightly from the dry run, because the trend and rho are refit daily (a few tenths of a percent per month).
- The numbers in sections 2, 12.1 and the summary are then updated mechanically from the regenerated JSON before hashing. **No method changes.**
- `competitors_freeze.py` stops with an error if the band peak date is no longer 2029-09-25. In that case the TP_2029 constant must be updated before hashing, and the note in this section says so.
- The dry-run outputs (2026-10-25) are kept in the lock package for comparison.

### 15.2 Amendments
- After the freeze, no frozen file changes; CI enforces this.
- Amendments go in `pipeline/frozen/band/AMENDMENTS.md`. That file is append-only. Each entry is dated, gives a reason, and is included in that day's stamped chain record.
- An amendment can add (a new labelled post-hoc benchmark, a display change, a fix), but it **cannot change** a prediction, a window, a hit rule, the price rule or the verdict rules. It can never apply retroactively.
- **Bugs in the grading code:** a corrected grader is added as a new file. Both results are published side by side, and any difference is labelled. The original result stays the headline unless the original cannot run.
- **A new band rule is a new version** with its own pre-registration (section 7).

### 15.3 Publication
- Results are published whatever the outcome, at every checkpoint in section 8, including FAIL, K-labels and competitor wins.
- Nothing is removed from the site because it failed. It is labelled instead.

## 16. Referee checklist (other issues considered)
- **Garden of forking paths:** see section 13. The hindsight backtests are in-sample, so only the cycle-4 forward test counts.
- **Cherry-picking among competitors after the fact:** prevented by 12.3 (fixed eligibility, the tie margin) and 12.4 (components not ranked).
- **Range width vs hit rate:** widths are reported next to every hit. Winners are decided by point error, not by hits.
- **Look-ahead in the grading data:** first-print prices (11.1). The snapshots are fixed and hashed. The append-only guard runs in CI.
- **Survivorship (dropping a failed claim):** not allowed. Failed claims stay, with labels (15.3).
- **Timezone and calendar:** all dates are UTC. Weekly close = the end of Sunday UTC (11.1).
- **Data vendor risk:** the fallback median, plus the source tag on every row (11.1).
- **Dependence between claims:** disclosed in 12.1.
- **Small n:** one cycle. Section 6 states plainly that H1–H3 cannot be statistically significant on one cycle.
- **Not financial advice:** stated on every page that shows these results.
