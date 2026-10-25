"""Display only: the LOCKED fan range for the scorecard section of the site (data/fan_locked.json).
Reads the frozen v2 fan file (frozen/fan_2026-10-25.json, read only) and derives v3 from it with the frozen v3 scales
(scorecard.v3_scale: median unchanged, half-widths x s90 / s50, frozen/v3/v3_spec.md section B). Fixed numbers: the frozen
fan was computed once at the freeze from the close of 2026-10-24 and is never recomputed with the live price.
Changes no file under frozen/, no score and no model. Model ranges, not predictions; not financial advice."""
import json, os, hashlib
import lib
from scorecard import v3_scale, S90, S50

QK = ("q5", "q25", "q50", "q75", "q95")
rec = json.load(open(os.path.join(lib.HERE, "frozen", "v2_freeze.json")))
path = os.path.join(lib.HERE, "frozen", rec["fan_file"]); raw = open(path, "rb").read(); FF = json.loads(raw)
ix = {d: i for i, d in enumerate(FF["dates"])}
rows = []
for d in ("2027-12-31", "2028-12-31"):
    i = ix[d]; v2 = {k: float(FF[k][i]) for k in QK}; v3 = v3_scale(v2)
    rows.append({"date": d, "v2": {k: round(v, 2) for k, v in v2.items()}, "v3": {k: round(v, 2) for k, v in v3.items()}})
out = {"generated_from": "pipeline/fan_locked.py (frozen fan file + frozen v3 scales; display only)",
       "frozen_on": FF["frozen_on"], "data_through": FF["data_through"], "fan_file": rec["fan_file"],
       "fan_sha256": hashlib.sha256(raw).hexdigest(), "s90": S90, "s50": S50, "rows": rows}
json.dump(out, open(os.path.join(lib.HERE, "..", "data", "fan_locked.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
