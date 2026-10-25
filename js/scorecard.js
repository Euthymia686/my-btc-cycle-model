/* Public forward scorecard (data/scorecard.json, built daily by pipeline/scorecard.py; rules in pipeline/frozen/v3/FREEZE.md). */
(function () {
  "use strict";
  const el = document.getElementById("scorecard"); if (!el) return;
  const I = (k) => (window.Explain ? window.Explain.i(k) : "");
  const pct = (v) => v == null || !isFinite(v) ? "--" : (100 * v).toFixed(1) + "%";
  const usd = (v) => v == null || !isFinite(v) ? "--" : "$" + Math.round(v).toLocaleString("en-US");
  const fmtDay = (s) => { const d = new Date(s + "T00:00:00Z"); return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }); };
  function covCell(v, target, n) {
    if (!n) return `<td class="na">no results yet</td>`;
    const off = Math.abs(v - target); const cls = off <= 0.05 ? "ok" : off <= 0.15 ? "meh" : "bad";
    return `<td class="${cls}">${pct(v)} <span class="small">(target ${pct(target).replace(".0", "")}, n=${n})</span></td>`;
  }
  const HZ = ["30", "90", "365"], VN = { v2: "v2", v3: "v3", base: "benchmark" };
  const pv = (p) => p == null ? "--" : p < 0.001 ? "&lt;0.001" : p < 0.01 ? p.toFixed(3) : p.toFixed(2);
  const pcls = (p) => p == null ? "" : p < 0.05 ? "bad" : "";
  const CMP = [["v2_vs_base", "v2 vs benchmark"], ["v3_vs_base", "v3 vs benchmark"], ["v3_vs_v2", "v3 vs v2"]];
  function covTable(T, live) {
    let b = `<div class="stwrap"><table class="sc st"><thead><tr><th>horizon</th><th></th><th>inside 50% band</th><th>p</th><th>inside 90% band</th><th>p</th><th>eff. n ${I("sc_ess")}</th></tr></thead><tbody>`;
    for (const h of HZ) {
      const c = (T.coverage || {})[h] || {}, n = ((c.v2 || {}).eff_n) || 0;
      if (live && n < (T.min_eff || 10)) { b += `<tr><th>${h} days</th><td colspan="6" class="na">not enough data yet (${n} of ${T.min_eff || 10} independent results; expected ${c.expected || "--"})</td></tr>`; continue; }
      for (const v of ["v2", "v3", "base"]) {
        const o = c[v]; if (!o) continue;
        b += `<tr><th>${v === "v2" ? h + " days" : ""}</th><td>${VN[v]}</td><td>${pct(o.in50.rate)} <span class="small">(${o.in50.hits}/${o.eff_n})</span></td><td class="${pcls(o.in50.p)}">${pv(o.in50.p)}</td>` +
             `<td>${pct(o.in90.rate)} <span class="small">(${o.in90.hits}/${o.eff_n})</span></td><td class="${pcls(o.in90.p)}">${pv(o.in90.p)}</td><td>${o.eff_n}</td></tr>`;
      }
    }
    return b + "</tbody></table></div>";
  }
  function skillTable(T, live) {
    let b = `<div class="stwrap"><table class="sc st"><thead><tr><th>horizon</th><th>comparison</th><th>mean log score difference</th><th>p</th><th>eff. n</th></tr></thead><tbody>`;
    for (const h of HZ) {
      const s = (T.skill || {})[h] || {}, n = ((s.v2_vs_base || {}).eff_n) || 0;
      if (live && n < (T.min_eff || 10)) { b += `<tr><th>${h} days</th><td colspan="4" class="na">not enough data yet (${n} of ${T.min_eff || 10}; expected ${s.expected || "--"})</td></tr>`; continue; }
      CMP.forEach(([k, lab], i) => { const o = s[k] || {}; const md = o.mean_diff;
        b += `<tr><th>${i ? "" : h + " days"}</th><td>${lab}</td><td>${md == null ? "--" : (md > 0 ? "+" : "") + md.toFixed(2)}</td><td class="${o.p != null && o.p < 0.05 ? (md > 0 ? "ok" : "bad") : ""}">${pv(o.p)}</td><td>${o.eff_n == null ? "--" : o.eff_n}</td></tr>`; });
    }
    return b + "</tbody></table></div>";
  }
  function flags(B) {
    const out = []; if (!B) return out;
    for (const h of HZ) for (const v of ["v2", "v3"]) { const o = ((B.coverage || {})[h] || {})[v]; if (!o) continue;
      for (const [k, t] of [["in50", 50], ["in90", 90]]) if (o[k].p != null && o[k].p < 0.05)
        out.push(`${v}'s ${t}% band at ${h} days held ${pct(o[k].rate)} of prices (${o[k].hits} of ${o.eff_n} independent forecasts, p ${pv(o[k].p)}), so it looks ${o[k].rate > t / 100 ? "too wide" : "too narrow"} there.`); }
    for (const h of HZ) for (const v of ["v2", "v3"]) { const o = ((B.skill || {})[h] || {})[v + "_vs_base"];
      if (o && o.p != null && o.p < 0.05 && o.mean_diff < 0) out.push(`At ${h} days the plain benchmark scored better than ${v} (p ${pv(o.p)}).`); }
    return out;
  }
  function killBlock(K, KB) {
    if (!K || !K.versions) return "";
    const R = K.rules || { a_p: 0.01, a_min: 10, b_weeks: 26, c_p: 0.05, c_min: 12 };
    const st = (on) => on ? `<td class="bad">triggered</td>` : `<td class="ok">not triggered</td>`;
    const aNote = (V) => { const r = V.a.filter((x) => x.eff_n >= R.a_min && x.p != null); if (!r.length) return `waiting for ${R.a_min} independent results (have ${Math.max(...V.a.map((x) => x.eff_n))})`; const m = r.reduce((x, y) => (y.p < x.p ? y : x)); return `lowest p ${pv(m.p)} (${m.h} days, n=${m.eff_n})`; };
    const cNote = (V) => { const r = V.c.filter((x) => x.p != null && x.mean_diff < 0); if (!r.length) { const n = Math.max(...V.c.map((x) => x.eff_n || 0)); return n < R.c_min ? `waiting for ${R.c_min} independent results (have ${n})` : "never behind the benchmark"; } const m = r.reduce((x, y) => (y.p < x.p ? y : x)); return `behind at ${m.h} days, p ${pv(m.p)}, n=${m.eff_n}${m.eff_n < R.c_min ? " (below " + R.c_min + ")" : ""}`; };
    const b = K.b || {}, lc = b.latest_close;
    const bLive = `${b.current_run || 0} weeks below the floor now (longest ${b.longest_run || 0})` + (lc ? `; latest close ${usd(lc.close)} vs floor ${usd(lc.floor)}` : "");
    const bb = (KB || {}).b; const bPast = !bb ? "--" : bb.runs && bb.runs.length ? `would have triggered ${bb.runs.length} times: ` + bb.runs.map((r) => `${r.weeks} weeks from ${fmtDay(r.start)}`).join(", ") : "never" + (bb.longest_run ? ` (longest run ${bb.longest_run} weeks, from ${fmtDay(bb.longest_start)})` : "");
    const V2 = K.versions.v2, V3 = K.versions.v3, P2 = KB && KB.versions ? KB.versions.v2 : null, P3 = KB && KB.versions ? KB.versions.v3 : null;
    const past = (on, txt) => `<td class="${on ? "bad" : ""}">${on ? "yes" : "no"}<span class="small">, ${txt}</span></td>`;
    const aOn = (V) => V.a.some((x) => x.triggered), cOn = (V) => V.c.some((x) => x.triggered);
    let h = `<div class="stwrap"><table class="sc st"><thead><tr><th>criterion</th><th>v2 (live)</th><th>v3 (live)</th><th>backtest (past data)</th></tr></thead><tbody>`;
    h += `<tr><th>(a) 90% band fails: p below ${R.a_p} on at least ${R.a_min} independent results</th>${st(aOn(V2))}${st(aOn(V3))}` +
         (P2 ? past(aOn(P2) || aOn(P3), `v2 ${aNote(P2)}; v3 ${aNote(P3)}`) : "<td>--</td>") + `</tr>`;
    h += `<tr><td colspan="4" class="small">Live: v2 ${aNote(V2)}; v3 ${aNote(V3)}.</td></tr>`;
    h += `<tr><th>(b) ${R.b_weeks} or more weekly closes in a row below the power-law floor (both versions)</th>${st(b.triggered)}${st(b.triggered)}` +
         `<td class="${bb && bb.triggered ? "bad" : ""}">${bPast}</td></tr>`;
    h += `<tr><td colspan="4" class="small">Live: ${bLive}.</td></tr>`;
    h += `<tr><th>(c) loses to the benchmark: p below ${R.c_p} on at least ${R.c_min} independent results</th>${st(cOn(V2))}${st(cOn(V3))}` +
         (P2 ? past(cOn(P2) || cOn(P3), `v2 ${cNote(P2)}; v3 ${cNote(P3)}`) : "<td>--</td>") + `</tr>`;
    h += `<tr><td colspan="4" class="small">Live: v2 ${cNote(V2)}; v3 ${cNote(V3)}.</td></tr>`;
    return h + `</tbody></table></div><p class="small">Overall: v2 <b>${V2.status}</b>, v3 <b>${V3.status}</b>. A triggered version is retired publicly and never restored; it keeps being logged so its record stays complete.</p>`;
  }
  function render(S) {
    const V = S.versions || {}, v2 = V.v2 || {}, v3 = V.v3 || {}, n2 = (v2.all || {}).matured || 0, n3 = (v3.all || {}).matured || 0;
    let live;
    if (!n2 && !n3) {
      live = `<p class="first">No forecast has matured yet. <b>First results on ${S.next_result || "2026-11-24"} (${S.next_result_horizon || 30}-day horizon).</b></p>`;
    } else {
      const row = (name, o) => `<tr><th>${name}</th>${covCell((o.all || {}).in50, 0.5, (o.all || {}).matured)}${covCell((o.all || {}).in90, 0.9, (o.all || {}).matured)}<td>${(o.all || {}).log_score == null ? "--" : (o.all.log_score).toFixed(2)}</td></tr>`;
      live = `<table class="sc"><thead><tr><th></th><th>inside 50% band ${I("sc_cov")}</th><th>inside 90% band</th><th>log score ${I("sc_log")}</th></tr></thead><tbody>${row("v2", v2)}${row("v3", v3)}${V.base ? row("benchmark", V.base) : ""}</tbody></table>` +
        `<p class="small">Matured predictions so far: ${n2} per version (30-day ${((v2.by_horizon || {})["30"] || {}).matured || 0}, 90-day ${((v2.by_horizon || {})["90"] || {}).matured || 0}, 365-day ${((v2.by_horizon || {})["365"] || {}).matured || 0}).` +
        (S.next_result ? ` Next result: ${S.next_result}.` : "") + `</p>`;
    }
    const L2 = v2.latest, L3 = v3.latest;
    const latest = L2 && L3 ? `<p class="small">Latest forecasts, made from the ${fmtDay(L2.close_date)} close of ${usd(L2.btc_close)}: ` +
      ["30", "90", "365"].map((h) => `${h} days: v2 ${usd(L2[h].q5)} to ${usd(L2[h].q95)}, v3 ${usd(L3[h].q5)} to ${usd(L3[h].q95)} (90% bands, middle ${usd(L2[h].q50)})`).join("; ") +
      `. Days logged so far: ${v2.forecast_days || 0}.</p>` : "";
    const B = S.backtest_2017on || {}, BA = S.backtest_v2_all;
    const bt = B.v2 ? `<table class="sc"><thead><tr><th></th><th>inside 50% band</th><th>inside 90% band</th></tr></thead><tbody>` +
      `<tr><th>v2</th><td>${pct(B.v2.in50)}</td><td>${pct(B.v2.in90)}</td></tr><tr><th>v3</th><td>${pct(B.v3.in50)}</td><td>${pct(B.v3.in90)}</td></tr></tbody></table>` +
      `<p class="small">Fans frozen ${B.freezes}, each checked on every later day up to about 3 years ahead (${(B.days || 0).toLocaleString("en-US")} checks, heavily overlapping). Within the first year ahead: v2 ${pct(B.first_year.v2.in90)}, v3 ${pct(B.first_year.v3.in90)} inside the 90% band.` +
      (BA ? ` v2 over all freezes 2015-2025: ${pct(BA.in90)} / ${pct(BA.in50)}.` : "") + `</p>` : "";
    el.innerHTML =
      `<div class="scgrid"><div><h3>Live (since ${S.live_since || "2026-10-25"}) ${I("sc_live")}</h3>${live}${latest}</div>` +
      `<div><h3>Backtest (past data) ${I("sc_backtest")}</h3>${bt}</div></div>` +
      `<h3>Statistical tests ${I("sc_tests")}</h3>` +
      `<p class="small"><b>Live (since ${S.live_since || "2026-10-25"}).</b> Coverage ${I("sc_binom")}</p>${covTable(S.tests_live || {}, true)}` +
      `<p class="small">Skill against a simple benchmark ${I("sc_dm")} ${I("sc_base")}</p>${skillTable(S.tests_live || {}, true)}` +
      (S.tests_backtest ? `<p class="small"><b>Backtest (past data)</b> ${I("sc_bt_p")}: one forecast per day from ${S.tests_backtest.first_origin}, each made with data up to its own date only (${(S.tests_backtest.origins || 0).toLocaleString("en-US")} forecasts). Coverage</p>${covTable(S.tests_backtest, false)}` +
        `<p class="small">Skill (positive means the first one scored better)</p>${skillTable(S.tests_backtest, false)}` : "") +
      `<h3>Kill criteria ${I("sc_kill")}</h3>` + killBlock(S.kill, S.kill_backtest) +
      "";
    const ws = document.getElementById("weakSpots"), weak = `<h3>Known weak spots ${I("sc_weak")}</h3><ul class="weak">` +
      `<li><b>Heat peaks are shrinking.</b> The score reached about 93 at the 2013 and 2017 tops but only about 65 to 68 at the 2021 and 2025 tops, so the next top may not look "hot".</li>` +
      `<li><b>The cycle path has pointed too high.</b> Even the scaled-down path ran far above the actual 2025 top, so it is a shape guide only.</li>` +
      `<li><b>The 90% band is too wide.</b> Checked up to 3 years ahead, about 98.6% of past prices landed inside the v3 90% band (99.4% for v2) instead of 90%. v3 narrows it, but not enough yet.</li>` +
      flags(S.tests_backtest).map((t) => `<li><b>Backtest test result.</b> ${t}</li>`).join("") +
      `<li><b>Data sources can fail.</b> If a source is down, the site keeps the last good data and the scorecard skips that day rather than guessing.</li></ul>`;
    if (ws) ws.innerHTML = weak; else el.innerHTML += weak;
    el.innerHTML +=
      `<p class="small">Promotion rule, set ${S.live_since || "2026-10-25"} before any result: v3 replaces v2 only if, from ${S.promotion_check_earliest || "2027-10-25"} on, it has the better log score <b>and</b> its 90% band is closer to 90% <b>and</b> it stays at or above 80% at every horizon. ` +
      `Raw data: <a href="data/scorecard.csv">scorecard.csv</a> · rules: <a href="https://github.com/Euthymia686/my-btc-cycle-model/blob/main/pipeline/frozen/v3/FREEZE.md" rel="noopener">FREEZE.md</a> · updated ${S.data_through ? "with data through " + S.data_through : "daily"}.</p>`;
  }
  /* Graded forecast range, locked 2026-10-25 (data/fan_locked.json, from pipeline/fan_locked.py): fixed numbers read from the
     frozen fan file, v3 = same fan with the frozen v3 scales. Not recomputed with the live price. Moved here from the main chart. */
  const lf = document.getElementById("lockedFan");
  if (lf) fetch("data/fan_locked.json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error("fan_locked " + r.status); return r.json(); }).then((F) => {
    const K = (v) => v == null || !isFinite(v) ? "--" : "$" + Math.round(v / 1000).toLocaleString("en-US") + "K";
    const row = (r, v) => `<tr><td>${fmtDay(r.date)}</td><td>${v}</td>${["q5", "q25", "q50", "q75", "q95"].map((k) => `<td${k === "q50" ? ' class="med"' : ""}>${K(r[v][k])}</td>`).join("")}</tr>`;
    lf.innerHTML = `<h3>Graded forecast range, locked ${F.frozen_on} ${I("lockedfan")}</h3>` +
      `<p class="small">Where the model expected the price to be, written down on ${F.frozen_on} (from the ${F.data_through} close) and never changed. Fixed numbers from the frozen fan file, not recomputed with the live price. If the model is right, the price on that date lands in the 25%-75% range about half the time and in the 5%-95% range about 90% of the time.</p>` +
      `<div class="stwrap"><table class="sc lf"><thead><tr><th>date</th><th>version</th><th>5%</th><th>25%</th><th>median</th><th>75%</th><th>95%</th></tr></thead><tbody>` +
      F.rows.map((r) => row(r, "v2") + row(r, "v3")).join("") + `</tbody></table></div>` +
      `<p class="small">v3 is the same fan with narrower bands (frozen scales ${F.s90} and ${F.s50}); which one is better is decided by the scorecard below. This range was drawn on the main chart until 2026-10-25; it is now shown here so it is not mixed up with the blue cycle band (a shape guide). Model ranges, not predictions. ` +
      `Frozen file: <a href="https://github.com/Euthymia686/my-btc-cycle-model/blob/main/pipeline/frozen/${F.fan_file}" rel="noopener">${F.fan_file}</a> <span class="mono">sha256 ${F.fan_sha256.slice(0, 12)}...</span></p>`;
  }).catch(() => { lf.innerHTML = ""; });
  /* Blue cycle band pre-registration (data/band_grades.json, from pipeline/frozen/band/grade_band.py; rules in PREREG_BAND.md).
     Display of the frozen claims and their grades only; nothing here is computed in the browser. */
  const bs = document.getElementById("bandScore");
  if (bs) fetch("data/band_grades.json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error("band_grades " + r.status); return r.json(); }).then((G) => {
    const K = (v) => v == null || !isFinite(v) ? "--" : "$" + Math.round(v / 1000).toLocaleString("en-US") + "K";
    const st = G.status || {}, top = st.top || {}, low = st.low || {}, C = G.claims || {};
    const res = (x) => !x || x.hit == null ? "pending" : (x.hit ? "hit" : "miss");
    const rng = (h) => h && h.range && h.range[0] != null ? `${K(h.range[0])} to ${K(h.range[1])} (point ${K(h.point)})` : (h ? K(h.point) : "--");
    const row = (name, c) => `<tr><th>${name}</th><td>${c.timing ? fmtDay(c.timing.predicted) : "--"}</td><td>${c.timing ? (/^same/.test(c.timing.source || "") ? "same date as the band" : res(c.timing)) : ""}</td>` +
      `<td>${c.height ? rng(c.height) : "--"}</td><td>${c.height ? res(c.height) : ""}</td><td>${c.low ? rng(c.low) : "--"}</td><td>${c.low ? res(c.low) : ""}</td></tr>`;
    const names = { band: "Blue band (main claim)", C1: "C1 ensemble-corrected band", C2: "C2 size law S1", C3: "C3 on-chain size law S3", C4: "C4 lengthening-cycle timing" };
    const P = G.path || {}, M = P.mae || {};
    const verdict = G.verdict_main && top.final && low.final ? `<b>Verdict on the main claim: ${G.verdict_main}.</b>` :
      `<b>Verdict: pending.</b> The top window opens 2028-01-02; a top counts only once confirmed (52 weeks and a 50% drawdown, or at the end of the window).`;
    bs.innerHTML = `<h3>Cycle band and its competitors, frozen 2026-10-25 ${I("bandscore")}</h3>` +
      `<p class="small">${verdict} Status: ${top.outcome_class || "pending"}${top.T_star && top.final ? ` (top ${fmtDay(top.T_star)} at ${K(top.close)})` : ""}${low.L_star && low.final ? `; low ${fmtDay(low.L_star)} at ${K(low.close)}` : ""}.</p>` +
      `<div class="stwrap"><table class="sc lf"><thead><tr><th>forecast</th><th>top date</th><th></th><th>top price</th><th></th><th>following low</th><th></th></tr></thead><tbody>` +
      ["band", "C1", "C2", "C3", "C4"].filter((k) => C[k]).map((k) => row(names[k], C[k])).join("") + `</tbody></table></div>` +
      (P.weeks ? `<p class="small">Weekly path so far (${P.weeks} weeks, mean absolute log10 error, lower is better): band ${(M.band ?? NaN).toFixed(3)}, C1 ${(M.C1 ?? NaN).toFixed(3)}, trend line ${(M.trend ?? NaN).toFixed(3)}. ` +
        (P.formal_results_allowed ? `Band vs trend test p = ${((P.H4_primary_DM_band_vs_trend || {}).p ?? NaN).toFixed(3)}.` : `Formal tests start after 104 weeks.`) + `</p>` : "") +
      (((G.events || {}).floor_breaks || []).length ? `<p class="small">Weekly closes below the trend floor: ${(G.events.floor_breaks || []).length} run(s).</p>` : "") +
      `<p class="small">The band drawn on the main chart is recomputed daily; this table grades the copy frozen on 2026-10-25, whose code and values are fixed by sha256 and timestamped. The competitors are secondary and cannot replace the main claim after the fact. Historical pattern test, not a price target. ` +
      `Rules: <a href="https://github.com/Euthymia686/my-btc-cycle-model/blob/main/pipeline/frozen/band/PREREG_BAND.md" rel="noopener">PREREG_BAND.md</a> · how to check: <a href="https://github.com/Euthymia686/my-btc-cycle-model/blob/main/VERIFY.md" rel="noopener">VERIFY.md</a> · raw: <a href="data/band_log.csv">band_log.csv</a>, <a href="data/band_prices.csv">band_prices.csv</a>, <a href="data/band_grades.json">band_grades.json</a>.</p>`;
  }).catch(() => { bs.innerHTML = ""; });
  const getJ = (n) => fetch("data/" + n + ".json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(n + " " + r.status); return r.json(); });
  const pS = getJ("scorecard"), pG = getJ("band_grades").catch(() => null), pF = getJ("fan_locked").catch(() => null);
  pS.then(render).catch(() => { el.innerHTML = `<p class="small">Scorecard data is not available yet. First results on 2026-11-24 (30-day horizon).</p>`; });
  /* Plain-language summary at the top of the scorecard: one row per pre-registered prediction, its status and when it is graded.
     Display only: it reads the same published files as the detailed tables below and computes nothing new. */
  const sum = document.getElementById("scoreSummary");
  if (sum) Promise.all([pS.catch(() => null), pG, pF]).then(([S, G, F]) => {
    const K = (v) => v == null || !isFinite(v) ? "--" : v >= 1e6 ? "$" + (v / 1e6).toFixed(2) + "M" : "$" + Math.round(v / 1000).toLocaleString("en-US") + "K";
    const pill = (st, txt) => `<span class="pill p-${st}">${txt}</span>`;
    const res = (x, fin) => !x || x.hit == null || !fin ? pill("wait", "pending") : x.hit ? pill("pass", "hit") : pill("fail", "miss");
    const addD = (iso, d) => { const t = new Date(iso + "T00:00:00Z"); t.setUTCDate(t.getUTCDate() + d); return t.toISOString().slice(0, 10); };
    const rows = [];
    const C = (G && G.claims) || {}, b = C.band, st = (G && G.status) || {};
    if (b) {
      rows.push([`Next cycle top: <b>when</b> ${I("lg_band")}`, `around <b>${fmtDay(b.timing.predicted)}</b><br><span class="small">counts if within &plusmn;91 days: ${fmtDay(addD(b.timing.predicted, -91))} to ${fmtDay(addD(b.timing.predicted, 91))}</span>`, res(b.timing, st.top && st.top.final), "Apr 6, 2031"]);
      rows.push([`Next cycle top: <b>how high</b>`, `<b>${K(b.height.range[0])} to ${K(b.height.range[1])}</b><br><span class="small">middle ${K(b.height.point)} (highest weekly close)</span>`, res(b.height, st.top && st.top.final), "Apr 6, 2031"]);
      rows.push([`Low after the top`, `<b>${K(b.low.range[0])} to ${K(b.low.range[1])}</b><br><span class="small">middle ${K(b.low.point)}, around ${fmtDay(b.low.date)}</span>`, res(b.low, st.low && st.low.final), "2 years after the top"]);
    }
    if (F && F.rows) rows.push([`Locked price range ${I("lockedfan")}`, F.rows.map((r) => `${fmtDay(r.date)}: <b>${K(r.v2.q5)} to ${K(r.v2.q95)}</b>`).join("<br>") + `<br><span class="small">90% range, middle ${F.rows.map((r) => K(r.v2.q50)).join(" / ")}</span>`, pill("wait", "pending"), F.rows.map((r) => fmtDay(r.date)).join(" and ")]);
    if (S) {
      const V = S.versions || {}, n2 = ((V.v2 || {}).all || {}).matured || 0, a2 = (V.v2 || {}).all || {}, a3 = ((V.v3 || {}).all) || {};
      const rt = (o) => { const v = o && o.in90 != null && typeof o.in90 === "object" ? o.in90.rate : o && o.in90; return v == null ? "--" : (100 * v).toFixed(0) + "%"; };
      const cov = n2 ? `v2 ${rt(a2)}, v3 ${rt(a3)} inside the 90% range (target 90%, ${n2} graded)` : "no forecast has come due yet";
      rows.push([`Daily price ranges, 30 / 90 / 365 days ahead ${I("v3")}`, `a new range every day, v2 vs v3 vs a simple benchmark<br><span class="small">${cov}</span>`, n2 ? pill("run", "being graded") : pill("wait", "pending"), `first on ${fmtDay(S.next_result || "2026-11-24")}, then daily`]);
      const k = S.kill && S.kill.versions, on = k ? ["v2", "v3"].filter((v) => k[v] && k[v].status !== "not triggered") : [];
      if (k) rows.push([`Rules that would retire the model ${I("sc_kill")}`, `3 rules written in advance (e.g. 26 weeks in a row below the floor)`, on.length ? pill("fail", "triggered: " + on.join(", ")) : pill("pass", "not triggered"), "checked every day"]);
    }
    if (!rows.length) { sum.innerHTML = ""; return; }
    sum.innerHTML = `<div class="stwrap"><table class="sc sumt"><thead><tr><th>What is predicted ${I("sc_sum")}</th><th>The prediction</th><th>Result</th><th>Graded on</th></tr></thead><tbody>` +
      rows.map((r) => `<tr><th>${r[0]}</th><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td></tr>`).join("") + `</tbody></table></div>` +
      `<p class="small">All frozen on Oct 25, 2026 and never changed: they pass or fail on real prices that did not exist yet. Pending means its date has not come.</p>`;
  });
})();
