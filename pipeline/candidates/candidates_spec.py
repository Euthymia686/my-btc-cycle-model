"""PRE-REGISTERED shadow candidates for the 2027-10-25 yearly review. Written and hash-locked 2026-10-26, before any forward
data (first forward close date: 2026-10-26). DO NOT EDIT: the sha256 of this file is in CANDIDATES_SHA256SUMS, which is
pinned in the workflow and timestamped with OpenTimestamps. Any change is an amendment (AMENDMENTS.md, new hash, new stamp)
or a new pre-registration. PREREG_CANDIDATES.md is the plain-language version; if the two disagree, PREREG_CANDIDATES.md governs.

Pure functions only: inputs are daily pandas Series indexed by UTC date (raw series as published by the sources); no fetching.
NOT part of the Cycle Heat Score, v1, v2, v3, the scorecard, the band test or any graded result.

Heat: the same causal percentile as frozen v2 (pipeline/v2_spec.py window_pct): percentile (0-100) of each day's value vs the
prior 2,922 observed daily values only, needing >= 730 prior values. Imported from the frozen file, so it is identical.
"""
import numpy as np, pandas as pd
from v2_spec import window_pct, PARAMS as V2   # frozen 2026-10-25, read only

FROZEN_ON = "2026-10-26"
FORWARD_FROM = "2026-10-26"         # first close date in the forward (out-of-sample) shadow log
WINDOW, MIN_OBS = V2["window_days"], V2["min_obs"]          # 2922, 730
MIN_FAMILIES = V2["min_families"]                           # 3
V2_FAMILIES = list(V2["families"])  # price_structure, onchain_valuation, network_usage, attention, timing
SCORED = ["miner_income", "leverage", "liquidity"]          # each candidate is its own family
DISPLAY_ONLY = ["etf_flows", "oi_crypto"]                   # never scored by this pre-registration
CME_BTC_PER_CONTRACT = {"133741": 5.0, "133742": 0.1}       # CFTC codes: CME Bitcoin (5 BTC), CME Micro Bitcoin (0.1 BTC)
LAGS = {"cftc": 4, "walcl": 2, "wtregen": 2, "rrp": 1, "dxy": 7}   # a value dated t is used from close date t + lag days
RRP_DAILY_FROM = "2013-09-23"   # ON RRP reported daily from here; earlier operations were occasional and small
STALE = {"cftc": 21, "walcl": 14, "wtregen": 14, "rrp": 10, "dxy": 21}   # max age (days) of the last usable value, else missing

def _daily(idx_end, start=None):
    return pd.date_range(start, idx_end, freq="D")

def asof(s, idx, lag, stale):
    """Value of a (possibly weekly/irregular) series usable on each day of idx: last obs dated <= day - lag, if not older
    than `stale` days (counted from the obs date to day - lag); else NaN."""
    s = s.dropna().sort_index()
    if s.empty: return pd.Series(np.nan, index=idx)
    shifted = pd.Series(s.values, index=s.index + pd.Timedelta(days=lag))
    obs_day = pd.Series(s.index, index=shifted.index)
    v = shifted.reindex(shifted.index.union(idx)).ffill().reindex(idx)
    od = obs_day.reindex(obs_day.index.union(idx)).ffill().reindex(idx)
    age = (idx.to_series() - pd.Timedelta(days=lag) - od).dt.days
    v[(age > stale) | age.isna()] = np.nan
    return v

# ---------------------------------------------------------------- 1. Puell Multiple (miner_income family)
def puell(iss_usd):
    """Puell = daily miner issuance in USD (CoinMetrics IssTotUSD, block subsidy only, no fees) / its mean over the 365 days
    ending that day (needs all 365). Raw signal = Puell."""
    s = iss_usd.astype(float).where(lambda x: x > 0)
    return s / s.rolling(365, min_periods=365).mean()

# ---------------------------------------------------------------- 2. Leverage (leverage family)
def cme_btc_oi(cot):
    """cot: dict {cftc_code: Series of open_interest_all (contracts) by report date}. BTC-equivalent CME open interest =
    5 x CME Bitcoin + 0.1 x CME Micro Bitcoin (micro counts 0 before its first report, 2021-05-04)."""
    parts = []
    for code, mult in CME_BTC_PER_CONTRACT.items():
        if code in cot and len(cot[code]): parts.append(cot[code].astype(float) * mult)
    if not parts: return pd.Series(dtype=float)
    df = pd.concat(parts, axis=1).sort_index()
    if "133741" not in cot or not len(cot["133741"]): return pd.Series(dtype=float)
    df = df[df.index.isin(cot["133741"].index)]          # report dates of the main contract
    return df.fillna(0.0).sum(axis=1)

