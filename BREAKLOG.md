# Break log

Each month one stress test tries to break the frozen models. Tests run on **copies** of the frozen files; the frozen versions
are never edited or patched because of a result. Findings go to `IDEAS.md` as proposals for the next yearly review.
Rotation: (a) leave one cycle out, (b) shuffled or shifted halving dates, (c) start-date and data-source sensitivity,
(d) a pure-trend or random benchmark beating the model, (e) a bad-data day, (f) a fee or timing change. Not financial advice.

| Date | Test | What broke / what held | Severity |
|---|---|---|---|
| 2026-11-02 | (a) Leave one cycle out, on the frozen blue band (`pipeline/frozen/band`, frozen 2026-10-25). Script: `tools/breaktest_a_loco.py` | See below | Medium (disclosure gap; nothing graded changes) |

## 2026-11-02, test (a): leave one cycle out

**Setup.** The frozen band code was copied to a temporary folder and run on CoinMetrics data cut at 2026-10-24 (the freeze
data). The copy reproduces the frozen snapshot exactly: next top 2029-09-25, middle $481K (range $355K to $653K); low after it
2030-06-04, middle $276K ($227K to $337K).

**1. Dropping one cycle from the dampening factor (rho).**

| Cycle left out | rho | 2029 top: date, middle (range) | 2030 low: date, middle |
|---|---|---|---|
| none (frozen) | 0.777 | 2029-09-25, $481K ($355K to $653K) | 2030-06-04, $276K |
| data start to 2012 | 0.728 | 2029-09-26, $462K ($354K to $603K) | 2030-06-03, $285K |
| 2012 cycle | 0.685 | 2029-09-27, $448K ($352K to $565K) | 2030-06-03, $293K |
| 2016 cycle | 0.685 | 2029-09-27, $448K ($352K to $565K) | 2030-06-03, $293K |
| 2020 cycle | 0.831 | 2029-09-25, $504K ($356K to $717K) | 2030-08-02, $266K |

- *Held:* the top date barely moves (two days) and the top's middle moves only about 7% down to 5% up.
- *Found:* rho is a geometric mean of successive ratios, so it collapses to (last peak / first peak) raised to 1/(number of
  ratios). The two middle cycles' peak heights have **no effect at all**; only the first cycle, the latest cycle and the count
  between them matter. That is why leaving out the 2012 or the 2016 cycle gives identical results. This is not stated in
  `PREREG_BAND.md`, which describes rho as using every completed cycle.

**2. Dropping one of the two past cycles the band's shape is copied from.**

| Shape source | 2029 top: date, middle (range) | 2030 low: date, middle |
|---|---|---|
| both (frozen) | 2029-09-25, $481K ($355K to $653K) | 2030-06-04, $276K |
| 2024 cycle only | 2029-07-15, $379K ($364K to $386K) | 2030-06-20, $234K |
| 2020 cycle only | 2029-10-08, $631K ($599K to $659K) | 2030-10-21, $286K |

- *Held:* each single-cycle middle stays inside the frozen band's range at the top, and each single-cycle low stays inside the
  frozen low range.
- *Found:* the band's height depends far more on which past cycle it copies than on rho (a $379K to $631K swing versus
  $448K to $504K). The band's width is mostly the gap between two cycle shapes, not a measured uncertainty.

**3. Held-out cycles (each cycle forecast only from data before its halving).**

| Cycle | Top inside the band? | Actual top vs band middle | Timing error |
|---|---|---|---|
| 2016 halving | no | 63% above | 158 days late |
| 2020 halving | yes | 1% below | 2 days early |
| 2024 halving | no | 51% below (2.0x too high) | 8 days late |

- These match the walk-forward tables already published in `PREREG_BAND.md` (the 2025 overshoot is disclosed there). The band
  caught one of three held-out tops on size; timing was close in the last two.

**Proposals (for the yearly review, not applied):** disclose the rho endpoint property; consider an estimator that uses every
cycle (for example a fitted decay line through all peak heights) and report the spread between single-cycle shapes as the
band's real uncertainty. Any change would be a new pre-registered version; the 2026-10-25 band stays graded as frozen.
