#!/usr/bin/env bash
# Dated raw-data snapshot, so any day's published numbers can be rebuilt offline (see README, "Reproduce a past day").
#   daily : snapshots/YYYY/YYYY-MM-DD.tar.xz with the small raw source files (pipeline/cache/*.json except
#           the CoinMetrics history and the PRIVATE files below)                                         ~20 KB
#   weekly: snapshots/YYYY/YYYY-MM-DD.weekly.tar.xz with the two large files (pipeline/cache/coinmetrics.json,
#           data/ohlc_daily.json from Bitstamp) on Sundays (UTC), or if none exists yet                 ~280 KB
#   always: one line per raw file in snapshots/MANIFEST.csv (date, file, bytes, sha256), so every day's exact raw
#           files can be verified; the public raw cache is also in the git history of pipeline/cache/.
#   PRIVATE: Yahoo Finance, Deribit, OKX and BitMEX raw files. Their terms do not allow republishing, so they are
#           not tracked (.gitignore) and not put in the tar; only their sha256 line goes to MANIFEST.csv.
# Idempotent: a date that already has a snapshot is not written again. Failure-tolerant.
set -u; cd "$(dirname "$0")/.."
BIG="pipeline/cache/coinmetrics.json data/ohlc_daily.json"
PRIVATE='/(yahoo_btc|yahoo_mstr|crowd_deribit|crowd_okx|crowd_bitmex)\.json$'
D=${SNAP_DATE:-$(date -u +%F)}; Y=${D:0:4}; OUT=snapshots/$Y; mkdir -p "$OUT"; M=snapshots/MANIFEST.csv
test -s "$M" || echo "date,file,bytes,sha256" > "$M"
if [ ! -e "$OUT/$D.tar.xz" ]; then
  files=$(ls pipeline/cache/*.json | grep -v coinmetrics.json)
  public=$(echo "$files" | grep -Ev "$PRIVATE")
  tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -cJf "$OUT/$D.tar.xz" $public || echo "::warning::daily snapshot failed"
  for f in $files $BIG; do echo "$D,$f,$(stat -c %s "$f"),$(sha256sum "$f" | cut -d' ' -f1)" >> "$M"; done
fi
if [ "$(date -u -d "$D" +%u)" = 7 ] || ! ls snapshots/*/*.weekly.tar.xz >/dev/null 2>&1; then
  test -e "$OUT/$D.weekly.tar.xz" || tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -cJf "$OUT/$D.weekly.tar.xz" $BIG || echo "::warning::weekly snapshot failed"
fi
echo "snapshot $D: $(du -ch "$OUT"/$D.* 2>/dev/null | tail -1 | cut -f1)"
