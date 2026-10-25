#!/usr/bin/env bash
# Daily refresh. Every step is failure-tolerant: if a source or step fails, the previous files stay in place.
# Never touches pipeline/frozen/ (v2, v3 and band), pipeline/v2_spec.py or pipeline/robust.py (checked by the workflow).
set -u; cd "$(dirname "$0")/.."; PY=${PY:-python}
( cd pipeline && $PY signals.py ) || echo "::warning::signals.py failed"
( cd pipeline && $PY backtest.py >/dev/null ) || echo "::warning::backtest.py failed"
( cd pipeline && $PY signals.py >/dev/null ) || echo "::warning::signals.py (2nd pass) failed"
$PY build_data.py --cycle-dir pipeline || echo "::warning::build_data.py failed - site keeps previous data"
# Wikipedia pageviews: no longer shown on the site; still collected (pipeline/cache, data/wiki.json) for the yearly signal review
$PY attention.py || echo "::warning::attention.py (Wikipedia pageviews, collected for the yearly review, not shown) failed - previous file kept"
$PY crowd.py || echo "::warning::crowd.py (crowd euphoria gauge, display only) failed - previous file kept"
# forward_band.py first: hero_png.py draws its forward cycle path from data/hero_fwd.json
( cd pipeline && $PY forward_band.py >/dev/null ) || echo "::warning::forward_band.py (display only) failed - previous file kept"
( cd pipeline && $PY hero_png.py >/dev/null ) || echo "::warning::hero_png.py failed - previous PNG kept"
( cd pipeline && $PY scorecard.py ) || echo "::warning::scorecard.py failed - previous scorecard kept"
# locked fan range table for the scorecard section (display only; reads the frozen fan file, never writes under frozen/)
( cd pipeline && $PY fan_locked.py >/dev/null ) || echo "::warning::fan_locked.py (display only) failed - previous file kept"
# Blue band pre-registration (PREREG_BAND.md): append-only price/band logs, then grading. Frozen code, run in place, writes only under data/.
# -P keeps the script folder off sys.path, so `lib` is pipeline/lib.py (live data cache), as when the snapshot was frozen.
( cd pipeline && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:frozen/band $PY -P frozen/band/band_log_daily.py ) || echo "::warning::band_log_daily.py failed - logs unchanged, retried next run"
( cd pipeline && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:frozen/band $PY -P frozen/band/grade_band.py frozen/band ../data/band_grades.json ../data/band_prices.csv >/dev/null ) || echo "::warning::grade_band.py failed - previous grades kept"
for f in history model fan fan2 meta mstr ohlc_daily health hero_bg; do test -s "data/$f.json" || { echo "::error::data/$f.json missing"; exit 1; }; done
echo "update done"
