/* "Being tested (not scored)": shadow signal candidates pre-registered on 2026-10-26 for the 2027-10-25 review
   (pipeline/candidates/PREREG_CANDIDATES.md). Display only: nothing here feeds the Cycle Heat Score, v2, v3 or the scorecard.
   Daily values come from data/candidates.json (built by candidates.py); the leverage tile adds a live exchange reading
   (Deribit open interest, fetched by the visitor's browser through js/feeds.js). Muted styling on purpose: no zone colors. */
(async function () {
  "use strict";
  const box = document.getElementById("candTiles"), sec = document.getElementById("candSec"); if (!box || !sec) return;
  const R = window.__cand = { errors: [] };
  const load = (n) => fetch("data/" + n + ".json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(n + " " + r.status); return r.json(); }).then(Feeds.clean);
  let D, M;
  try { [D, M] = await Promise.all([load("candidates"), load("model")]); } catch (e) { R.errors.push(String(e.message)); sec.hidden = true; return; }
  const T = {}; (D.tiles || []).forEach((t) => { T[t.id] = t; });
  const f = (v, d = 2) => v == null || !isFinite(v) ? "--" : Number(v).toFixed(d);
  const ago = (ms) => { const s = Math.max(0, Math.round(ms / 1000)); return s < 90 ? s + "s ago" : Math.round(s / 60) + " min ago"; };
  const usdB = (v) => !isFinite(v) ? "--" : "$" + (v / 1e9).toFixed(2) + "B";
  const REV = D.review_date || "2027-10-25";
  const NOT = `It does not feed the Cycle Heat Score or any graded version (v2, v3, the band test). It is logged every day, in public, and judged at the review on ${REV} under rules written down before any new data (PREREG_CANDIDATES.md). The heat (0-100) uses the same percentile method as the scored signals, but it is shown in gray because it has no zone yet.`;
  const oi = new Feeds.DeribitOI(() => render());   // live leverage context, direct from Deribit in the visitor's browser
  Feeds.onWake(() => oi.wake()); R.oi = oi;
  const liveMcap = () => { const L = window.__app && window.__app.last; return L && L.price && L.via === "live" && M.supply ? L.price * M.supply : null; };
  const closePx = () => { const L = window.__app && window.__app.last; return L && L.price ? L.price : null; };
  const X = window.Explain.T;
  X.cand = "Signals being tested for possible use in a future version. None of them is in the Cycle Heat Score. Each is logged daily from 2026-10-26 and checked on " + REV + " against rules fixed in advance: does it pick out past tops and lows, add something the score does not already have, and avoid false alarms. If in doubt, nothing changes.";
  X.cand_puell = `Puell Multiple: miners' daily income from new coins (in dollars) divided by its 1-year average. High values mean miners are earning far above normal, which happened near past tops. (Uses issuance only; fees are excluded because the free data does not include them.)\n\n${NOT}\n\nUpdates daily, at the CoinMetrics close (latest: ${(T.puell || {}).as_of || "--"}). Source: ${(T.puell || {}).source || "CoinMetrics"}.`;
  X.cand_leverage = () => { const t = T.leverage || {}, m = liveMcap();
    return `Futures leverage: open interest in CME bitcoin futures as a share of bitcoin's market cap, compared with its own past year (the heat). High means leverage is building up.\n\n${NOT}\n\nHow often it updates: the tested value is weekly (CFTC Commitments of Traders, Tuesday data published Friday; latest report ${t.report_date || "--"}). The "live" line is extra context only: Deribit's public BTC futures open interest, fetched by your browser every minute and divided by the live market cap. Deribit is one exchange, not the whole market, so its share is much smaller than the total.\n\nLive now: ${oi.fresh() ? `${usdB(oi.usd)} open interest${m ? ` = ${f(100 * oi.usd / m, 3)}% of market cap` : " (waiting for a live price)"}, checked ${ago(Date.now() - oi.okAt)}` : oi.err ? `Deribit not reachable from this network (${oi.err}); showing the daily figures` : "connecting..."}.`; };
  X.cand_liquidity = `Liquidity (a skeptical test): the Fed's net liquidity (its balance sheet minus the Treasury's account and reverse repos) and the broad dollar index, each compared with a year ago. High means liquidity is growing and the dollar falling. Many charts claim bitcoin follows this; this test checks whether it adds anything.\n\n${NOT}\n\nUpdates weekly: the Fed balance sheet is published on Thursdays (as of ${(T.liquidity || {}).as_of || "--"}); the dollar index is daily with about a week's delay. Source: Federal Reserve via FRED (public domain).`;
  X.cand_etf = `Spot ETF flows: daily net money into US spot bitcoin ETFs. If shown, it would be display only and never tested for scoring, because the history only starts in January 2024.\n\nNot shown: we found no free source whose terms allow republishing the daily flow numbers (the common trackers and issuer pages do not permit it). It will be added only if a source gives permission.`;

  const spark = (pts) => { if (!pts || pts.length < 2) return ""; const w = 200, h = 26, n = pts.length;
    const p = pts.map(([, v], i) => v == null ? null : `${(i / (n - 1) * w).toFixed(1)},${(h - 2 - v / 100 * (h - 4)).toFixed(1)}`).filter(Boolean);
    return `<svg class="cspark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-label="heat, last 12 months"><polyline fill="none" stroke="currentColor" stroke-width="1.2" vector-effect="non-scaling-stroke" points="${p.join(" ")}"/></svg>`; };
  const heatBar = (h) => h == null ? "" : `<div class="cbar" title="heat ${f(h, 0)} / 100 (not scored)"><span style="width:${Math.max(1, Math.min(100, h))}%"></span></div>`;
  const tag = (k) => `<span class="ctag${k === "live" ? " on" : ""}">${k}</span>`;
  const prev = {};
  function card(id, k, title, mode, val, h, lines, sp) {
    const html = `<div class="ct"><span>${title} ${window.Explain.i(k)}</span>${tag(mode)}</div><div class="cval">${val}</div>${heatBar(h)}<div class="cd">${lines}</div>${sp || ""}`;
    if (prev[id] !== html) { document.getElementById("c_" + id).innerHTML = html; prev[id] = html; } }
  box.innerHTML = ["puell", "leverage", "liquidity", "etf_flows"].map((id) => `<div class="ctile${id === "etf_flows" ? " omit" : ""}" id="c_${id}"></div>`).join("");
  function render() {
    try { const t = T.puell; card("puell", "cand_puell", "Puell Multiple", "daily", t.value_fmt, t.heat, `heat ${f(t.heat, 0)} &middot; as of ${t.as_of}`, spark(t.spark)); } catch (e) { R.errors.push("puell " + e.message); }
    try { const t = T.leverage, m = liveMcap(), live = oi.fresh() && m;
      const ctx = t.context || {}, liveLine = live ? `Deribit OI ${usdB(oi.usd)} = ${f(100 * oi.usd / m, 3)}% of mcap, live (${ago(Date.now() - oi.okAt)})`
        : `exchange context: OKX ${ctx.okx_oi_mcap != null ? f(100 * ctx.okx_oi_mcap, 2) + "%" : "--"}${ctx.deribit_oi_mcap != null ? `, Deribit ${f(100 * ctx.deribit_oi_mcap, 2)}%` : ""} of mcap, daily`;
      card("leverage", "cand_leverage", "Futures leverage", live ? "live" : "weekly", t.value_fmt, t.heat, `CME, heat ${f(t.heat, 0)} &middot; CFTC report ${t.report_date}<br>${liveLine}`, spark(t.spark)); } catch (e) { R.errors.push("leverage " + e.message); }
    try { const t = T.liquidity; card("liquidity", "cand_liquidity", "Liquidity (Fed + dollar)", "weekly", t.value_fmt, t.heat, `heat ${f(t.heat, 0)} &middot; Fed data as of ${t.as_of}`, spark(t.spark)); } catch (e) { R.errors.push("liquidity " + e.message); }
    try { card("etf_flows", "cand_etf", "Spot ETF flows", "not shown", `<span class="cna">not shown</span>`, null, "no free source allows republishing; display only if one does", ""); } catch (e) { R.errors.push("etf " + e.message); }
  }
  render(); setInterval(() => { if (!document.hidden) render(); }, 5000);
})().catch((e) => { (window.__cand = window.__cand || { errors: [] }).errors.push("init: " + e.message); });
