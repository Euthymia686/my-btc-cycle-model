"""Daily scorecard timing gate. OPERATIONAL code only (added 2026-10-26): it decides WHEN the daily run writes the scorecard
rows, the dated raw-data snapshot and the daily hash-chain record. It does not change what is computed: no model math, no
grading rule and nothing under pipeline/frozen/ is read for rules or written. Standard library only.

Why: CoinMetrics Community publishes a day's PriceUSD before its on-chain fields (market cap, MVRV, supply, active
addresses). On 2026-10-26 the 00:30 UTC run saw the 2026-10-25 close without them, so that day's scorecard rows carry a Heat
Score built from incomplete inputs (see data/scorecard_notes.csv). From now on:
  * The scorecard rows for close date D are written only once the CoinMetrics row for D has every field the Heat Score
    uses (REQUIRED below). The 00:30 UTC run refreshes the site as before; if D is incomplete it skips the scorecard step.
  * Retry runs (03:00, 06:00, 09:00, 12:00 UTC, backstop 18:00) try again. A retry with nothing left to do exits at once.
  * Deadline: from 12:00 UTC on D+1 the rows are written anyway, and an append-only note in data/scorecard_notes.csv
    lists the missing fields, so a day is never skipped because of this gate.
  * The day's snapshot and hash-chain record (one per UTC day, never rewritten) wait until yesterday's rows are written
    or the deadline has passed, so the chain record of day D+1 covers the rows for D, as before.

Subcommands, run from the repo root:
  needed    prints "needed=true|false" (for $GITHUB_OUTPUT): false when today's chain record exists and yesterday's
            scorecard rows exist, so a retry has nothing to do.
  decide    after build_data.py: prints have|score|wait|force for the latest CoinMetrics close, saves the decision
  note      after scorecard.py: appends the deadline note if rows were written with missing inputs; rebuilds
            data/scorecard_notes.json (shown on the site)
  settled   exit 0 if today's snapshot and chain record may be written now, 1 if they should wait for a retry
Test hook: GATE_NOW=YYYY-MM-DDTHH:MM (UTC) overrides the clock."""
import csv, datetime as dt, json, math, os, sys, traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CM = os.path.join(ROOT, "pipeline", "cache", "coinmetrics.json")
SC = os.path.join(ROOT, "data", "scorecard.csv")
CHAIN = os.path.join(ROOT, "pipeline", "timestamps", "chain.csv")
NOTES = os.path.join(ROOT, "data", "scorecard_notes.csv"); NOTES_JSON = os.path.join(ROOT, "data", "scorecard_notes.json")
STATE = os.environ.get("SCORE_GATE_STATE", os.path.join(ROOT, "pipeline", ".score_gate.json"))   # per run, not committed
REQUIRED = ("PriceUSD", "CapMrktCurUSD", "CapMVRVCur", "SplyCur", "AdrActCnt")   # every CoinMetrics field the Heat Score uses
VERSIONS = ("v2", "v3", "base")                                                   # pipeline/scorecard.py VERSIONS
START = dt.date(2026, 10, 24)                                                     # pipeline/scorecard.py START
DEADLINE_HOUR = 12                                                                # UTC, on the day after the close
NOTE_COLS = ["close_date", "noted_utc", "kind", "missing_fields", "note"]

def now():
    s = os.environ.get("GATE_NOW")
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc) if s else dt.datetime.now(dt.timezone.utc)

def deadline(close):                       # close date D -> 12:00 UTC on D+1
    return dt.datetime.combine(close + dt.timedelta(days=1), dt.time(DEADLINE_HOUR), dt.timezone.utc)

def num_ok(v):
    try: x = float(v)
    except (TypeError, ValueError): return False
    return math.isfinite(x) and x > 0

def latest_close():
    """(date, missing fields) of the latest CoinMetrics row that has a price, read from the cache the run just built."""
    rows = json.load(open(CM))["data"]
    for r in reversed(rows):
        if num_ok(r.get("PriceUSD")):
            return dt.date.fromisoformat(r["time"][:10]), [k for k in REQUIRED if not num_ok(r.get(k))]
    raise ValueError("no CoinMetrics row with a price")

