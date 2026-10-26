# My BTC Cycle Model

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23643772.svg)](https://doi.org/10.5281/zenodo.23643772)

Live site: https://euthymia686.github.io/my-btc-cycle-model/

A live Bitcoin cycle chart built from raw public data:
- **Projection fan** (5/25/50/75/95%): a power-law trend refit daily, widened by how wrong that trend has actually been out of sample. A copy frozen on 2026-10-25 is kept unchanged and scored only on later data.
- **Cycle Heat Score** (0-100): valuation, on-chain, usage, attention and halving-timing signals, each turned into a percentile against its own history.
- **Cycle band**: where the two previous halving cycles sat at the same day since halving.
- **Chart to 2030**: the time axis, the trend corridor and the blue cycle band run to the end of 2030. After now the band is the past cycles scaled down, a shape guide (not a forecast, not graded) that shows the next possible top and the low after it. The graded forecast range (the locked fan) is not on the chart; it is shown as a table in the site's scorecard section.
- **Crowd euphoria** (display only): Fear & Greed Index plus BTC perpetual funding rates (`crowd.py`), a contrarian gauge that is not part of any score. Ideas for future versions are logged in `IDEAS.md`.

![hero](hero_combined.png)

> **Disclaimer.** These are model ranges, not predictions. Nothing here is financial advice or a recommendation to buy or sell anything.
>
> Disclosure: the author holds Bitcoin-related investments. The model rules are locked and graded in public so that this cannot quietly shape the results.
> Past cycles may not repeat, data sources can be wrong or late, and the code may contain errors. Do your own research.

## How it works
- `index.html`, `js/`, `css/`: static site. Live prices stream from Coinbase, Kraken and Bitstamp public WebSockets, and blocks from mempool.space, straight into the browser.
- `data/*.json`: daily files rebuilt by `build_data.py` from `pipeline/`.
- `pipeline/`: data fetch and models (CoinMetrics Community, CoinGecko, Yahoo Finance, Google Trends, Strategy.com / SEC EDGAR). If a source fails, the last cached copy in `pipeline/cache/` is used. Raw Yahoo Finance, Deribit and OKX files are not published (their terms do not allow it); the workflow keeps them in the GitHub Actions cache.
- `pipeline/frozen/`, `pipeline/v2_spec.py`, `pipeline/robust.py`: pre-registered, hash-checked. They are never edited; any change becomes a new version.
- `pipeline/frozen/`: locked model versions. v2 (`v2_freeze.json`, the frozen fan) and v3 (`v3/`: pre-registered rules, tests, and `FREEZE.md` with what v3 changes and the rule for promoting it over v2), both frozen 2026-10-25. `FROZEN_SHA256SUMS` lists every frozen file; the workflow fails if any of them changes. The list is timestamped in the Bitcoin blockchain with OpenTimestamps (`pipeline/timestamps/`). Two v3 research files are not published; their hashes are in `v3/withheld_sha256.txt`.
- `pipeline/scorecard.py` and `data/scorecard.csv`: the public forward scorecard. Each daily run logs the v2 and v3 forecasts for 30, 90 and 365 days ahead and grades them when they mature (inside the 50% band, inside the 90% band, log score). Rows are only appended, once per daily close.
- Statistical grading (method pre-registered in `pipeline/frozen/v3/FREEZE.md`, code in `pipeline/scorestats.py`): an exact binomial test of band coverage on non-overlapping forecasts, and a Diebold-Mariano test (Newey-West errors) of log score against a plain benchmark (power-law trend with a constant-width lognormal band, logged daily as version `base`) and of v3 against v2. Results are shown once at least 10 independent forecasts have matured. The same tests on past data are in `data/scorecard_backtest.json` (`pipeline/scorecard_backtest.py`); those p-values are optimistic because the models were designed after seeing that data.
- Kill criteria (pre-registered in `pipeline/frozen/v3/FREEZE.md`): a version is retired in public if (a) its 90% band fails the coverage test with p below 0.01 on at least 10 independent forecasts, (b) the weekly close stays below the power-law floor for 26 or more weeks in a row, or (c) it loses to the plain benchmark with p below 0.05 over at least 12 independent forecasts. The scorecard shows each one's status. On past data, (b) would never have fired (longest run below the floor: 17 weeks, from February 2012). It was first set at 8 weeks and changed to 26 on 2026-10-25, before any live weekly close counted, because 8 would have fired in four past bear markets; see `RESEARCH_LOG.md`.
- `RESEARCH_LOG.md`: every variant tried, including the dropped ones, with when and why.
- `.github/workflows/update-and-deploy.yml`: runs daily at about 00:30 UTC (or manually). It rebuilds the data, commits it if anything changed, and deploys to GitHub Pages. If CoinMetrics has not yet published every field for the latest close, the scorecard rows wait (`scripts/score_gate.py`): retries at 03:00, 06:00 and 09:00 UTC, and at 12:00 UTC the rows are written anyway with a note in `data/scorecard_notes.csv` (append-only). Retries with nothing left to do exit without a commit.
- `scripts/snapshot.sh`: each daily run saves a dated raw-data snapshot in `snapshots/` (small source files daily, about 30 KB; the large CoinMetrics and Bitstamp files weekly on Sundays, about 290 KB) and a sha256 line per raw file in `snapshots/MANIFEST.csv`. Newer snapshots leave out the Yahoo Finance, Deribit and OKX raw files; only their sha256 lines stay in the manifest.

Run it locally: `pip install -r requirements.txt && bash scripts/update.sh && python -m http.server`.

See `docs/ARCHITECTURE.md`, `docs/ROBUSTNESS.md` and `pipeline/SOURCES.md`.

## Reproduce a past day
1. Check out the "Daily data refresh" commit of that day (its `pipeline/cache/` holds the exact raw data that run used), or restore `pipeline/cache/` and `data/ohlc_daily.json` from that day's snapshot plus the latest weekly snapshot on or before it, and check them against `snapshots/MANIFEST.csv`.
2. Install Python 3.12.15 and the exact versions in `requirements.txt` (`pip install -r requirements.txt`).
3. Run `OFFLINE=1 bash scripts/update.sh`. With `OFFLINE=1` nothing is fetched; every step uses the cached raw files.
4. Compare with that commit's `data/` files. Fields that record the run time (for example `updated_utc`) will differ.

Raw Yahoo Finance, Deribit and OKX files are no longer in the repo or the newer snapshots, only their sha256 in `snapshots/MANIFEST.csv`. They feed only the display-only crowd gauge (`data/crowd.json`) and a fallback MSTR price and cross-check; nothing graded or in the daily hash chain uses them. To rebuild `data/crowd.json` exactly, fetch the funding history again from Deribit or OKX.

## How to cite
See `CITATION.cff`. Releases are archived on Zenodo. DOI for all versions: [10.5281/zenodo.23643772](https://doi.org/10.5281/zenodo.23643772). First release (v3-freeze-2026-10-25): [10.5281/zenodo.23643773](https://doi.org/10.5281/zenodo.23643773).

## How this was built

Designed and directed by Euthymia686, built with help from an AI assistant. The model rules, data sources and code are all public in this repo, locked versions are hash-checked, and every forecast is graded on the public scorecard, so you can judge the work by its track record rather than by who or what wrote it.

## License

Copyright (c) 2026 Euthymia686. This project is licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) (see `LICENSE`).

- Free for personal and other non-commercial use, including study, research and hobby projects.
- Commercial use needs permission from the copyright holder. Open an issue on this repository or email [btc.cycle.model@gmail.com](mailto:btc.cycle.model@gmail.com) to ask.
- Earlier copies of this repository were published under the MIT License. Copies obtained under MIT keep those terms; this license applies from this commit on.

The bundled Lightweight Charts library is (c) TradingView and stays under its own Apache-2.0 license (`js/vendor/LICENSE-lightweight-charts.txt`, `js/vendor/NOTICE-lightweight-charts.txt`). Charts: TradingView Lightweight Charts™, https://www.tradingview.com/.

Third-party data is not covered by this license. It stays under each provider's own terms, and the names belong to their owners:
- Coin Metrics Community data: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) (values are transformed).
- [alternative.me Crypto Fear & Greed Index](https://alternative.me/crypto/fear-and-greed-index/), price data by [CoinGecko](https://www.coingecko.com/), data source: [Google Trends](https://www.google.com/trends), Wikimedia pageviews (CC0).
- Shadow candidates (research only, `pipeline/candidates/`): CFTC Commitments of Traders (public domain), FRED / Federal Reserve and New York Fed series (public domain), Coin Metrics Community issuance (CC BY-NC 4.0); OKX and Deribit open interest is used but only a derived share of market cap is published.
- Bitstamp daily price history (`data/ohlc_daily.json`), Coinbase, Kraken and Bitstamp live prices, mempool.space blocks, Strategy.com and SEC EDGAR. Raw Yahoo Finance, Deribit and OKX data is used but not republished.

## Prior work and credits

This model builds on public ideas by others:
- Time-based power-law trend: Giovanni Santostasi (r/Bitcoin, 2018) and Harold Christopher Burger, "Bitcoin's natural long-term power-law corridor of growth" (2019).
- Mayer Multiple (price / 200-day average): Trace Mayer.
- Puell Multiple (shadow candidate only): David Puell (2019).
- MVRV ratio: Murad Mahmudov and David Puell (2018), building on realized cap by Nic Carter and Antoine Le Calvez. MVRV Z-score: Awe & Wonder (2018).
- Pi Cycle Top indicator: Philip Swift (2019).
- Stock-to-flow (discussed as a cautionary example, not used): PlanB, "Modeling Bitcoin's Value with Scarcity" (2019).
