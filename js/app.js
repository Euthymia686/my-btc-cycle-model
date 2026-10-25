/* My BTC Cycle Model - live page. Static: loads data/*.json, then everything updates in the browser. */
(async function () {
  "use strict";
  window.__app = { errors: [], ticks: 0 };
  window.addEventListener("error", (e) => window.__app.errors.push(String(e.message || e)));
  const $ = (id) => document.getElementById(id), LC = window.LightweightCharts, BM = window.BTCModel, DAY = 86400;
  const ZC = { cool: "#3b82f6", neutral: "#9ca3af", warm: "#f59e0b", hot: "#ef4444", "n/a": "#555" };
  const usd = (v, d = 0) => v == null || !isFinite(v) ? "--" : "$" + v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const usdK = (v) => !isFinite(v) ? "--" : v >= 1e6 ? "$" + (v / 1e6).toFixed(2) + "M" : v >= 1e4 ? "$" + (v / 1e3).toFixed(0) + "K" : usd(v);
  const f = (v, d = 2) => v == null || !isFinite(v) ? "--" : Number(v).toFixed(d);
  const isoDay = (sec) => new Date(sec * 1000).toISOString().slice(0, 10);
  const ago = (ms) => { const s = Math.max(0, Math.round(ms / 1000)); return s < 90 ? s + "s ago" : s < 5400 ? Math.round(s / 60) + " min ago" : Math.round(s / 3600) + " h ago"; };
  const load = (n) => fetch("data/" + n + ".json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(n + " " + r.status); return r.json(); }).then(Feeds.clean);   // strings in data files are escaped (shown as text, never as HTML)

  const [M, H, FAN2, HEALTH, META] = await Promise.all(["model", "history", "fan2", "health", "meta"].map(load));
  const [BG, FWD] = await Promise.all([load("hero_bg").catch(() => null), load("hero_fwd").catch(() => null)]);
  const CR = await load("crowd").catch(() => null);   // display-only crowd euphoria gauge (optional file)   // optional files
  $("built").textContent = `Daily data files built ${META.built_utc.replace("T", " ").slice(0, 16)} UTC (on-chain as of ${M.last_daily}). Live prices and blocks come directly from the exchanges and mempool.space into your browser (WebSocket streaming, HTTPS polling as fallback).`;

  /* ---------- live feeds (start connecting right away, in parallel with the optional gap-fill below) ---------- */
  let lastTick = null, prevShown = null;
  const feeds = Feeds.SOURCES.map((s) => new Feeds.Feed(s, () => {}));
  const pollers = Feeds.POLL_SOURCES.map((s) => new Feeds.Poller(s)), allSrc = feeds.concat(pollers), t0 = Date.now();
  let polling = false;   // polling mode: fewer than 2 exchange WebSockets delivering prices (checked every second in tick)
  function setPolling() { const ok = feeds.filter((x) => x.wsFresh()).length;
    const want = ok < 2 && (Date.now() - t0 > Feeds.WS_GRACE_MS || feeds.every((x) => x.diag().ws === "blocked"));
    if (want !== polling) { polling = want; pollers.forEach((x) => x.setActive(want)); } }
  const blocks = new Feeds.Blocks((b, isNew) => { if (isNew) flash($("height")); });
  window.__app.feeds = feeds; window.__app.pollers = pollers; window.__app.blocks = blocks; window.__app.wakes = [];
  Feeds.onWake((why) => { window.__app.wakes.push(why); allSrc.forEach((x) => x.wake()); blocks.wake(); setTimeout(() => { try { tick(true); } catch (e) {} }, 50); });

  /* ---------- daily history: CoinMetrics closes, gap-filled from Coinbase daily candles if the files are a few days old ---------- */
  const closes = H.close.slice(), cT = H.t.slice();
  let todayOpen = null, gapFilled = 0;
  try {
    const cb = await Promise.race([Feeds.getJSON("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400"),
      new Promise((_, rej) => setTimeout(() => rej(new Error("timeout (3.5 s), page continues with the daily files")), 3500))]);
    const today0 = BM.utcDay(Date.now());
    if (!Array.isArray(cb)) throw new Error("unexpected candle response");
    cb.filter((r) => Array.isArray(r)).map((r) => r.slice(0, 5).map(Number)).filter((r) => Number.isInteger(r[0]) && Feeds.num(r[4]) && Feeds.num(r[3]))   // finite numbers only
      .sort((a, b) => a[0] - b[0]).forEach(([t, lo, hi, op, cl]) => {
      if (t === today0) todayOpen = op;
      if (t > cT[cT.length - 1] && t < today0) { cT.push(t); closes.push(cl); gapFilled++; }
    });
  } catch (e) { window.__app.errors.push("coinbase daily candles: " + e.message); }

  /* index price: median of feeds with a tick < 15 s old, outliers (> 0.5% from the others) dropped. Never presents an old price as live. */
  function indexPrice() {
    const c = Feeds.combine(allSrc);
    if (c) { lastTick = { p: c.p, at: c.at, used: c.used.map((x) => x.src.name), dropped: c.dropped.map((x) => x.src.name), disagree: c.disagree, streaming: c.streaming }; return { p: c.p, n: c.used.length, via: "live" }; }
    if (lastTick) return { p: lastTick.p, n: 0, via: "stale" };
    return { p: closes[closes.length - 1], n: 0, via: "close" };   // no tick yet: the model runs on the last daily close, the header says so
  }
  const hms = (ms) => new Date(ms).toISOString().slice(11, 19);
  const diagTxt = (d) => [d.ws ? "WebSocket " + d.ws : null, "REST " + d.rest].filter(Boolean).join(" / ");
  /* Live-status details, shown in the (i) next to the small status indicator in the chart header (the price itself is on the chart).
     Built fresh each time the note opens: one line per price source (price, status, WebSocket/REST state), blocks, connection check. */
  const STNAME = { live: "fresh", rest: "waiting", stale: "no price for > 15 s (not used)", down: "down", out: "> 0.5% from the others (left out)" };
  function liveInfo() {
    const now = Date.now(), out = new Set(lastTick && priceVia === "live" ? lastTick.dropped : []), L = [];
    L.push("Status of the live BTC/USD price shown on the chart (right-axis price tag, the dot and the hover note). The price is the middle (median) of several exchanges, using only sources with a price under 15 s old; one more than 0.5% away from the others is left out. \"live\" = streaming connection; \"polling every 10s\" = re-checked by ordinary web requests (e.g. when a network blocks WebSockets); STALE = no new price for 15 s; gray \"last close\" = no live source reachable, so the model runs on the last daily close.");
    L.push("");
    if (priceVia === "live") L.push(`Now: ${lastTick.streaming ? "live (streaming)" : `live (polling every ${Feeds.POLL_MS / 1000}s)`}, ${usd(lastTick.p, 0)} from ${lastTick.used.length} source${lastTick.used.length > 1 ? "s" : ""} (${lastTick.used.join(", ")}), last tick ${hms(lastTick.at)} UTC${lastTick.disagree ? ", sources disagree" : ""}.`);
    else if (priceVia === "stale") L.push(`Now: STALE, last price ${usd(lastTick.p, 0)} at ${hms(lastTick.at)} UTC (${ago(now - lastTick.at)}), reconnecting.`);
    else L.push(`Now: not live, showing the last daily close (${lastClose()}). ${notLiveWhy(now)}.`);
    L.push("");
    for (const x of allSrc.filter((x) => feeds.includes(x) || x.active || x.at)) { const st = out.has(x.src.name) ? "out" : x.status();
      L.push(`${x.src.name}: ${x.price ? usd(x.price, 0) : "--"} · ${STNAME[st] || st} · ${diagTxt(x.diag())}${x.at ? ` · last ${hms(x.at)} UTC via ${x.via === "ws" ? "WebSocket" : "REST"}` : ""}`); }
    L.push(`Blocks: ${blocks.height ? blocks.height.toLocaleString() : "--"} · ${diagTxt(blocks.diag())}${blocks.src ? " · from " + blocks.src : ""}`);
    // connection check (also useful when a work network blocks crypto sites)
    const parts = feeds.map((x) => { const d = x.diag(); return `${x.src.name}: WS ${d.ws}, REST ${d.rest}`; })
      .concat(pollers.filter((x) => x.active || x.restTries).map((x) => `${x.src.name}: REST ${x.diag().rest}`))
      .concat([`Blocks: WS ${blocks.diag().ws}, REST ${blocks.diag().rest}`]);
    L.push(""); L.push("Connection check: " + parts.join(" · "));
    return L.join("\n");
  }
  Explain.T.live = liveInfo;
  function notLiveWhy(now) { const tried = now - t0 > 12000, wsBlocked = feeds.every((x) => x.diag().ws === "blocked"), restBlocked = allSrc.every((x) => x.restErr && !x.at);
    return !tried ? "Trying exchange WebSockets, then HTTPS polling" : `${wsBlocked ? "WebSockets blocked" : "No WebSocket price"}${restBlocked ? ", HTTPS price APIs blocked too (network filter?)" : ", polling HTTPS"}`; }
  function renderStatus(now) {   // small indicator in the chart header: dot + live / live (polling every 10s) / STALE / last close (gray)
    const el = $("liveSt"); if (!el) return;
    let cls, txt, ttl;
    if (priceVia === "live") { cls = lastTick.streaming ? "stream" : "poll"; txt = lastTick.streaming ? "live" : `live (polling every ${Feeds.POLL_MS / 1000}s)`; ttl = `last tick ${hms(lastTick.at)} UTC`; }
    else if (priceVia === "stale") { cls = "stale"; txt = "STALE"; ttl = `last price ${ago(now - lastTick.at)}, reconnecting`; }
    else { cls = "close"; txt = now - t0 > 12000 ? "last close · not live" : "connecting..."; ttl = notLiveWhy(now); }
    el.className = "livest m-" + cls; $("liveTxt").textContent = txt; el.title = ttl;
  }
  function flash(el) { el.style.transition = "none"; el.style.color = "#22c55e"; requestAnimationFrame(() => { el.style.transition = "color 2s"; el.style.color = ""; }); }

  /* ---------- shared chart options (used by js/hero.js) ---------- */
  const priceFmt = { type: "custom", minMove: 0.01, formatter: (p) => p >= 1000 ? "$" + Math.round(p).toLocaleString("en-US") : "$" + p.toFixed(2) };
  const baseOpts = (el) => ({ autoSize: true, layout: { background: { type: "solid", color: "#131722" }, textColor: "#b2b5be", attributionLogo: false, panes: { separatorColor: "#2a2e39", enableResize: true } },
    grid: { vertLines: { color: "#1e222d" }, horzLines: { color: "#1e222d" } }, rightPriceScale: { borderColor: "#2a2e39" },
    timeScale: { borderColor: "#2a2e39", rightOffset: 6 }, crosshair: { mode: 0 } });
  const C = M.calibration;
  let calc = null;

  /* ---------- tiles ---------- */
  const TILE_ORDER = ["cycle_day", "mayer", "p200w", "trend_mult", "mvrv_z", "pi_ratio", "crowd", "activity", "levels"];
  $("tiles").innerHTML = TILE_ORDER.map((s) => `<div class="tile" id="t_${s}"></div>`).join("");
  const badge = (k) => `<span class="badge ${k}">${k.toUpperCase()}</span>`;
  let priceVia = "live";
  const lastClose = () => isoDay(cT[cT.length - 1]);
  function tile(id, { title, val, zone, zlabel, heat, desc, kind }) {
    const el = $("t_" + id); if (!el) return; const z = zone || "n/a";
    const upd = kind === "daily" || kind === "monthly" ? `<div class="upd">updated ${kind}, last: ${(desc.match(/\d{4}-\d{2}(-\d{2})?/) || [lastClose()])[0]}</div>`
      : priceVia === "close" ? `<div class="upd">no live price reachable · showing the last daily close (${lastClose()})</div>`
      : priceVia === "stale" && kind === "live" ? `<div class="upd">price STALE · last tick ${hms(lastTick.at)} UTC, reconnecting</div>` : "";
    if (kind === "live" && priceVia === "close") kind = "daily"; else if (kind === "live" && priceVia === "stale") kind = "stale";
    el.className = "tile z-" + (z === "n/a" ? "na" : z);
    el.innerHTML = `<div class="t"><span>${title} ${Explain.i(id)} ${badge(kind)}</span><span class="zn z-${z}">${zlabel || z}</span></div><div class="val">${val}</div>`
      + (heat != null ? `<div class="bar z-${z}" title="heat ${f(heat, 0)} / 100"><span style="width:${Math.max(1, Math.min(100, heat))}%"></span></div>` : "") + `<div class="d">${desc}</div>` + upd;
  }
  function tileFailed(id, title, e) {   // never leave a tile blank: say what it is and when its data last updated
    const el = $("t_" + id); if (!el) return; el.className = "tile z-na";
    el.innerHTML = `<div class="t"><span>${title} ${Explain.i(id)}</span><span class="zn">n/a</span></div><div class="val pending">not available right now</div><div class="upd">updated daily, last: ${M.last_daily}</div>`;
    window.__app.errors.push("tile " + id + ": " + (e && e.message)); }
  const TITLES = { cycle_day: "Cycle timing", mayer: "Price / 200-day avg", p200w: "Price / 200-week avg", trend_mult: "Price / long-term trend", mvrv_z: "Market value vs holder cost", pi_ratio: "Pi Cycle top ratio", crowd: "Crowd euphoria", activity: "Network activity", levels: "Trend line & realized price" };
  for (const id of Object.keys(TITLES)) { const el = $("t_" + id); if (el) { el.className = "tile z-na"; el.innerHTML = `<div class="t"><span>${TITLES[id]} ${Explain.i(id)}</span></div><div class="val pending">loading...</div>`; } }
  function renderTiles(c) {
    const H_ = c.heat, Z = c.zones, T = c.thr, hotP = (s, base) => T[s] ? ` (hot &asymp; ${usdK(T[s].hot * base)})` : "";
    const z = (s) => `heat ${f(H_[s], 0)}`;
    try { tile("cycle_day", { title: TITLES.cycle_day, kind: "live", val: `day ${c.cycleDay} <span class="sm">since the ${isoDay(c.lastHalving)} halving</span>`, zone: Z.cycle_day, heat: H_.cycle_day, desc: cycleTiming(c) }); } catch (e) { tileFailed("cycle_day", TITLES["cycle_day"], e); }
    try { tile("mayer", { title: TITLES.mayer, kind: "live", val: f(c.vals.mayer) + "x", zone: Z.mayer, heat: H_.mayer, desc: `${z("mayer")} &middot; warm &ge; ${f(T.mayer.warm)} &middot; hot &ge; ${f(T.mayer.hot)}${hotP("mayer", c.ma200)} &middot; 200-day avg ${usdK(c.ma200)}` }); } catch (e) { tileFailed("mayer", TITLES["mayer"], e); }
    try { tile("p200w", { title: TITLES.p200w, kind: "live", val: f(c.vals.p200w) + "x", zone: Z.p200w, heat: H_.p200w, desc: `${z("p200w")} &middot; warm &ge; ${f(T.p200w.warm)} &middot; hot &ge; ${f(T.p200w.hot)}${hotP("p200w", c.ma1400)} &middot; 200-week avg ${usdK(c.ma1400)}` }); } catch (e) { tileFailed("p200w", TITLES["p200w"], e); }
    try { tile("trend_mult", { title: TITLES.trend_mult, kind: "live", val: f(c.vals.trend_mult) + "x", zone: Z.trend_mult, heat: H_.trend_mult, desc: `${z("trend_mult")} &middot; warm &ge; ${f(T.trend_mult.warm)} &middot; hot &ge; ${f(T.trend_mult.hot)}${hotP("trend_mult", c.trendLine)} &middot; trend line ${usdK(c.trendLine)}` }); } catch (e) { tileFailed("trend_mult", TITLES["trend_mult"], e); }
    const std = (c.mcap - M.realized_cap) / c.vals.mvrv_z, zHotP = (T.mvrv_z.hot * std + M.realized_cap) / M.supply;
    try { tile("mvrv_z", { title: TITLES.mvrv_z, kind: "live", val: f(c.vals.mvrv_z), zone: Z.mvrv_z, heat: H_.mvrv_z, desc: `${z("mvrv_z")} &middot; warm &ge; ${f(T.mvrv_z.warm)} &middot; hot &ge; ${f(T.mvrv_z.hot)} (&asymp; ${usdK(zHotP)}) &middot; MVRV Z-score: market value live, holder cost (realized cap) daily, ${M.realized_cap_asof}` }); } catch (e) { tileFailed("mvrv_z", TITLES["mvrv_z"], e); }
    try { tile("pi_ratio", { title: TITLES.pi_ratio, kind: "live", val: f(c.vals.pi_ratio, 3), zone: Z.pi_ratio, heat: H_.pi_ratio, desc: `${z("pi_ratio")} &middot; warm &ge; ${f(T.pi_ratio.warm, 3)} &middot; hot &ge; ${f(T.pi_ratio.hot, 3)} &middot; 1.00 = the 111-day avg crossing 2&times; the 350-day avg` }); } catch (e) { tileFailed("pi_ratio", TITLES["pi_ratio"], e); }
    const ac = M.fixed.activity;
    try { if (!CR || CR.gauge == null) throw new Error("data/crowd.json not available");
      const czCls = { calm: "cool", normal: "neutral", excited: "warm", euphoric: "hot" }[CR.zone] || "n/a", fu = CR.funding || {}, fg = CR.fng || {};
      tile("crowd", { title: TITLES.crowd, kind: "daily", val: `${f(CR.gauge, 0)} <span class="sm">/ 100 &middot; ${CR.zone}</span>`, zone: czCls, zlabel: CR.zone, heat: CR.gauge,
        desc: `Fear &amp; Greed ${fg.value != null ? f(fg.value, 0) : "--"} (7-day avg ${fg.avg7 != null ? f(fg.avg7, 0) : "--"}) &middot; BTC perpetual funding ${fu.ann7 != null ? f(fu.ann7, 1) + "%" : "--"} a year (7-day avg; 30-day ${fu.ann30 != null ? f(fu.ann30, 1) + "%" : "--"}), as of ${CR.asof}${crowdSpark()}<span class="note">display only, a contrarian crowd gauge: not in the Cycle Heat Score or any graded version. Zones calm / normal / excited / euphoric at 25 / 55 / 75, not calibrated.</span>` }); } catch (e) { tileFailed("crowd", TITLES["crowd"], e); }
    try { tile("activity", { title: TITLES.activity, kind: "daily", val: f(ac.value) + "x", zone: Z.activity, heat: H_.activity, desc: `heat ${f(ac.heat, 0)} &middot; active addresses, 30-day vs 1-year average, as of ${ac.asof}; on-chain data published once a day` }); } catch (e) { tileFailed("activity", TITLES["activity"], e); }
    try { tile("levels", { title: TITLES.levels, kind: "live", val: `${usdK(c.trendLine)} / ${usdK(c.realizedPrice)}`, zone: "n/a", heat: null, desc: `trend line (refit including today) / realized price, the average cost of all coins (daily, ${M.realized_cap_asof}). BTC is ${f(100 * (c.live / c.trendLine - 1), 1)}% vs trend` }); } catch (e) { tileFailed("levels", TITLES["levels"], e); }
  }

  /* Crowd euphoria gauge, last 3 years, with the 75 (euphoric) line */
  let crowdSVG = null;
  function crowdSpark() {
    if (crowdSVG != null) return crowdSVG;
    const g = CR.gauge_daily || [], n = g.length, from = Math.max(0, n - 3 * 365), w = 220, h = 34, pts = [], t0 = BM.tsOf(CR.t0);
    for (let i = from; i < n; i++) if (g[i] != null) pts.push(`${((i - from) / (n - 1 - from) * w).toFixed(1)},${(h - 2 - g[i] / 100 * (h - 4)).toFixed(1)}`);
    if (pts.length < 2) return (crowdSVG = "");
    const y75 = (h - 2 - 0.75 * (h - 4)).toFixed(1), yr = new Date((t0 + from * DAY) * 1000).getUTCFullYear();
    return (crowdSVG = `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-label="Crowd euphoria gauge, last 3 years"><line x1="0" x2="${w}" y1="${y75}" y2="${y75}" stroke="#ef5350" stroke-width="1" stroke-dasharray="3 3" vector-effect="non-scaling-stroke" opacity=".6"/><polyline fill="none" stroke="currentColor" stroke-width="1.4" vector-effect="non-scaling-stroke" points="${pts.join(" ")}"/></svg><span class="sparkax"><span>${yr}</span><span>dashed = 75</span><span>${CR.asof.slice(0, 7)}</span></span>`);
  }

  /* Cycle timing: everything from the live block height */
  function cycleTiming(c) {
    const lo = Math.min(...C.top_days), hi = Math.max(...C.top_days), now = Date.now(), day = (ms) => new Date(ms).toISOString().slice(0, 10);
    const tops = Object.values(M.tops), lastTop = tops[tops.length - 1], topDay = Math.round((BM.tsOf(lastTop) - c.lastHalving) / DAY);
    let s = `heat ${f(c.heat.cycle_day, 0)} &middot; past peaks came on day ${lo}-${hi} after a halving`;
    if (blocks.height) {
      const left = M.next_halving_block - blocks.height, eta = now + left * 600000, w0 = eta + lo * DAY * 1000, w1 = eta + hi * DAY * 1000, dd = (ms) => Math.ceil((ms - now) / 864e5);
      s += `<div class="kvs"><div><span>Next halving (block ${M.next_halving_block.toLocaleString()})</span><b>~${day(eta)} &middot; in ${dd(eta)} days</b></div>`
        + `<div><span>From live block ${blocks.height.toLocaleString()}</span><b>${left.toLocaleString()} blocks at 10 min</b></div>`
        + `<div><span>Historical top window (halving +${lo} to +${hi} d)</span><b>${day(w0)} &ndash; ${day(w1)}</b></div>`
        + `<div><span>Window opens in</span><b>${dd(w0).toLocaleString()} days (closes in ${dd(w1).toLocaleString()})</b></div>`
        + `<div><span>This cycle</span><b>top ${lastTop} on day ${topDay}, ${topDay >= lo && topDay <= hi ? "inside" : "outside"} the ${lo}-${hi} window</b></div></div>`;
    } else s += `<div class="kvs"><div><span>Next halving / top window</span><b>waiting for the live block height</b></div></div>`;
    return s + `<span class="note">Historical window from past 4 cycles, not a prediction. The halving date moves with the real block rate; 10 min/block is the protocol target.</span>`;
  }

  /* ---------- hero charts (js/hero.js) ---------- */
  const hero = window.Hero.init({ LC, BM, M, H, FAN2, HEALTH, BG, FWD, cT, closes, baseOpts, priceFmt, $, usd, usdK, f, ZC, C });

  /* ---------- freshness table ---------- */
  function renderFresh(n) {
    const rows = [["BTC price", priceVia === "live" ? `${badge("live")} ${lastTick.streaming ? "streaming (WebSocket)" : "polling HTTPS every 10 s"}: median of ${lastTick.used.length} source${lastTick.used.length > 1 ? "s" : ""} with a price < 15 s old (${lastTick.used.join(", ")})${lastTick.dropped.length ? `; ${lastTick.dropped.join(", ")} left out (> 0.5% from the others)` : ""}; last tick ${hms(lastTick.at)} UTC`
        : priceVia === "stale" ? `${badge("stale")} no price from any source in the last 15 s; showing the last one (${hms(lastTick.at)} UTC), retrying` : `${badge("daily")} no live source reachable yet; the model runs on the last daily close (${lastClose()})`],
      ["Blocks / halving countdown", `${badge(blocks.status() === "down" ? "daily" : "live")} ${blocks.src || "mempool.space"} ${blocks.status() === "live" ? "WebSocket" : "REST"}; last block ${blocks.blockTime ? ago(Date.now() - blocks.blockTime * 1000) : "--"}`],
      ["Mayer, 200W MA, trend, Pi Cycle", `${badge("live")} live price as today's close + daily closes to ${isoDay(cT[cT.length - 1])}${gapFilled ? ` (${gapFilled} recent days from Coinbase candles)` : ""}`],
      ["MVRV Z", `${badge("live")} market cap live; ${badge("daily")} realized cap ${M.realized_cap_asof}`],
      ["Address activity", `${badge("daily")} as of ${M.fixed.activity.asof} (on-chain, published daily)`],
      ["Crowd euphoria (display only)", CR ? `${badge("daily")} as of ${CR.asof} (Fear &amp; Greed ${CR.fng && CR.fng.asof}, alternative.me; funding ${CR.funding && CR.funding.asof}, Deribit with OKX backup)` : `${badge("daily")} not available`],
      ["Google search interest (score input)", `${badge("monthly")} ${(M.fixed.trends.month || "").slice(0, 7)} (Google Trends monthly)`],
      ["Score calibration", `past tops ${C.prior_tops.join(", ")}`]];
    $("fresh").innerHTML = rows.map(([k, v]) => `<div><span>${k}</span><span>${v}</span></div>`).join("");
  }

  /* ---------- main tick ---------- */
  let lastFresh = 0;
  function tick(force) {
    const now = Date.now(); setPolling(); const { p, n, via } = indexPrice(); priceVia = n ? "live" : via; try { renderStatus(now); } catch (e) {}
    if (!p) return;
    const sect = (name, fn) => { try { return fn(); } catch (e) { const k = name + ": " + e.message; if (!window.__app.errors.includes(k)) { window.__app.errors.push(k); console.error(name, e); } } };
    // UTC day rolled over while the page was open: yesterday's last index becomes a provisional daily close
    const today = BM.utcDay(now);
    if (today - DAY > cT[cT.length - 1]) { cT.push(today - DAY); closes.push(prevShown || p); todayOpen = p; }
    calc = BM.compute(M, closes, p, now); window.__app.ticks++; window.__app.last = { price: p, sources: n, via: priceVia, score: calc.score, t: now, tickAt: lastTick && lastTick.at, used: lastTick && lastTick.used, dropped: lastTick && lastTick.dropped };
    if (priceVia === "live") prevShown = p;
    sect("score", () => {
    $("score").textContent = f(calc.score, 1); $("score").className = "score z-" + calc.scoreZone;
    { const rz = document.getElementById("r30zone");   // 30-second read under the chart title: today's zone and score
      if (rz && isFinite(calc.score)) { const txt = `${String(calc.scoreZone).toUpperCase()} (Heat ${Math.round(calc.score)})`;
        if (rz.textContent !== txt) { rz.textContent = txt; rz.className = "z-" + calc.scoreZone; } document.getElementById("r30now").hidden = false; } }
    $("scoreZone").textContent = calc.scoreZone; $("scoreZone").className = "zone z-" + calc.scoreZone;
    $("meterFill").style.left = `calc(${Math.max(0, Math.min(100, calc.score))}% - 1px)`; $("markWarm").style.left = C.score_warm + "%"; $("markHot").style.left = C.score_hot + "%";
    $("scoreNote").textContent = `cool < 40 · warm ≥ ${C.score_warm} · hot ≥ ${C.score_hot} · average of 8 signals, updated every second`;
    $("nHot").textContent = `${calc.nHot} / ${calc.nSignals}`; $("cycDay").textContent = `${calc.cycleDay} (peaks: ${Math.min(...C.top_days)}-${Math.max(...C.top_days)})`;
    if (blocks.height) { const left = M.next_halving_block - blocks.height, eta = new Date(now + left * 600000); $("height").textContent = blocks.height.toLocaleString() + (blocks.blockTime ? ` · ${ago(now - blocks.blockTime * 1000)}` : "");
      $("halving").textContent = `${left.toLocaleString()} blocks · ~${eta.toISOString().slice(0, 10)}`; }
    const ath = Math.max(...closes, p), dd = p / ath - 1; $("dd").textContent = `${(dd * 100).toFixed(1)}% (peak ${usd(ath, 0)})`;
    });
    sect("tiles", () => renderTiles(calc));
    sect("hero", () => { const v2 = BM.computeV2(M, calc); window.__app.last.v2 = v2.score; hero.update(p, now, calc, v2, priceVia); });
    if (force || now - lastFresh > 5000) { sect("freshness", renderFresh); lastFresh = now; }
    document.title = `${priceVia === "close" ? "last close " + usd(p, 0) : usd(p, 0) + (priceVia === "stale" ? " (stale)" : "")} · score ${f(calc.score, 0)} · My BTC Cycle Model`;
  }
  tick(true);
  setInterval(() => { try { tick(); } catch (e) { window.__app.errors.push("tick: " + e.message); } }, 1000);
})().catch((e) => { (window.__app = window.__app || { errors: [] }).errors.push("init: " + e.message); const p = document.getElementById("liveTxt"); if (p) p.textContent = "data failed to load"; console.error(e); });
