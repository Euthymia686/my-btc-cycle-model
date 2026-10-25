"""My BTC Cycle Model - daily signal run.
Usage:  python signals.py        (safe to run any number of times a day; journal keeps one row per UTC date, latest run wins)
Writes: state.json (latest readings) and journal.csv (history of daily readings)."""
import json, os, csv, warnings, datetime as dt; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, lib, backtest, health

def r(x, n=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)

def main():
    now = dt.datetime.now(dt.timezone.utc); today = pd.Timestamp(now.date())
    cm = lib.coinmetrics(); tr = lib.google_trends(); cg = lib.coingecko_live()
    if cm is None or cm.empty: raise SystemExit("No CoinMetrics data (live or cached) - cannot compute signals.")
    cm = cm.copy(); last = cm.index.max()
    live_price = cg["price"] if cg else None
    if live_price and today > last:                       # add today's live row; on-chain fields carried from last print
        row = cm.ffill().iloc[-1].copy(); rcap = row["mcap"] / row["mvrv"]
        row["price"] = live_price; row["mcap"] = live_price * row["supply"]; row["mvrv"] = row["mcap"] / rcap
        cm.loc[today] = row
    elif live_price:
        cm.loc[cm.index.max(), "price"] = live_price
    cm = cm.sort_index().ffill()
    df, (a, b) = lib.build_signals(cm, tr); p = df["price"]
    tops, bottoms = lib.find_tops_bottoms(p.loc[:today])
    cal, H, se, sf, nh = backtest.calibrate(df, None, tops, str((today + pd.Timedelta(days=1)).date()))
    d = df.index.max(); hot = cal["score_hot"]["equal"]; warm = hot - 15
    sig = {}
    for s in lib.SIGNALS:
        h = H[s].get(d, np.nan); shot = cal["signal_hot"].get(s, 90.0); swarm = max(shot - 15, 55)
        raw = df[s].get(d, np.nan) if s != "cycle_day" else df["days_since_halving"].get(d)
        # raw value that today corresponds to the hot / warm heat (inverse of history-to-date distribution)
        hist = df[s].loc[:d].dropna() if s != "cycle_day" else None
        thr = None if hist is None or hist.empty else {"warm_at": r(np.percentile(hist, swarm), 3), "hot_at": r(np.percentile(hist, shot), 3)}
        sig[s] = {"label": lib.LABELS[s], "value": r(raw, 3), "heat": r(h, 1), "zone": lib.zone(h, shot, swarm),
                  "zone_rule": f"hot if heat >= {shot:.0f}, warm >= {swarm:.0f}, neutral >= 40, else cool", "thresholds_today": thr}
    td = cal["top_days"]; mu = float(np.mean(td))
    sig["cycle_day"]["note"] = f"day {int(df['days_since_halving'][d])} since the {lib.last_halving(d).date()} halving; past halving-to-peak days {td} (mean {mu:.0f})"
    if tr and tr.get("weekly"):
        wk = pd.Series(tr["weekly"]); sig["trends"]["latest_weekly_5y_scale"] = {"date": wk.index[-1], "value": int(wk.iloc[-1])}
    score = se.get(d, np.nan); nhot = nh.get(d, np.nan)
    # MSTR context (price, holdings, mNAV)
    stg = lib.strategy_kpis() or {}; sh = (lib.shares_outstanding() or {}).get("shares")
    ym = lib.yahoo_mstr(); mstr_px = stg.get("mstr_close") or (ym["close"][-1] if ym else None)
    hold = stg.get("holdings"); btc = live_price or float(p.iloc[-1])
    mnav = mstr_px * sh / (hold * btc) if (mstr_px and sh and hold) else None
    mnav_zone = None if mnav is None else ("cool" if mnav < 1 else "neutral" if mnav < 1.5 else "warm" if mnav < 2.5 else "hot")
    # cross-checks with Yahoo BTC
    yb = lib.yahoo_btc(); xchk = None
    if yb:
        ys = pd.Series(yb["close"], index=pd.to_datetime(yb["dates"]))
        xchk = {"yahoo_last_close": r(ys.iloc[-1], 0), "yahoo_200d_ma": r(ys.rolling(200).mean().iloc[-1], 0),
                "yahoo_200w_ma_weekly": r(ys.resample("W").last().rolling(200).mean().iloc[-1], 0) if len(ys) > 1400 else None,
                "cm_200d_ma": r(df["ma200"][d], 0), "cm_200w_ma": r(df["ma1400"][d], 0)}
    ath_d = p.loc[:d].idxmax()
    state = {
        "run_utc": now.isoformat(timespec="seconds"), "date": str(d.date()),
        "btc": {"price": r(btc, 0), "source": "CoinGecko live" if cg and lib.STATUS.get("coingecko.json", {}).get("from") == "live" else "CoinMetrics/cached",
                "chg24_pct": r(cg.get("chg24") if cg else None), "ath": r(p.max(), 0), "ath_date": str(ath_d.date()),
                "drawdown_pct": r(100 * (btc / p.max() - 1), 1), "days_since_peak": (d - ath_d).days,
                "days_since_halving": int(df["days_since_halving"][d]), "next_halving_est": next_halving(),
                "trend_line": r(10 ** (a + b * np.log10((d - lib.GENESIS).days)), 0), "realized_price": r(df["realized_price"][d], 0),
                "onchain_asof": str(last.date())},
        "score": {"value": r(score, 1), "zone": lib.zone(score, hot, warm), "hot_at": hot, "warm_at": warm,
                  "signals_hot": None if np.isnan(nhot) else int(nhot), "n_signals": len(cal["signal_hot"]),
                  "method": "equal-weight mean of signal heats (see METHOD.md)", "fitted_weight_variant": r(sf.get(d, np.nan), 1)},
        "signals": sig,
        "mstr": {"price": mstr_px, "price_time": stg.get("mstr_time"), "shares": sh, "btc_holdings": hold,
                 "mnav_simple": r(mnav, 3), "mnav_zone": mnav_zone, "mnav_zone_rule": "judgement bands (<1 cool, 1-1.5 neutral, 1.5-2.5 warm, >2.5 hot); not backtested - no free holdings history",
                 "mnav_strategy_ev_based": stg.get("mnav_strategy")},
        "cross_checks": xchk, "edgar_latest_8k": lib.edgar_latest_8k(), "block_height": (lib.block_height() or {}).get("height"),
        "sources": lib.STATUS,
    }
    # v2 (pre-registered, frozen) score + model health (fan coverage since freeze, backtest, spec-hash check)
    try:
        hl, sc2, F2 = health.build(df, closes=lib.coinmetrics()["price"])
        state["v2"] = hl["v2_today"]; state["health"] = {k: hl[k] for k in ("integrity", "forward", "trend_drift", "fan_today")}
        state["health"]["fan_backtest_summary"] = hl["fan_backtest"]["summary"]; state["_journal_extra"] = health.today_fields(hl)
        pd.DataFrame({"score_v2": sc2, **{f"v2_{k}": F2[k] for k in F2.columns}}).to_csv(os.path.join(lib.HERE, "out", "score_v2_history.csv"), index_label="date")
    except Exception as e:
        state["health_error"] = str(e); state["_journal_extra"] = {"health_error": str(e)}
    extra = state.pop("_journal_extra", {})
    with open(os.path.join(lib.HERE, "state.json"), "w") as f: json.dump(state, f, indent=1, default=str)
    append_journal(state, extra)
    return state

