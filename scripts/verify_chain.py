"""Check the daily record chain (PREREG_BAND.md section 9 / VERIFY.md step 3). Read-only.
For each row of pipeline/timestamps/chain.csv: the record file's sha256 matches, its 'prev' line equals the previous row's sha,
and (with --git) each file hash in the record equals that file in the git commit that added the record.
Exit 0 = chain OK, 1 = break found."""
import csv, hashlib, os, subprocess, sys
ROOT = "."; GIT = "--git" in sys.argv
sha = lambda b: hashlib.sha256(b).hexdigest()
rows = list(csv.DictReader(open(os.path.join(ROOT, "pipeline/timestamps/chain.csv")))); breaks = []; prev = "0" * 64; stamped = 0
for r in rows:
    p = os.path.join(ROOT, "pipeline/timestamps/chain", r["date"] + ".txt"); b = open(p, "rb").read()
    if sha(b) != r["record_sha256"]: breaks.append(f"{r['date']}: record sha mismatch")
    lines = b.decode().splitlines()
    if lines[1] != f"prev {prev}" or r["prev_record_sha256"] != prev: breaks.append(f"{r['date']}: prev link broken")
    stamped += os.path.exists(p + ".ots"); prev = r["record_sha256"]
    if GIT:
        c = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "--", p], capture_output=True, text=True).stdout.split()
        for ln in lines[2:]:
            h, f = ln.split("  ", 1)
            if c and sha(subprocess.run(["git", "show", f"{c[-1]}:{f}"], capture_output=True).stdout) != h: breaks.append(f"{r['date']}: {f} differs from commit {c[-1][:8]}")
print(f"chain {'OK' if not breaks else 'BROKEN'}: {len(rows)} days, first {rows[0]['date'] if rows else '-'}, last {rows[-1]['date'] if rows else '-'}, "
      f"{len(breaks)} breaks, {stamped} with .ots"); [print("  " + x) for x in breaks]; sys.exit(1 if breaks else 0)
