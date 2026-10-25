"""FROZEN (band pre-registration). Daily, after scripts/update.sh, from pipeline/:  PYTHONPATH=.:frozen/band python frozen/band/band_log_daily.py
Append-only records (never edits an earlier row; one run per UTC day; every step is failure-tolerant and never fails the update):
  data/band_prices.csv          first-print daily close log used for ALL grading (PREREG_BAND.md section 4.0)
  data/band_price_revisions.csv later differences between the source and the first print (information only, never applied)
  data/band_log.csv             live band, live corrected band, live S1/S3 (drift record; secondary)
  data/band_rerun.json          written ONCE: S1-R and S3-R, the first run after the 2025-cycle low window closes (2027-10-03)
  data/halving_2028.json        written ONCE: UTC date of block 1,050,000 (secondary halving-relative readout only)"""
import csv, datetime as dt, json, os, statistics, sys, traceback, urllib.request, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import lib
DATA = os.path.join(lib.HERE, "..", "data"); TODAY = dt.datetime.now(dt.timezone.utc).date()
FALLBACK_AFTER_DAYS = 7
def jget(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "btc-cycle-band-log"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)

def fallback_close(day):
    """Median of the UTC daily candle closes (close = price at 00:00 UTC of the next day) of three named exchanges. Needs >= 2 of 3."""
    t0 = int(pd.Timestamp(day).timestamp()); vals = {}
    for name, fn in [
        ("coinbase", lambda: next(float(c[4]) for c in jget(f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start={t0}&end={t0 + 86400}") if int(c[0]) == t0)),
        ("kraken", lambda: next(float(c[4]) for c in jget(f"https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440&since={t0 - 1}")["result"]["XXBTZUSD"] if int(c[0]) == t0)),
        ("bitstamp", lambda: next(float(c["close"]) for c in jget(f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=2&start={t0}")["data"]["ohlc"] if int(c["timestamp"]) == t0))]:
        try: vals[name] = fn()
        except Exception: pass
    return (statistics.median(vals.values()), "fallback_median(" + ",".join(f"{k}={v:.2f}" for k, v in sorted(vals.items())) + ")") if len(vals) >= 2 else (None, None)

def update_prices():
    f = os.path.join(DATA, "band_prices.csv"); rv = os.path.join(DATA, "band_price_revisions.csv")
    old = pd.read_csv(f, dtype={"date": str}) if os.path.exists(f) else pd.DataFrame(columns=["date", "close", "source", "logged_utc"])
    have = dict(zip(old.date, old.close.astype(float))); cm = lib.coinmetrics()["price"].dropna()
    cm = cm[cm.index >= pd.Timestamp("2026-10-01")]; new, revs = [], []
    for d, v in cm.items():
        k = str(d.date())
        if k not in have: new.append([k, f"{v:.6f}", "coinmetrics_PriceUSD", TODAY.isoformat()])
        elif abs(v / have[k] - 1) > 1e-9: revs.append([TODAY.isoformat(), k, f"{have[k]:.6f}", f"{v:.6f}", f"{v / have[k] - 1:+.4%}"])
    last = max([pd.Timestamp(x) for x in list(have) + [r[0] for r in new]] or [cm.index[-1]])
    d = last + pd.Timedelta(days=1)                                       # dates CoinMetrics still has not published
    while d.date() <= TODAY - dt.timedelta(days=FALLBACK_AFTER_DAYS):
        v, src = fallback_close(d.date())
        if v is None: break                                               # retry tomorrow; never guess
        new.append([str(d.date()), f"{v:.6f}", src, TODAY.isoformat()]); d += pd.Timedelta(days=1)
    for path, hdr, rows in ((f, ["date", "close", "source", "logged_utc"], new), (rv, ["seen_utc", "date", "first_print", "source_now", "diff"], revs)):
        if not rows: continue
        exists = os.path.exists(path)
        with open(path, "a", newline="") as fh:
            w = csv.writer(fh); exists or w.writerow(hdr); w.writerows(sorted(rows))

def band_log_row():
    import bandlib as B, corrected_rule as CR, laws_rule as LR
    T = B.P.index[-1] + pd.Timedelta(days=1)
    bd, info = B.band(T, pd.Timestamp("2031-03-30"), "damp"); bd = (10 ** bd).dropna()
    nx = bd.loc[pd.Timestamp("2028-04-11"):]; pk = nx.md.idxmax(); lo = nx.loc[pk:].md.idxmin()
    row = dict(run_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), data_to=str(B.P.index[-1].date()), rho=info["rho"], a=info["a"], b=info["b"],
               peak_date=str(pk.date()), peak_mid=bd.md[pk], peak_lo=bd.lo[pk], peak_hi=bd.hi[pk], low_date=str(lo.date()), low_mid=bd.md[lo], low_lo=bd.lo[lo], low_hi=bd.hi[lo])
    targets = [d for d in pd.date_range("2027-03-31", "2030-09-30", freq="QE")] + [pd.Timestamp("2029-09-25"), pd.Timestamp("2030-06-04")]
    for d in targets:
        for c in ("lo", "md", "hi"): row[f"{d.date()}_{c}"] = float(bd[c].get(d, np.nan))
    row.update({k: "" for k in ("corr_top", "corr_top_lo", "corr_top_hi", "corr_tp", "corr_low", "corr_low_lo", "corr_low_hi", "corr_tl", "corr_included_top", "corr_error")})
    try:
        cor, s = CR.corrected(bd, T)
        row.update(corr_top=s["ens_top"], corr_top_lo=s["top_range"][0], corr_top_hi=s["top_range"][1], corr_tp=s["tp"],
                   corr_low=s["ens_low"], corr_low_lo=s["low_range"][0], corr_low_hi=s["low_range"][1], corr_tl=s["tl"], corr_included_top="|".join(s["included_top"]))
    except Exception as e: row["corr_error"] = repr(e)[:200]
    L = LR.run(T)
    for k in ("S1", "S3"): row.update({f"{k}_top": L[k]["top"], f"{k}_lo": L[k]["range"][0], f"{k}_hi": L[k]["range"][1]})
    row.update(low2025_date=L["S1"]["low_used"]["date"], low2025_price=L["S1"]["low_used"]["price"], low2025_complete=L["S1"]["low_used"]["complete"])
    return row, L, T

def append_log(row):
    f = os.path.join(DATA, "band_log.csv")
    if os.path.exists(f):
        last = list(csv.DictReader(open(f)))
        if last and last[-1]["run_utc"][:10] == row["run_utc"][:10]: return            # one row per UTC day
        cols = list(last[0].keys()) if last else list(row)
    else: cols = list(row)
    fmt = lambda v: f"{v:.8g}" if isinstance(v, float) else str(v)
    exists = os.path.exists(f)
    with open(f, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); exists or w.writeheader(); w.writerow({k: fmt(row.get(k, "")) for k in cols})

def rerun_once(L, T):
    f = os.path.join(DATA, "band_rerun.json")
    if os.path.exists(f) or not L["S1"]["low_used"]["complete"]: return
    json.dump(dict(written_utc=dt.datetime.now(dt.timezone.utc).isoformat(), origin=str(T.date()), rule="PREREG_BAND.md 11.2 (S1-R, S3-R)",
                   **{f"{k}-R": dict(top=L[k]["top"], range=L[k]["range"], x=L[k]["x"], low_used=L[k]["low_used"]) for k in ("S1", "S3")}),
              open(f, "w"), indent=1, default=float)

def halving_once():
    f = os.path.join(DATA, "halving_2028.json")
    if os.path.exists(f) or TODAY < dt.date(2027, 12, 1): return
    try:
        h = urllib.request.urlopen("https://mempool.space/api/block-height/1050000", timeout=30).read().decode().strip()
        ts = jget(f"https://mempool.space/api/block/{h}")["timestamp"]
        json.dump(dict(block=1050000, hash=h, utc=dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(),
                       date=str(dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()), source="mempool.space"), open(f, "w"), indent=1)
    except Exception: pass                                                  # not mined yet or source down: retry tomorrow

if __name__ == "__main__":
    for step in ("prices", "log", "halving"):
        try:
            if step == "prices": update_prices()
            elif step == "log": row, L, T = band_log_row(); append_log(row); rerun_once(L, T)
            else: halving_once()
        except Exception: print(f"::warning::band_log_daily step {step} failed"); traceback.print_exc()
