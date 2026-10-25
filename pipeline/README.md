# My BTC Cycle Model

Run `python signals.py` once a day (any number of runs is safe; journal.csv keeps one row per UTC date).
- `state.json`: the latest readings (score, each signal value, heat and zone, MSTR, source status)
- `journal.csv`: one row per day, appended
- `python backtest.py`: walk-forward backtest -> out/backtest.json, out/score_history.csv
- `python charts.py`: PNGs + out/my_btc_cycle_model.pdf (run make_report.py first to refresh REPORT.md)
- `./run_daily.sh`: runs all of the above in order
If a source fails, the last cached copy (cache/) is used and the failure is recorded in state.json -> sources.
Model output, not predictions. Not financial advice.