def next_halving():
    h = (lib.block_height() or {}).get("height")
    if not h: return None
    return str((pd.Timestamp.utcnow().normalize() + pd.Timedelta(minutes=10 * (lib.NEXT_HALVING_BLOCK - h))).date())

def append_journal(s, extra=None):
    path = os.path.join(lib.HERE, "journal.csv")
    row = {"date": s["date"], "run_utc": s["run_utc"], "btc": s["btc"]["price"], "score": s["score"]["value"], "score_zone": s["score"]["zone"],
           "signals_hot": s["score"]["signals_hot"]}
    for k, v in s["signals"].items(): row[f"{k}"] = v["value"]; row[f"{k}_heat"] = v["heat"]; row[f"{k}_zone"] = v["zone"]
    row.update({"mstr": s["mstr"]["price"], "mnav_simple": s["mstr"]["mnav_simple"],
                "sources_failed": ";".join(k for k, v in s["sources"].items() if v.get("from") != "live")})
    row.update(extra or {})
    rows = []
    if os.path.exists(path):
        with open(path) as f: rows = [x for x in csv.DictReader(f) if x["date"] != row["date"]]
    rows.append({k: ("" if v is None else v) for k, v in row.items()})
    cols = list(row.keys()) + [k for x in rows for k in x if k not in row and k is not None]
    cols = list(dict.fromkeys(cols))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

if __name__ == "__main__":
    s = main()
    print(f"{s['date']}  BTC ${s['btc']['price']:,.0f}  Cycle Heat Score {s['score']['value']} ({s['score']['zone']}; hot >= {s['score']['hot_at']})")
    for k, v in s["signals"].items(): print(f"  {v['label']:<42} {str(v['value']):>10}  heat {str(v['heat']):>5}  {v['zone']}")
    if s.get("v2"): print(f"  Score v2 (pre-registered {health.freeze_record()['frozen_on'] if health.freeze_record() else 'NOT FROZEN'}): {s['v2']['value']} ({s['v2']['zone']})  families {s['v2']['families']}")
    if s.get("health"):
        hh = s["health"]; fw = hh.get("forward") or {}
        print(f"  Fan: spec ok {hh['integrity'].get('v2_spec_ok')}/{hh['integrity'].get('fan_ok')}; forward days {fw.get('days', 0)}"
              + (f", inside 90% band {100*fw['in90']:.0f}%, 50% band {100*fw['in50']:.0f}%" if fw.get('days') else "")
              + f"; backtest 90%-band coverage {100*hh['fan_backtest_summary']['all']['in90']:.1f}%, 50%-band {100*hh['fan_backtest_summary']['all']['in50']:.1f}%")
    print(f"  MSTR ${s['mstr']['price']}  mNAV {s['mstr']['mnav_simple']}")
    bad = {k: v for k, v in s["sources"].items() if v.get("from") != "live"}
    print("  sources:", "all live" if not bad else bad)
