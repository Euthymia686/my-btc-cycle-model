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
      `<h3>Known weak spots ${I("sc_weak")}</h3><ul class="weak">` +
      `<li><b>Heat peaks are shrinking.</b> The score reached about 93 at the 2013 and 2017 tops but only about 65 to 68 at the 2021 and 2025 tops, so the next top may not look "hot".</li>` +
      `<li><b>The cycle path has pointed too high.</b> Even the scaled-down path ran far above the actual 2025 top, so it is a shape guide only.</li>` +
      `<li><b>The 90% band is too wide.</b> Checked up to 3 years ahead, about 98.6% of past prices landed inside the v3 90% band (99.4% for v2) instead of 90%. v3 narrows it, but not enough yet.</li>` +
      flags(S.tests_backtest).map((t) => `<li><b>Backtest test result.</b> ${t}</li>`).join("") +
      `<li><b>Data sources can fail.</b> If a source is down, the site keeps the last good data and the scorecard skips that day rather than guessing.</li></ul>` +
      `<p class="small">Promotion rule, set ${S.live_since || "2026-10-25"} before any result: v3 replaces v2 only if, from ${S.promotion_check_earliest || "2027-10-25"} on, it has the better log score <b>and</b> its 90% band is closer to 90% <b>and</b> it stays at or above 80% at every horizon. ` +
      `Raw data: <a href="data/scorecard.csv">scorecard.csv</a> · rules: <a href="https://github.com/Euthymia686/my-btc-cycle-model/blob/main/pipeline/frozen/v3/FREEZE.md" rel="noopener">FREEZE.md</a> · updated ${S.data_through ? "with data through " + S.data_through : "daily"}.</p>`;
  }
  fetch("data/scorecard.json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error("scorecard " + r.status); return r.json(); })
    .then(render).catch(() => { el.innerHTML = `<p class="small">Scorecard data is not available yet. First results on 2026-11-24 (30-day horizon).</p>`; });
})();
