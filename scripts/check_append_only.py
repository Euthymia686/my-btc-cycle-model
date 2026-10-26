"""CI guard (PREREG_BAND.md section 9, item 3). Fails (exit 1) if an append-only file lost or changed an earlier row vs the base commit.
Usage: python scripts/check_append_only.py <base_ref>      (e.g. HEAD~1 or origin/main before the run's commit)"""
import subprocess, sys
base = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
STRICT = ["data/band_log.csv", "data/band_prices.csv", "data/band_price_revisions.csv", "pipeline/timestamps/chain.csv",
          "data/scorecard_notes.csv",   # notes on scorecard rows (scripts/score_gate.py): added 2026-10-26, append-only
          "data/candidates/shadow_log.csv", "pipeline/timestamps/candidates_chain.csv"]   # shadow candidates (PREREG_CANDIDATES.md), 2026-10-26
WRITE_ONCE = ["data/band_rerun.json", "data/halving_2028.json", "data/candidates/shadow_backfill.csv",
              "pipeline/candidates/PREREG_CANDIDATES.md", "pipeline/candidates/candidates_spec.py", "pipeline/candidates/CANDIDATES_SHA256SUMS"]
FILL_LATER = {"data/scorecard.csv": ("_actual", "in50", "in90", "log_score")}   # only these cells may be filled in later
bad = []
def old(f):
    r = subprocess.run(["git", "show", f"{base}:{f}"], capture_output=True, text=True); return r.stdout if r.returncode == 0 else None
for f in STRICT:
    o = old(f)
    if o is None: continue
    n = open(f).read()
    if not n.startswith(o): bad.append(f"{f}: earlier rows changed or removed")
for f in WRITE_ONCE:
    o = old(f)
    if o is not None and open(f).read() != o: bad.append(f"{f}: write-once file changed")
for f, fillable in FILL_LATER.items():
    o = old(f)
    if o is None: continue
    ol, nl = o.splitlines(), open(f).read().splitlines(); hdr = ol[0].split(",")
    if nl[:1] != ol[:1] or len(nl) < len(ol): bad.append(f"{f}: header changed or rows removed"); continue
    for a, b in zip(ol[1:], nl[1:]):
        for h, x, y in zip(hdr, a.split(","), b.split(",")):
            if x != y and not (x == "" and any(k in h for k in fillable)): bad.append(f"{f}: prediction cell {h} changed"); break
print("append-only OK" if not bad else "\n".join(bad)); sys.exit(1 if bad else 0)
