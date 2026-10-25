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
    const { LC, BM, M, H, FAN2, HEALTH, BG, FWD, cT, closes, baseOpts, priceFmt, $, usd, usdK, f, ZC, C } = ctx;
    const P = FAN2.params, g0 = BM.tsOf(M.genesis), mobile = window.matchMedia("(max-width: 700px)").matches;
    const weekStart = (t) => { const d = new Date(t * 1000).getUTCDay(); return t - ((d + 6) % 7) * DAY; };
    // the chart's time axis, the corridor and the forward cycle band run to the end of 2030 (display only, not graded).
    // The graded forecast range (the locked fan) is NOT drawn on this chart; it is shown in the scorecard section (js/scorecard.js).
    const dispEnd = BM.tsOf((FWD && FWD.display_end) || "2030-12-31");
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
    const opts = () => { const o = baseOpts(); o.timeScale.rightOffset = 2; o.handleScroll = { vertTouchDrag: false }; return o; };
    const hiddenScale = { visible: false, scaleMargins: { top: 0, bottom: 0 } };

    const overlays = [];
    function halvingLines(ch, el) {   // faint vertical lines as HTML overlays (positioned from the time scale)
      el.style.position = "relative";
      const L = [...M.halvings.map((d) => [d, "halving " + d.slice(0, 4)]), [FAN2.next_halving_est, "est. halving " + FAN2.next_halving_est.slice(0, 4), "vline est"]];
      const items = L.map(([d, lab, cls]) => {
        const v = document.createElement("div"); v.className = cls || "vline"; v.innerHTML = `<span>${lab}</span>`; el.appendChild(v); return { t: weekStart(BM.tsOf(d)), v }; });
      const place = () => { const ts = ch.timeScale(), w = ts.width(); for (const it of items) { const x = ts.timeToCoordinate(it.t); it.v.style.display = x == null || x < 0 || x > w ? "none" : "block"; if (x != null) it.v.style.left = x + "px"; } };
      ch.timeScale().subscribeVisibleLogicalRangeChange(place); ch.timeScale().subscribeSizeChange(place); overlays.push(place); return place;
    }

    /* ===== (A) combined chart (light theme): heat-coloured weekly price over trend corridor / cycle band (past and ahead) ===== */
    const KA = { corr: "#f1f2f5", band: "#dde8fb", bg: "#ffffff" };
    const oA = opts(); oA.layout = { ...oA.layout, background: { type: "solid", color: "#ffffff" }, textColor: "#4b5563" };
    oA.grid = { vertLines: { color: "#eef0f3" }, horzLines: { color: "#eef0f3" } }; oA.rightPriceScale = { borderColor: "#d1d5db" }; oA.timeScale = { ...oA.timeScale, borderColor: "#d1d5db" };
    const A = LC.createChart($("heroC"), oA);
    const ser = (type, o, pane) => A.addSeries(type, { priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, priceFormat: priceFmt, ...o }, pane || 0);
    const AR = (c) => ser(LC.AreaSeries, { lineVisible: false, lineWidth: 1, lineColor: c, topColor: c, bottomColor: c });
    const LN = (color, w, style) => ser(LC.LineSeries, { color, lineWidth: w, lineStyle: style });
    // background layers are opaque stacked areas, drawn back to front; each "mask" area paints the colour of the layer beneath it
    const bgT = BG ? BG.t : [];
    const gA = { ceil: AR(KA.corr), bandHi: AR(KA.band), bandLo: AR(KA.corr) };
    // invisible carriers for the forward cycle band: they let the band ahead take part in the price autoscale and host its drawing
    const fwdHi = LN("rgba(0,0,0,0)", 1, 0), fwdLo = LN("rgba(0,0,0,0)", 1, 0);
    gA.floorM = AR(KA.bg);   // floor mask drawn after the band ahead: shading is cut off at the floor line (display only)
    const lA = { ceil: LN("#9ca3af", 1, 1), mid: LN("#6b7280", 1, 2), floor: LN("#d97706", 1.5, 0), bandMd: LN("rgba(59,130,246,.55)", 1, 0) };
    if (BG) {
      const D = (k, from) => bgT.map((t, i) => ({ time: t, value: BG[k][i] })).filter((x) => x.value != null && (!from || x.time >= from));
      const nowW = weekStart(BM.utcDay(Date.now())); gA.ceil.setData(D("ceil")); gA.floorM.setData(D("floor")); lA.ceil.setData(D("ceil")); lA.mid.setData(D("mid")); lA.floor.setData(D("floor"));
      // the past cycle band stops at this week; from here on the dampened forward path (below) takes over
      const past = (k) => D(k).filter((x) => x.time <= nowW);
      gA.bandHi.setData(past("band_hi")); lA.bandMd.setData(past("band_md"));
      gA.bandLo.setData(past("band_lo"));
    }
    const histA = ser(LC.LineSeries, { lineWidth: mobile ? 2 : 2.5, lastValueVisible: false, crosshairMarkerVisible: true, color: "#9ca3af" });
    histA.priceScale().applyOptions({ mode: LC.PriceScaleMode.Logarithmic, scaleMargins: { top: 0.14, bottom: 0.04 } });
    const wk0 = weekStart(BM.utcDay(Date.now()));
    const histAData = weekly(mobile ? "2017-01-01" : "2014-01-01", (i, t) => { const s = scoreByT.get(t); return { value: closes[i], color: heatColor(s), s }; }).filter((x) => x.time < wk0);
    for (let i = 1; i < histAData.length; i++) if (histAData[i].s == null) histAData[i].color = histAData[i - 1].color;
    histA.setData(histAData.map(({ time, value, color }) => ({ time, value, color })));
    // only the price and the forward cycle band drive autoscale (backgrounds extend far above/below)
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
    /* Hover tooltip: weekly close and Cycle Heat Score for past weeks; live price and live score for this week; after now the cycle band ahead (shape guide). */
    const zoneOf = (s) => s == null || !isFinite(s) ? "n/a" : s >= C.score_hot ? "hot" : s >= C.score_warm ? "warm" : s >= 40 ? "neutral" : "cool";
    const sByW = new Map(histAData.map((x) => [x.time, x.s])), vByW = new Map(histAData.map((x) => [x.time, x.value]));
    const fmtD = (t) => new Date(t * 1000).toISOString().slice(0, 10);
    let tipLive = null;
    const tip = document.createElement("div"); tip.className = "herotip"; tip.style.display = "none"; $("heroC").appendChild(tip);
    A.subscribeCrosshairMove((pr) => {
      if (!pr.point || pr.time == null || pr.point.x < 0 || pr.point.y < 0) { tip.style.display = "none"; return; }
      const t = pr.time, d = pr.seriesData.get(histA); let h = "";
      if (t > histEnd && tipLive) { const L = tipLive, lbl = L.via === "close" ? "last close" : L.via === "stale" ? "stale" : "now";
        if (t <= histEnd + 14 * DAY) h = `<b>${lbl} ${usd(L.p, 0)}</b><br>score <b style="color:${heatColor(L.s)}">${f(L.s, 1)} ${L.z}</b>`;
        else { const c = fwdByT.get(t), mk = fwdMk.pk && fwdMk.pk.t === t ? "<br><b>possible next top</b> (band middle)" : fwdMk.lo && fwdMk.lo.t === t ? "<br><b>low after it</b> (band middle)" : "";
          if (c) h = `${fmtD(t)}<br>cycle band ahead: past cycles scaled down<br>(shape guide, not a forecast)<br>middle ${usdK(c.md)} · band ${usdK(c.lo)} - ${usdK(c.hi)}${mk}`;
          else { const j = BG ? BG.t.indexOf(t) : -1; if (j >= 0) h = `${fmtD(t)}<br>trend ${usdK(BG.mid[j])} · corridor ${usdK(BG.floor[j])} - ${usdK(BG.ceil[j])}`; } } }
      else { const v = d && d.value != null ? d.value : vByW.get(t), s = sByW.get(t);
        if (v != null) h = `week of ${fmtD(t)}<br><b>${usd(v, 0)}</b> close<br>score <b style="color:${heatColor(s)}">${s == null ? "n/a" : f(s, 1) + " " + zoneOf(s)}</b>`; }
      if (!h) { tip.style.display = "none"; return; }
      tip.innerHTML = h; tip.style.display = "block";
      const W = $("heroC").clientWidth, tw = tip.offsetWidth, th = tip.offsetHeight;
      let x = pr.point.x + 14, y = pr.point.y - th - 10; if (x + tw > W - 70) x = pr.point.x - tw - 14; if (y < 4) y = pr.point.y + 14;
      tip.style.left = Math.max(4, x) + "px"; tip.style.top = y + "px";
    });
    /* Forward cycle band (display only): dampened cycle band from data/hero_fwd.json, drawn from this week as far as the prior
       cycles' data reaches (late 2030, one more day each day), in the same light-blue band + middle line style as the past band.
       The first 8 weeks blend in log space from the past band's value to the dampened one, so the two meet without a step at "now".
       The possible next top (highest band middle after the next halving) and the low after it are found from the data on each load. */
    const fwdByT = new Map(), fwdMk = { pk: null, lo: null };
    const mon = (t) => new Date(t * 1000).toLocaleString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
    const fwd = { pts: [], attached(p) { this.chart = p.chart; this.series = p.series; this.req = p.requestUpdate; }, detached() {}, updateAllViews() {}, paneViews() { return [fwdView]; } };
    if (FWD && BG) {
      const nowW = weekStart(BM.utcDay(Date.now())), bi = new Map(BG.t.map((t, i) => [t, i])), BLEND = 8;
      const mix = (b, d, w) => b == null ? d : Math.exp((1 - w) * Math.log(b) + w * Math.log(d));
      FWD.t.forEach((t, i) => { if (t < nowW || t > dispEnd + 6 * DAY || FWD.md[i] == null) return; const j = bi.get(t), w = Math.min(1, (t - nowW) / (7 * DAY) / BLEND);
        fwd.pts.push({ t, lo: mix(j != null ? BG.band_lo[j] : null, FWD.lo[i], w), md: mix(j != null ? BG.band_md[j] : null, FWD.md[i], w), hi: mix(j != null ? BG.band_hi[j] : null, FWD.hi[i], w) }); });
      fwd.pts.forEach((q) => fwdByT.set(q.t, q));
      fwdHi.setData(fwd.pts.map((q) => ({ time: q.t, value: q.hi }))); fwdLo.setData(fwd.pts.map((q) => ({ time: q.t, value: q.lo })));
      const nh = weekStart(BM.tsOf(FAN2.next_halving_est)), after = fwd.pts.filter((q) => q.t >= nh);
      if (after.length) { const pk = after.reduce((m, q) => q.md > m.md ? q : m), rest = after.filter((q) => q.t > pk.t);
        fwdMk.pk = pk; fwdMk.lo = rest.length ? rest.reduce((m, q) => q.md < m.md ? q : m) : null; }
      const txt = (q) => `~${mon(q.t)}, middle ~${usdK(q.md)} (band ~${usdK(q.lo)}-${usdK(q.hi)})`;
      fwdMk.pkTxt = fwdMk.pk ? "possible next top: " + txt(fwdMk.pk) : ""; fwdMk.loTxt = fwdMk.lo ? "low after it: " + txt(fwdMk.lo) : "";
      window.__app.fwdMk = { pk: fwdMk.pkTxt, lo: fwdMk.loTxt, end: fmtD(fwd.pts[fwd.pts.length - 1].t) };
      window.__app.fwd = { n: fwd.pts.length, first: fwd.pts[0], last: fwd.pts[fwd.pts.length - 1], rho: FWD.rho };
    }
    const fwdView = { zOrder: () => "normal", renderer: () => ({ draw(target) {
      if (fwd.pts.length < 2 || !fwd.series) return;
      const ts = fwd.chart.timeScale(), sr = fwd.series;
      const P = fwd.pts.map((q) => ({ x: ts.timeToCoordinate(q.t), lo: sr.priceToCoordinate(q.lo), md: sr.priceToCoordinate(q.md), hi: sr.priceToCoordinate(q.hi) })).filter((q) => q.x != null && q.lo != null && q.hi != null);
      if (P.length < 2) return;
      target.useMediaCoordinateSpace(({ context: g }) => {
        g.save(); g.beginPath(); P.forEach((q, i) => i ? g.lineTo(q.x, q.hi) : g.moveTo(q.x, q.hi)); for (let i = P.length - 1; i >= 0; i--) g.lineTo(P[i].x, P[i].lo); g.closePath();
        g.fillStyle = KA.band; g.fill();   // same colour as the past band
        g.beginPath(); P.forEach((q, i) => i ? g.lineTo(q.x, q.md) : g.moveTo(q.x, q.md)); g.strokeStyle = "rgba(59,130,246,.55)"; g.lineWidth = 1; g.stroke(); g.restore();
      });
    } }) };
    /* light annotations of the possible next top and the low after it: small dots always; the text only on wide charts
       (on phones the same text is in the legend and the tooltip). Drawn on top so the dots sit over the price lines. */
    const mkView = { zOrder: () => "top", renderer: () => ({ draw(target) {
      if (!fwd.series || !fwdMk.pk) return;
      const ts = fwd.chart.timeScale(), sr = fwd.series;
      target.useMediaCoordinateSpace(({ context: g, mediaSize }) => {
        const W = mediaSize.width, Hh = mediaSize.height, wide = W >= 640, boxes = [];
        for (const [q, lab, up] of [[fwdMk.pk, fwdMk.pkTxt, true], [fwdMk.lo, fwdMk.loTxt, false]]) {
          if (!q) continue; const x = ts.timeToCoordinate(q.t), y = sr.priceToCoordinate(q.md); if (x == null || y == null || x < 0 || x > W) continue;
          g.save(); g.beginPath(); g.arc(x, y, wide ? 3.5 : 3, 0, 2 * Math.PI); g.fillStyle = "rgba(37,99,235,.8)"; g.fill(); g.lineWidth = 1.2; g.strokeStyle = "#ffffff"; g.stroke(); g.restore();
          if (!wide) continue;
          const i = lab.indexOf(", middle"), L = [lab.slice(0, i), lab.slice(i + 2)];
          g.save(); g.font = "11px system-ui, -apple-system, Segoe UI, Roboto, sans-serif"; const tw = Math.max(...L.map((l) => g.measureText(l).width)) + 10, th = 32;
          let bx = Math.min(Math.max(4, x - tw / 2 - (up ? 60 : 40)), W - tw - 4), by = up ? y - th - 28 : y + 26;
          if (by < 22) by = 22; if (by + th > Hh - 4) by = Hh - th - 4;
          for (const b of boxes) if (bx < b.x + b.w && bx + tw > b.x && by < b.y + b.h && by + th > b.y) by = up ? b.y - th - 4 : b.y + b.h + 4;
          boxes.push({ x: bx, y: by, w: tw, h: th });
          g.strokeStyle = "rgba(147,197,253,.9)"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(x, y); g.lineTo(Math.min(Math.max(x, bx + 6), bx + tw - 6), up ? by + th : by); g.stroke();
          g.fillStyle = "rgba(255,255,255,.88)"; g.fillRect(bx, by, tw, th);
          g.fillStyle = "rgba(30,58,138,.88)"; g.textAlign = "center"; g.textBaseline = "middle"; L.forEach((l, k) => g.fillText(l, bx + tw / 2, by + 9 + k * 14));
          g.restore();
        }
      });
    } }) };
    fwdHi.attachPrimitive(fwd);   // after the past band areas, before the floor mask and the trend/floor/ceiling lines
    fwdLo.attachPrimitive({ attached() {}, detached() {}, updateAllViews() {}, paneViews: () => [mkView] });
    const liveA = histA.createPriceLine({ price: 1, color: "#3b82f6", lineWidth: 1, lineStyle: 3, lineVisible: false, axisLabelVisible: true, axisLabelColor: "#3b82f6", axisLabelTextColor: "#ffffff", title: "" });
    halvingLines(A, $("heroC"));
    A.timeScale().fitContent();
    $("heroCLegend").innerHTML = `<span class="scale"><b>Line color = Cycle Heat Score</b> <i class="grad"></i><span class="ticks"><span>0 cool</span><span>40</span><span>${C.score_warm} warm</span><span>${C.score_hot}+ hot</span></span></span>`
      + `<span><i style="background:#d1d5db"></i>trend corridor</span><span><i style="background:#6b7280"></i>trend (dashed) / ceiling (dotted)</span><span><i style="background:#d97706"></i>floor</span>`
      + `<span><i style="background:#93c5fd"></i>past cycle band (prior 2 cycles)</span>`
      + (FWD ? `<span title="After now: the same cycle band, with each prior cycle's swing scaled down by the measured shrink rate of past peaks (rho ${FWD.rho.toFixed(2)}); first 8 weeks blended from the past band. Runs to late 2030, as far as the prior cycles' data reaches. Display only, not in the score, not graded."><i style="background:#93c5fd"></i>cycle band ahead (past cycles scaled down): shape guide, not a forecast</span>` : "")
      + (fwdMk.pk ? `<span><i style="background:#2563eb;width:7px;height:7px;border-radius:50%"></i>${fwdMk.pkTxt}${fwdMk.lo ? " · " + fwdMk.loTxt : ""}</span>` : "")
      + `<span><i style="background:#9ca3af"></i>halvings</span>`;
    $("heroAlt").innerHTML = `The blue band after "now" is the past cycles scaled down and is recomputed daily; the copy frozen on 2026-10-25 is the pre-registered, graded claim (see the <a href="#scorecardSec">scorecard section</a>)${fwd.pts.length ? ` (it ends ${fmtD(fwd.pts[fwd.pts.length - 1].t)}, as far as the prior cycles' data reaches)` : ""}. The locked forecast range (the fan) is also in the scorecard section, not on this chart. Model ranges, not predictions; not financial advice.`;
    document.querySelector("#heroCLegend .grad").style.background = `linear-gradient(90deg, ${[0, 20, 30, 40, C.score_warm, C.score_hot, 90].map((s) => heatColor(s) + " " + s + "%").join(",")})`;


    /* initial view: from 2014 (2017 on phones) through the end of 2030 (corridor + cycle band ahead), with right padding so the last
       weeks and the axis labels are not clipped; price autoscale includes the band ahead (other background layers are excluded above). Re-fit on resize. */
    function fitA() {
      const last = Math.max(fwd.pts.length ? fwd.pts[fwd.pts.length - 1].t : 0, BG ? Math.min(weekStart(dispEnd), bgT[bgT.length - 1]) : 0), ts = A.timeScale();
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

    let firstRender = true, firstPlace = true;
    function update(p, now, calc, v2, via) {
      const wk = weekStart(BM.utcDay(now)), col = heatColor(calc.score);
      if (firstRender) { fitA(); firstRender = false; }
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
      const today = BM.utcDay(now);
      if (firstPlace) { overlays.forEach((f) => f()); firstPlace = false; }
      // one-line summary under the combined chart
      const ath = Math.max(...closes, p), athI = closes.lastIndexOf(Math.max(...closes)), athT = p >= ath ? today : cT[athI];
      $("heroLine").innerHTML = `<b>${usd(p, 0)}</b> · score <b style="color:${col}">${f(calc.score, 1)} ${calc.scoreZone}</b> (stricter v2 score <b style="color:${ZC[v2.zone] || "#999"}">${f(v2.score, 1)} ${v2.zone}</b> ${Explain.i("v2")}) · day <b>${calc.cycleDay}</b> since halving · <b>${Math.round((today - athT) / DAY)}</b> days since peak ${usdK(ath)} (${(100 * (p / ath - 1)).toFixed(1)}%)`;
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
