"""Shadow signal candidates for the 2027-10-25 review (pipeline/candidates/PREREG_CANDIDATES.md). Operational code: fetches
free public data, applies the hash-locked formulas in pipeline/candidates/candidates_spec.py, and writes
  data/candidates/shadow_backfill.csv  history from the data available on 2026-10-26, in_sample=1 (written once)
  data/candidates/shadow_log.csv       forward log, one row per CoinMetrics close date from 2026-10-26, append-only
  data/candidates.json                 display values for the site (no NaN)
NOT an input of the Cycle Heat Score, the scorecard, v1/v2/v3, the band test or the daily chain record. Failure-tolerant:
each source falls back to its cache, and any failure here leaves the official files untouched (update.sh ignores its exit).
Sources and terms:
  CoinMetrics Community API (IssTotUSD, SplyCur, CapMrktCurUSD): CC BY-NC 4.0; cache public, like pipeline/cache/coinmetrics.json
  CFTC Commitments of Traders (CME Bitcoin 133741, Micro Bitcoin 133742): public domain; cache public
  FRED (WALCL, WTREGEN, RRPONTSYD, DTWEXBGS; Federal Reserve / NY Fed data): public domain series; cache public
  OKX rubik open interest, Deribit book summary: exchange data; raw caches PRIVATE (gitignored, Actions cache only),
    only the derived share of market cap is published
  Spot ETF flows: no source with terms that allow republishing was found; not fetched.
Test hooks: OFFLINE=1 (caches only), GATE_NOW=YYYY-MM-DDTHH:MM (clock, as scripts/score_gate.py)."""
import csv, io, json, math, os, sys, time, datetime as dt
import numpy as np, pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "pipeline", "candidates"), os.path.join(HERE, "pipeline")]
import candidates_spec as cs   # noqa: E402  (imports the frozen pipeline/v2_spec.py read-only)
CD = os.path.join(HERE, "pipeline", "cache", "candidates"); os.makedirs(CD, exist_ok=True)
DD = os.path.join(HERE, "data", "candidates"); os.makedirs(DD, exist_ok=True)
LOG, BACK, OUT = os.path.join(DD, "shadow_log.csv"), os.path.join(DD, "shadow_backfill.csv"), os.path.join(HERE, "data", "candidates.json")
UA = {"User-Agent": "my-btc-cycle-model/1.0 (https://euthymia686.github.io/my-btc-cycle-model/; research shadow log)"}
OFF = os.environ.get("OFFLINE") == "1"
DEADLINE_HOUR = 12
ERR = {}

def now():
    s = os.environ.get("GATE_NOW")
    return dt.datetime.fromisoformat(s) if s else dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
def deadline(close): return dt.datetime.combine(close + dt.timedelta(days=1), dt.time(DEADLINE_HOUR))
def stamp(): return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def cache_rw(name, fn):
    p = os.path.join(CD, name); old = json.load(open(p)) if os.path.exists(p) else None
    if OFF: ERR[name] = "OFFLINE=1, using cache"; return old
    try:
        new = fn(old); tmp = p + ".tmp"; json.dump(new, open(tmp, "w"), separators=(",", ":")); os.replace(tmp, p); return new
    except Exception as e:
        ERR[name] = f"{type(e).__name__}: {str(e)[:160]}"; return old

def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=60, **kw); r.raise_for_status(); return r

# ---------------------------------------------------------------- fetchers
def f_cm(old):
    url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
    params = {"assets": "btc", "metrics": "IssTotUSD,SplyCur,CapMrktCurUSD", "frequency": "1d", "start_time": "2010-07-18",
              "page_size": 10000, "paging_from": "start"}
    rows, nxt = [], None
    for _ in range(20):
        j = get(nxt or url, params=None if nxt else params).json(); rows += j["data"]; nxt = j.get("next_page_url")
        if not nxt: break
    if len(rows) < 5000: raise ValueError(f"only {len(rows)} rows")
    return {"source": "CoinMetrics Community API (CC BY-NC 4.0)", "fetched_utc": stamp(),
            "rows": [{k: r.get(k) for k in ("time", "IssTotUSD", "SplyCur", "CapMrktCurUSD")} for r in rows]}

def f_cftc(old):
    q = {"$select": "report_date_as_yyyy_mm_dd,cftc_contract_market_code,open_interest_all",
         "$where": "cftc_contract_market_code in('133741','133742')", "$order": "report_date_as_yyyy_mm_dd", "$limit": 50000}
    d = get("https://publicreporting.cftc.gov/resource/6dca-aqww.json", params=q).json()
    out = {}
    for x in d: out.setdefault(x["cftc_contract_market_code"], {})[x["report_date_as_yyyy_mm_dd"][:10]] = float(x["open_interest_all"])
    if len(out.get("133741", {})) < 300: raise ValueError("too few CFTC rows")
    return {"source": "CFTC Commitments of Traders, legacy futures-only (public domain)", "fetched_utc": stamp(), "open_interest_contracts": out}

