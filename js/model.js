/* My BTC Cycle Model - signal maths (pure functions, no DOM). Mirrors cycle_signals/lib.py. */
(function (root) {
  const DAY = 86400;
  function bisectL(a, v) { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] < v) lo = m + 1; else hi = m; } return lo; }
  function bisectR(a, v) { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] <= v) lo = m + 1; else hi = m; } return lo; }
  function pct(dist, v) { if (!dist || !dist.length || !isFinite(v)) return NaN; return 100 * (bisectL(dist, v) + bisectR(dist, v)) / 2 / dist.length; }
  function quantile(dist, q) { if (!dist || !dist.length) return NaN; const i = Math.min(dist.length - 1, Math.max(0, Math.floor(q / 100 * (dist.length - 1)))); return dist[i]; }
  function zone(h, hot, warm) { if (h == null || !isFinite(h)) return "n/a"; return h >= hot ? "hot" : h >= warm ? "warm" : h >= 40 ? "neutral" : "cool"; }
  const utcDay = (ms) => Math.floor(ms / 86400000) * DAY;          // unix seconds at 00:00 UTC
  const daysBetween = (aSec, bSec) => Math.round((bSec - aSec) / DAY);
  const tsOf = (iso) => Date.parse(iso + "T00:00:00Z") / 1000;

  /* closes: array of daily closes (oldest -> newest) for all days BEFORE today; live: today's live price. */
  function compute(M, closes, live, nowMs) {
    const n = closes.length, today = utcDay(nowMs);
    const tail = (k) => { let s = live; for (let i = n - (k - 1); i < n; i++) s += closes[i]; return s / k; };
    const ma200 = tail(200), ma1400 = tail(1400), ma111 = tail(111), ma350 = tail(350);
    // expanding power-law fit including today
    const T = M.trend_expanding_sums, x = Math.log10(daysBetween(tsOf(M.genesis), today)), y = Math.log10(live);
    const N = T.n + 1, sx = T.sx + x, sy = T.sy + y, sxx = T.sxx + x * x, sxy = T.sxy + x * y;
    const b = (N * sxy - sx * sy) / (N * sxx - sx * sx), a = (sy - b * sx) / N, trendLine = Math.pow(10, a + b * x);
    // MVRV Z with live market cap; std of market cap updated with today's value (Welford, ddof=1)
    const mcap = live * M.supply, mm = M.mcap_moments, n1 = mm.n + 1, dlt = mcap - mm.mean, mean1 = mm.mean + dlt / n1, m2 = mm.m2 + dlt * (mcap - mean1);
    const mvrvZ = (mcap - M.realized_cap) / Math.sqrt(m2 / (n1 - 1));
    // halving-cycle day
    const halv = M.halvings.map(tsOf).filter((h) => h <= today); const lastH = halv[halv.length - 1];
    const cday = daysBetween(lastH, today), C = M.calibration;
    const vals = { cycle_day: cday, mayer: live / ma200, p200w: live / ma1400, trend_mult: live / trendLine, mvrv_z: mvrvZ,
                   pi_ratio: ma111 / (2 * ma350), trends: M.fixed.trends.value, activity: M.fixed.activity.value };
    const heat = {}, zones = {}, thr = {};
    for (const s of M.signals) {
      if (s === "cycle_day") heat[s] = 100 * Math.exp(-0.5 * Math.pow((cday - C.timing_mu) / C.timing_sd, 2));
      else if (M.distributions[s]) heat[s] = pct(M.distributions[s], vals[s]);
      else heat[s] = M.fixed[s].heat;
      const hot = C.signal_hot[s] ?? 90, warm = Math.max(hot - 15, 55);
      zones[s] = zone(heat[s], hot, warm);
      if (M.distributions[s]) thr[s] = { warm: quantile(M.distributions[s], warm), hot: quantile(M.distributions[s], hot) };
    }
    const hs = M.signals.map((s) => heat[s]).filter((h) => isFinite(h));
    const score = hs.length >= 3 ? hs.reduce((p, q) => p + q, 0) / hs.length : NaN;
    const nHot = M.signals.filter((s) => heat[s] >= (C.signal_hot[s] ?? 90)).length;
    return { today, live, ma200, ma1400, ma111, ma350, trendLine, a, b, mcap, realizedPrice: M.realized_cap / M.supply, vals, heat, zones, thr,
             score, scoreZone: zone(score, C.score_hot, C.score_warm), nHot, nSignals: M.signals.length, cycleDay: cday, lastHalving: lastH };
  }
  /* Pre-registered v2 (frozen; see cycle_signals/v2_spec.py): window percentiles, 5 families, fixed zones. */
  function computeV2(M, c) {
    const V = M.v2, P = V.params, heat = {};
    for (const s of ["mayer", "p200w", "trend_mult", "mvrv_z", "pi_ratio"]) heat[s] = pct(V.distributions[s], c.vals[s]);
    heat.cycle_day = 100 * Math.exp(-0.5 * Math.pow((c.cycleDay - P.timing_mu) / P.timing_sd, 2));
    heat.activity = V.fixed_heat.activity; heat.trends = V.fixed_heat.trends;
    const fam = {};
    for (const [k, mem] of Object.entries(P.families)) { const v = mem.map((s) => heat[s]).filter((x) => x != null && isFinite(x)); fam[k] = v.length ? v.reduce((a, b) => a + b, 0) / v.length : NaN; }
    const fv = Object.values(fam).filter((x) => isFinite(x)), score = fv.length >= P.min_families ? fv.reduce((a, b) => a + b, 0) / fv.length : NaN;
    const Z = P.zones, zone = !isFinite(score) ? "n/a" : score >= Z.hot ? "hot" : score >= Z.warm ? "warm" : score >= Z.neutral ? "neutral" : "cool";
    return { score, zone, fam, heat };
  }
  /* Robust fan (cycle_signals/robust.py): log10 q = a + b*log10(days since genesis) + alpha_h + beta_h*r0 + q_h */
  function interp(x, X, Y) { if (x <= X[0]) return Y[0]; if (x >= X[X.length - 1]) return Y[Y.length - 1]; let lo = 0, hi = X.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (X[m] <= x) lo = m; else hi = m; } const w = (x - X[lo]) / (X[hi] - X[lo]); return Y[lo] + w * (Y[hi] - Y[lo]); }
  function fanAt(P, genesisSec, originSec, tSec, r0) {
    const h = Math.max(0, (tSec - originSec) / DAY), al = interp(h, P.h, P.alpha), be = interp(h, P.h, P.beta);
    const base = P.a + P.b * Math.log10((tSec - genesisSec) / DAY) + al + be * r0, out = {};
    P.qs.forEach((k, i) => { out["q" + k] = Math.pow(10, base + interp(h, P.h, P.q.map((r) => r[i]))); });
    return out;
  }
  function fanR0(P, genesisSec, tSec, price) { return Math.log10(price) - (P.a + P.b * Math.log10((tSec - genesisSec) / DAY)); }
  /* position of a price inside quantile levels (5..95), log-interpolated; <5 or >95 clipped to 0/100 */
  function fanPos(q, v) { const ks = [5, 25, 50, 75, 95], lv = ks.map((k) => Math.log(q["q" + k])), x = Math.log(v);
    if (x < lv[0]) return 0; if (x > lv[4]) return 100; return interp(x, lv, ks); }
  function normCdf(x) { const t = 1 / (1 + 0.2316419 * Math.abs(x)), d = 0.3989423 * Math.exp(-x * x / 2);
    const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); return x > 0 ? 1 - p : p; }
  function bsCall(S, K, T, r, sig) { if (T <= 0 || sig <= 0) return Math.max(S - K, 0);
    const d1 = (Math.log(S / K) + (r + sig * sig / 2) * T) / (sig * Math.sqrt(T)), d2 = d1 - sig * Math.sqrt(T);
    return S * normCdf(d1) - K * Math.exp(-r * T) * normCdf(d2); }
  function median(a) { if (!a.length) return NaN; const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
  const api = { compute, computeV2, fanAt, fanR0, fanPos, interp, pct, quantile, zone, bsCall, median, utcDay, tsOf, DAY };
  if (typeof module !== "undefined") module.exports = api; else root.BTCModel = api;
})(this);
