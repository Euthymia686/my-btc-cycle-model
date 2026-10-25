"""My BTC Cycle Model - data fetch + signal engine (primary data only).
Every fetch is cached in cache/; if a source fails, the last cached copy is used and the failure is recorded."""
import json, os, time, bisect, datetime as dt
import numpy as np, pandas as pd, requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)
UA = {"User-Agent": "my-btc-cycle-model/1.0 (personal research)"}
GENESIS = pd.Timestamp("2009-01-03")
HALVINGS = [pd.Timestamp(x) for x in ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20"]]
NEXT_HALVING_BLOCK = 1_050_000
HORIZON = pd.Timestamp("2028-12-31")   # display horizon for the projection fan (end of the next halving cycle's first year)
STATUS = {}

# ---------------------------------------------------------------- cache helpers
def _cpath(name): return os.path.join(CACHE, name)
def _save(name, obj):
    with open(_cpath(name), "w") as f: json.dump({"saved_utc": dt.datetime.utcnow().isoformat(timespec="seconds"), "data": obj}, f)
def _load(name):
    p = _cpath(name)
    if not os.path.exists(p): return None, None
    with open(p) as f: j = json.load(f)
    return j["data"], j["saved_utc"]
def cached(name, fn):
    """Run fn(); on success cache it, on failure fall back to cache. Records status."""
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore"); d = fn()
        _save(name, d); STATUS[name] = {"ok": True, "from": "live"}; return d
    except Exception as e:
        d, t = _load(name)
        STATUS[name] = {"ok": d is not None, "from": f"cache {t}" if d is not None else "unavailable", "error": f"{type(e).__name__}: {e}"[:200]}
        return d

# ---------------------------------------------------------------- sources
def _cm():
    url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
    params = {"assets": "btc", "metrics": "PriceUSD,CapMrktCurUSD,CapMVRVCur,SplyCur,AdrActCnt", "frequency": "1d",
              "start_time": "2010-07-18", "page_size": 10000}
    rows, nxt = [], None
    for _ in range(20):
        r = requests.get(nxt or url, params=None if nxt else params, headers=UA, timeout=60); r.raise_for_status()
        j = r.json(); rows += j["data"]; nxt = j.get("next_page_url")
        if not nxt: break
    if len(rows) < 5000: raise ValueError(f"only {len(rows)} rows")
    return rows
def coinmetrics():
    rows = cached("coinmetrics.json", _cm)
    df = pd.DataFrame(rows); df["date"] = pd.to_datetime(df["time"]).dt.tz_localize(None).dt.normalize()
    df = df.set_index("date").drop(columns=["asset", "time"]).apply(pd.to_numeric, errors="coerce")
    return df.rename(columns={"PriceUSD": "price", "CapMrktCurUSD": "mcap", "CapMVRVCur": "mvrv", "SplyCur": "supply", "AdrActCnt": "active"})

def coingecko_live():
    def f():
        r = requests.get("https://api.coingecko.com/api/v3/simple/price", params={"ids": "bitcoin", "vs_currencies": "usd",
                         "include_24hr_change": "true", "include_last_updated_at": "true"}, headers=UA, timeout=20)
        r.raise_for_status(); b = r.json()["bitcoin"]
        return {"price": b["usd"], "chg24": b.get("usd_24h_change"), "t": b.get("last_updated_at")}
    return cached("coingecko.json", f)

def _yf_hist(tk, period):
    import yfinance as yf
    h = yf.Ticker(tk).history(period=period, interval="1d", auto_adjust=False)
    if h.empty: raise ValueError("empty")
    h.index = h.index.tz_localize(None) if h.index.tz is None else h.index.tz_convert(None)
    return {"dates": [d.strftime("%Y-%m-%d") for d in h.index], "close": [float(x) for x in h["Close"]]}
def yahoo_btc(): return cached("yahoo_btc.json", lambda: _yf_hist("BTC-USD", "5y"))
def yahoo_mstr(): return cached("yahoo_mstr.json", lambda: _yf_hist("MSTR", "6y"))
def strategy_kpis():
    def f():
        a = requests.get("https://api.strategy.com/btc/bitcoinKpis", headers=UA, timeout=20); a.raise_for_status()
        b = requests.get("https://api.strategy.com/btc/mstrKpiData", headers=UA, timeout=20); b.raise_for_status()
        ra = a.json()["results"]; rb = b.json()[0]
        return {"holdings": int(str(ra["btcHoldings"]).replace(",", "")), "mnav_strategy": ra.get("mNav"),
                "mstr_close": rb.get("ufPrice"), "mstr_time": rb.get("timeStampUtc"),
                "mcap_musd": float(str(rb.get("marketCap")).replace(",", "")), "ev_musd": float(str(rb.get("entVal")).replace(",", "")),
                "asof": a.json().get("timestamp")}
    return cached("strategy.json", f)

def edgar_latest_8k():
    def f():
        r = requests.get("https://data.sec.gov/submissions/CIK0001050446.json", headers={"User-Agent": "personal research btc-model@example.com"}, timeout=20)
        r.raise_for_status(); rec = r.json()["filings"]["recent"]
        for form, date, acc, doc in zip(rec["form"], rec["filingDate"], rec["accessionNumber"], rec["primaryDocument"]):
            if form == "8-K":
                return {"date": date, "url": f"https://www.sec.gov/Archives/edgar/data/1050446/{acc.replace('-', '')}/{doc}"}
        raise ValueError("no 8-K")
    return cached("edgar.json", f)

def shares_outstanding():
    """Shares: Yahoo impliedSharesOutstanding (primary filings-derived); fallback cached."""
    def f():
        import yfinance as yf
        i = yf.Ticker("MSTR").info
        s = i.get("impliedSharesOutstanding") or i.get("sharesOutstanding")
        if not s: raise ValueError("no shares")
        return {"shares": int(s)}
    return cached("shares.json", f)

def google_trends():
    def f():
        from pytrends.request import TrendReq
        p = TrendReq(hl="en-US", tz=0, timeout=(10, 30))
        p.build_payload(["bitcoin"], timeframe="all"); m = p.interest_over_time()
        time.sleep(2)
        p.build_payload(["bitcoin"], timeframe="today 5-y"); w = p.interest_over_time()
        return {"monthly": {d.strftime("%Y-%m-%d"): int(v) for d, v in m["bitcoin"].items()},
                "weekly": {d.strftime("%Y-%m-%d"): int(v) for d, v in w["bitcoin"].items()}}
    return cached("trends.json", f)

def block_height():
    def f():
        r = requests.get("https://mempool.space/api/blocks/tip/height", headers=UA, timeout=20); r.raise_for_status()
        return {"height": int(r.text)}
    return cached("block.json", f)

# ---------------------------------------------------------------- signals
SIGNALS = ["cycle_day", "mayer", "p200w", "trend_mult", "mvrv_z", "pi_ratio", "trends", "activity"]
LABELS = {"cycle_day": "Halving-cycle timing", "mayer": "Mayer Multiple (price / 200-day MA)",
          "p200w": "Price / 200-week MA", "trend_mult": "Price / trend line (power-law fit)",
          "mvrv_z": "MVRV Z-score", "pi_ratio": "Pi Cycle ratio (111DMA / 2x350DMA)",
          "trends": "Google search interest", "activity": "Active addresses (30d / 365d avg)"}
SHORT = {"cycle_day": "Cycle timing", "mayer": "Mayer Multiple", "p200w": "Price / 200W MA", "trend_mult": "Price / trend line",
         "mvrv_z": "MVRV Z", "pi_ratio": "Pi Cycle ratio", "trends": "Search interest", "activity": "Address activity"}

def last_halving(d):
    prev = [h for h in HALVINGS if h <= d]
    return prev[-1] if prev else None

def expanding_trend(price):
    """Causal power-law fit: each day's fit log10(p) = a + b*log10(days since genesis) uses only data up to that day."""
    d = (price.index - GENESIS).days.values.astype(float)
    x, y = np.log10(d), np.log10(price.values)
    n = np.arange(1, len(x) + 1); sx, sy = np.cumsum(x), np.cumsum(y); sxx, sxy = np.cumsum(x * x), np.cumsum(x * y)
    b = (n * sxy - sx * sy) / np.where(n * sxx - sx ** 2 == 0, np.nan, n * sxx - sx ** 2); a = (sy - b * sx) / n
    fit = a + b * x; fit[:365] = np.nan
    return pd.Series(10 ** (y - fit), index=price.index), a[-1], b[-1]

def build_signals(cm, trends=None):
    df = cm.copy().dropna(subset=["price"])
    p = df["price"]
    df["ma200"] = p.rolling(200).mean(); df["ma1400"] = p.rolling(1400).mean()
    df["mayer"] = p / df["ma200"]; df["p200w"] = p / df["ma1400"]
    df["pi_ratio"] = p.rolling(111).mean() / (2 * p.rolling(350).mean())
    df["trend_mult"], a, b = expanding_trend(p)
    rcap = df["mcap"] / df["mvrv"]; df["realized_price"] = rcap / df["supply"]
    df["mvrv_z"] = (df["mcap"] - rcap) / df["mcap"].expanding(365).std()
    act = df["active"]; df["activity"] = act.rolling(30).mean() / act.rolling(365).mean()
    df["days_since_halving"] = [(d - last_halving(d)).days if last_halving(d) is not None else np.nan for d in df.index]
    if trends and trends.get("monthly"):
        m = pd.Series(trends["monthly"]); m.index = pd.to_datetime(m.index)
        m.index = m.index + pd.offsets.MonthBegin(1)          # month M is only known once M is over
        df["trends"] = m.reindex(df.index, method="ffill")
    else:
        df["trends"] = np.nan
    df["ath"] = p.cummax(); df["drawdown"] = p / df["ath"] - 1
    return df, (a, b)

def expanding_pct(s, min_obs=365):
    """Percentile (0-100) of each value vs all PRIOR values (strictly causal)."""
    out = np.full(len(s), np.nan); hist = []
    for i, v in enumerate(s.values):
        if not np.isnan(v):
            if len(hist) >= min_obs:
                lo = bisect.bisect_left(hist, v); hi = bisect.bisect_right(hist, v)
                out[i] = 100.0 * (lo + hi) / 2 / len(hist)
            bisect.insort(hist, v)
    return pd.Series(out, index=s.index)

def find_tops_bottoms(p):
    win = [("2011", "2011-01-01", "2012-06-30"), ("2013", "2013-07-01", "2014-12-31"), ("2017", "2017-01-01", "2018-12-31"),
           ("2021", "2021-01-01", "2022-12-31"), ("2025", "2025-01-01", None)]
    tops = {k: p.loc[s:e].idxmax() for k, s, e in win}
    keys = list(tops); bottoms = {}
    for i, k in enumerate(keys[:-1]):
        bottoms[k] = p.loc[tops[k]:tops[keys[i + 1]]].idxmin()
    return tops, bottoms

def cycle_heat(days, top_days, sigma_min=60):
    """Timing heat: 100 at the average halving-to-peak day of the calibration tops, Gaussian fall-off."""
    if not top_days: return pd.Series(np.nan, index=days.index)
    mu = float(np.mean(top_days)); sd = max(sigma_min, float(np.std(top_days)) if len(top_days) > 1 else sigma_min)
    return 100 * np.exp(-0.5 * ((days - mu) / sd) ** 2)

def heats(df, cal_top_days):
    H = pd.DataFrame(index=df.index)
    for s in SIGNALS:
        H[s] = cycle_heat(df["days_since_halving"], cal_top_days) if s == "cycle_day" else expanding_pct(df[s])
    return H

def score_from(H, weights=None, cols=None):
    cols = cols or SIGNALS
    w = pd.Series(weights if weights else {c: 1.0 for c in cols})[cols]
    X = H[cols]; m = X.notna()
    num = (X.fillna(0) * w).sum(1); den = (m * w).sum(1)
    sc = num / den.replace(0, np.nan)
    sc[m.sum(1) < 3] = np.nan            # need at least 3 signals
    return sc

def zone(h, hot, warm):
    if h is None or np.isnan(h): return "n/a"
    return "hot" if h >= hot else "warm" if h >= warm else "neutral" if h >= 40 else "cool"

def bs_call(S, K, T, r, sig):
    from scipy.stats import norm
    if T <= 0: return max(S - K, 0)
    d1 = (np.log(S / K) + (r + sig * sig / 2) * T) / (sig * np.sqrt(T)); d2 = d1 - sig * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
