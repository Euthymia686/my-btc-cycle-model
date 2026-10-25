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
  const load = (n) => fetch("data/" + n + ".json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(n + " " + r.status); return r.json(); });

  const [M, H, O, FAN2, HEALTH, MS, META] = await Promise.all(["model", "history", "ohlc_daily", "fan2", "health", "mstr", "meta"].map(load));
  const BG = await load("hero_bg").catch(() => null);
  $("built").textContent = `Daily data files built ${META.built_utc.replace("T", " ").slice(0, 16)} UTC (on-chain as of ${M.last_daily}). Live prices and blocks stream directly from the exchanges and mempool.space into your browser.`;

  /* ---------- live feeds (start connecting right away, in parallel with the optional gap-fill below) ---------- */
  let lastIdx = null, prevShown = null;
  const feeds = Feeds.SOURCES.map((s) => new Feeds.Feed(s, () => {}));
  const blocks = new Feeds.Blocks((b, isNew) => { if (isNew) flash($("height")); });

  /* ---------- daily history: CoinMetrics closes, gap-filled from Coinbase daily candles if the files are a few days old ---------- */
  const closes = H.close.slice(), cT = H.t.slice();
  const bars = new Map(O.bars.map((b) => [b[0], { time: b[0], open: b[1], high: b[2], low: b[3], close: b[4] }]));
  let todayOpen = null, gapFilled = 0;
  try {
    const cb = await Promise.race([Feeds.getJSON("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400"),
      new Promise((_, rej) => setTimeout(() => rej(new Error("timeout (3.5 s), page continues with the daily files")), 3500))]);
    const today0 = BM.utcDay(Date.now());
    cb.sort((a, b) => a[0] - b[0]).forEach(([t, lo, hi, op, cl]) => {
      if (t === today0) todayOpen = op; else bars.set(t, { time: t, open: op, high: hi, low: lo, close: cl });
      if (t > cT[cT.length - 1] && t < today0) { cT.push(t); closes.push(cl); gapFilled++; }
    });
  } catch (e) { window.__app.errors.push("coinbase daily candles: " + e.message); }
  const dailyBars = [...bars.values()].filter((b) => b.time < BM.utcDay(Date.now())).sort((a, b) => a.time - b.time);

  let geckoAt = 0;
  function indexPrice() {
    const live = feeds.filter((x) => x.fresh()).map((x) => x.price);
    if (live.length) { lastIdx = BM.median(live); return { p: lastIdx, n: live.length }; }
    if (Date.now() - geckoAt > 30000) { geckoAt = Date.now(); Feeds.getJSON("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd").then((r) => { if (!feeds.some((x) => x.fresh())) lastIdx = r.bitcoin.usd; }).catch(() => {}); }
    if (lastIdx) return { p: lastIdx, n: 0, via: "coingecko" };
    return { p: closes[closes.length - 1], n: 0, via: "close" };   // no live source yet: show the model on the last daily close
  }
  function renderFeeds() {
    $("feeds").innerHTML = feeds.map((x) => `<span class="feed" title="${x.src.name}: ${x.via === "rest" ? "REST fallback" : "WebSocket"}, ${x.at ? "updated " + ago(Date.now() - x.at) : "waiting"}"><span class="dot ${x.status()}"></span>${x.src.name} <b>${x.price ? usd(x.price, 0) : "--"}</b></span>`).join("")
      + `<span class="feed" title="mempool.space blocks"><span class="dot ${blocks.status()}"></span>Blocks <b>${blocks.height ? blocks.height.toLocaleString() : "--"}</b></span>`;
  }
  function flash(el) { el.style.transition = "none"; el.style.color = "#22c55e"; requestAnimationFrame(() => { el.style.transition = "color 2s"; el.style.color = ""; }); }

  /* ---------- main chart (price pane + score pane) ---------- */
  const priceFmt = { type: "custom", minMove: 0.01, formatter: (p) => p >= 1000 ? "$" + Math.round(p).toLocaleString("en-US") : "$" + p.toFixed(2) };
  const baseOpts = (el) => ({ autoSize: true, layout: { background: { type: "solid", color: "#131722" }, textColor: "#b2b5be", attributionLogo: false, panes: { separatorColor: "#2a2e39", enableResize: true } },
    grid: { vertLines: { color: "#1e222d" }, horzLines: { color: "#1e222d" } }, rightPriceScale: { borderColor: "#2a2e39" },
    timeScale: { borderColor: "#2a2e39", rightOffset: 6 }, crosshair: { mode: 0 } });
  const chart = LC.createChart($("chart"), baseOpts());
  const candle = chart.addSeries(LC.CandlestickSeries, { upColor: "#26a69a", downColor: "#ef5350", borderVisible: false, wickUpColor: "#26a69a", wickDownColor: "#ef5350", priceFormat: priceFmt }, 0);
  candle.priceScale().applyOptions({ mode: LC.PriceScaleMode.Logarithmic, scaleMargins: { top: 0.06, bottom: 0.06 } });
  const L = (color, w = 1, style = 0, pane = 0, extra = {}) => chart.addSeries(LC.LineSeries, { color, lineWidth: w, lineStyle: style, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, priceFormat: priceFmt, ...extra }, pane);
  const OV = { ma200: L("#f59e0b", 1), ma1400: L("#22d3ee", 2), trend: L("#a78bfa", 1, 2), floor: L("#34d399", 1, 1), ceil: L("#f472b6", 1, 1) };
  const scoreS = chart.addSeries(LC.LineSeries, { color: "#e5e7eb", lineWidth: 2, priceFormat: { type: "price", precision: 1, minMove: 0.1 }, lastValueVisible: true, priceLineVisible: false }, 1);
  const scoreWf = chart.addSeries(LC.LineSeries, { color: "#6b7280", lineWidth: 1, lineStyle: 2, priceFormat: { type: "price", precision: 1, minMove: 0.1 }, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false }, 1);
  const C = M.calibration;
  scoreS.createPriceLine({ price: C.score_hot, color: ZC.hot, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "hot" });
  scoreS.createPriceLine({ price: C.score_warm, color: ZC.warm, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "warm" });
  scoreS.createPriceLine({ price: 40, color: ZC.cool, lineWidth: 1, lineStyle: 3, axisLabelVisible: false, title: "" });
  try { chart.panes()[1].setHeight(150); } catch (e) {}
  const markers = LC.createSeriesMarkers(candle, []);

  // daily overlay arrays from closes (time-aligned with cT)
  const tf = M.trend_full_fit, g0 = BM.tsOf(M.genesis);
  const fullTrend = (t, q) => Math.pow(10, tf.a + tf.b * Math.log10((t - g0) / DAY) + q);
  function rolling(arr, n) { const out = new Array(arr.length).fill(null); let s = 0; for (let i = 0; i < arr.length; i++) { s += arr[i]; if (i >= n) s -= arr[i - n]; if (i >= n - 1) out[i] = s / n; } return out; }
  const r200 = rolling(closes, 200), r1400 = rolling(closes, 1400);
  const tIndex = new Map(cT.map((t, i) => [t, i]));
  const scoreByT = new Map(H.t.map((t, i) => [t, H.score[i]])), wfByT = new Map(H.t.map((t, i) => [t, H.score_wf[i]]));
  const firstBar = dailyBars[0].time;

  let mode = "1D", liveBar = null, minuteBars = [], minuteScore = [], calc = null;
  const weekStart = (t) => { const d = new Date(t * 1000).getUTCDay(); return t - ((d + 6) % 7) * DAY; };
  function series(kind) {   // build data for the current mode
    if (kind === "bars") {
      if (mode === "1D") return dailyBars;
      const w = new Map(); for (const b of dailyBars) { const k = weekStart(b.time), x = w.get(k);
        if (!x) w.set(k, { time: k, open: b.open, high: b.high, low: b.low, close: b.close }); else { x.high = Math.max(x.high, b.high); x.low = Math.min(x.low, b.low); x.close = b.close; } }
      return [...w.values()];
    }
  }
  function overlayData(get) {   // daily or weekly(last value of week) overlay points
    const pts = []; for (let i = 0; i < cT.length; i++) { const t = cT[i]; if (t < firstBar) continue; const v = get(i, t); if (v == null || !isFinite(v)) continue;
      if (mode === "1W") { const k = weekStart(t); if (pts.length && pts[pts.length - 1].time === k) pts[pts.length - 1].value = v; else pts.push({ time: k, value: v }); } else pts.push({ time: t, value: v }); }
    return pts;
  }
  const ovVisible = () => Object.fromEntries([...document.querySelectorAll("#ov input")].map((i) => [i.dataset.ov, i.checked]));
  function applyOverlays() {
    const v = ovVisible(), on = mode !== "1m";
    OV.ma200.applyOptions({ visible: on && v.ma200 }); OV.ma1400.applyOptions({ visible: on && v.ma1400 }); OV.trend.applyOptions({ visible: on && v.trend });
    OV.floor.applyOptions({ visible: on && v.band }); OV.ceil.applyOptions({ visible: on && v.band });
    const mk = [];
    if (on && v.marks) {
      for (const [k, d] of Object.entries(M.tops)) { const t = BM.tsOf(d); if (t >= firstBar) mk.push({ time: mode === "1W" ? weekStart(t) : t, position: "aboveBar", color: ZC.hot, shape: "arrowDown", text: "top " + d.slice(0, 7) }); }
      for (const [k, d] of Object.entries(M.bottoms)) { const t = BM.tsOf(d); if (t >= firstBar) mk.push({ time: mode === "1W" ? weekStart(t) : t, position: "belowBar", color: ZC.cool, shape: "arrowUp", text: "low " + d.slice(0, 7) }); }
    }
    markers.setMarkers(mk.sort((a, b) => a.time - b.time));
  }
  async function setMode(m) {
    mode = m; document.querySelectorAll("#tf button").forEach((b) => b.classList.toggle("on", b.dataset.tf === m));
    liveBar = null;
    if (m === "1m") {
      try { const cb = await Feeds.getJSON("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60");
        minuteBars = cb.sort((a, b) => a[0] - b[0]).map(([t, lo, hi, op, cl]) => ({ time: t, open: op, high: hi, low: lo, close: cl })); } catch (e) { minuteBars = []; }
      candle.setData(minuteBars); for (const s of Object.values(OV)) s.setData([]);
      scoreS.setData(minuteScore.slice()); scoreWf.setData([]);
      candle.priceScale().applyOptions({ mode: LC.PriceScaleMode.Normal }); $("logBtn").classList.remove("on");
      chart.timeScale().applyOptions({ timeVisible: true, secondsVisible: false });
    } else {
      candle.setData(series("bars"));
      OV.ma200.setData(overlayData((i) => r200[i])); OV.ma1400.setData(overlayData((i) => r1400[i]));
      OV.trend.setData(overlayData((i, t) => fullTrend(t, tf.q_mid))); OV.floor.setData(overlayData((i, t) => fullTrend(t, tf.q_floor))); OV.ceil.setData(overlayData((i, t) => fullTrend(t, tf.q_ceil)));
      scoreS.setData(overlayData((i, t) => scoreByT.get(t))); scoreWf.setData(overlayData((i, t) => wfByT.get(t)));
      chart.timeScale().applyOptions({ timeVisible: false });
    }
    applyOverlays(); tick(true);
    const n = mode === "1D" ? dailyBars.length : mode === "1W" ? Math.ceil(dailyBars.length / 7) : minuteBars.length;
    const span = mode === "1D" ? 800 : mode === "1W" ? 420 : 180;
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - span), to: n + 5 });
  }
  document.querySelectorAll("#tf button").forEach((b) => b.onclick = () => setMode(b.dataset.tf));
  document.querySelectorAll("#ov input").forEach((i) => i.onchange = applyOverlays);
  $("logBtn").onclick = () => { const on = !$("logBtn").classList.contains("on"); $("logBtn").classList.toggle("on", on); candle.priceScale().applyOptions({ mode: on ? LC.PriceScaleMode.Logarithmic : LC.PriceScaleMode.Normal }); };
  $("fitBtn").onclick = () => chart.timeScale().fitContent();
  $("legend").innerHTML = [["#f59e0b", "200-day MA"], ["#22d3ee", "200-week MA"], ["#a78bfa", "Trend line (my power-law fit)"], ["#34d399", "Trend floor (5%)"], ["#f472b6", "Trend ceiling (95%)"], ["#e5e7eb", "Cycle Heat Score (today's calibration)"], ["#6b7280", "Score, walk-forward backtest"]]
    .map(([c, t]) => `<span><i style="background:${c}"></i>${t}</span>`).join("") + `<span id="lgLive"></span>`;

  function updateChart(p, now) {
    const today = BM.utcDay(now);
    if (mode === "1m") {
      const m = Math.floor(now / 60000) * 60, last = minuteBars[minuteBars.length - 1];
      if (last && last.time === m) { last.high = Math.max(last.high, p); last.low = Math.min(last.low, p); last.close = p; }
      else if (!last || m > last.time) minuteBars.push({ time: m, open: last ? last.close : p, high: p, low: p, close: p });
      candle.update({ ...minuteBars[minuteBars.length - 1] });
      if (calc && isFinite(calc.score)) { const ms = minuteScore[minuteScore.length - 1]; if (ms && ms.time === m) ms.value = calc.score; else minuteScore.push({ time: m, value: calc.score }); scoreS.update({ ...minuteScore[minuteScore.length - 1] }); }
      return;
    }
    const t = mode === "1W" ? weekStart(today) : today;
    if (!liveBar || liveBar.time !== t) {
      let open = todayOpen ?? p;
      if (mode === "1W") { const wk = dailyBars.filter((b) => b.time >= t); if (wk.length) open = wk[0].open; liveBar = { time: t, open, high: Math.max(p, ...wk.map((b) => b.high)), low: Math.min(p, ...wk.map((b) => b.low)), close: p }; }
      else liveBar = { time: t, open, high: Math.max(open, p), low: Math.min(open, p), close: p };
    }
    liveBar.high = Math.max(liveBar.high, p); liveBar.low = Math.min(liveBar.low, p); liveBar.close = p;
    candle.update({ ...liveBar });
    if (calc) {
      OV.ma200.update({ time: t, value: calc.ma200 }); OV.ma1400.update({ time: t, value: calc.ma1400 });
      OV.trend.update({ time: t, value: fullTrend(today, tf.q_mid) }); OV.floor.update({ time: t, value: fullTrend(today, tf.q_floor) }); OV.ceil.update({ time: t, value: fullTrend(today, tf.q_ceil) });
      if (isFinite(calc.score)) scoreS.update({ time: t, value: calc.score });
    }
  }

  /* ---------- tiles ---------- */
  const TILE_ORDER = ["cycle_day", "mayer", "p200w", "trend_mult", "mvrv_z", "pi_ratio", "trends", "activity"];
  $("tiles").innerHTML = TILE_ORDER.map((s) => `<div class="tile" id="t_${s}"></div>`).join("") + ["mnav", "levels"].map((s) => `<div class="tile" id="t_${s}"></div>`).join("");
  const badge = (k) => `<span class="badge ${k}">${k.toUpperCase()}</span>`;
  let priceVia = "live";
  const lastClose = () => isoDay(cT[cT.length - 1]);
  function tile(id, { title, val, zone, heat, desc, kind }) {
    const el = $("t_" + id); if (!el) return; const z = zone || "n/a";
    const upd = kind === "daily" || kind === "monthly" ? `<div class="upd">updated ${kind}, last: ${(desc.match(/\d{4}-\d{2}(-\d{2})?/) || [lastClose()])[0]}</div>`
      : priceVia === "close" ? `<div class="upd">live feed connecting · showing the last daily close (${lastClose()})</div>` : "";
    if (kind === "live" && priceVia === "close") kind = "daily";
    el.className = "tile z-" + (z === "n/a" ? "na" : z);
    el.innerHTML = `<div class="t"><span>${title} ${badge(kind)}</span><span class="zn z-${z}">${z}</span></div><div class="val">${val}</div>`
      + (heat != null ? `<div class="bar z-${z}" title="heat ${f(heat, 0)} / 100"><span style="width:${Math.max(1, Math.min(100, heat))}%"></span></div>` : "") + `<div class="d">${desc}</div>` + upd;
  }
  function tileFailed(id, title, e) {   // never leave a tile blank: say what it is and when its data last updated
    const el = $("t_" + id); if (!el) return; el.className = "tile z-na";
    el.innerHTML = `<div class="t"><span>${title}</span><span class="zn">n/a</span></div><div class="val pending">not available right now</div><div class="upd">updated daily, last: ${M.last_daily}</div>`;
    window.__app.errors.push("tile " + id + ": " + (e && e.message)); }
  const TITLES = { cycle_day: "Cycle timing", mayer: "Mayer Multiple", p200w: "Price / 200W MA", trend_mult: "Price / my trend line", mvrv_z: "MVRV Z", pi_ratio: "Pi Cycle ratio", trends: "Search interest", activity: "Address activity", mnav: "MSTR mNAV", levels: "Trend & realized price" };
  for (const id of Object.keys(TITLES)) { const el = $("t_" + id); if (el) { el.className = "tile z-na"; el.innerHTML = `<div class="t"><span>${TITLES[id]}</span></div><div class="val pending">loading...</div>`; } }
  const mnavZone = (m) => m < 1 ? "cool" : m < 1.5 ? "neutral" : m < 2.5 ? "warm" : "hot";
  function renderTiles(c) {
    const H_ = c.heat, Z = c.zones, T = c.thr, hotP = (s, base) => T[s] ? ` (hot &asymp; ${usdK(T[s].hot * base)})` : "";
    const z = (s) => `heat ${f(H_[s], 0)}`;
    try { tile("cycle_day", { title: "Cycle timing", kind: "live", val: `day ${c.cycleDay}`, zone: Z.cycle_day, heat: H_.cycle_day, desc: `${z("cycle_day")} &middot; since ${isoDay(c.lastHalving)} halving; past peaks came on day ${Math.min(...C.top_days)}-${Math.max(...C.top_days)}` }); } catch (e) { tileFailed("cycle_day", TITLES["cycle_day"], e); }
    try { tile("mayer", { title: "Mayer Multiple", kind: "live", val: f(c.vals.mayer) + "x", zone: Z.mayer, heat: H_.mayer, desc: `${z("mayer")} &middot; warm &ge; ${f(T.mayer.warm)} &middot; hot &ge; ${f(T.mayer.hot)}${hotP("mayer", c.ma200)} &middot; 200D MA ${usdK(c.ma200)}` }); } catch (e) { tileFailed("mayer", TITLES["mayer"], e); }
    try { tile("p200w", { title: "Price / 200W MA", kind: "live", val: f(c.vals.p200w) + "x", zone: Z.p200w, heat: H_.p200w, desc: `${z("p200w")} &middot; warm &ge; ${f(T.p200w.warm)} &middot; hot &ge; ${f(T.p200w.hot)}${hotP("p200w", c.ma1400)} &middot; 200W MA ${usdK(c.ma1400)}` }); } catch (e) { tileFailed("p200w", TITLES["p200w"], e); }
    try { tile("trend_mult", { title: "Price / my trend line", kind: "live", val: f(c.vals.trend_mult) + "x", zone: Z.trend_mult, heat: H_.trend_mult, desc: `${z("trend_mult")} &middot; warm &ge; ${f(T.trend_mult.warm)} &middot; hot &ge; ${f(T.trend_mult.hot)}${hotP("trend_mult", c.trendLine)} &middot; trend ${usdK(c.trendLine)}` }); } catch (e) { tileFailed("trend_mult", TITLES["trend_mult"], e); }
    const std = (c.mcap - M.realized_cap) / c.vals.mvrv_z, zHotP = (T.mvrv_z.hot * std + M.realized_cap) / M.supply;
    try { tile("mvrv_z", { title: "MVRV Z", kind: "live", val: f(c.vals.mvrv_z), zone: Z.mvrv_z, heat: H_.mvrv_z, desc: `${z("mvrv_z")} &middot; warm &ge; ${f(T.mvrv_z.warm)} &middot; hot &ge; ${f(T.mvrv_z.hot)} (&asymp; ${usdK(zHotP)}) &middot; live market cap, realized cap daily (${M.realized_cap_asof})` }); } catch (e) { tileFailed("mvrv_z", TITLES["mvrv_z"], e); }
    try { tile("pi_ratio", { title: "Pi Cycle ratio", kind: "live", val: f(c.vals.pi_ratio, 3), zone: Z.pi_ratio, heat: H_.pi_ratio, desc: `${z("pi_ratio")} &middot; warm &ge; ${f(T.pi_ratio.warm, 3)} &middot; hot &ge; ${f(T.pi_ratio.hot, 3)} &middot; 1.00 = the 111DMA crossing 2&times;350DMA` }); } catch (e) { tileFailed("pi_ratio", TITLES["pi_ratio"], e); }
    const tr = M.fixed.trends, ac = M.fixed.activity;
    try { tile("trends", { title: "Search interest", kind: "monthly", val: `${f(tr.value, 0)}/100`, zone: Z.trends, heat: H_.trends, desc: `heat ${f(tr.heat, 0)} &middot; Google Trends, month of ${(tr.month || "").slice(0, 7)}; only changes when the next month is published` }); } catch (e) { tileFailed("trends", TITLES["trends"], e); }
    try { tile("activity", { title: "Address activity", kind: "daily", val: f(ac.value) + "x", zone: Z.activity, heat: H_.activity, desc: `heat ${f(ac.heat, 0)} &middot; 30d / 365d active addresses, as of ${ac.asof}; on-chain data published once a day` }); } catch (e) { tileFailed("activity", TITLES["activity"], e); }
    let mnav = null; try { mnav = MS.price * MS.shares / (MS.btc_holdings * c.live); } catch (e) {}
    try { tile("mnav", { title: "MSTR mNAV", kind: "live", val: f(mnav) + "x", zone: mnavZone(mnav), heat: null, desc: `MSTR ${usd(MS.price, 2)} (last close ${String(MS.price_time).slice(0, 10)}) &times; ${(MS.shares / 1e6).toFixed(1)}M shares / (${MS.btc_holdings.toLocaleString()} BTC &times; live BTC). Zones are judgement bands, not backtested` }); } catch (e) { tileFailed("mnav", TITLES["mnav"], e); }
    try { tile("levels", { title: "Trend & realized price", kind: "live", val: `${usdK(c.trendLine)} / ${usdK(c.realizedPrice)}`, zone: "n/a", heat: null, desc: `my trend line (refit including today) / realized price (daily, ${M.realized_cap_asof}). BTC is ${f(100 * (c.live / c.trendLine - 1), 1)}% vs trend` }); } catch (e) { tileFailed("levels", TITLES["levels"], e); }
    return mnav;
  }

  /* ---------- hero charts (js/hero.js) ---------- */
  const hero = window.Hero.init({ LC, BM, M, H, MS, FAN2, HEALTH, BG, cT, closes, baseOpts, priceFmt, $, usd, usdK, f, ZC, C });

  /* ---------- freshness table ---------- */
  function renderFresh(n) {
    const live = feeds.filter((x) => x.fresh()).length;
    const rows = [["Own index price", live ? `${badge("live")} ${live}/3 exchanges, recomputed every second` : `${badge("daily")} live feeds connecting; showing ${priceVia === "coingecko" ? "CoinGecko REST price" : "the last daily close (" + lastClose() + ")"}`],
      ["Blocks / halving countdown", `${badge(blocks.status() === "down" ? "daily" : "live")} mempool.space ${blocks.status() === "live" ? "WebSocket" : "REST"}; last block ${blocks.blockTime ? ago(Date.now() - blocks.blockTime * 1000) : "--"}`],
      ["Mayer, 200W MA, trend, Pi Cycle", `${badge("live")} live price as today's close + daily closes to ${isoDay(cT[cT.length - 1])}${gapFilled ? ` (${gapFilled} recent days from Coinbase candles)` : ""}`],
      ["MVRV Z", `${badge("live")} market cap live; ${badge("daily")} realized cap ${M.realized_cap_asof}`],
      ["Address activity", `${badge("daily")} as of ${M.fixed.activity.asof} (on-chain, published daily)`],
      ["Search interest", `${badge("monthly")} ${(M.fixed.trends.month || "").slice(0, 7)} (Google Trends monthly)`],
      ["MSTR price (for mNAV)", `${badge("daily")} last close ${String(MS.price_time).slice(0, 16)}; no free real-time stock feed in the browser`],
      ["BTC holdings / shares", `${badge("daily")} latest 8-K ${(MS.edgar_latest_8k || {}).date || "--"}`],
      ["Score calibration", `past tops ${C.prior_tops.join(", ")}`]];
    $("fresh").innerHTML = rows.map(([k, v]) => `<div><span>${k}</span><span>${v}</span></div>`).join("");
  }

  /* ---------- main tick ---------- */
  let lastFresh = 0;
  function tick(force) {
    const now = Date.now(), { p, n, via } = indexPrice(); priceVia = n ? "live" : via; try { renderFeeds(); } catch (e) {}
    if (!p) { $("px").textContent = "connecting..."; return; }
    const sect = (name, fn) => { try { return fn(); } catch (e) { const k = name + ": " + e.message; if (!window.__app.errors.includes(k)) { window.__app.errors.push(k); console.error(name, e); } } };
    // UTC day rolled over while the page was open: yesterday's last index becomes a provisional daily close
    const today = BM.utcDay(now);
    if (today - DAY > cT[cT.length - 1]) { cT.push(today - DAY); closes.push(prevShown || p); dailyBars.push(liveBar && mode === "1D" ? { ...liveBar } : { time: today - DAY, open: p, high: p, low: p, close: p }); todayOpen = p; liveBar = null; }
    calc = BM.compute(M, closes, p, now); window.__app.ticks++; window.__app.last = { price: p, sources: n, score: calc.score, t: now };
    const px = $("px"); px.textContent = usd(p, 0); px.classList.toggle("fallback", priceVia === "close"); px.classList.remove("up", "down"); if (prevShown && p !== prevShown) px.classList.add(p > prevShown ? "up" : "down"); prevShown = p;
    if (priceVia === "close") $("chg").innerHTML = `<span class="small">last daily close ${lastClose()} · live feeds connecting</span>`;
    else if (priceVia === "coingecko") $("chg").innerHTML = `<span class="small">CoinGecko REST price · exchange feeds connecting</span>`;
    const open = todayOpen; if (open && priceVia === "live") { const ch = p / open - 1; $("chg").innerHTML = `<span style="color:${ch >= 0 ? "#26a69a" : "#ef5350"}">${ch >= 0 ? "+" : ""}${(ch * 100).toFixed(2)}%</span> <span class="small">vs 00:00 UTC open ${usd(open, 0)}</span>`; }
    sect("score", () => {
    $("score").textContent = f(calc.score, 1); $("score").className = "score z-" + calc.scoreZone;
    $("scoreZone").textContent = calc.scoreZone; $("scoreZone").className = "zone z-" + calc.scoreZone;
    $("meterFill").style.left = `calc(${Math.max(0, Math.min(100, calc.score))}% - 1px)`; $("markWarm").style.left = C.score_warm + "%"; $("markHot").style.left = C.score_hot + "%";
    $("scoreNote").textContent = `hot ≥ ${C.score_hot}, warm ≥ ${C.score_warm}, cool < 40. Plain average of 8 signal heats, recomputed every second. In the backtest it peaked at ~93 (2013, 2017) but only ~65-68 (2021, 2025).`;
    $("nHot").textContent = `${calc.nHot} / ${calc.nSignals}`; $("cycDay").textContent = `${calc.cycleDay} (peaks: ${Math.min(...C.top_days)}-${Math.max(...C.top_days)})`;
    if (blocks.height) { const left = M.next_halving_block - blocks.height, eta = new Date(now + left * 600000); $("height").textContent = blocks.height.toLocaleString() + (blocks.blockTime ? ` · ${ago(now - blocks.blockTime * 1000)}` : "");
      $("halving").textContent = `${left.toLocaleString()} blocks · ~${eta.toISOString().slice(0, 10)}`; }
    const ath = Math.max(...closes, p), dd = p / ath - 1; $("dd").textContent = `${(dd * 100).toFixed(1)}% (peak ${usd(ath, 0)})`;
    });
    const mnav = sect("tiles", () => renderTiles(calc));
    sect("main chart", () => updateChart(p, now));
    sect("hero", () => { const v2 = BM.computeV2(M, calc); window.__app.last.v2 = v2.score; hero.update(p, now, calc, v2, mnav); });
    sect("legend", () => $("lgLive").innerHTML = `<b style="color:#d1d4dc">200D ${usdK(calc.ma200)} · 200W ${usdK(calc.ma1400)} · trend ${usdK(calc.trendLine)} · score ${f(calc.score, 1)}</b>`);
    if (force || now - lastFresh > 5000) { sect("freshness", renderFresh); lastFresh = now; }
    document.title = `${usd(p, 0)} · score ${f(calc.score, 0)} · My BTC Cycle Model`;
  }
  await setMode("1D");
  setInterval(() => { try { tick(); } catch (e) { window.__app.errors.push("tick: " + e.message); } }, 1000);
})().catch((e) => { (window.__app = window.__app || { errors: [] }).errors.push("init: " + e.message); const p = document.getElementById("px"); if (p) p.textContent = "data failed to load"; console.error(e); });
