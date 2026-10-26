/* Live public market-data feeds. No keys, no backend.
   1) WebSockets from 3 exchanges (streaming). 2) If fewer than 2 sockets deliver a price within ~5 s, HTTPS REST polling every 10 s
   from the 3 exchanges + 5 more CORS-enabled public endpoints on different domains. A price counts for the index only if it is
   < 15 s old; any source > 0.5% from the median of the others is dropped. Every source keeps a short diagnostic (ws / REST state). */
(function (root) {
  const FRESH_MS = 15000, SILENCE_MS = 10000, OUTLIER = 0.005, POLL_MS = 10000, WS_GRACE_MS = 5000;
  const num = (v) => { const x = parseFloat(v); return isFinite(x) && x > 0 ? x : null; };
  /* Safety: nothing read from the network may be inserted as HTML. Prices and block numbers are coerced to finite numbers
     (num, int); strings in our own data/*.json files are HTML-escaped once on load (clean), so a tampered file shows as text. */
  const int = (v) => { const x = Number(v); return Number.isFinite(x) && x > 0 ? Math.floor(x) : null; };
  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ESC[c]);
  const clean = (x) => typeof x === "string" ? esc(x) : Array.isArray(x) ? x.map(clean)
    : x && typeof x === "object" ? Object.fromEntries(Object.entries(x).map(([k, v]) => [esc(k), clean(v)]))
    : typeof x === "number" || typeof x === "boolean" || x == null ? x : null;
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
  /* REST-only sources, used only in polling mode. All checked to send CORS headers to this site (Oct 2026). */
  const POLL_SOURCES = [
    { id: "gemini", name: "Gemini", host: "api.gemini.com", rest: async () => num((await getJSON("https://api.gemini.com/v1/pubticker/btcusd")).last) },
    { id: "binanceus", name: "Binance.US", host: "api.binance.us", rest: async () => num((await getJSON("https://api.binance.us/api/v3/ticker/price?symbol=BTCUSD")).price) },
    { id: "cryptocom", name: "Crypto.com", host: "api.crypto.com", rest: async () => { const r = await getJSON("https://api.crypto.com/exchange/v1/public/get-tickers?instrument_name=BTC_USD"); return num(r.result.data[0].a); } },
    { id: "blockchain", name: "Blockchain.com", host: "blockchain.info", rest: async () => num((await getJSON("https://blockchain.info/ticker")).USD.last) },
    { id: "coingecko", name: "CoinGecko", host: "api.coingecko.com", rest: async () => num((await getJSON("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")).bitcoin.usd) },
  ];
  async function getJSON(url) { const c = new AbortController(); const t = setTimeout(() => c.abort(), 8000);
    try { const r = await fetch(url, { signal: c.signal, cache: "no-store" }); if (!r.ok) { const e = new Error("HTTP " + r.status); e.http = true; throw e; } return await r.json(); } finally { clearTimeout(t); } }
  /* what a failed fetch most likely means, in words */
  const why = (e) => !e ? null : e.name === "AbortError" ? "timeout" : e.http ? e.message : e instanceof SyntaxError ? "bad response (not JSON)" : e instanceof TypeError ? "blocked" : "error";

  class Feed {
    constructor(src, onPrice) {
      Object.assign(this, { src, onPrice, ws: null, price: null, at: 0, wsAt: 0, via: null, tries: 0, msgs: 0, lastMsg: 0, openedAt: 0, reconnects: 0, restBusy: false, retryT: null,
        wsOpens: 0, wsFails: 0, restOk: 0, restErr: null, restTries: 0, born: Date.now() });
      this.connect(); this.rest();                                  // REST right away so the first price does not wait for the socket
      this.timer = setInterval(() => this.watch(), 2000);
    }
    connect() {
      clearTimeout(this.retryT); this.retryT = null;
      const old = this.ws; this.ws = null; if (old) { try { old.onclose = old.onmessage = old.onerror = null; old.close(); } catch (e) {} }
      let ws; try { ws = new WebSocket(this.src.url); } catch (e) { this.wsFails++; return this.retry(); }
      this.ws = ws; this.openedAt = Date.now(); this.lastMsg = 0; let opened = false;
      ws.onopen = () => { opened = true; this.wsOpens++; this.tries = 0; this.lastMsg = Date.now(); this.src.subscribe.forEach((s) => ws.send(JSON.stringify(s))); };
      ws.onmessage = (ev) => { if (this.ws !== ws) return; this.lastMsg = Date.now(); let m; try { m = JSON.parse(ev.data); } catch { return; }
        const p = this.src.parse(m); if (p) { this.msgs++; this.set(p, "ws"); } };
      ws.onerror = () => {}; ws.onclose = () => { if (!opened) this.wsFails++; if (this.ws === ws) { this.ws = null; this.retry(); } };
    }
    retry() { if (this.retryT) return; const wait = Math.min(30000, 1000 * Math.pow(2, this.tries++)); this.retryT = setTimeout(() => { this.retryT = null; this.connect(); }, wait); }
    reconnect() { this.reconnects++; this.connect(); }
    open() { return !!(this.ws && this.ws.readyState === 1); }
    set(p, via) { this.price = p; this.at = Date.now(); this.via = via; if (via === "ws") this.wsAt = this.at; this.onPrice && this.onPrice(this, p); }
    async rest() { if (this.restBusy) return; this.restBusy = true; this.restTries++;
      try { const p = await this.src.rest(); if (!p) throw new SyntaxError("no price"); this.restOk = Date.now(); this.restErr = null; this.set(p, "rest"); }
      catch (e) { this.restErr = why(e); } finally { this.restBusy = false; } }
    watch() {   // every 2 s: liveness ping, silence watchdog, REST every 10 s while the socket has no recent price
      const now = Date.now();
      if (this.open() && this.src.ping && now - (this.pingAt || 0) > 5000) { this.pingAt = now; try { this.ws.send(JSON.stringify(this.src.ping)); } catch (e) {} }
      if (this.ws) {
        const silentFor = now - (this.lastMsg || this.openedAt);
        if (silentFor > SILENCE_MS) this.reconnect();               // open-but-dead (phone slept, NAT dropped) or stuck connecting
      }
      const every = !this.restOk && !this.wsOpens && now - this.born > 60000 ? 60000 : POLL_MS;   // never reached (blocked network?): retry once a minute
      if (now - this.wsAt > WS_GRACE_MS && now - (this.restAt || 0) >= every) { this.restAt = now; this.rest(); }
    }
    wake() {    // page visible again / back online / focus: do not trust an old socket
      this.tries = 0; const now = Date.now();
      if (!this.open() || now - (this.lastMsg || 0) > 3000) this.reconnect();
      this.rest();
    }
    wsFresh() { return Date.now() - this.wsAt < FRESH_MS; }
    age() { return this.at ? Date.now() - this.at : Infinity; }
    fresh() { return this.age() < FRESH_MS; }
    status() { if (!this.at) return "down"; if (!this.fresh()) return "stale"; return this.via === "rest" ? "rest" : "live"; }
    diag() {
      const ws = this.wsFresh() ? "ok" : this.open() ? (this.wsAt ? "silent" : "open, no data yet") : this.wsOpens === 0 && this.wsFails >= 2 ? "blocked"
        : this.wsOpens ? "reconnecting" : "connecting";
      const rest = this.restErr ? this.restErr : this.restOk && Date.now() - this.restOk < 30000 ? "ok" : this.restTries ? "trying" : "not needed";
      return { ws, rest };
    }
  }

  /* BTC perpetual funding for the crowd gauge: Deribit public funding-rate history (hourly interest_8h records), fetched
     directly by the visitor's browser every 60 s (a new record lands each hour). Last 7 UTC days + today. If it never
     succeeds (blocked network) it backs off to once every 5 minutes; the page then shows the daily gauge. */
  class Funding {
    constructor(onUpdate) { Object.assign(this, { onUpdate, rows: [], at: 0, okAt: 0, err: null, tries: 0, busy: false }); this.poll(); this.timer = setInterval(() => this.watch(), 5000); }
    watch() { const every = !this.okAt && this.tries >= 3 ? 300000 : 60000; if (Date.now() - this.at >= every) this.poll(); }
    wake() { if (Date.now() - this.at > 15000) this.poll(); }
    fresh() { return this.okAt && Date.now() - this.okAt < 180000; }
    async poll() { if (this.busy) return; this.busy = true; this.at = Date.now(); this.tries++;
      try { const end = Date.now(), start = (Math.floor(end / 86400000) - 7) * 86400000;
        const j = await getJSON(`https://www.deribit.com/api/v2/public/get_funding_rate_history?instrument_name=BTC-PERPETUAL&start_timestamp=${start}&end_timestamp=${end}`);
        const r = (j && j.result || []).map((x) => ({ t: +x.timestamp, r: +x.interest_8h })).filter((x) => isFinite(x.t) && isFinite(x.r));
        if (!r.length) throw new SyntaxError("no funding rows");
        this.rows = r; this.okAt = Date.now(); this.err = null; this.onUpdate && this.onUpdate(this);
      } catch (e) { this.err = why(e); } finally { this.busy = false; } }
  }

  /* REST-only source: polls every 10 s while active (polling mode). Same interface as Feed for combine() and the header. */
  class Poller {
    constructor(src) { Object.assign(this, { src, price: null, at: 0, via: "rest", active: false, busy: false, restOk: 0, restErr: null, restTries: 0, born: Date.now() }); this.timer = setInterval(() => this.watch(), 1000); }
    setActive(on) { if (on && !this.active) this.lastPoll = 0; this.active = on; if (on) this.watch(); }
    watch() { const now = Date.now(), every = !this.restOk && this.restTries >= 3 ? 60000 : POLL_MS; if (this.active && now - (this.lastPoll || 0) >= every) { this.lastPoll = now; this.poll(); } }
    async poll() { if (this.busy) return; this.busy = true; this.restTries++;
      try { const p = await this.src.rest(); if (!p) throw new SyntaxError("no price"); this.price = p; this.at = this.restOk = Date.now(); this.restErr = null; }
      catch (e) { this.restErr = why(e); } finally { this.busy = false; } }
    wake() { if (this.active) { this.lastPoll = 0; this.watch(); } }
    wsFresh() { return false; }
    age() { return this.at ? Date.now() - this.at : Infinity; }
    fresh() { return this.age() < FRESH_MS; }
    status() { if (!this.at) return "down"; return this.fresh() ? "rest" : "stale"; }
    diag() { return { ws: null, rest: this.restErr ? this.restErr : !this.active && !this.restTries ? "standby" : this.restOk && Date.now() - this.restOk < 30000 ? "ok" : "trying" }; }
  }

  /* Combine fresh sources into one index price: median of sources < 15 s old, dropping any > 0.5% from the median of the others. */
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
    return { p: med(used.map((x) => x.price)), used, dropped, disagree, at: Math.max(...used.map((x) => x.at)), streaming: used.some((x) => x.via === "ws") };
  }

  /* blocks: mempool.space WebSocket; REST fallback chain mempool.space -> blockstream.info -> blockchain.info */
  const BLOCK_REST = [
    { name: "mempool.space", get: async () => { const b = await getJSON("https://mempool.space/api/v1/blocks"); return { h: b[0].height, t: b[0].timestamp }; } },
    { name: "blockstream.info", get: async () => { const b = await getJSON("https://blockstream.info/api/blocks"); return { h: b[0].height, t: b[0].timestamp }; } },
    { name: "blockchain.info", get: async () => { const h = await getJSON("https://blockchain.info/q/getblockcount?cors=true"); return { h: parseInt(h, 10), t: null }; } },
  ];
  class Blocks {
    constructor(onBlock) { Object.assign(this, { onBlock, height: null, blockTime: null, at: 0, via: null, src: null, tries: 0, lastMsg: 0, wsOpens: 0, wsFails: 0, restErr: {} });
      this.connect(); this.poll(); setInterval(() => this.watch(), 15000); }
    connect() {
      clearTimeout(this.retryT); this.retryT = null;
      const old = this.ws; this.ws = null; if (old) { try { old.onclose = old.onmessage = old.onerror = null; old.close(); } catch (e) {} }
      let ws; try { ws = new WebSocket("wss://mempool.space/api/v1/ws"); } catch { this.wsFails++; return this.retry(); }
      this.ws = ws; this.openedAt = Date.now(); let opened = false;
      ws.onopen = () => { opened = true; this.wsOpens++; this.tries = 0; this.lastMsg = Date.now(); ws.send(JSON.stringify({ action: "init" })); ws.send(JSON.stringify({ action: "want", data: ["blocks", "stats"] })); };
      ws.onmessage = (ev) => { this.lastMsg = Date.now(); let m; try { m = JSON.parse(ev.data); } catch { return; }
        const bl = m.block ? [m.block] : (m.blocks || []); for (const b of bl) if (b && b.height && (!this.height || b.height >= this.height)) this.set(b.height, b.timestamp, "ws", !!m.block, "mempool.space"); };
      ws.onclose = () => { if (!opened) this.wsFails++; if (this.ws === ws) { this.ws = null; this.retry(); } }; ws.onerror = () => {};
    }
    retry() { if (this.retryT) return; const wait = Math.min(60000, 2000 * Math.pow(2, this.tries++)); this.retryT = setTimeout(() => { this.retryT = null; this.connect(); }, wait); }
    set(h, t, via, isNew, src) { h = int(h); t = int(t); if (!h || (this.height && h < this.height)) return; const changed = h !== this.height; this.height = h; if (t || changed) this.blockTime = t || null; this.at = Date.now(); this.via = via; this.src = src; if (changed) this.onBlock && this.onBlock(this, isNew); }
    async poll() { if (this.busy) return; this.busy = true;
      try { for (const s of BLOCK_REST) { try { const r = await s.get(); if (!int(r.h)) throw new SyntaxError("bad block height"); this.restErr[s.name] = null; this.set(r.h, r.t, this.ws && this.ws.readyState === 1 ? this.via || "rest" : "rest", false, s.name); return; } catch (e) { this.restErr[s.name] = why(e); } } }
      finally { this.busy = false; } }
    watch() { const now = Date.now();
      if (this.ws && now - (this.lastMsg || this.openedAt) > 120000) this.connect();   // mempool pushes stats every few seconds; 2 min of silence = dead socket
      if (!this.ws || this.ws.readyState !== 1 || now - this.at > 300000) this.poll(); }
    wake() { this.tries = 0; if (!this.ws || this.ws.readyState !== 1 || Date.now() - this.lastMsg > 30000) this.connect(); this.poll(); }
    status() { if (!this.at) return "down"; if (this.ws && this.ws.readyState === 1) return "live"; return "rest"; }
    diag() { const ws = this.ws && this.ws.readyState === 1 ? "ok" : this.wsOpens === 0 && this.wsFails >= 2 ? "blocked" : this.wsOpens ? "reconnecting" : "connecting";
      return { ws, rest: BLOCK_REST.map((s) => `${s.name} ${this.restErr[s.name] === undefined ? "–" : this.restErr[s.name] || "ok"}`).join(", ") }; }
  }

  /* Reconnect everything when the tab comes back (phones freeze background tabs and silently kill sockets). */
  function onWake(fn) {
    let last = 0; const go = (why) => { const now = Date.now(); if (now - last < 1000) return; last = now; fn(why); };
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") go("visible"); });
    window.addEventListener("online", () => go("online")); window.addEventListener("focus", () => go("focus"));
    window.addEventListener("pageshow", (e) => { if (e.persisted) go("pageshow"); });
  }
  root.Feeds = { SOURCES, POLL_SOURCES, Feed, Poller, Blocks, Funding, getJSON, combine, onWake, num, int, esc, clean, FRESH_MS, SILENCE_MS, OUTLIER, POLL_MS, WS_GRACE_MS };
})(this);
