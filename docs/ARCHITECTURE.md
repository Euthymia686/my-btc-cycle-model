# My BTC Cycle Model: architecture and roadmap

This is a model, not a prediction, and not financial advice.

## Phase 1: static site on free hosting (built now)

```
browser ──WebSocket──> Coinbase / Kraken / Bitstamp   (trades and tickers; median = own index, recomputed every 1 s)
        ──WebSocket──> mempool.space                  (new blocks: height, halving countdown)
        ──REST(CORS)─> Coinbase candles, CoinGecko    (gap fill and fallback price)
        ──static────> data/*.json                     (history, calibration, distributions, fan, chart layers)
```

* All maths runs in the browser (`js/model.js`, which mirrors `cycle_signals/lib.py`), so no server is needed.
* `build_data.py` rebuilds `data/` from `pipeline/`. Run it once a day:
  * with cron on the box: `run_daily.sh && python build_data.py`; or
  * with a scheduled GitHub Action that commits `data/`, after which the host redeploys.
* Hosting options, all free tier:
  * **Cloudflare Pages, direct upload.** Drag and drop the folder, or run `wrangler pages deploy live_site`. A GitHub account is not needed.
  * **GitHub plus Cloudflare Pages, Vercel or Netlify.** You get version history and auto-deploy on every data commit. This is the easiest way to automate the daily refresh.
  * **Netlify Drop.** Drag and drop; no Git needed.
* Limits in phase 1, and why:
  * **Realized cap, active addresses and supply are daily.** They come from CoinMetrics community data. Computing them in real time needs your own node and indexer (phase 2).
  * **Google Trends is monthly.** That is the only resolution Google publishes for this term over long ranges.
  * **The MSTR premium (mNAV) is no longer shown on the site.** The daily pipeline still writes `data/mstr.json` (delayed MSTR price, holdings, shares) for private use.

## Phase 2: our own raw data

| Component | What it does | Size / cost (rough estimates, check before buying) |
|---|---|---|
| Bitcoin Core full node (unpruned, `txindex=1`) | Ground-truth blocks and transactions | about 700 GB+ of disk today, growing roughly 60–90 GB a year; 4+ cores, 8–16 GB RAM; the initial sync takes 1–3 days on NVMe |
| On-chain indexer (custom Python or Rust, or an electrs/fulcrum-style base) | Per block: UTXO set with creation price, giving realized cap, MVRV, UTXO age bands (HODL waves) and active addresses | UTXO database plus per-block metrics, about 100–300 GB; it needs a historical daily or hourly BTC price to value UTXOs |
| Exchange aggregator | One server WebSocket fan-in (Coinbase, Kraken, Bitstamp, plus optionally Binance, OKX and Bybit), with a volume-weighted index and outlier rejection; it re-broadcasts one stream to users | Tiny: under 1 vCPU and 1 GB RAM |
| Time-series store and API | Postgres/Timescale or SQLite plus a small HTTP/WebSocket API: `/signals`, `/ws` | Under 50 GB |
| Stock feed (optional) | Real-time MSTR price | Paid: for example Polygon.io, about $29–199 a month depending on tier (check current pricing) |

Hosting choices:

* **Home node.** A mini-PC with a 2 TB NVMe, about $300–600 one-off plus power. The site stays on free hosting and the node pushes JSON or a WebSocket through a tunnel (e.g. Cloudflare Tunnel, free).
* **VPS or dedicated server with 2 TB NVMe.** About $40–100 a month (Hetzner or OVH tier, check current prices).

What this gives you: per-block (about every 10 minutes) MVRV, realized cap and active addresses computed from your own data, plus your own price index. No third-party metrics are needed.

## Phase 3: public launch

* **Domain:** about $10–15 a year, pointed at Cloudflare.
* **Caching and protection:**
  * CDN caching for `data/*.json`, at about a 5-minute TTL.
  * Rate limits on the phase-2 API, e.g. Cloudflare rules.
  * A single upstream connection per exchange; users connect to our relay, not to the exchanges.
* **Legal:**
  * Clear "not financial advice" text and terms of use.
  * Privacy note: no tracking, or privacy-friendly analytics.
  * Respect each data provider's terms; CoinMetrics community data is non-commercial.
* **Operations:**
  * Monitoring: uptime checks, alerts when the feed is stale, a check that the daily build succeeded.
  * Versioned methodology page and a changelog for model recalibrations.

## Page layout (current)
* **Hero: "My BTC Cycle Model"** (`js/hero.js`): one white-background panel. Log BTC price (weekly) coloured by the live v1 Cycle Heat Score over the trend corridor 5-95%, ceiling (dotted), trend (dashed), floor, cycle band, and the projection fan (25-75% and 5-95%, median dotted) recomputed from the live price to its locked horizon of Dec 31 2028 (never extended; a dashed "locked forecast ends Dec 2028" line marks it). The time axis, the corridor (`data/hero_bg.json`) and the dampened forward cycle path (`data/hero_fwd.json`) run on to Dec 31 2030 as display context only, not graded forecasts; the cycle path stops where the prior cycles' data ends. Halving / est. halving lines, a blue live-price tag and a "now" point updated every second. A small status in the chart header (live / live (polling every 10s) / STALE / last close) replaces the old price header; its (i) lists each feed's connection state. The initial view fits 2014 (2017 on phones) through the end of the forward layers with the fan included in the price autoscale; it re-fits on resize, on double-click and with "Reset view".
* **Directly under the hero:** the live Cycle Heat Score panel and the cycle facts next to it (signals at hot level, halving-cycle day, block height, next halving, drawdown).
* **Cycle Heat Score history** (v1, v1 walk-forward, pre-registered v2).
* Below: candle chart, signal tiles, **Model health** (backtest coverage, forward coverage since freeze, integrity hashes, trend drift), freshness table, method.
* If no exchange feed has delivered a price yet, the page computes everything on the last daily close and the chart status says "last close"; each tile shows a value or "updated daily, last: date".
* All hero charts use weekly points because lightweight-charts spaces points evenly by index; mixing daily history with a weekly forecast would distort time.
* Data: `data/fan2.json` (fan parameters + frozen fan), `data/health.json`, `data/hero_bg.json` (background layers from `pipeline/hero_png.py`, same `charts.fits` / `charts.cycle_band`), `model.json.v2` (8-year window distributions). See ROBUSTNESS.md.
* Static high-res PNG: `hero_combined.png` from `pipeline/hero_png.py`, using the frozen fan file.
