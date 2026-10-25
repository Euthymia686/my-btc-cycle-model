"""Backtest (past data) version of the scorecard tests, by the same method as the live scorecard (frozen/v3/FREEZE.md,
"Grading method"): one forecast per day from 2015-01-01, each using only closes up to its own date, scored on the close
30, 90 and 365 days later. Writes data/scorecard_backtest.json. Run by hand (it takes a few minutes); not part of the
daily job. These p-values are optimistic: the models were designed, and the v3 scales estimated, after seeing this data."""
import json, os, datetime as dt
import pandas as pd, lib, scorecard as SC

FIRST = pd.Timestamp("2015-01-01")

def main(p=None):
    p = (lib.coinmetrics()["price"] if p is None else p).dropna(); p = p[p > 0]; last = p.index[-1]; rows = []
    for d in p.index[(p.index >= FIRST) & (p.index <= last - pd.Timedelta(days=min(SC.HORIZONS)))]:
        pr = SC.predictions(p, d)
        for v in SC.VERSIONS:
            r = {"close_date": str(d.date()), "version": v}
            for h in SC.HORIZONS:
                t = d + pd.Timedelta(days=h); q = pr[v][h]; r[f"h{h}_actual"] = ""
                if t in p.index:
                    x = float(p[t]); r.update({f"h{h}_actual": f"{x:.2f}", f"h{h}_in50": str(int(q["q25"] <= x <= q["q75"])),
                                               f"h{h}_in90": str(int(q["q5"] <= x <= q["q95"])), f"h{h}_log_score": f"{SC.score_one(v, q, x):.6f}"})
            rows.append(r)
    out = SC.tests(rows); out.update({"label": "backtest (past data)", "first_origin": str(FIRST.date()), "data_through": str(last.date()),
                                      "origins": len(rows) // len(SC.VERSIONS), "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    for c in out["coverage"].values(): c.pop("expected", None)
    for c in out["skill"].values(): c.pop("expected", None)
    with open(os.path.join(SC.ROOT, "data", "scorecard_backtest.json"), "w") as f: json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))

if __name__ == "__main__": main()
