/* Live public market-data feeds (browser WebSockets) with watchdog reconnect + REST fallback. No keys, no backend.
   A price counts for the index only if its last tick is < 15 s old; a feed > 0.5% away from the others is dropped. */
(function (root) {
  const FRESH_MS = 15000, SILENCE_MS = 10000, OUTLIER = 0.005;
  const num = (v) => { const x = parseFloat(v); return isFinite(x) && x > 0 ? x : null; };
  const SOURCES = [
    { id: "coinbase", name: "Coinbase", url: "wss://advanced-trade-ws.coinbase.com",
      subscribe: [{ type: "subscribe", product_ids: ["BTC-USD"], channel: "ticker" }, { type: "subscribe", product_ids: ["BTC-USD"], channel: "heartbeats" }],
      parse(m) { if (m.channel !== "ticker" || !m.events) return null; for (const e of m.events) for (const t of e.tickers || []) if (t.product_id === "BTC-USD") return num(t.price); return null; },
      rest: async () => num((await getJSON("https://api.exchange.coinbase.com/products/BTC-USD/ticker")).price) },
    { id: "kraken", name: "Kraken", url: "wss://ws.kraken.com/v2",            // Kraken v2 sends a heartbeat every second
      subscribe: [{ method: "subscribe", params: { channel: "ticker", symbol: ["BTC/USD"] } }],
      parse(m) { return m.channel === "ticker" && m.data && m.data[0] ? num(m.data[0].last) : null; },
      rest: async () => { const r = await getJSON("https://api.kraken.com/0/public/Ticker?pair=XBTUSD"); const k = Object.keys(r.result || {})[0]; return k ? num(r.result[k].c[0]) : null; } },
    { id: "bitstamp", name: "Bitstamp", url: "wss://ws.bitstamp.net",
      subscribe: [{ event: "bts:subscribe", data: { channel: "live_trades_btcusd" } }],
      ping: { event: "bts:heartbeat" },                                       // Bitstamp answers, so a quiet market is not mistaken for a dead socket
      parse(m) { return m.event === "trade" && m.data ? num(m.data.price) : null; },
      rest: async () => { const r = await getJSON("https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=60&limit=1"); return num(r.data.ohlc.slice(-1)[0].close); } },
  ];
  async function getJSON(url) { const c = new AbortController(); const t = setTimeout(() => c.abort(), 8000);
    try { const r = await fetch(url, { signal: c.signal, cache: "no-store" }); if (!r.ok) throw new Error(r.status); return await r.json(); } finally { clearTimeout(t); } }

  class Feed {
    constructor(src, onPrice) {
      Object.assign(this, { src, onPrice, ws: null, price: null, at: 0, wsAt: 0, via: null, tries: 0, msgs: 0, lastMsg: 0, openedAt: 0, reconnects: 0, restBusy: false, retryT: null });
      this.connect(); this.rest();                                  // REST right away so the first price does not wait for the socket
      this.timer = setInterval(() => this.watch(), 2000);
    }
    connect() {
      clearTimeout(this.retryT); this.retryT = null;
      const old = this.ws; this.ws = null; if (old) { try { old.onclose = old.onmessage = old.onerror = null; old.close(); } catch (e) {} }
      let ws; try { ws = new WebSocket(this.src.url); } catch (e) { return this.retry(); }
      this.ws = ws; this.openedAt = Date.now(); this.lastMsg = 0;
      ws.onopen = () => { this.tries = 0; this.lastMsg = Date.now(); this.src.subscribe.forEach((s) => ws.send(JSON.stringify(s))); };
      ws.onmessage = (ev) => { if (this.ws !== ws) return; this.lastMsg = Date.now(); let m; try { m = JSON.parse(ev.data); } catch { return; }
        const p = this.src.parse(m); if (p) { this.msgs++; this.set(p, "ws"); } };
      ws.onerror = () => {}; ws.onclose = () => { if (this.ws === ws) { this.ws = null; this.retry(); } };
    }
    retry() { if (this.retryT) return; const wait = Math.min(30000, 1000 * Math.pow(2, this.tries++)); this.retryT = setTimeout(() => { this.retryT = null; this.connect(); }, wait); }
    reconnect() { this.reconnects++; this.connect(); }
    open() { return !!(this.ws && this.ws.readyState === 1); }
    set(p, via) { this.price = p; this.at = Date.now(); this.via = via; if (via === "ws") this.wsAt = this.at; this.onPrice && this.onPrice(this, p); }
    async rest() { if (this.restBusy) return; this.restBusy = true; try { const p = await this.src.rest(); if (p) this.set(p, "rest"); } catch (e) {} finally { this.restBusy = false; } }
    watch() {   // every 2 s: liveness ping, silence watchdog, REST while the socket has no recent price
      const now = Date.now();
      if (this.open() && this.src.ping && now - (this.pingAt || 0) > 5000) { this.pingAt = now; try { this.ws.send(JSON.stringify(this.src.ping)); } catch (e) {} }
      if (this.ws) {
        const silentFor = now - (this.lastMsg || this.openedAt);
        if (silentFor > SILENCE_MS) this.reconnect();               // open-but-dead (phone slept, NAT dropped) or stuck connecting
      }
      if (now - this.wsAt > 6000 && now - (this.restAt || 0) >= 4000) { this.restAt = now; this.rest(); }                        // socket down or not delivering prices: keep the price fresh via REST
    }
    wake() {    // page visible again / back online / focus: do not trust an old socket
      this.tries = 0; const now = Date.now();
      if (!this.open() || now - (this.lastMsg || 0) > 3000) this.reconnect();
      this.rest();
    }
    age() { return this.at ? Date.now() - this.at : Infinity; }
    fresh() { return this.age() < FRESH_MS; }
    status() { if (!this.at) return "down"; if (!this.fresh()) return "stale"; return this.via === "rest" ? "rest" : "live"; }
  }

  /* Combine fresh feeds into one index price: median of feeds < 15 s old, dropping any feed > 0.5% from the median of the others. */
  function combine(feeds) {
    const fr = feeds.filter((x) => x.fresh() && x.price);
    const med = (a) => { const s = a.slice().sort((x, y) => x - y), n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
    let used = fr, dropped = [], disagree = false;
    if (fr.length >= 3) {
      used = fr.filter((x) => Math.abs(x.price / med(fr.filter((y) => y !== x).map((y) => y.price)) - 1) <= OUTLIER);
      dropped = fr.filter((x) => !used.includes(x));
      if (!used.length) { used = fr; dropped = []; disagree = true; }
    } else if (fr.length === 2 && Math.abs(fr[0].price / fr[1].price - 1) > OUTLIER) {
      const newest = fr[0].at >= fr[1].at ? fr[0] : fr[1]; used = [newest]; dropped = fr.filter((x) => x !== newest); disagree = true;
    }
    if (!used.length) return null;
    return { p: med(used.map((x) => x.price)), used, dropped, disagree, at: Math.max(...used.map((x) => x.at)) };
  }

  /* mempool.space blocks */
  class Blocks {
    constructor(onBlock) { Object.assign(this, { onBlock, height: null, blockTime: null, at: 0, via: null, tries: 0, lastMsg: 0 }); this.connect(); this.poll(); setInterval(() => this.watch(), 15000); }
    connect() {
      clearTimeout(this.retryT); this.retryT = null;
      const old = this.ws; this.ws = null; if (old) { try { old.onclose = old.onmessage = old.onerror = null; old.close(); } catch (e) {} }
      let ws; try { ws = new WebSocket("wss://mempool.space/api/v1/ws"); } catch { return this.retry(); }
      this.ws = ws; this.openedAt = Date.now();
      ws.onopen = () => { this.tries = 0; this.lastMsg = Date.now(); ws.send(JSON.stringify({ action: "init" })); ws.send(JSON.stringify({ action: "want", data: ["blocks", "stats"] })); };
      ws.onmessage = (ev) => { this.lastMsg = Date.now(); let m; try { m = JSON.parse(ev.data); } catch { return; }
        const bl = m.block ? [m.block] : (m.blocks || []); for (const b of bl) if (b && b.height && (!this.height || b.height >= this.height)) this.set(b.height, b.timestamp, "ws", !!m.block); };
      ws.onclose = () => { if (this.ws === ws) { this.ws = null; this.retry(); } }; ws.onerror = () => {};
    }
    retry() { if (this.retryT) return; const wait = Math.min(60000, 2000 * Math.pow(2, this.tries++)); this.retryT = setTimeout(() => { this.retryT = null; this.connect(); }, wait); }
    set(h, t, via, isNew) { const changed = h !== this.height; this.height = h; this.blockTime = t; this.at = Date.now(); this.via = via; if (changed) this.onBlock && this.onBlock(this, isNew); }
    async poll() { try { const b = await getJSON("https://mempool.space/api/v1/blocks"); if (b && b[0]) this.set(b[0].height, b[0].timestamp, this.ws && this.ws.readyState === 1 ? this.via || "rest" : "rest"); } catch {} }
    watch() { const now = Date.now();
      if (this.ws && now - (this.lastMsg || this.openedAt) > 120000) this.connect();   // mempool pushes stats every few seconds; 2 min of silence = dead socket
      if (!this.ws || this.ws.readyState !== 1 || now - this.at > 300000) this.poll(); }
    wake() { this.tries = 0; if (!this.ws || this.ws.readyState !== 1 || Date.now() - this.lastMsg > 30000) this.connect(); this.poll(); }
    status() { if (!this.at) return "down"; if (this.ws && this.ws.readyState === 1) return "live"; return "rest"; }
  }

  /* Reconnect everything when the tab comes back (phones freeze background tabs and silently kill sockets). */
  function onWake(fn) {
    let last = 0; const go = (why) => { const now = Date.now(); if (now - last < 1000) return; last = now; fn(why); };
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") go("visible"); });
    window.addEventListener("online", () => go("online")); window.addEventListener("focus", () => go("focus"));
    window.addEventListener("pageshow", (e) => { if (e.persisted) go("pageshow"); });
  }
  root.Feeds = { SOURCES, Feed, Blocks, getJSON, combine, onWake, FRESH_MS, SILENCE_MS, OUTLIER };
})(this);
