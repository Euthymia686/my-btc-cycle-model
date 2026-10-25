/* Hero chart: combined "My BTC Cycle Model" chart (with a live tail from the last weekly close to the live price), plus model-health panel.
   It uses WEEKLY points (lightweight-charts spaces points by index, so mixing daily history with a weekly forecast would distort time). */
(function () {
  "use strict";
  const DAY = 86400;
  const STOPS = [[0, [30, 64, 175]], [30, [59, 130, 246]], [40, [156, 163, 175]], [47, [245, 158, 11]], [62, [239, 68, 68]], [100, [185, 28, 28]]];
  function heatColor(s) {
    if (s == null || !isFinite(s)) return "#6b7280";
    s = Math.max(0, Math.min(100, s)); let i = 1; while (i < STOPS.length - 1 && s > STOPS[i][0]) i++;
    const [x0, c0] = STOPS[i - 1], [x1, c1] = STOPS[i], w = x1 === x0 ? 0 : (s - x0) / (x1 - x0);
    return "rgb(" + c0.map((c, k) => Math.round(c + w * (c1[k] - c))).join(",") + ")";
  }

  function init(ctx) {
    const { LC, BM, M, H, MS, FAN2, HEALTH, BG, FWD, cT, closes, baseOpts, priceFmt, $, usd, usdK, f, ZC, C } = ctx;
    const P = FAN2.params, g0 = BM.tsOf(M.genesis), mobile = window.matchMedia("(max-width: 700px)").matches;
    const weekStart = (t) => { const d = new Date(t * 1000).getUTCDay(); return t - ((d + 6) % 7) * DAY; };
    const endT = BM.tsOf(FAN2.end);   // public display horizon of the projection fan (Dec 31 2028)
    // set hot/warm stops from the live v1 calibration
    STOPS[3][0] = C.score_warm; STOPS[4][0] = C.score_hot;
    const scoreByT = new Map(H.t.map((t, i) => [t, H.score[i]]));
    function weekly(fromIso, getV) {
      const out = [], t0 = BM.tsOf(fromIso);
      for (let i = 0; i < cT.length; i++) { const t = cT[i]; if (t < t0) continue; const k = weekStart(t), v = getV(i, t);
        if (v == null || !isFinite(v.value)) continue;
        if (out.length && out[out.length - 1].time === k) out[out.length - 1] = { ...v, time: k }; else out.push({ ...v, time: k }); }
      return out;
    }
    const futureT = (now) => { const w = weekStart(BM.utcDay(now)), ts = []; for (let t = w; t <= endT + 6 * DAY; t += 7 * DAY) ts.push(t); return ts; };
    const trendAt = (t) => Math.pow(10, P.a + P.b * Math.log10((t - g0) / DAY));
    const opts = () => { const o = baseOpts(); o.timeScale.rightOffset = 2; o.handleScroll = { vertTouchDrag: false }; return o; };
    const hiddenScale = { visible: false, scaleMargins: { top: 0, bottom: 0 } };

    const overlays = [];
    function halvingLines(ch, el) {   // faint vertical lines as HTML overlays (positioned from the time scale)
      el.style.position = "relative";
      const L = [...M.halvings.map((d) => [d, "halving"]), [FAN2.next_halving_est, "est. halving", "vline est"]];
      const items = L.map(([d, lab, cls]) => {
        const v = document.createElement("div"); v.className = cls || "vline"; v.innerHTML = `<span>${lab} ${d.slice(0, 4)}</span>`; el.appendChild(v); return { t: weekStart(BM.tsOf(d)), v }; });
      const place = () => { const ts = ch.timeScale(), w = ts.width(); for (const it of items) { const x = ts.timeToCoordinate(it.t); it.v.style.display = x == null || x < 0 || x > w ? "none" : "block"; if (x != null) it.v.style.left = x + "px"; } };
      ch.timeScale().subscribeVisibleLogicalRangeChange(place); ch.timeScale().subscribeSizeChange(place); overlays.push(place); return place;
    }
    let fanCache = null;
    function computeFan(p, now) {
      const t0 = BM.utcDay(now), r0 = BM.fanR0(P, g0, t0, p), ts = futureT(now), rows = ts.map((t) => ({ t, q: BM.fanAt(P, g0, t0, Math.max(t, t0), r0) }));
      rows[0].q = { q5: p, q25: p, q50: p, q75: p, q95: p };   // fan opens at the live price
      const qe = BM.fanAt(P, g0, t0, endT, r0);
      fanCache = { r0, rows, qe, at: now }; return fanCache;
    }

    /* ===== (A) combined chart (light theme): heat-coloured weekly price over trend corridor / cycle band / fan ===== */
    const KA = { corr: "#f1f2f5", band: "#dde8fb", fanO: "#f7f4fd", fanI: "#efe9fb", bg: "#ffffff" };   // fan kept faint: it sits behind the forward cycle path
    const oA = opts(); oA.layout = { ...oA.layout, background: { type: "solid", color: "#ffffff" }, textColor: "#4b5563" };
    oA.grid = { vertLines: { color: "#eef0f3" }, horzLines: { color: "#eef0f3" } }; oA.rightPriceScale = { borderColor: "#d1d5db" }; oA.timeScale = { ...oA.timeScale, borderColor: "#d1d5db" };
    const A = LC.createChart($("heroC"), oA);
    const ser = (type, o, pane) => A.addSeries(type, { priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, priceFormat: priceFmt, ...o }, pane || 0);
    const AR = (c) => ser(LC.AreaSeries, { lineVisible: false, lineWidth: 1, lineColor: c, topColor: c, bottomColor: c });
    const LN = (color, w, style) => ser(LC.LineSeries, { color, lineWidth: w, lineStyle: style });
    // background layers are opaque stacked areas, drawn back to front; each "mask" area paints the colour of the layer beneath it
    const bgT = BG ? BG.t : [];
    const gA = { ceil: AR(KA.corr), bandHi: AR(KA.band), bandLo: AR(KA.corr) };
    const fA = { q95: AR(KA.fanO), q75: AR(KA.fanI), q25: AR(KA.fanO), q5: AR(KA.bg) };
    gA.floorM = AR(KA.bg);   // floor mask drawn after the fan and the forward path: shading is cut off at the floor (display only; quantiles unchanged)
    const lA = { ceil: LN("#9ca3af", 1, 1), mid: LN("#6b7280", 1, 2), floor: LN("#d97706", 1.5, 0), bandMd: LN("rgba(59,130,246,.55)", 1, 0), q50: LN("rgba(109,40,217,.45)", 1, 1) };
    if (BG) {
      const D = (k, from) => bgT.map((t, i) => ({ time: t, value: BG[k][i] })).filter((x) => x.value != null && (!from || x.time >= from));
      const nowW = weekStart(BM.utcDay(Date.now())); gA.ceil.setData(D("ceil")); gA.floorM.setData(D("floor")); lA.ceil.setData(D("ceil")); lA.mid.setData(D("mid")); lA.floor.setData(D("floor"));
      // the past cycle band stops at this week; from here on the dampened forward path (below) takes over
      const past = (k) => D(k).filter((x) => x.time <= nowW);
      gA.bandHi.setData(past("band_hi")); lA.bandMd.setData(past("band_md"));
      gA.bandLo.setData(past("band_lo"));
    }
    function setBandsA(fc) {
      for (const k of ["q25", "q75", "q95"]) fA[k].setData(fc.rows.map((r) => ({ time: r.t, value: r.q[k] })));
      fA.q5.setData(fc.rows.map((r) => ({ time: r.t, value: r.q.q5 })));
      lA.q50.setData(fc.rows.map((r) => ({ time: r.t, value: r.q.q50 })));
    }
    const histA = ser(LC.LineSeries, { lineWidth: mobile ? 2 : 2.5, lastValueVisible: false, crosshairMarkerVisible: true, color: "#9ca3af" });
    histA.priceScale().applyOptions({ mode: LC.PriceScaleMode.Logarithmic, scaleMargins: { top: 0.09, bottom: 0.04 } });
    const wk0 = weekStart(BM.utcDay(Date.now()));
    const histAData = weekly(mobile ? "2017-01-01" : "2014-01-01", (i, t) => { const s = scoreByT.get(t); return { value: closes[i], color: heatColor(s), s }; }).filter((x) => x.time < wk0);
    for (let i = 1; i < histAData.length; i++) if (histAData[i].s == null) histAData[i].color = histAData[i - 1].color;
    histA.setData(histAData.map(({ time, value, color }) => ({ time, value, color })));
    // only the price and fan drive autoscale (backgrounds extend far above/below)
    for (const sr of [gA.ceil, gA.floorM, gA.bandHi, gA.bandLo, lA.ceil, lA.mid, lA.floor, lA.bandMd]) sr.applyOptions({ autoscaleInfoProvider: () => null });
    let histEnd = histAData.length ? histAData[histAData.length - 1].time : wk0 - 7 * DAY, histEndV = histAData.length ? histAData[histAData.length - 1].value : null;
    /* Live tail: from the last weekly close through this week's daily closes to the live price, coloured by score, redrawn every tick.
       Drawn as a series primitive at fractional x inside the current week's slot, so the weekly time spacing is not distorted. */
    const tail = { pts: [], col: "#6b7280",
      attached(p) { this.chart = p.chart; this.series = p.series; this.req = p.requestUpdate; }, detached() {}, updateAllViews() {},
      paneViews() { return [tailView]; } };
    const tailView = { zOrder: () => "top", renderer: () => ({ draw(target) {
      if (!tail.pts.length || !tail.series) return;
      const ts = tail.chart.timeScale(), x0 = ts.timeToCoordinate(histEnd), x1 = ts.timeToCoordinate(histEnd + 7 * DAY);
      if (x0 == null || x1 == null) return;
      const X = (T) => x0 + (T - (histEnd + 7 * DAY)) / (7 * DAY) * (x1 - x0), Y = (v) => tail.series.priceToCoordinate(v);
      const P = tail.pts.map((q) => ({ x: X(q.T), y: Y(q.v), c: q.c })).filter((q) => q.y != null);
      target.useMediaCoordinateSpace(({ context: g, mediaSize }) => {
        g.save(); g.lineCap = "round"; g.lineJoin = "round"; g.lineWidth = mobile ? 2 : 2.5;
        for (let i = 1; i < P.length; i++) { g.strokeStyle = P[i].c; g.beginPath(); g.moveTo(P[i - 1].x, P[i - 1].y); g.lineTo(P[i].x, P[i].y); g.stroke(); }
        const e = P[P.length - 1]; if (!e) { g.restore(); return; }
        g.beginPath(); g.arc(e.x, e.y, mobile ? 4 : 5, 0, 2 * Math.PI); g.fillStyle = tail.col; g.fill(); g.lineWidth = 2; g.strokeStyle = "#ffffff"; g.stroke();
        g.restore();
      });
    } }) };
    histA.attachPrimitive(tail); window.__app.heroChart = A;
    /* Hover tooltip: weekly close and Cycle Heat Score for past weeks; live price and live score for this week; fan median and 5-95% after now. */
    const zoneOf = (s) => s == null || !isFinite(s) ? "n/a" : s >= C.score_hot ? "hot" : s >= C.score_warm ? "warm" : s >= 40 ? "neutral" : "cool";
    const sByW = new Map(histAData.map((x) => [x.time, x.s])), vByW = new Map(histAData.map((x) => [x.time, x.value]));
    const fmtD = (t) => new Date(t * 1000).toISOString().slice(0, 10);
    let tipLive = null;
    const tip = document.createElement("div"); tip.className = "herotip"; tip.style.display = "none"; $("heroC").appendChild(tip);
    A.subscribeCrosshairMove((pr) => {
      if (!pr.point || pr.time == null || pr.point.x < 0 || pr.point.y < 0) { tip.style.display = "none"; return; }
      const t = pr.time, d = pr.seriesData.get(histA); let h = "";
      if (t > histEnd && tipLive) { const L = tipLive, lbl = L.via === "close" ? "last close" : L.via === "stale" ? "stale" : "now";
        if (t < histEnd + 14 * DAY) h = `<b>${lbl} ${usd(L.p, 0)}</b><br>score <b style="color:${heatColor(L.s)}">${f(L.s, 1)} ${L.z}</b>`;
        else if (fanCache) { const r = fanCache.rows.find((x) => x.t === t); if (r) h = `${fmtD(t)}<br>fan median ${usdK(r.q.q50)}<br>5-95%: ${usdK(r.q.q5)} - ${usdK(r.q.q95)}`; } }
      else { const v = d && d.value != null ? d.value : vByW.get(t), s = sByW.get(t);
        if (v != null) h = `week of ${fmtD(t)}<br><b>${usd(v, 0)}</b> close<br>score <b style="color:${heatColor(s)}">${s == null ? "n/a" : f(s, 1) + " " + zoneOf(s)}</b>`; }
      if (!h) { tip.style.display = "none"; return; }
      tip.innerHTML = h; tip.style.display = "block";
      const W = $("heroC").clientWidth, tw = tip.offsetWidth, th = tip.offsetHeight;
      let x = pr.point.x + 14, y = pr.point.y - th - 10; if (x + tw > W - 70) x = pr.point.x - tw - 14; if (y < 4) y = pr.point.y + 14;
      tip.style.left = Math.max(4, x) + "px"; tip.style.top = y + "px";
    });
    /* Forward cycle path (display only): dampened cycle band from data/hero_fwd.json, drawn from this week to the end of the fan,
       same light-blue band + middle line as the past band, over the (faint) fan. The first 8 weeks blend in log space from the
       past band's value to the dampened one, so the two meet without a step at "now". */
    const fwd = { pts: [], attached(p) { this.chart = p.chart; this.series = p.series; this.req = p.requestUpdate; }, detached() {}, updateAllViews() {}, paneViews() { return [fwdView]; } };
    if (FWD && BG) {
      const nowW = weekStart(BM.utcDay(Date.now())), bi = new Map(BG.t.map((t, i) => [t, i])), BLEND = 8;
      const mix = (b, d, w) => b == null ? d : Math.exp((1 - w) * Math.log(b) + w * Math.log(d));
      FWD.t.forEach((t, i) => { if (t < nowW || t > endT + 6 * DAY || FWD.md[i] == null) return; const j = bi.get(t), w = Math.min(1, (t - nowW) / (7 * DAY) / BLEND);
        fwd.pts.push({ t, lo: mix(j != null ? BG.band_lo[j] : null, FWD.lo[i], w), md: mix(j != null ? BG.band_md[j] : null, FWD.md[i], w), hi: mix(j != null ? BG.band_hi[j] : null, FWD.hi[i], w) }); });
      window.__app.fwd = { n: fwd.pts.length, first: fwd.pts[0], rho: FWD.rho };
    }
    const fwdView = { zOrder: () => "normal", renderer: () => ({ draw(target) {
      if (fwd.pts.length < 2 || !fwd.series) return;
      const ts = fwd.chart.timeScale(), sr = fwd.series;
      const P = fwd.pts.map((q) => ({ x: ts.timeToCoordinate(q.t), lo: sr.priceToCoordinate(q.lo), md: sr.priceToCoordinate(q.md), hi: sr.priceToCoordinate(q.hi) })).filter((q) => q.x != null && q.lo != null && q.hi != null);
      if (P.length < 2) return;
      target.useMediaCoordinateSpace(({ context: g }) => {
        g.save(); g.beginPath(); P.forEach((q, i) => i ? g.lineTo(q.x, q.hi) : g.moveTo(q.x, q.hi)); for (let i = P.length - 1; i >= 0; i--) g.lineTo(P[i].x, P[i].lo); g.closePath();
        g.fillStyle = "rgba(214,227,250,0.85)"; g.fill();
        g.beginPath(); P.forEach((q, i) => i ? g.lineTo(q.x, q.md) : g.moveTo(q.x, q.md)); g.strokeStyle = "rgba(59,130,246,.55)"; g.lineWidth = 1; g.stroke(); g.restore();
      });
    } }) };
    fA.q5.attachPrimitive(fwd);   // after the fan areas, before the floor mask and the trend/floor/ceiling lines
    const liveA = histA.createPriceLine({ price: 1, color: "#3b82f6", lineWidth: 1, lineStyle: 3, lineVisible: false, axisLabelVisible: true, axisLabelColor: "#3b82f6", axisLabelTextColor: "#ffffff", title: "" });
    halvingLines(A, $("heroC"));
    A.timeScale().fitContent();
    $("heroCLegend").innerHTML = `<span class="scale"><b>Line colour = Cycle Heat Score</b> <i class="grad"></i><span class="ticks"><span>0 cool</span><span>40</span><span>${C.score_warm} warm</span><span>${C.score_hot}+ hot</span></span></span>`
      + `<span><i style="background:#d1d5db"></i>trend corridor 5-95%</span><span><i style="background:#6b7280"></i>trend (dashed) / ceiling (dotted)</span><span><i style="background:#d97706"></i>floor</span>`
      + `<span><i style="background:#93c5fd"></i>cycle band (prior 2 cycles)</span>`
      + (FWD ? `<span title="After now: the same cycle band, with each prior cycle's swing scaled down by the measured shrink rate of past peaks (rho ${FWD.rho.toFixed(2)}); first 8 weeks blended from the past band. Display only, not in the score."><i style="background:#93c5fd"></i>cycle path (past cycles, dampened) — shape guide</span>` : "")
      + `<span><i style="background:#ddd0f8"></i>probability range (fan) 25-75% / 5-95%, median dotted</span>`
      + `<span><i style="background:#9ca3af"></i>halvings</span>`;
    document.querySelector("#heroCLegend .grad").style.background = `linear-gradient(90deg, ${[0, 20, 30, 40, C.score_warm, C.score_hot, 90].map((s) => heatColor(s) + " " + s + "%").join(",")})`;


    /* initial view: from 2014 (2017 on phones) through the end of the fan, with right padding so the fan's last weeks and the
       axis labels are not clipped; price autoscale includes the fan (background layers are excluded above). Re-fit on resize. */
    function fitA() {
      if (!fanCache) return;
      const last = fanCache.rows[fanCache.rows.length - 1].t, ts = A.timeScale();
      // work in logical (bar index) space: setVisibleRange + getVisibleLogicalRange can return the previous range before the chart re-lays out
      const i0 = ts.timeToIndex(weekStart(BM.tsOf(mobile ? "2017-01-01" : "2014-06-01")), true), i1 = ts.timeToIndex(last, true);
      if (i0 == null || i1 == null) { ts.fitContent(); }
      else ts.setVisibleLogicalRange({ from: i0, to: i1 + Math.max(3, (i1 - i0) * 0.035) });
      A.priceScale("right").applyOptions({ autoScale: true });
      setTimeout(() => overlays.forEach((g) => g()), 0);
    }
    let rsT = null, lastW = 0;
    // re-fit only when the container is resized (window/rotation); the time scale's own size also changes when price-axis labels
    // widen or narrow during a zoom, and re-fitting on that would snap the user's zoom back
    new ResizeObserver((es) => { const w = Math.round(es[0].contentRect.width); if (!lastW) { lastW = w; return; } if (Math.abs(w - lastW) < 2) return; lastW = w; clearTimeout(rsT); rsT = setTimeout(fitA, 120); }).observe($("heroC"));
    const heroEl = $("heroC"); heroEl.addEventListener("dblclick", fitA);
    const fitBtn = $("heroFit"); if (fitBtn) fitBtn.addEventListener("click", fitA);

    const pct = (x) => x == null ? "--" : (100 * x).toFixed(1) + "%";
    /* ===== model health panel (static parts) ===== */
    renderHealth(ctx);

    let lastFan = 0, firstRender = true, firstPlace = true;
    function update(p, now, calc, v2, mnav, via) {
      const wk = weekStart(BM.utcDay(now)), col = heatColor(calc.score);
      if (firstRender || now - lastFan > (mobile ? 15000 : 5000)) { const fc = computeFan(p, now); setBandsA(fc); lastFan = now; if (firstRender) fitA(); firstRender = false; }
      // week rolled over while open: move completed weeks from the tail into the weekly history
      while (histEnd + 7 * DAY < wk) { const k = histEnd + 7 * DAY; let v = null, s = null;
        for (let i = cT.length - 1; i >= 0 && cT[i] >= k; i--) if (weekStart(cT[i]) === k) { v = closes[i]; s = scoreByT.get(cT[i]); break; }
        if (v == null) v = p; histA.update({ time: k, value: v, color: s != null ? heatColor(s) : col }); histEnd = k; histEndV = v; }
      const pts = [{ T: histEnd + 7 * DAY, v: histEndV ?? p, c: col }];
      for (let i = 0; i < cT.length; i++) if (cT[i] >= wk && cT[i] < BM.utcDay(now)) { const s = scoreByT.get(cT[i]); pts.push({ T: cT[i] + DAY, v: closes[i], c: s != null ? heatColor(s) : col }); }
      pts.push({ T: now / 1000, v: p, c: col });
      tail.pts = pts; tail.col = !via || via === "live" ? col : "#9ca3af"; tail.req && tail.req();
      tipLive = { p, s: calc.score, z: calc.scoreZone, via };
      window.__app.tail = { x: null, p, n: pts.length };
      { const live = !via || via === "live", c = live ? "#3b82f6" : "#9ca3af"; liveA.applyOptions({ price: p, color: c, axisLabelColor: c }); }
      { const qe = fanCache.qe; $("heroAlt").textContent = `Projection fan at its end (Dec 31 2028), recomputed with the live price: 5% ${usdK(qe.q5)} \u00b7 median ${usdK(qe.q50)} \u00b7 95% ${usdK(qe.q95)}. Model ranges, not predictions; not financial advice.`; }
      const today = BM.utcDay(now);
      if (firstPlace) { overlays.forEach((f) => f()); firstPlace = false; }
      // one-line summary under the combined chart
      const ath = Math.max(...closes, p), athI = closes.lastIndexOf(Math.max(...closes)), athT = p >= ath ? today : cT[athI];
      $("heroLine").innerHTML = `<b>${usd(p, 0)}</b> · score <b style="color:${col}">${f(calc.score, 1)} ${calc.scoreZone}</b> (v2 <b style="color:${ZC[v2.zone] || "#999"}">${f(v2.score, 1)} ${v2.zone}</b>) · day <b>${calc.cycleDay}</b> since halving · <b>${Math.round((today - athT) / DAY)}</b> days since peak ${usdK(ath)} (${(100 * (p / ath - 1)).toFixed(1)}%)`;
      // live position of today's price inside the frozen fan
      const FZ = FAN2.frozen; if (FZ) { const j = FZ.today.t.indexOf(today); if (j >= 0) { const q = { q5: FZ.today.q5[j], q25: FZ.today.q25[j], q50: FZ.today.q50[j], q75: FZ.today.q75[j], q95: FZ.today.q95[j] };
        $("hLive").innerHTML = `Live price is at model percentile <b>${f(BM.fanPos(q, p), 0)}</b> of the frozen fan for today (5-95%: ${usdK(q.q5)}-${usdK(q.q95)}; inside the 90% band: <b>${p >= q.q5 && p <= q.q95 ? "yes" : "NO"}</b>).`; }
        else $("hLive").textContent = "Today is outside the frozen fan's weekly cache; see the daily journal for coverage."; }
    }
    function renderHealth() {
      const h = HEALTH, I = h.integrity, S = h.fan_backtest.summary, fw = h.forward || {};
      const ok = (b) => b ? `<b class="ok">OK</b>` : `<b class="bad">CHANGED</b>`;
      const rows = h.fan_backtest.freezes.map((r) => `<tr${r.in90 < 0.85 ? ' class="warnrow"' : ""}><td>${r.freeze}</td><td>${r.days}</td><td>${pct(r.in90)}</td><td>${pct(r.in50)}</td><td>${pct(r.below5)}</td><td>${pct(r.above95)}</td><td>${pct(r.fixed_corridor_in90)}</td></tr>`).join("");
      $("health").innerHTML = `
        <div class="hgrid">
          <div><h3>Since the freeze (${I.frozen_on}) <span class="small">out-of-sample</span></h3>
            <p>${fw.days ? `${fw.days} daily closes so far: inside 90% band <b>${pct(fw.in90)}</b> (target 90%), inside 50% band <b>${pct(fw.in50)}</b> (target 50%).` : "0 daily closes yet. This fills in automatically from the first finalized close after the freeze; it needs months before it means anything."}</p>
            <p id="hLive"></p>
            <h3>Integrity</h3><p>v2 spec ${ok(I.v2_spec_ok)} · fan code ${ok(I.robust_ok)} · frozen fan ${ok(I.fan_ok)}<br><span class="small mono">v2_spec.py sha256 ${I.v2_spec_sha256}</span></p>
            <h3>Trend drift <span class="small">(Dec 2028 trend value, by fit date)</span></h3>
            <table class="t"><tr><th>fit date</th><th>slope</th><th>trend at end-2028</th></tr>${h.trend_drift.map((d) => `<tr><td>${d.fit_date}</td><td>${d.slope_b}</td><td>${usdK(d.trend_at_horizon)}</td></tr>`).join("")}</table>
            <p class="small">The trend's 2028 value has fallen as data arrived (diminishing returns). A single fixed target would have been stale; this is why the fan is refit daily and widens with horizon.</p></div>
          <div><h3>Backtest: band coverage <span class="small">22 freezes, each fitted only on data before it, scored on the next ${h.fan_backtest.horizon_days} days</span></h3>
            <table class="t"><tr><th>horizon</th><th>in 90% band</th><th>in 50% band</th><th>days</th></tr>${["all", "0-1y", "1-2y", "2-3y"].map((k) => `<tr><td>${k}</td><td>${pct(S[k].in90)}</td><td>${pct(S[k].in50)}</td><td>${S[k].days.toLocaleString()}</td></tr>`).join("")}</table>
            <p class="small">Calibrated would be 90% / 50%. The fan is <b>conservative</b> (too wide) overall. A fixed, non-widening 5-95% corridor scored ${pct(S.fixed_corridor_all_in90)} overall but broke after the 2015 regime shift (21% / 43%).</p>
            <details><summary>Per-freeze detail</summary><table class="t"><tr><th>freeze</th><th>days</th><th>in 90%</th><th>in 50%</th><th>below 5%</th><th>above 95%</th><th>fixed corridor in 90%</th></tr>${rows}</table></details></div>
        </div>`;
    }
    return { update };
  }
  window.Hero = { init, heatColor };
})();
