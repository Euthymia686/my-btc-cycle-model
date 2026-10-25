"""FROZEN (band pre-registration). One-time, on the freeze day, after band_freeze.py: writes the competitor snapshots.
  corrected_band_snapshot_<T0>.csv   C1 ensemble-corrected band (SELECTION_RULE.md applied to the frozen band snapshot)
  competitors_freeze.json            C1 summary, C2 = S1, C3 = S3, C4 = lengthening-cycle timing, input/code hashes
Usage (from pipeline/): OFFLINE=1 PYTHONPATH=.:frozen/band python frozen/band/competitors_freeze.py frozen/band"""
import json, os, sys, hashlib, warnings; warnings.filterwarnings("ignore")
import pandas as pd
import lib, corrected_rule as CR, laws_rule as LR
OUT = sys.argv[1] if len(sys.argv) > 1 else "frozen_band_draft"
T0 = CR.LAST + pd.Timedelta(days=1)
snap = pd.read_csv(os.path.join(OUT, f"band_snapshot_{T0.date()}.csv"), parse_dates=["date"]).set_index("date")
pk_snap = snap.band_mid.loc["2028-04-11":].idxmax()
if pk_snap != LR.TP_2029: sys.exit(f"STOP: band peak date {pk_snap.date()} != laws_rule.TP_2029 {LR.TP_2029.date()}; update TP_2029 before hashing (PREREG 15.1)")
bdf = snap.rename(columns={"band_lo": "lo", "band_mid": "md", "band_hi": "hi"})[["lo", "md", "hi"]]
cor, c1 = CR.corrected(bdf, T0)
f = os.path.join(OUT, f"corrected_band_snapshot_{T0.date()}.csv")
cor.rename(columns={"lo": "corr_lo", "md": "corr_mid", "hi": "corr_hi"}).round(2).rename_axis("date").to_csv(f)
laws = LR.run(T0); c4 = LR.lengthening_timing()
sens = {str(lp): LR.run(T0, low_override=lp)["S1"]["top"] for lp in (59517, 50000, 40000)}
sha = lambda fn: hashlib.sha256(open(fn, "rb").read()).hexdigest()
here = os.path.dirname(os.path.abspath(__file__))
meta = dict(origin_T0=str(T0.date()), data_through=str(CR.LAST.date()),
            C1_corrected=c1, C2_S1=laws["S1"], C3_S3=laws["S3"], C4_lengthening_timing=c4, S1_sensitivity_to_low=sens,
            inputs_sha256={"pipeline/cache/coinmetrics.json": sha(os.path.join(lib.CACHE, "coinmetrics.json"))},
            code_sha256={fn: sha(os.path.join(here, fn)) for fn in ("bandlib.py", "corrected_rule.py", "laws_rule.py", "competitors_freeze.py")},
            corrected_snapshot_sha256=sha(f))
json.dump(meta, open(os.path.join(OUT, "competitors_freeze.json"), "w"), indent=1, default=lambda x: float(x) if hasattr(x, "__float__") else str(x))
r = lambda v: round(v) if isinstance(v, float) else v
print("C1 top", r(c1["ens_top"]), [r(x) for x in c1["top_range"]], "low", r(c1["ens_low"]), [r(x) for x in c1["low_range"]], c1["tp"], c1["tl"])
for k in ("S1", "S3"): print(k, r(laws[k]["top"]), [r(x) for x in laws[k]["range"]], "w", round(laws[k]["w"], 3), "slope", round(laws[k]["slope"], 3), "int", round(laws[k]["intercept"], 3), laws[k]["low_used"])
print("C4", c4); print("S1 sensitivity", {k: r(v) for k, v in sens.items()})