def leverage(cot, supply, idx):
    """L = CME BTC-equivalent open interest (latest report usable on the day: report date <= day - 4, at most 21 days old)
    / circulating supply (CoinMetrics SplyCur) = futures open interest as a share of market cap (price cancels).
    Raw signal = leverage stretch = L / median(L over the 365 days before the day, needing >= 300 values), so the
    structural growth of CME open interest does not read as heat by itself."""
    oi = asof(cme_btc_oi(cot), idx, LAGS["cftc"], STALE["cftc"])
    L = oi / supply.reindex(idx).astype(float)
    med = L.shift(1).rolling(365, min_periods=300).median()
    return L, L / med

def oi_crypto_ratio(oi_usd, mcap):
    """DISPLAY/DIAGNOSTIC ONLY (not scored): crypto-exchange BTC futures + perpetual open interest in USD (OKX all BTC
    contracts + Deribit BTC futures/perpetual, as fetched) / CoinMetrics market cap."""
    return oi_usd.astype(float) / mcap.reindex(oi_usd.index).astype(float)

# ---------------------------------------------------------------- 3. Liquidity (liquidity family; skeptical test)
def liquidity(walcl, wtregen, rrp, dxy, idx):
    """Fed net liquidity NL = WALCL - WTREGEN - 1000 x RRPONTSYD ($ millions; FRED, H.4.1 and NY Fed), each series as of
    the day with the LAGS/STALE rules (RRP counts 0 when missing before RRP_DAILY_FROM). Dollar = DTWEXBGS (nominal broad dollar index, H.10).
    Components: g_nl = ln(NL / NL 365 days earlier); g_usd = ln(DXY / DXY 365 days earlier).
    Heat = mean of window_pct(g_nl) and window_pct(-g_usd) (rising liquidity and a falling dollar read hot); needs both."""
    r = asof(rrp, idx, LAGS["rrp"], STALE["rrp"])
    r[(r.isna()) & (idx < pd.Timestamp(RRP_DAILY_FROM))] = 0.0   # before the daily ON RRP facility: no operation = 0
    nl = asof(walcl, idx, LAGS["walcl"], STALE["walcl"]) - asof(wtregen, idx, LAGS["wtregen"], STALE["wtregen"]) - 1000.0 * r
    usd = asof(dxy, idx, LAGS["dxy"], STALE["dxy"])
    g_nl = np.log(nl / nl.shift(365)); g_usd = np.log(usd / usd.shift(365))
    return nl, usd, g_nl, g_usd

def liquidity_heat(g_nl, g_usd):
    h = pd.concat([window_pct(g_nl, WINDOW, MIN_OBS), window_pct(-g_usd, WINDOW, MIN_OBS)], axis=1)
    return h.mean(axis=1, skipna=False)

# ---------------------------------------------------------------- heats and shadow scores
def heat(raw):
    return window_pct(raw.astype(float), WINDOW, MIN_OBS)

def shadow_scores(v2_fam, cand_heat):
    """v2_fam: DataFrame of the five v2 family heats (pipeline/out/score_v2_history.csv, columns v2_<family>), by date.
    cand_heat: DataFrame with columns miner_income, leverage, liquidity.
    Each shadow score = plain mean of the available family heats, needing >= 3 families (as v2):
      shadow_all   = v2's 5 families + all 3 candidates (8 families)
      shadow_puell = v2 + miner_income;  shadow_lev = v2 + leverage;  shadow_liq = v2 + liquidity
    ETF flows and crypto-exchange open interest are never part of any shadow score."""
    out = {}
    F = v2_fam.reindex(cand_heat.index)
    for name, add in [("shadow_all", SCORED), ("shadow_puell", ["miner_income"]), ("shadow_lev", ["leverage"]), ("shadow_liq", ["liquidity"])]:
        G = pd.concat([F, cand_heat[add]], axis=1)
        s = G.mean(axis=1, skipna=True); s[G.notna().sum(axis=1) < MIN_FAMILIES] = np.nan; out[name] = s
    return pd.DataFrame(out)

def zone(x):
    """Same fixed zones as v2 (hot >= 80, warm >= 65, neutral >= 40, cool < 40)."""
    z = V2["zones"]
    if x is None or not np.isfinite(x): return "n/a"
    return "hot" if x >= z["hot"] else "warm" if x >= z["warm"] else "neutral" if x >= z["neutral"] else "cool"

# ---------------------------------------------------------------- 2027-10-25 review (mechanical; PREREG_CANDIDATES.md section 6)
REVIEW_DATE = "2027-10-25"
TOP_WIN, LOW_WIN = 60, 30          # days either side of a cycle top / low
HOT, COOL = V2["zones"]["hot"], V2["zones"]["neutral"]   # 80, 40
COVER_ADOPT, COVER_DROP = 0.90, 0.75
MAX_RHO = 0.80                     # Spearman vs the v2 price_structure family heat
MIN_TOPS = 2
LOW_SLACK = 2.0                    # shadow score may be at most 2 points warmer than v2 at cycle lows
CONFLICT_DAYS = 30                 # forward: candidate hot while v2 cool for 30+ days in a row = conflict

