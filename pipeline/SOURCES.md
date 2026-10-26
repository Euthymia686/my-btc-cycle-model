# Source quality note (My BTC Cycle Model)

## Ranking of what we use / have looked at
| Rank | Source | Type | Used for | Notes |
|---|---|---|---|---|
| 1 | SEC EDGAR (8-K, 10-Q) | Primary, official | MSTR BTC holdings, shares, debt/preferreds | Legal filings; weekly 8-Ks on purchases. Free. |
| 2 | CoinMetrics Community API | Primary (computed from the blockchain + exchange data) | Daily price, market cap, MVRV (-> realized cap), supply, active addresses | Free, documented methods, ~1 day lag; realized cap itself is paid-tier, so derived as mcap / MVRV. |
| 3 | mempool.space | Primary (node data) | Block height, next-halving estimate | Free. |
| 4 | Strategy.com KPI JSON | Primary (issuer) | Holdings, issuer's EV-based mNAV, MSTR close | Company-published; cross-check against EDGAR. Unofficial endpoint, may change. |
| 5 | CoinGecko | Aggregator (primary-ish) | Live spot price | Free tier, volume-weighted across exchanges. |
| 6 | Yahoo Finance (yfinance) | Aggregator, unofficial API | BTC/MSTR closes | Free, delayed ~15 min, can break. |
| 7 | Google Trends (pytrends) | Sampled, relative index | Retail attention | 0-100 relative, resampled per request; noisy; unofficial library. |
| 8 | Chart sites (bitbo, lookintobitcoin, blockchaincenter, etc.) | Derived / interpretive | Not used as inputs | Other people's models on top of the same primary data. |
| 9 | X accounts / influencer charts | Interpretive / opinion | Not used | Hindsight and survivorship bias; no published, testable rules. |

## Best primary sources per signal family
| Family | Best free | Best paid | Comment |
|---|---|---|---|
| Price | CoinMetrics Community (daily reference rate), CoinGecko, exchange APIs (Coinbase, Kraken, Binance public endpoints) | CoinMetrics Pro, Kaiko | Exchange APIs are the true primary source for trades. |
| On-chain | CoinMetrics Community; your own Bitcoin Core node (+ mempool.space) | Glassnode, CoinMetrics Pro, CryptoQuant | Realized cap, SOPR, LTH/STH supply, coin-age (RHODL) are paid at good resolution. A full node lets you compute them yourself. |
| ETF flows | Issuer websites (iShares IBIT, Fidelity FBTC daily holdings), SEC N-PORT/13F | Bloomberg, Farside (free but compiled) | Issuer daily holdings files are the primary data. Checked 2026-10-26 for the ETF-flows candidate: Farside is all rights reserved, SoSoValue forbids redistribution and scraping, issuer files cover one fund each and restrict data use, so flows are not shown. |
| Derivatives | Exchange public APIs: Deribit (options, implied volatility), Binance/Bybit/OKX (funding, open interest), CME (futures OI, delayed) | Laevitas, Amberdata, Kaiko, CoinGlass Pro | Funding rates and OI are good leverage/froth gauges. The leverage shadow candidate uses CME open interest from the CFTC weekly reports (public domain, from 2018-04); Binance and Bybit block this build machine. |
| Macro | FRED (M2, fed funds, real yields, dollar index proxy), US Treasury | Bloomberg | FRED is free and official. Not in the score; WALCL, WTREGEN, RRPONTSYD and DTWEXBGS feed the liquidity shadow candidate (2026-10-26). |
| MSTR | SEC EDGAR (holdings, shares, capital stack), Strategy.com, exchange quotes | A broker or Polygon/Cboe quote feed | Real-time stock quotes are paid. |
