# Why this model is built not to fail the way stock-to-flow did

Everything here is a model. It is not a prediction and not financial advice.

## The stock-to-flow lesson
Stock-to-flow fitted one formula to past data and published one future price path (e.g. "$100k by 2021", later much higher).
When price left that path there was no way to tell, ahead of time, how far off it could be, and nothing in the model said
"I am now failing". Three design rules here come from that:

1. **No single price target.** The page shows a range (a fan), never one number for the future.
2. **The fan's width comes from the model's own past mistakes**, so it gets wider the further out you look.
3. **The rules are written down and frozen before the future happens**, and the page checks them against what actually happens.

## 1. Trend refit daily on all data
The trend is a power law: log10(price) = a + b * log10(days since 3 Jan 2009), fitted by least squares on every daily close.
It is refit every day. The refit itself is evidence: the trend's value for Dec 15 2028 has drifted down as data arrived.

| fit date | slope b | trend value on Dec 15 2028 |
|---|---|---|
| 2018-10-24 | 5.891 | $403,585 |
| 2022-10-24 | 5.849 | $373,187 |
| 2024-10-24 | 5.697 | $296,693 |
| 2025-10-24 | 5.705 | $300,102 |
| 2026-10-24 | 5.638 | $273,597 |

A fixed target set in 2018 would now be about 47% too high versus today's own trend. That table is on the page (Model health) and is recomputed daily.

## 2. A fan made from forecast errors (code: `cycle_signals/robust.py`)
For every past day t since 2012 the trend was fitted using only data up to t (no hindsight). Then, for each horizon h
(every 7 days up to 1,600 days), we record the error: actual log price at t+h minus what that trend predicted.
* The error is regressed on how far price was from trend at the start (r0), because being far below trend today tends to mean-revert partly.
* The leftover errors give the 5 / 25 / 50 / 75 / 95% bands at each horizon. Bands are forced never to narrow as h grows.
* Recent cycles count more (half-life 4 years, one halving cycle). This number was chosen before looking at results and not tuned.
* No statsmodels on the box, so this is weighted least squares + weighted empirical quantiles (not a quantile-regression library).
* In the browser, the fan is recomputed every 5 s (15 s on phones) from the live price.

Today's fan for Dec 15 2028 (from the 2026-10-24 close): 5%: $77,305 · 25%: $150,038 · median: $226,237 · 75%: $333,865 · 95%: $767,869.

### Honest backtest (22 freezes: 1 Jan and 1 Jul, 2015-2025; each fan built only from data before its freeze date; scored on the next 1,150 days)
| horizon | inside 90% band | inside 50% band | days |
|---|---|---|---|
| all | 98.2% | 70.7% | 23,713 |
| 0-1 year | 96.9% | 63.2% | |
| 1-2 years | 97.6% | 67.7% | |
| 2-3 years | 100% | 81.0% | |

* Perfect calibration would be 90% / 50%. The fan is **too wide** (conservative). Read the bands as "generous".
* **Worst case:** the fan frozen on 2015-01-01 had price inside its 90% band only 76.9% of the time (below the 5% line 23% of the time). Early data was short and the trend was steeper.
* For comparison a fixed, non-widening 5-95% corridor around one formula (the "single formula" approach) scored 90.2% overall but only 20.8% and 43.2% after the 2015 freezes: it broke in exactly the regime change where you most need it.

## 3. Score built from independent signal families
v1 (unchanged) averages 8 signals, but 4 of them are all "price vs its own average" and move together, so price is effectively counted 4 times.
v2 groups signals into five families and averages the families, so no one kind of evidence dominates:

| family | signals | update |
|---|---|---|
| price structure | Mayer Multiple, price/200-week MA, price/trend, Pi Cycle ratio | live |
| on-chain valuation | MVRV Z-score | live price, daily realized cap |
| network usage | active addresses 30d/365d | daily |
| attention | Google search interest | monthly |
| timing | days since halving (bell curve, mean 494, sd 71.4 days) | daily |

## 4. Pre-registered v2 ("cycle-relative") score, frozen 2026-10-25
* Heat of each signal = its percentile versus the **prior 8 years (2,922 days) only**, needing at least 730 days, so the score adapts to a maturing market instead of comparing 2026 to 2011.
* Family heat = mean of its members. Score = mean of the families (at least 3 needed).
* Zones are fixed in advance: hot >= 80, warm >= 65, neutral >= 40, cool < 40.
* Frozen file hashes (sha256), checked every day by `health.py` and shown on the page:
  * `v2_spec.py` 1ed15c4c00d49512ceacfeb6b00ca5d4dba2ba665f3ace9e1bc4ad3b6a1e2162
  * `robust.py` d03a0e5a6dd831065a17262e5c30a7012df6f344ebc303fd0c19a080bc3f1acc
  * `frozen/fan_2026-10-25.json` 0c1d1ddebbac8e44c529c4c3e6090d3fd935be3584d230b3a2b40b1c47da2a3d
* Rule: never edit the frozen files. A change means a new version (v3) with a new freeze date; v2 keeps being logged so it can be judged.
* Honest in-sample look (this is hindsight, not proof): v2 peaked at 80.0 (2013 top), 91.6 (2017), 69.8 (2021) and 67.2 (2025), and bottomed around 20-23. So v2 would only have said "warm" at the last two tops. That was not tuned away; the forward log will show whether v2 is any better than v1.
* Today (2026-10-24 close): v2 = 34.1 cool; v1 = 34.2 cool.

## 5. Model-health monitor
Every daily run (`run_daily.sh` -> `signals.py` -> `health.py`) logs to `cycle_signals/journal.csv`:
v1 score, v2 score and families, whether the frozen files still match their hashes, and how often finalized daily closes since the freeze
have stayed inside the frozen fan's 50% and 90% bands. If, over many months, price sits inside the 90% band much less than 90% of the time
(or the 50% band far from 50%), the model is failing and the page says so in numbers. Forward tracking starts at 0 days on 2026-10-25;
it will take months before it means anything.

## What could still break it
* A real change in Bitcoin's growth regime (e.g. an ETF/treasury era with lower volatility) makes the past error distribution too wide or wrongly centred. The fan is conservative, which helps, but it is not a guarantee.
* Data sources (CoinMetrics community, Google Trends) can change or stop; the daily run records which sources failed.
* Bands are model quantiles, not probabilities.