FRED = ["WALCL", "WTREGEN", "RRPONTSYD", "DTWEXBGS"]
def f_fred(old):
    out = {}
    for sid in FRED:
        t = get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": sid}).text
        rd = list(csv.reader(io.StringIO(t)))[1:]
        out[sid] = {r[0]: float(r[1]) for r in rd if len(r) > 1 and r[1] not in (".", "")}
        if len(out[sid]) < 500: raise ValueError(f"{sid}: {len(out[sid])} rows")
        time.sleep(0.5)
    return {"source": "FRED, Federal Reserve Bank of St. Louis (Federal Reserve H.4.1/H.10, NY Fed); public domain series",
            "fetched_utc": stamp(), "series": out}

def f_okx(old):   # PRIVATE raw
    d = get("https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume", params={"ccy": "BTC", "period": "1D"}).json()
    if d.get("code") != "0" or not d.get("data"): raise ValueError(str(d)[:120])
    daily = dict((old or {}).get("daily", {}))
    for ts, oi, _vol in d["data"]:
        daily[dt.datetime.fromtimestamp(int(ts) / 1000, dt.timezone.utc).strftime("%Y-%m-%d")] = float(oi)
    return {"source": "OKX rubik contracts open interest, BTC, 1D (USD)", "fetched_utc": stamp(), "daily": dict(sorted(daily.items()))}

