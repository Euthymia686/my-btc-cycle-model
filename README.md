# My BTC Cycle Model

Live site: https://euthymia686.github.io/my-btc-cycle-model/

A live Bitcoin cycle chart built from raw public data:
- **Projection fan** (5/25/50/75/95%): a power-law trend refit daily, widened by how wrong that trend has actually been out of sample. A copy frozen on 2026-10-25 is kept unchanged and scored only on later data.
- **Cycle Heat Score** (0-100): valuation, on-chain, usage, attention and halving-timing signals, each turned into a percentile against its own history.
- **Cycle band**: where the two previous halving cycles sat at the same day since halving.

![hero](hero_combined.png)

> **Disclaimer.** These are model ranges, not predictions. Nothing here is financial advice or a recommendation to buy or sell anything.
>
> Disclosure: the author holds Bitcoin-related investments. The model rules are locked and graded in public so that this cannot quietly shape the results.
> Past cycles may not repeat, data sources can be wrong or late, and the code may contain errors. Do your own research.

## How it works
- `index.html`, `js/`, `css/`: static site. Live prices stream from Coinbase, Kraken and Bitstamp public WebSockets, and blocks from mempool.space, straight into the browser.
- `data/*.json`: daily files rebuilt by `build_data.py` from `pipeline/`.
- `pipeline/`: data fetch and models (CoinMetrics Community, CoinGecko, Yahoo Finance, Google Trends, Strategy.com / SEC EDGAR). If a source fails, the last cached copy in `pipeline/cache/` is used.
- `pipeline/frozen/`, `pipeline/v2_spec.py`, `pipeline/robust.py`: pre-registered, hash-checked. They are never edited; any change becomes a new version.
- `pipeline/frozen/`: locked model versions. v2 (`v2_freeze.json`, the frozen fan) and v3 (`v3/`: pre-registered rules, tests, and `FREEZE.md` with what v3 changes and the rule for promoting it over v2), both frozen 2026-10-25. `FROZEN_SHA256SUMS` lists every frozen file; the workflow fails if any of them changes. The list is timestamped in the Bitcoin blockchain with OpenTimestamps (`pipeline/timestamps/`). Two v3 research files are not published; their hashes are in `v3/withheld_sha256.txt`.
- `pipeline/scorecard.py` and `data/scorecard.csv`: the public forward scorecard. Each daily run logs the v2 and v3 forecasts for 30, 90 and 365 days ahead and grades them when they mature (inside the 50% band, inside the 90% band, log score). Rows are only appended, once per daily close.
- Statistical grading (method pre-registered in `pipeline/frozen/v3/FREEZE.md`, code in `pipeline/scorestats.py`): an exact binomial test of band coverage on non-overlapping forecasts, and a Diebold-Mariano test (Newey-West errors) of log score against a plain benchmark (power-law trend with a constant-width lognormal band, logged daily as version `base`) and of v3 against v2. Results are shown once at least 10 independent forecasts have matured. The same tests on past data are in `data/scorecard_backtest.json` (`pipeline/scorecard_backtest.py`); those p-values are optimistic because the models were designed after seeing that data.
- Kill criteria (pre-registered in `pipeline/frozen/v3/FREEZE.md`): a version is retired in public if (a) its 90% band fails the coverage test with p below 0.01 on at least 10 independent forecasts, (b) the weekly close stays below the power-law floor for 26 or more weeks in a row, or (c) it loses to the plain benchmark with p below 0.05 over at least 12 independent forecasts. The scorecard shows each one's status. On past data, (b) would never have fired (longest run below the floor: 17 weeks, from February 2012). It was first set at 8 weeks and changed to 26 on 2026-10-25, before any live weekly close counted, because 8 would have fired in four past bear markets; see `RESEARCH_LOG.md`.
- `RESEARCH_LOG.md`: every variant tried, including the dropped ones, with when and why.
- `.github/workflows/update-and-deploy.yml`: runs daily at about 00:30 UTC (or manually). It rebuilds the data, commits it if anything changed, and deploys to GitHub Pages.
- `scripts/snapshot.sh`: each daily run saves a dated raw-data snapshot in `snapshots/` (small source files daily, about 30 KB; the large CoinMetrics and Bitstamp files weekly on Sundays, about 290 KB) and a sha256 line per raw file in `snapshots/MANIFEST.csv`.

Run it locally: `pip install -r requirements.txt && bash scripts/update.sh && python -m http.server`.

See `docs/ARCHITECTURE.md`, `docs/ROBUSTNESS.md` and `pipeline/SOURCES.md`.

## Reproduce a past day
1. Check out the "Daily data refresh" commit of that day (its `pipeline/cache/` holds the exact raw data that run used), or restore `pipeline/cache/` and `data/ohlc_daily.json` from that day's snapshot plus the latest weekly snapshot on or before it, and check them against `snapshots/MANIFEST.csv`.
2. Install Python 3.12.15 and the exact versions in `requirements.txt` (`pip install -r requirements.txt`).
3. Run `OFFLINE=1 bash scripts/update.sh`. With `OFFLINE=1` nothing is fetched; every step uses the cached raw files.
4. Compare with that commit's `data/` files. Fields that record the run time (for example `updated_utc`) will differ.

## How to cite
See `CITATION.cff`. Releases are archived with a DOI once the repository is linked to Zenodo.

## How this was built

Designed and directed by Euthymia686, built with help from an AI assistant. The model rules, data sources and code are all public in this repo, locked versions are hash-checked, and every forecast is graded on the public scorecard, so you can judge the work by its track record rather than by who or what wrote it.

## License

Copyright (c) 2026 Euthymia686. This project is licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) (see `LICENSE`).

- Free for personal and other non-commercial use, including study, research and hobby projects.
- Commercial use needs permission from the copyright holder. Open an issue on this repository to ask.
- Earlier copies of this repository were published under the MIT License. Copies obtained under MIT keep those terms; this license applies from this commit on.

The bundled Lightweight Charts library is (c) TradingView and stays under its own Apache-2.0 license.
