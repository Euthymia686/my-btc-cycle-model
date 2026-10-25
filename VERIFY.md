# VERIFY: check the blue band pre-registration yourself

Everything below is read-only and needs only `git`, `sha256sum`, Python 3 and (for step 2) the free OpenTimestamps client.
The rules being checked are in `pipeline/frozen/band/PREREG_BAND.md`.

```
pip install opentimestamps-client==0.7.2
git clone https://github.com/Euthymia686/my-btc-cycle-model && cd my-btc-cycle-model
```

## 1. Are the frozen files unchanged?
```
sha256sum -c pipeline/frozen/FROZEN_SHA256SUMS          # the earlier fan freeze (v2/v3)
sha256sum -c pipeline/frozen/band/BAND_SHA256SUMS       # the band, its competitors, the grading code
sha256sum pipeline/frozen/band/BAND_SHA256SUMS          # must equal BAND_LIST_SHA256 in .github/workflows/update-and-deploy.yml
```
Expect every line to end in `: OK`. CI runs the same check before and after every daily run, so any edit to a frozen file fails the build.

## 2. Was the hash list anchored in Bitcoin on the freeze day?
```
ots verify pipeline/frozen/band/BAND_SHA256SUMS.ots
```
- With a local Bitcoin Core node, expect `Success! Bitcoin block NNNNNN attests existence as of <freeze day>`.
- Without a node, run `ots info pipeline/frozen/band/BAND_SHA256SUMS.ots`. It shows `BitcoinBlockHeaderAttestation(NNNNNN)`; look that block up on any explorer and check its date. Or drag both files onto opentimestamps.org.
- `Pending confirmation` only means the proof is under about a day old and has not been upgraded yet.

## 3. Is the daily record chain intact?
```
python scripts/verify_chain.py          # record hashes and prev links
python scripts/verify_chain.py --git    # also: each file hash equals that file in the commit that added the record
```
Expect `chain OK: N days, ... 0 breaks`. Each daily record `pipeline/timestamps/chain/YYYY-MM-DD.txt` (UTC date) lists the sha256 of the logs, the grades and the hash lists, plus the sha of the previous record, and is stamped with OpenTimestamps. A day whose stamp failed is covered by the next day's stamp through the chain.

## 4. Did a given day's files exist on that date?
```
ots verify pipeline/timestamps/chain/2027-01-15.txt.ots
grep band_log pipeline/timestamps/chain/2027-01-15.txt
git show <commit of that day>:data/band_log.csv | sha256sum      # must match the line above
```

## 5. Are the append-only logs really append-only?
```
python scripts/check_append_only.py <older commit>
```
This fails if any earlier row of `data/band_log.csv`, `data/band_prices.csv`, `data/band_price_revisions.csv` or `pipeline/timestamps/chain.csv` changed, or if a write-once file (`data/band_rerun.json`, `data/halving_2028.json`) changed.

## 6. Re-run the grading yourself
```
cd pipeline
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:frozen/band python frozen/band/grade_band.py frozen/band /tmp/my_grades.json ../data/band_prices.csv
diff <(python -m json.tool /tmp/my_grades.json) <(python -m json.tool ../data/band_grades.json)
```
The grades are computed only from the frozen snapshots in `pipeline/frozen/band/` and the price log. Nothing typed by hand enters them.

## What the price log means
- `data/band_prices.csv` is the **first-print** daily close: the CoinMetrics community `PriceUSD` for day D (the price at 00:00 UTC of D+1), written once the first time it appears and **never edited**. All grading uses this file.
- If CoinMetrics has no value for a day after 7 days, the close is the median of the Coinbase, Kraken and Bitstamp UTC daily candle closes (at least 2 of 3), marked with its source.
- Later changes by the source go to `data/band_price_revisions.csv` for information only. They are never applied.
- A **weekly close** is the close dated Sunday, i.e. the price at Monday 00:00 UTC.
- `data/band_log.csv` records the live (daily recomputed) band and competitors. It is a drift record only; the graded claims are the frozen snapshots.

Historical pattern test, not a price target. Not financial advice.
