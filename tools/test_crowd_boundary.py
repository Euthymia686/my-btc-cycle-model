"""Test for the crowd.py Deribit boundary-day fix (2026-10-26).
Offline (default): a fake Deribit API with the real semantics (start_timestamp exclusive, end_timestamp inclusive, verified
against the live API on 2026-10-26) checks that every refetched day is averaged from all 24 hourly records, that the
earlier code got 23/24 on its first day, and that no partial earlier day is written.
  python tools/test_crowd_boundary.py
Online (optional): compare a cached Deribit file against a fresh full-day fetch, and the official gauge built from each.
  python tools/test_crowd_boundary.py --online <crowd_deribit.json> <crowd_fng.json> [days=21]"""
import copy, datetime as dt, json, os, sys, tempfile
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import crowd

H = 3600 * 1000
def ms(d): return int(pd.Timestamp(d).tz_localize("UTC").timestamp() * 1000)
def rate(t): return 1e-5 * (1 + (t // H) % 97) / 7   # a distinct value every hour, so a missing record changes the mean

def fake_get(now_ms, calls):
    def get(url, params=None, **kw):
        a, b = params["start_timestamp"], params["end_timestamp"]; calls.append((a, b))
        t = (a // H + 1) * H   # exclusive start
        out = []
        while t <= b and t <= now_ms: out.append({"timestamp": t, "interest_8h": rate(t)}); t += H
        return {"result": out}
    return get

def old_f_deribit(old, get):   # the code before 2026-10-26, kept here only to show the bug
    start = pd.Timestamp(max(old["daily"])) - pd.Timedelta(days=2); end = pd.Timestamp(crowd.now()); rows = []; t = start
    while t < end:
        t2 = min(t + pd.Timedelta(hours=743), end)
        r = get("", params={"start_timestamp": int(t.timestamp() * 1000), "end_timestamp": int(t2.timestamp() * 1000)})["result"]
        rows += [(dt.datetime.fromtimestamp(x["timestamp"] / 1000, dt.timezone.utc).strftime("%Y-%m-%d"), float(x["interest_8h"])) for x in r]; t = t2
    return rows

def offline():
    now = pd.Timestamp("2026-10-26 10:30"); now_ms = ms(now); crowd.now = lambda: now.to_pydatetime(); crowd.time.sleep = lambda s: None
    old = {"daily": {d.strftime("%Y-%m-%d"): -1.0 for d in pd.date_range("2026-09-01", "2026-10-25")}}   # -1 marks stale values
    calls = []; crowd.get = fake_get(now_ms, calls)
    new = crowd.f_deribit(copy.deepcopy(old))["daily"]
    first = (pd.Timestamp("2026-10-25") - pd.Timedelta(days=crowd.DERIBIT_REFETCH_DAYS)).strftime("%Y-%m-%d")
    days = [d for d in new if d >= first and d < "2026-10-26"]
    for d in days:
        recs = [rate(t) for t in range(ms(d), ms(d) + 24 * H, H)]
        assert len(recs) == 24 and new[d] == float(np.mean(recs)), f"{d}: not the mean of all 24 hourly records"
    assert all(new[d] == -1.0 for d in new if d < first), "a day before the refetch window was overwritten (partial day)"
    today = [rate(t) for t in range(ms("2026-10-26"), now_ms + 1, H)]
    assert new["2026-10-26"] == float(np.mean(today)) and len(today) == 11, "today: all hourly records so far (00:00-10:00)"
    # long backfill (many 743-hour chunks): every record exactly once at chunk edges
    calls2 = []; crowd.get = fake_get(now_ms, calls2); full = crowd.f_deribit(None)["daily"]
    n = {d: 0 for d in full}; s = {d: 0.0 for d in full}
    for t in range(ms("2019-04-30"), now_ms + 1, H): d = pd.Timestamp(t, unit="ms").strftime("%Y-%m-%d"); n[d] += 1; s[d] += rate(t)
    assert len(calls2) > 50 and all(n[d] == 24 for d in full if d < "2026-10-26"), "backfill: some day not 24/24"
    assert all(abs(full[d] - s[d] / n[d]) < 1e-18 for d in full), "backfill: means differ"
    # the old code: its first refetched day had 23 of 24 records
    rows = old_f_deribit(old, fake_get(now_ms, []))
    cnt = pd.Series([d for d, _ in rows]).value_counts().sort_index()
    print(f"new code: {len(days)} past days refetched ({days[0]}..{days[-1]}), each 24/24 records; today {len(today)}/11 so far; "
          f"backfill {len(full)} days in {len(calls2)} requests, all complete days 24/24")
    print("old code records per day:", {k: int(v) for k, v in cnt.items()}); assert cnt.iloc[0] == 23
    print("offline test OK")

def online(der_path, fng_path, ndays=21):
    import requests
    der = json.load(open(der_path)); fng = json.load(open(fng_path))
    now = pd.Timestamp(crowd.now()); first = pd.Timestamp(now.date()) - pd.Timedelta(days=ndays + 7)
    recs, t = {}, first - pd.Timedelta(hours=1)
    while t < now:
        t2 = min(t + pd.Timedelta(hours=743), now)
        r = requests.get("https://www.deribit.com/api/v2/public/get_funding_rate_history", params={"instrument_name": "BTC-PERPETUAL",
                         "start_timestamp": int(t.timestamp() * 1000), "end_timestamp": int(t2.timestamp() * 1000)}, headers=crowd.UA, timeout=40).json()["result"]
        recs.update({int(x["timestamp"]): float(x["interest_8h"]) for x in r}); t = t2
    by = {}
    for k, v in recs.items(): by.setdefault(pd.Timestamp(k, unit="ms").strftime("%Y-%m-%d"), []).append(v)
    fixed = copy.deepcopy(der); fixed["daily"].update({d: float(np.mean(v)) for d, v in by.items() if d >= first.strftime("%Y-%m-%d")})
    print("day         records  cached mean        full-day mean      rel. diff")
    for d in sorted(by)[-ndays - 7:]:
        c = der["daily"].get(d); print(f"{d}  {len(by[d]):>2}/24   {c!s:<18} {np.mean(by[d]):<18.10g} {'' if c is None else f'{(c / np.mean(by[d]) - 1) * 100:+.2f}%'}")
    def build(dd):
        with tempfile.TemporaryDirectory() as tmp:
            json.dump(dd, open(os.path.join(tmp, "crowd_deribit.json"), "w")); json.dump(fng, open(os.path.join(tmp, "crowd_fng.json"), "w"))
            crowd.CD, crowd.OUT, crowd.OFF = tmp, os.path.join(tmp, "crowd.json"), True
            crowd.main(); return json.load(open(crowd.OUT))
    a, b = build(der), build(fixed)
    def raw(dd):   # unrounded, same steps as crowd.main (Deribit only; OKX/BitMEX only fill days Deribit lacks)
        f = pd.Series(dd["daily"], dtype=float).rename(index=pd.Timestamp).sort_index(); g = pd.Series(fng["daily"], dtype=float).rename(index=pd.Timestamp)
        idx = pd.date_range(f.index.min(), pd.Timestamp(now.date())); f7 = (f.reindex(idx) * 3 * 365).rolling(7, min_periods=5).mean()
        fs = f7.apply(lambda x: crowd.fund_score(x) if np.isfinite(x) else np.nan); g7 = g.reindex(idx).rolling(7, min_periods=5).mean()
        return pd.concat([g7, fs], axis=1).mean(axis=1, skipna=False)
    ra, rb = raw(der), raw(fixed)
    t0 = pd.Timestamp(a["t0"]); idx = pd.date_range(t0, periods=len(a["gauge_daily"]))
    print("\nofficial gauge   published (1 dp): old  new   |  unrounded: old            new                diff")
    diffs = []
    for i in range(len(idx) - ndays, len(idx)):
        x, y = a["gauge_daily"][i], b["gauge_daily"][i]
        d = idx[i]; u, v = ra.get(d, np.nan), rb.get(d, np.nan); diffs.append(abs(v - u))
        print(f"  {d.strftime('%Y-%m-%d')}            {x!s:<5}  {y!s:<5} |  {u:<18.12g} {v:<18.12g} {v - u:+.4f}")
    print(f"max |diff| over the last {ndays} days: {np.nanmax(diffs):.4f} gauge points (unrounded); published values differ on "
          f"{sum(1 for i in range(len(idx) - ndays, len(idx)) if a['gauge_daily'][i] != b['gauge_daily'][i])} of {ndays} days; zones old {a['zone']} / new {b['zone']}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--online": online(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 21)
    else: offline()
