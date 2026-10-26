# Idea log

Dated model ideas, kept so that changes happen rarely and in the open: ideas are logged here as they come up and are
only adopted as a new locked version (v4 and so on) at the yearly review, never by editing v2 or v3. The full record of
variants tried, with results, is in `RESEARCH_LOG.md`. Entries are only added, never removed or rewritten. Not
financial advice.

Next review: 2027-10-25.

- 2026-10-25: Crowd-euphoria signal (funding rates + Fear & Greed) added as display only. Proposed as a v4 candidate. A shadow candidate score will be pre-registered and tracked live until the 2027-10-25 review.
  - Display only for now: `crowd.py` writes `data/crowd.json` (Fear & Greed from alternative.me; funding from Deribit,
    with OKX as backup and BitMEX tried for pre-2019 history). The shadow score is not built yet.
- 2026-10-25: Signal review for v4 candidate. Price-stretch family (Mayer, 200W, trend multiple, Pi Cycle) is largely redundant; family averaging already limits its weight. Candidates for the 2027-10-25 review: add crowd euphoria (funding rates + Fear & Greed); consider dropping or down-weighting Pi Cycle ratio (did not fire at the 2025 top) and active addresses (weakened by ETF/exchange custody and off-chain activity); add a long-term-holder selling signal if a free, reliable data source exists. No change to v2/v3.
- 2026-10-26: Data-timing issue found in weekly upkeep. At the 00:30 UTC daily run, CoinMetrics Community had published the 2026-10-25 price but not yet its on-chain fields (MVRV, active addresses, supply). The v2/v3 Heat Score for that day was therefore scored without its on-chain and network families (26.6 instead of about 33), and that scorecard row stays as written (append-only). Proposals, for the owner to decide (not applied): run the daily update later in the UTC day once CoinMetrics has filled the row, or have the daily run wait for a complete row before scoring. The blue band test uses only the price and is unaffected. No change to v2/v3.