def f_deribit(old):   # PRIVATE raw; one snapshot per UTC day (first fetch of the day kept)
    r = get("https://www.deribit.com/api/v2/public/get_book_summary_by_currency", params={"currency": "BTC", "kind": "future"}).json()["result"]
    usd = float(sum(x["open_interest"] for x in r))   # inverse BTC futures/perpetual: open interest is in USD
    daily = dict((old or {}).get("daily", {})); daily.setdefault(dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"), usd)
    return {"source": "Deribit public book summary, BTC futures + perpetual open interest (USD)", "fetched_utc": stamp(), "daily": dict(sorted(daily.items()))}

def ser(d):
    return pd.Series({pd.Timestamp(k): v for k, v in (d or {}).items()}, dtype=float).sort_index()

# ---------------------------------------------------------------- compute
COLS = ["close_date", "written_utc", "in_sample", "puell", "lev_ratio", "lev_stretch", "liq_netliq_musd", "liq_g_nl", "liq_g_usd",
        "heat_miner_income", "heat_leverage", "heat_liquidity", "v2_score", "v2_price_structure", "v2_onchain_valuation",
        "v2_network_usage", "v2_attention", "v2_timing", "shadow_all", "shadow_puell", "shadow_lev", "shadow_liq",
        "oi_okx_mcap", "oi_deribit_mcap", "cftc_report_used", "fred_walcl_used", "fred_dxy_used", "missing"]

def compute():
    cm = cache_rw("cm_candidates.json", f_cm); cf = cache_rw("cftc_cot.json", f_cftc); fr = cache_rw("fred.json", f_fred)
    okx = cache_rw("okx_oi.json", f_okx); der = cache_rw("deribit_oi.json", f_deribit)
    if not cm: raise RuntimeError("no CoinMetrics candidate data")
    df = pd.DataFrame(cm["rows"]); df["date"] = pd.to_datetime(df["time"]).dt.tz_localize(None).dt.normalize()
    df = df.set_index("date").drop(columns="time").apply(pd.to_numeric, errors="coerce").sort_index()
    idx = pd.date_range(df.index.min(), df.index.max(), freq="D"); df = df.reindex(idx)
    R = pd.DataFrame(index=idx)
    R["puell"] = cs.puell(df["IssTotUSD"])
    if cf:
        cot = {k: ser(v) for k, v in cf["open_interest_contracts"].items()}
        R["lev_ratio"], R["lev_stretch"] = cs.leverage(cot, df["SplyCur"], idx)
        rep = cs.cme_btc_oi(cot); rd = pd.Series(rep.index, index=rep.index)
        R["cftc_report_used"] = cs.asof(pd.Series(rd.map(lambda t: t.value), index=rd.index).astype(float), idx, cs.LAGS["cftc"], cs.STALE["cftc"])
    if fr:
        s = {k: ser(v) for k, v in fr["series"].items()}
        nl, usd, g1, g2 = cs.liquidity(s["WALCL"], s["WTREGEN"], s["RRPONTSYD"], s["DTWEXBGS"], idx)
        R["liq_netliq_musd"], R["liq_g_nl"], R["liq_g_usd"] = nl, g1, g2
        for k, sid in [("fred_walcl_used", "WALCL"), ("fred_dxy_used", "DTWEXBGS")]:
            v = s[sid]; R[k] = cs.asof(pd.Series(v.index.map(lambda t: t.value), index=v.index).astype(float), idx, cs.LAGS["walcl" if sid == "WALCL" else "dxy"], cs.STALE["walcl" if sid == "WALCL" else "dxy"])
    H = pd.DataFrame(index=idx)
    H["miner_income"] = cs.heat(R["puell"])
    H["leverage"] = cs.heat(R["lev_stretch"]) if "lev_stretch" in R else np.nan
    H["liquidity"] = cs.liquidity_heat(R["liq_g_nl"], R["liq_g_usd"]) if "liq_g_nl" in R else np.nan
    v2p = os.path.join(HERE, "pipeline", "out", "score_v2_history.csv")
    v2 = pd.read_csv(v2p, index_col=0, parse_dates=True).reindex(idx)
    S = cs.shadow_scores(v2.rename(columns=lambda x: x.replace("v2_", ""))[cs.V2_FAMILIES], H)
    mcap = df["CapMrktCurUSD"]
    out = pd.DataFrame(index=idx)
    for c in ["puell", "lev_ratio", "lev_stretch", "liq_netliq_musd", "liq_g_nl", "liq_g_usd"]: out[c] = R.get(c, np.nan)
    for c in cs.SCORED: out[f"heat_{c}"] = H[c]
    out["v2_score"] = v2["score_v2"]
    for f in cs.V2_FAMILIES: out[f"v2_{f}"] = v2[f"v2_{f}"]
    for c in S: out[c] = S[c]
    out["oi_okx_mcap"] = (ser((okx or {}).get("daily")).reindex(idx) / mcap) if okx else np.nan
    out["oi_deribit_mcap"] = (ser((der or {}).get("daily")).reindex(idx) / mcap) if der else np.nan
    for k in ["cftc_report_used", "fred_walcl_used", "fred_dxy_used"]:
        v = R.get(k); out[k] = v.map(lambda x: "" if not np.isfinite(x) else str(pd.Timestamp(int(x)).date())) if v is not None else ""
    out["missing"] = [";".join(c for c in cs.SCORED if not np.isfinite(out.at[d, f"heat_{c}"])) for d in idx]
    last_close = df.dropna(subset=["IssTotUSD", "SplyCur"], how="all").index.max()
    return out, df, last_close, {"okx": okx, "deribit": der, "fred": fr, "cftc": cf}

def fmt(v):
    if isinstance(v, str): return v
    if v is None or (isinstance(v, float) and not math.isfinite(v)): return ""
    return f"{v:.6g}" if abs(v) < 1e4 else f"{v:.1f}"

def row(out, d, in_sample):
    r = out.loc[d]; vals = {c: fmt(r[c]) if c in r.index else "" for c in COLS}
    vals.update(close_date=str(d.date()), written_utc=stamp(), in_sample=str(in_sample)); return [vals[c] for c in COLS]

def main():
    out, df, last_close, raw = compute()
    fwd0 = pd.Timestamp(cs.FORWARD_FROM)
    if not os.path.exists(BACK):     # once: history before the forward period, from today's data vintage
        with open(BACK, "w", newline="") as f:
            w = csv.writer(f); w.writerow(COLS)
            for d in out.index[out.index < fwd0]: w.writerow(row(out, d, 1))
        print(f"candidates: backfill written ({(out.index < fwd0).sum()} rows, in-sample)")
    if not os.path.exists(LOG):
        with open(LOG, "w", newline="") as f: csv.writer(f).writerow(COLS)
    have = set(pd.read_csv(LOG, usecols=["close_date"])["close_date"].astype(str))
    t = now(); added = []
    # main CoinMetrics close (the scorecard's close date); the candidates' own fetch may lag, so use the official cache's latest date
    cmain = json.load(open(os.path.join(HERE, "pipeline", "cache", "coinmetrics.json")))
    rows = cmain["data"] if isinstance(cmain, dict) else cmain
    official = pd.Timestamp(max(x["time"] for x in rows if x.get("PriceUSD") not in (None, ""))[:10])
    for d in pd.date_range(fwd0, official, freq="D"):
        ds = str(d.date())
        if ds in have: continue
        complete = d in out.index and not out.at[d, "missing"]
        if not complete and t < deadline(d.date()):
            print(f"candidates: {ds} waits (missing {out.at[d, 'missing'] if d in out.index else 'all'}; deadline {deadline(d.date())} UTC)"); continue
        if d not in out.index:
            out.loc[d] = np.nan; out.at[d, "missing"] = ";".join(cs.SCORED)
            for k in ["cftc_report_used", "fred_walcl_used", "fred_dxy_used"]: out.at[d, k] = ""
        added.append(row(out, d, 0))
    if added:
        with open(LOG, "a", newline="") as f: csv.writer(f).writerows(added)
    print(f"candidates: log +{len(added)} rows (official close {official.date()}, candidate data to {last_close.date()})")
    write_json(out, raw)
    if ERR: print("candidates: source notes:", json.dumps(ERR), file=sys.stderr)

def write_json(out, raw):
    def last(col):
        s = out[col].dropna() if col in out else pd.Series(dtype=float)
        return (str(s.index[-1].date()), float(s.iloc[-1])) if len(s) else (None, None)
    def num(x): return None if x is None or not math.isfinite(x) else round(float(x), 4)
    def spark(col, n=365):
        s = out[col].dropna().iloc[-n:] if col in out else pd.Series(dtype=float)
        s = s.iloc[::7]
        return [[str(i.date()), round(float(v), 1)] for i, v in s.items()]
    tiles = []
    d, v = last("heat_miner_income"); _, p = last("puell")
    tiles.append({"id": "puell", "name": "Puell Multiple", "value": num(p), "value_fmt": None if p is None else f"{p:.2f}x",
                  "heat": num(v), "as_of": d, "update": "daily (CoinMetrics close)", "spark": spark("heat_miner_income"),
                  "what": "Miners' daily issuance revenue in USD vs its 1-year average. High = miners earning far above normal, historically near cycle tops.",
                  "source": "CoinMetrics Community (CC BY-NC 4.0)"})
    d, v = last("heat_leverage"); _, lr = last("lev_ratio"); rep = out["cftc_report_used"].replace("", np.nan).dropna()
    _, ok = last("oi_okx_mcap"); _, de = last("oi_deribit_mcap")
    tiles.append({"id": "leverage", "name": "Futures leverage", "value": num(lr), "value_fmt": None if lr is None else f"{lr*100:.2f}% of mcap",
                  "heat": num(v), "as_of": d, "report_date": rep.iloc[-1] if len(rep) else None,
                  "update": "weekly (CFTC report, Tuesday data published Friday); exchange context daily",
                  "context": {"okx_oi_mcap": num(ok), "deribit_oi_mcap": num(de)}, "spark": spark("heat_leverage"),
                  "what": "CME bitcoin futures open interest as a share of market cap, vs its own past year. High = leverage building up.",
                  "source": "CFTC Commitments of Traders (public domain); OKX/Deribit context"})
    d, v = last("heat_liquidity"); wu = out["fred_walcl_used"].replace("", np.nan).dropna(); _, nl = last("liq_netliq_musd")
    tiles.append({"id": "liquidity", "name": "Liquidity (Fed + dollar)", "value": num(nl), "value_fmt": None if nl is None else f"${nl/1e6:.2f}T net",
                  "heat": num(v), "as_of": wu.iloc[-1] if len(wu) else None, "computed_for": d,
                  "update": "weekly (Fed balance sheet, Thursdays); dollar index daily with a 1-week lag", "spark": spark("heat_liquidity"),
                  "what": "Fed net liquidity (balance sheet minus Treasury account and reverse repo) and the dollar, each vs a year ago. High = liquidity growing, dollar falling. A skeptical test.",
                  "source": "FRED / Federal Reserve (public domain)"})
    tiles.append({"id": "etf_flows", "name": "Spot ETF flows", "value": None, "heat": None, "as_of": None, "omitted": True,
                  "update": "not shown: no free source whose terms allow republishing",
                  "what": "Daily net money into US spot bitcoin ETFs. Would be display only (history starts 2024, too short to test).",
                  "source": "none yet"})
    d, sa = last("shadow_all")
    J = {"generated_utc": stamp(), "note": "Being tested for the 2027-10-25 review. Not part of the Cycle Heat Score.",
         "prereg": "pipeline/candidates/PREREG_CANDIDATES.md", "review_date": cs.REVIEW_DATE, "shadow_all": num(sa), "shadow_as_of": d,
         "tiles": tiles, "source_errors": {k: v for k, v in ERR.items() if not v.startswith("OFFLINE")}}
    s = json.dumps(J, separators=(",", ":"), allow_nan=False)
    tmp = OUT + ".tmp"; open(tmp, "w").write(s); os.replace(tmp, OUT)

if __name__ == "__main__":
    main()
