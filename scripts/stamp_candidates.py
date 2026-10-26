"""Daily hash-chain record + OpenTimestamps stamp for the shadow candidates (pipeline/candidates/PREREG_CANDIDATES.md).
Separate from scripts/stamp_daily.py on purpose: the files of the main daily record are fixed by PREREG_BAND.md section 9.
NEVER fails the update job (always exits 0). Run from the repo root:  python scripts/stamp_candidates.py
Writes pipeline/timestamps/candidates/YYYY-MM-DD.txt (UTC date): 'date', 'prev <previous record sha256>', then 'sha256  path'
per file, appends (date, record_sha256, prev_record_sha256) to pipeline/timestamps/candidates_chain.csv, then runs `ots stamp`
on today's record and on any earlier record still without a .ots. The private raw caches are covered by hash only."""
import csv, datetime as dt, hashlib, os, subprocess, sys, traceback
ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
FILES = ["pipeline/candidates/CANDIDATES_SHA256SUMS", "data/candidates/shadow_log.csv", "data/candidates/shadow_backfill.csv",
         "data/candidates.json", "pipeline/cache/candidates/cm_candidates.json", "pipeline/cache/candidates/cftc_cot.json",
         "pipeline/cache/candidates/fred.json", "pipeline/cache/candidates/okx_oi.json", "pipeline/cache/candidates/deribit_oi.json"]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()

def main():
    d = dt.datetime.now(dt.timezone.utc).date().isoformat()
    cdir = os.path.join(ROOT, "pipeline/timestamps/candidates"); os.makedirs(cdir, exist_ok=True)
    chain = os.path.join(ROOT, "pipeline/timestamps/candidates_chain.csv"); rows = list(csv.DictReader(open(chain))) if os.path.exists(chain) else []
    if not rows or rows[-1]["date"] != d:                                       # one record per UTC day, never rewritten
        prev = rows[-1]["record_sha256"] if rows else "0" * 64
        lines = [f"date {d}", f"prev {prev}"] + [f"{sha(os.path.join(ROOT, f))}  {f}" for f in FILES if os.path.exists(os.path.join(ROOT, f))]
        rec = os.path.join(cdir, f"{d}.txt")
        with open(rec, "w") as fh: fh.write("\n".join(lines) + "\n")
        new = not os.path.exists(chain)
        with open(chain, "a", newline="") as fh:
            w = csv.writer(fh); new and w.writerow(["date", "record_sha256", "prev_record_sha256"]); w.writerow([d, sha(rec), prev])
    for f in sorted(os.listdir(cdir)):
        if f.endswith(".txt") and not os.path.exists(os.path.join(cdir, f + ".ots")):
            try: subprocess.run([os.environ.get("OTS", "ots"), "stamp", os.path.join(cdir, f)], timeout=120, check=True)
            except Exception as e: print(f"::warning::candidates ots stamp failed for {f}: {e}; will retry on the next run")

if __name__ == "__main__":
    try: main()
    except Exception: print("::warning::stamp_candidates failed; update continues"); traceback.print_exc()
    sys.exit(0)
