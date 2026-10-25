#!/usr/bin/env bash
# Daily refresh. Every step is failure-tolerant: if a source or step fails, the previous files stay in place.
# Never touches pipeline/frozen/, pipeline/v2_spec.py, pipeline/robust.py or pipeline/v3/v3_spec.md (checked by the workflow).
set -u; cd "$(dirname "$0")/.."; PY=${PY:-python}
( cd pipeline && $PY signals.py ) || echo "::warning::signals.py failed"
( cd pipeline && $PY backtest.py >/dev/null ) || echo "::warning::backtest.py failed"
( cd pipeline && $PY signals.py >/dev/null ) || echo "::warning::signals.py (2nd pass) failed"
$PY build_data.py --cycle-dir pipeline || echo "::warning::build_data.py failed - site keeps previous data"
( cd pipeline && $PY hero_png.py >/dev/null ) || echo "::warning::hero_png.py failed - previous PNG kept"
# sanity: the site must still have its data files
for f in history model fan fan2 meta mstr ohlc_daily health hero_bg; do test -s "data/$f.json" || { echo "::error::data/$f.json missing"; exit 1; }; done
echo "update done"
