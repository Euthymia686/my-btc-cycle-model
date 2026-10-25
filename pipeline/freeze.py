"""One-time pre-registration: records SHA-256 of v2_spec.py + robust.py and freezes today's projection fan.
Refuses to overwrite an existing freeze (pre-registration must not move). Usage: python freeze.py"""
import hashlib, json, os, datetime as dt, sys
import pandas as pd, lib, robust, v2_spec
FZ = os.path.join(lib.HERE, "frozen")
def sha(path): return hashlib.sha256(open(path, "rb").read()).hexdigest()
def main():
    os.makedirs(FZ, exist_ok=True); rec = os.path.join(FZ, "v2_freeze.json")
    if os.path.exists(rec): sys.exit("already frozen: " + rec)
    p = lib.coinmetrics()["price"].dropna(); P = robust.fan_params(p)
    dates = pd.date_range(pd.Timestamp(v2_spec.FROZEN_ON), "2028-12-31")
    F = robust.fan_at(P, dates)
    fan = {"frozen_on": v2_spec.FROZEN_ON, "data_through": P["asof"], "method": "robust.fan_params (decay-weighted forecast-error fan)",
           "params": P, "dates": [str(d.date()) for d in dates], **{k: [round(float(v), 2) for v in F[k]] for k in F.columns}}
    fp = os.path.join(FZ, f"fan_{v2_spec.FROZEN_ON}.json")
    with open(fp, "w") as f: json.dump(fan, f, separators=(",", ":"))
    out = {"frozen_on": v2_spec.FROZEN_ON, "frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "v2_spec_sha256": sha(os.path.join(lib.HERE, "v2_spec.py")), "robust_sha256": sha(os.path.join(lib.HERE, "robust.py")),
           "fan_file": os.path.basename(fp), "fan_sha256": sha(fp), "v2_params": v2_spec.PARAMS,
           "rule": "v2 and the frozen fan are judged only on data after frozen_on. Edits => new version + new freeze."}
    with open(rec, "w") as f: json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ("frozen_on", "v2_spec_sha256", "robust_sha256", "fan_sha256")}, indent=1))
if __name__ == "__main__": main()
