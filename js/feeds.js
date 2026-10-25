/* Live public market-data feeds (browser WebSockets) with reconnect + REST fallback. No keys, no backend. */
(function (root) {
  const FRESH_MS = 90000, STALE_MS = 15000;
  const num = (v) => { const x = parseFloat(v); return isFinite(x) && x > 0 ? x : null; };
  const SOURCES = [
    { id: "coinbase", name: "Coinbase", url: "wss://advanced-trade-ws.coinbase.com",
      subscribe: [{ type: "subscribe", product_ids: ["BTC-USD"], channel: "ticker" }, { type: "subscribe", product_ids: ["BTC-USD"], channel: "heartbeats" }],
      parse(m) { if (m.channel !== "ticker" || !m.events) return null; for (const e of m.events) for (const t of e.tickers || []) if (t.product_id === "BTC-USD") return num(t.price); return null; },
      rest: async () => num((await getJSON("https://api.exchange.coinbase.com/products/BTC-USD/ticker")).price) },
    { id: "kraken", name: "Kraken", url: "wss://ws.kraken.com/v2",
      subscribe: [{ method: "subscribe", params: { channel: "ticker", symbol: ["BTC/USD"] } }],
      parse(m) { return m.channel === "ticker" && m.data && m.data[0] ? num(m.data[0].last) : null; },
      rest: async () => { const r = await getJSON("https://api.kraken.com/0/public/Ticker?pair=XBTUSD"); const k = Object.keys(r.result || {})[0]; return k ? num(r.result[k].c[0]) : null; } },
    { id: "bitstamp", name: "Bitstamp", url: "wss://ws.bitstamp.net",
      subscribe: [{ event: "bts:subscribe", data: { channel: "live_trades_btcusd" } }],
      parse(m) { return m.event === "trade" && m.data ? num(m.data.price) : null; },
      rest: async () => { const r = await getJSON("https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=60&limit=1"); return num(r.data.ohlc.slice(-1)[0].close); } },
  ];
  async function getJSON(url) { const c = new AbortController(); const t = setTimeout(() => c.abort(), 8000);
    try { const r = await fetch(url, { signal: c.signal, cache: "no-store" }); if (!r.ok) throw new Error(r.status); return await r.json(); } finally { clearTimeout(t); } }

  class Feed {
    constructor(src, onPrice) { Object.assign(this, { src, onPrice, ws: null, price: null, at: 0, via: null, state: "connecting", tries: 0, msgs: 0, lastMsg: 0 });
      this.connect(); this.restTimer = setInterval(() => this.maybeRest(), 5000); }
    connect() {
      let ws; try { ws = new WebSocket(this.src.url); } catch (e) { return this.retry(); }
      this.ws = ws; this.state = "connecting";
      ws.onopen = () => { this.tries = 0; this.src.subscribe.forEach((s) => ws.send(JSON.stringify(s))); };
      ws.onmessage = (ev) => { this.lastMsg = Date.now(); let m; try { m = JSON.parse(ev.data); } catch { return; }
        const p = this.src.parse(m); if (p) { this.msgs++; this.set(p, "ws"); } };
      ws.onerror = () => {}; ws.onclose = () => { if (this.ws === ws) { this.ws = null; this.retry(); } };
    }
    retry() { this.state = "down"; const wait = Math.min(30000, 1000 * Math.pow(2, this.tries++)); setTimeout(() => this.connect(), wait); }
    set(p, via) { this.price = p; this.at = Date.now(); this.via = via; this.onPrice && this.onPrice(this, p); }
    async maybeRest() {   // poll REST while the socket is down or silent
      // "silent" = no PRICE from the socket for 20 s (heartbeats alone do not count), so a socket that is open but not delivering ticks still gets REST
      const silent = Date.now() - (this.via === "ws" ? this.at : 0) > 20000;
      if (this.ws && this.ws.readyState === 1 && !silent) return;
      try { const p = await this.src.rest(); if (p) this.set(p, "rest"); } catch (e) {}
    }
    status() { const age = Date.now() - this.at;
      if (!this.at) return this.ws && this.ws.readyState === 1 ? "stale" : "down";
      if (age > FRESH_MS) return "down"; if (this.via === "rest") return "rest"; return age > STALE_MS && !(this.ws && this.ws.readyState === 1) ? "stale" : "live"; }
    fresh() { return this.at && Date.now() - this.at < FRESH_MS; }
  }

  /* mempool.space blocks */
  class Blocks {
    constructor(onBlock) { Object.assign(this, { onBlock, height: null, blockTime: null, at: 0, via: null, tries: 0 }); this.connect(); this.poll(); setInterval(() => this.maybePoll(), 60000); }
    connect() { let ws; try { ws = new WebSocket("wss://mempool.space/api/v1/ws"); } catch { return this.retry(); }
      this.ws = ws;
      ws.onopen = () => { this.tries = 0; ws.send(JSON.stringify({ action: "init" })); ws.send(JSON.stringify({ action: "want", data: ["blocks"] })); };
      ws.onmessage = (ev) => { let m; try { m = JSON.parse(ev.data); } catch { return; }
        const bl = m.block ? [m.block] : (m.blocks || []); for (const b of bl) if (b && b.height && (!this.height || b.height >= this.height)) this.set(b.height, b.timestamp, "ws", !!m.block); };
      ws.onclose = () => { if (this.ws === ws) { this.ws = null; this.retry(); } }; ws.onerror = () => {};
    }
    retry() { const wait = Math.min(60000, 2000 * Math.pow(2, this.tries++)); setTimeout(() => this.connect(), wait); }
    set(h, t, via, isNew) { const changed = h !== this.height; this.height = h; this.blockTime = t; this.at = Date.now(); this.via = via; if (changed) this.onBlock && this.onBlock(this, isNew); }
    async poll() { try { const b = await getJSON("https://mempool.space/api/v1/blocks"); if (b && b[0]) this.set(b[0].height, b[0].timestamp, this.ws && this.ws.readyState === 1 ? this.via || "rest" : "rest"); } catch {} }
    maybePoll() { if (!this.ws || this.ws.readyState !== 1) this.poll(); }
    status() { if (!this.at) return "down"; if (this.ws && this.ws.readyState === 1) return "live"; return "rest"; }
  }
  root.Feeds = { SOURCES, Feed, Blocks, getJSON };
})(this);
