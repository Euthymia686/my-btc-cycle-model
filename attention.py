"""Display-only attention signal: English Wikipedia daily pageviews of the "Bitcoin" article.
Source: Wikimedia REST pageviews API (per-article, en.wikipedia, all-access, agent=user, daily), data from 2015-07-01.
Heat = percentile of the 30-day average vs the prior 8 years of 30-day averages (prior data only, so it is walk-forward).
NOT an input of the Cycle Heat Score (v1/v2 are unchanged and keep using Google Trends). Writes data/wiki.json.
Failure-tolerant: on a source error the cached series is reused."""
import json, os, sys, datetime as dt
import numpy as np, pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "pipeline", "cache", "wiki_bitcoin.json"); OUT = os.path.join(HERE, "data", "wiki.json")
UA = {"User-Agent": "my-btc-cycle-model/1.0 (https://euthymia686.github.io/my-btc-cycle-model/; display-only attention signal)"}
API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Bitcoin/daily/{a}/{b}"
WIN = 2922  # 8 years of days

def fetch():
    end = (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=1)).strftime("%Y%m%d00")
    r = requests.get(API.format(a="2015070100", b=end), headers=UA, timeout=60); r.raise_for_status()
    s = {i["timestamp"][:8]: int(i["views"]) for i in r.json()["items"]}
    return {"source": "Wikimedia REST pageviews API, en.wikipedia 'Bitcoin', all-access, agent=user, daily", "fetched_utc": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
            "views": {f"{k[:4]}-{k[4:6]}-{k[6:]}": v for k, v in sorted(s.items())}}

def series(raw):
    s = pd.Series(raw["views"], dtype=float); s.index = pd.to_datetime(s.index)
    s = s.asfreq("D")  # missing days stay NaN
    ma = s.rolling(30, min_periods=25).mean()
    v = ma.to_numpy(); heat = np.full(len(v), np.nan); n_prior = np.zeros(len(v), int)
    for i in range(len(v)):
        if not np.isfinite(v[i]): continue
        w = v[max(0, i - WIN):i]; w = w[np.isfinite(w)]
        if len(w) < 365: continue  # need at least a year of prior history
        heat[i] = 100.0 * (np.sum(w < v[i]) + 0.5 * np.sum(w == v[i])) / len(w); n_prior[i] = len(w)
    return s, ma, pd.Series(heat, index=s.index), pd.Series(n_prior, index=s.index)

def main():
    err = None
    try: raw = fetch(); json.dump(raw, open(CACHE, "w"), separators=(",", ":"))
    except Exception as e:
        err = str(e)
        if not os.path.exists(CACHE): print("wiki: no data", err); return 0
        raw = json.load(open(CACHE))
    s, ma, heat, n = series(raw)
    last = heat.last_valid_index()
    r1 = lambda x: None if not np.isfinite(x) else round(float(x), 1)
    out = {"source": raw["source"], "fetched_utc": raw["fetched_utc"], "error": err, "display_only": True,
           "method": "heat = percentile of the 30-day average of daily views vs the prior 8 years (2922 days) of 30-day averages; prior data only",
           "asof": last.strftime("%Y-%m-%d"), "views_last": None if not np.isfinite(s[last]) else int(s[last]), "ma30": r1(ma[last]), "heat": r1(heat[last]),
           "prior_days": int(n[last]),
           "t0": s.index[0].strftime("%Y-%m-%d"), "ma30_daily": [r1(x) for x in ma.to_numpy()], "heat_daily": [r1(x) for x in heat.to_numpy()]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True); tmp = OUT + ".tmp"; json.dump(out, open(tmp, "w"), separators=(",", ":")); os.replace(tmp, OUT)
    print(f"wiki: asof {out['asof']} ma30 {out['ma30']} heat {out['heat']} ({os.path.getsize(OUT)} bytes){' [cached: ' + err + ']' if err else ''}")
    return 0

if __name__ == "__main__": sys.exit(main())