def scored(day):
    if not os.path.exists(SC): return False
    have = {r["version"] for r in csv.DictReader(open(SC, newline="")) if r["close_date"] == str(day)}
    return all(v in have for v in VERSIONS)

def chain_has(day):
    return os.path.exists(CHAIN) and any(r["date"] == str(day) for r in csv.DictReader(open(CHAIN, newline="")))

def needed():
    t = now(); today = t.date()
    done = chain_has(today) and scored(today - dt.timedelta(days=1))
    print(f"needed={'false' if done else 'true'}")
    print(f"score_gate needed: today {today}, chain record {'yes' if chain_has(today) else 'no'}, "
          f"rows for {today - dt.timedelta(days=1)} {'yes' if scored(today - dt.timedelta(days=1)) else 'no'}", file=sys.stderr)

def decide():
    t = now()
    try:
        d, missing = latest_close()
        if d < START or scored(d): dec = "have"
        elif not missing: dec = "score"
        elif t >= deadline(d): dec = "force"
        else: dec = "wait"
        info = {"decision": dec, "close_date": str(d), "missing": missing, "deadline_utc": deadline(d).isoformat(), "checked_utc": t.isoformat(timespec="seconds")}
    except Exception as e:                 # cannot read the data: behave as before the gate, but only once the deadline hour has passed
        dec = "force" if t.hour >= DEADLINE_HOUR else "wait"
        info = {"decision": dec, "close_date": None, "missing": ["unknown: " + repr(e)[:120]], "checked_utc": t.isoformat(timespec="seconds")}
    json.dump(info, open(STATE, "w"))
    print(dec)
    print(f"score_gate decide: {json.dumps(info)}", file=sys.stderr)

def read_notes():
    return list(csv.DictReader(open(NOTES, newline=""))) if os.path.exists(NOTES) else []

def write_notes_json():
    notes = read_notes(); tmp = NOTES_JSON + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"source": "data/scorecard_notes.csv (append-only)", "notes": notes}, f, indent=1)
    os.replace(tmp, NOTES_JSON)

def append_note(row):
    new = not os.path.exists(NOTES)
    with open(NOTES, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=NOTE_COLS, lineterminator="\n"); new and w.writeheader(); w.writerow(row)

def note():
    info = json.load(open(STATE)) if os.path.exists(STATE) else {}
    d = info.get("close_date")
    if info.get("decision") == "force" and d and scored(d):
        if not any(n["close_date"] == d and n["kind"] == "inputs_incomplete_at_deadline" for n in read_notes()):
            rows = [r for r in csv.DictReader(open(SC, newline="")) if r["close_date"] == d]
            run = rows[0]["run_utc"] if rows else ""
            append_note({"close_date": d, "noted_utc": now().isoformat(timespec="seconds"), "kind": "inputs_incomplete_at_deadline",
                         "missing_fields": "|".join(info.get("missing") or []),
                         "note": f"CoinMetrics had not published these fields for {d} by the {DEADLINE_HOUR}:00 UTC deadline on the next day. "
                                 f"The rows (run {run}) were written anyway so the day is not skipped; their heat_score columns were computed "
                                 f"without these inputs. The forecast ranges use the price only and are unaffected."})
            print(f"score_gate note: added deadline note for {d}", file=sys.stderr)
    write_notes_json()

def settled():
    t = now(); today = t.date()
    ok = chain_has(today) or scored(today - dt.timedelta(days=1)) or t >= dt.datetime.combine(today, dt.time(DEADLINE_HOUR), dt.timezone.utc)
    print(f"score_gate settled: {'yes' if ok else 'no, waiting for the scorecard rows of ' + str(today - dt.timedelta(days=1))}", file=sys.stderr)
    return 0 if ok else 1

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if cmd == "needed": needed()
        elif cmd == "decide": decide()
        elif cmd == "note": note()
        elif cmd == "settled": sys.exit(settled())
        else: print(__doc__); sys.exit(2)
    except SystemExit: raise
    except Exception:
        traceback.print_exc()
        if cmd == "needed": print("needed=true")     # when unsure, run
        elif cmd == "settled": sys.exit(0)          # when unsure, write the record (a missed day cannot be back-filled)
        elif cmd == "decide": print("force" if now().hour >= DEADLINE_HOUR else "wait")
        sys.exit(0)
