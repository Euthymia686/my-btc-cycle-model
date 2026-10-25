"""Daily hash-chain record + OpenTimestamps stamp (PREREG_BAND.md section 9). NEVER fails the update job (always exits 0).
Run from the repo root after the daily update:  python scripts/stamp_daily.py
Writes pipeline/timestamps/chain/YYYY-MM-DD.txt (UTC date):  'date', 'prev <previous record sha256>', then 'sha256  path' per file,
appends (date, record_sha256, prev_record_sha256) to pipeline/timestamps/chain.csv, then runs `ots stamp` on today's record
and on every earlier record that still has no .ots (calendar outage: retried on the next run)."""
import csv, datetime as dt, hashlib, os, subprocess, sys, traceback
ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
FILES = ["data/scorecard.csv", "data/band_log.csv", "data/band_prices.csv", "data/band_price_revisions.csv", "data/band_grades.json",
         "data/band_rerun.json", "data/halving_2028.json", "snapshots/MANIFEST.csv", "pipeline/frozen/FROZEN_SHA256SUMS",
         "pipeline/frozen/band/BAND_SHA256SUMS", "pipeline/frozen/band/competitors_freeze.json", "pipeline/frozen/band/AMENDMENTS.md", "data/hero_fwd.json", "data/fan.json"]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()

def main():
    d = dt.datetime.now(dt.timezone.utc).date().isoformat()
    cdir = os.path.join(ROOT, "pipeline/timestamps/chain"); os.makedirs(cdir, exist_ok=True)
    chain = os.path.join(ROOT, "pipeline/timestamps/chain.csv"); rows = list(csv.DictReader(open(chain))) if os.path.exists(chain) else []
    if not rows or rows[-1]["date"] != d:                                       # one record per UTC day, never rewritten
        prev = rows[-1]["record_sha256"] if rows else "0" * 64
        lines = [f"date {d}", f"prev {prev}"] + [f"{sha(os.path.join(ROOT, f))}  {f}" for f in FILES if os.path.exists(os.path.join(ROOT, f))]
        rec = os.path.join(cdir, f"{d}.txt")
        with open(rec, "w") as fh: fh.write("\n".join(lines) + "\n")
        new = not os.path.exists(chain)
        with open(chain, "a", newline="") as fh:
            w = csv.writer(fh); new and w.writerow(["date", "record_sha256", "prev_record_sha256"]); w.writerow([d, sha(rec), prev])
    for f in sorted(os.listdir(cdir)):                                          # stamp today + retry any day whose stamp failed
        if f.endswith(".txt") and not os.path.exists(os.path.join(cdir, f + ".ots")):
            try: subprocess.run(["ots", "stamp", os.path.join(cdir, f)], timeout=120, check=True)
            except Exception as e: print(f"::warning::ots stamp failed for {f}: {e}; will retry on the next run")

if __name__ == "__main__":
    try: main()
    except Exception: print("::warning::stamp_daily failed; update continues"); traceback.print_exc()
    sys.exit(0)
