# My BTC Cycle Model

Live site: https://euthymia686.github.io/my-btc-cycle-model/

A live Bitcoin cycle chart built from raw public data:
- **Projection fan** (5/25/50/75/95%): a power-law trend refit daily, widened by how wrong that trend has actually been out of sample. A copy frozen on 2026-10-25 is kept unchanged and scored only on later data.
- **Cycle Heat Score** (0-100): valuation, on-chain, usage, attention and halving-timing signals, each turned into a percentile against its own history.
- **Cycle band**: where the two previous halving cycles sat at the same day since halving.

![hero](hero_combined.png)

> **Disclaimer.** These are model ranges, not predictions. Nothing here is financial advice or a recommendation to buy or sell anything.
> Past cycles may not repeat, data sources can be wrong or late, and the code may contain errors. Do your own research.

## How it works
- `index.html`, `js/`, `css/`: static site. Live prices stream from Coinbase, Kraken and Bitstamp public WebSockets, and blocks from mempool.space, straight into the browser.
- `data/*.json`: daily files rebuilt by `build_data.py` from `pipeline/`.
- `pipeline/`: data fetch and models (CoinMetrics Community, CoinGecko, Yahoo Finance, Google Trends, Strategy.com / SEC EDGAR). If a source fails, the last cached copy in `pipeline/cache/` is used.
- `pipeline/frozen/`, `pipeline/v2_spec.py`, `pipeline/robust.py`: pre-registered, hash-checked. They are never edited; any change becomes a new version.
- `pipeline/v3/`: v3 research candidate (dampened cycle band + calibrated fan width), pre-registered in `PREREG.md`. It is not used on the site. Some research scripts and plots listed in `v3_hashes.txt` are not published in this repository.
- `.github/workflows/update-and-deploy.yml`: runs daily at about 00:30 UTC (or manually). It rebuilds the data, commits it if anything changed, and deploys to GitHub Pages.

Run it locally: `pip install -r requirements.txt && bash scripts/update.sh && python -m http.server`.

See `docs/ARCHITECTURE.md`, `docs/ROBUSTNESS.md` and `pipeline/SOURCES.md`.

License: MIT (see LICENSE). Lightweight Charts is (c) TradingView, Apache-2.0.