def _longest(mask):
    best = run = 0
    for m in mask:
        run = run + 1 if m else 0; best = max(best, run)
    return best

def evaluate(cand_heat, fwd, v2_score, v2_fam, tops, bottoms, review_date=REVIEW_DATE):
    """cand_heat: DataFrame (miner_income, leverage, liquidity) of daily heats over all history (backfill + forward).
    fwd: forward shadow log as DataFrame indexed by close date (columns heat_<family> and v2_score), first prints.
    v2_score / v2_fam: v2 score and family heats (score_v2_history.csv at review time). tops/bottoms: dicts of Timestamps
    (pipeline/lib.find_tops_bottoms on the CoinMetrics close). Returns {family: {checks..., verdict}}."""
    rv = pd.Timestamp(review_date); last = cand_heat.index.max()
    fdays = pd.date_range(FORWARD_FROM, rv - pd.Timedelta(days=1), freq="D")
    res = {}
    for c in SCORED:
        h = cand_heat[c]; r = {}
        col = f"heat_{c}"
        present = fwd[col].reindex(fdays).notna() if col in fwd else pd.Series(False, index=fdays)
        r["forward_days"] = int(len(fdays)); r["forward_coverage"] = float(present.mean()) if len(fdays) else 0.0
        ct = [t for t in tops.values() if t + pd.Timedelta(days=TOP_WIN) <= last and np.isfinite(h.get(t, np.nan))]
        cb = [b for b in bottoms.values() if b + pd.Timedelta(days=LOW_WIN) <= last and np.isfinite(h.get(b, np.nan))]
        w = lambda s, t, k: s.loc[t - pd.Timedelta(days=k): t + pd.Timedelta(days=k)]
        top_max = [float(w(h, t, TOP_WIN).max()) for t in ct]; low_mean = [float(w(h, b, LOW_WIN).mean()) for b in cb]
        r["covered_tops"] = [str(t.date()) for t in ct]; r["top_max_heat"] = top_max
        r["covered_lows"] = [str(b.date()) for b in cb]; r["low_mean_heat"] = low_mean
        r["history_pass"] = bool(len(ct) >= MIN_TOPS and all(x >= HOT for x in top_max) and all(x <= COOL for x in low_mean))
        ps = v2_fam["v2_price_structure"] if "v2_price_structure" in v2_fam else v2_fam["price_structure"]
        both = pd.concat([h, ps], axis=1).dropna()
        rho = float(both.iloc[:, 0].rank().corr(both.iloc[:, 1].rank())) if len(both) > 30 else float("nan")
        r["spearman_vs_price_structure"] = rho; r["nonredundant_pass"] = bool(np.isfinite(rho) and abs(rho) < MAX_RHO)
        fam = v2_fam.rename(columns=lambda x: x.replace("v2_", ""))[V2_FAMILIES]
        sh = shadow_scores(fam, cand_heat)[{"miner_income": "shadow_puell", "leverage": "shadow_lev", "liquidity": "shadow_liq"}[c]]
        st = [float(w(sh, t, TOP_WIN).max()) for t in ct]; vt = [float(w(v2_score, t, TOP_WIN).max()) for t in ct]
        sl = [float(w(sh, b, LOW_WIN).mean()) for b in cb]; vl = [float(w(v2_score, b, LOW_WIN).mean()) for b in cb]
        r["shadow_vs_v2_tops"] = [float(np.mean(st)) if st else None, float(np.mean(vt)) if vt else None]
        r["shadow_vs_v2_lows"] = [float(np.mean(sl)) if sl else None, float(np.mean(vl)) if vl else None]
        r["improve_pass"] = bool(st and sl and np.mean(st) >= np.mean(vt) and np.mean(sl) <= np.mean(vl) + LOW_SLACK)
        fh = fwd[col].reindex(fdays) if col in fwd else pd.Series(np.nan, index=fdays)
        fv = fwd["v2_score"].reindex(fdays) if "v2_score" in fwd else pd.Series(np.nan, index=fdays)
        r["forward_conflict_days"] = int(_longest(((fh >= HOT) & (fv < COOL)).fillna(False).tolist()))
        r["forward_pass"] = r["forward_conflict_days"] < CONFLICT_DAYS
        if r["forward_coverage"] < COVER_DROP or not r["history_pass"] or not r["nonredundant_pass"]: v = "DROP"
        elif r["forward_coverage"] >= COVER_ADOPT and r["improve_pass"] and r["forward_pass"]: v = "ADOPT_INTO_V4_CANDIDATE"
        else: v = "KEEP_TRACKING"
        r["verdict"] = v; res[c] = r
    return res
