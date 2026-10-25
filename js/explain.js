/* Plain-language explainers: a small (i) button next to a label opens a short note (hover on desktop, tap on phones).
   One shared popover outside the live-updating parts of the page, so the note stays open while tiles refresh every second. */
(function () {
  "use strict";
  const T = {
    price: "Bitcoin's price in US dollars: the middle value of several large exchanges, updated live. \"Streaming\" means a live connection; \"polling\" means the price is re-checked every 10 seconds.",
    feeds: "Each dot is one price source. Green: fresh price. Orange: waiting for a price. Gray: not used right now (no recent price, or too far from the others). \"Blocks\" is the newest Bitcoin block number, used for the halving countdown.",
    diag: "Technical status of each connection (WS = live connection, REST = ordinary web request). If a work or school network blocks crypto sites, this line shows which ones failed.",
    chart: "Weekly Bitcoin price since 2014 on a log scale, colored by the Cycle Heat Score, with the long-term trend corridor and the model's range of outcomes to the end of 2028. Hover or tap for the price and score of any week; scroll or pinch to zoom; double-click or Reset view to see everything.",
    v2: "v2 is a stricter version of the score, fixed in advance on 2026-10-25 and logged daily so it can be tested honestly on new data. It compares only with the last 8 years and averages 5 groups of signals instead of 8 single signals.",
    score: "One number from 0 to 100 for how stretched Bitcoin looks versus its own history, the plain average of 8 signal heats. Higher means closer to how past cycle tops looked. It moves over weeks and months: cycle context, not a buy or sell signal.",
    nhot: "How many of the 8 signals are at a level that, in the past, was only reached near cycle tops.",
    cycday: "Days since the last halving, the event about every 4 years when the reward for new bitcoin is cut in half. Past cycle tops came about 1 to 1.5 years after a halving.",
    height: "The number of the newest block on the Bitcoin network. A new block arrives roughly every 10 minutes.",
    halving: "The next halving happens at block 1,050,000. The date is an estimate assuming 10 minutes per block, so it shifts a little as real blocks arrive.",
    dd: "How far the price is below its highest daily close so far.",
    signals: "Each tile is one measurement. The colored bar is its heat from 0 to 100: the share of past days on which the reading was lower (its percentile). A heat of 90 means higher than on 90% of past days. Zones (cool, neutral, warm, hot) follow from the heat.",
    cycle_day: "Where we are in the roughly 4-year halving cycle. Heat is 100 on the average day past tops happened after a halving and falls off on either side. The dates below are historical windows, not predictions.",
    mayer: "Price divided by its 200-day average (known as the Mayer Multiple). Above 1 means price is above its 200-day average; readings far above that have shown up near past tops.",
    p200w: "Price divided by its 200-week average, about 4 years of prices. Past cycle lows came near this average, and large multiples of it appeared near tops.",
    trend_mult: "Price divided by this site's long-term trend line, a power-law curve fitted to all of Bitcoin's history. 1.0x means exactly on trend; high multiples came near past tops.",
    mvrv_z: "Compares Bitcoin's total market value with what holders paid for their coins on average (the MVRV Z-score). High values mean most holders sit on large gains, which has happened near past tops.",
    pi_ratio: "The 111-day average divided by twice the 350-day average (the Pi Cycle Top indicator). A ratio of 1.00 means the two lines cross, which happened close to several past tops.",
    wiki: "Daily views of the English Wikipedia \"Bitcoin\" article, a rough gauge of public attention. Shown for context only; it is not part of the score.",
    activity: "Bitcoin addresses active in the last 30 days compared with the last year. Network use running well above normal has come with past bull runs.",
    mnav: "Strategy (MSTR) stock market value divided by the value of the bitcoin it holds (called mNAV). Above 1x the stock trades at a premium to its bitcoin. Shown for context; not part of the score.",
    levels: "Today's value of the trend line, and the realized price: the average price at which all coins last moved, a rough \"average holder cost\".",
    health: "A running check that the model still works on new data. The fan from the freeze date is kept unchanged, and over time about 90% of daily prices should land inside its 90% band. \"OK\" means the frozen files have not been altered.",
    fresh: "Which numbers change every second, and which only update daily or monthly, with the date of the latest data for each.",
    scorecard: "A public report card. Every day the site writes down what each model version expects for the price 30, 90 and 365 days later, as a range. When that day arrives, the forecast is graded. Nothing is deleted or edited afterwards, so anyone can check the record in the raw file.",
    sc_live: "Only forecasts made after the freeze on 2026-10-25, graded on prices that did not exist when they were made. This is the honest test. It starts empty and fills in as forecasts mature.",
    sc_backtest: "How the same rules would have done on past data, by pretending to stand at earlier dates and checking against what happened next. Useful, but easier to pass than the live test, because the rules were designed while looking at that history.",
    sc_weak: "Known ways the model has been wrong or could fail. Listed up front so the results can be read fairly.",
    sc_cov: "The share of matured forecasts where the actual price landed inside the band. A good 50% band holds the price about half the time, a good 90% band about 90% of the time. Much more means the band is too wide; much less means too narrow.",
    sc_log: "A single grade for each forecast that rewards ranges that are narrow but still contain the price, and punishes misses. Higher is better. It only means something when comparing v2 with v3 on the same days.",
    sc_tests: "Checks whether the results so far could just be luck. Each test gives a p-value: the chance of a result at least this far off if the band were sized exactly right (coverage) or if the two forecasts were equally good (skill).",
    sc_binom: "Exact binomial test of how often the price landed inside each band versus the target (50% or 90%). p below 0.05 means the band is probably mis-sized; a high p means no evidence it's wrong yet, not proof it's right.",
    sc_ess: "Effective sample size: the number of forecasts that do not overlap in time (for example one 30-day forecast every 30 days), so each outcome is independent. Daily forecasts that overlap mostly repeat the same information, so only these are counted. Tests are shown from 10 on.",
    sc_dm: "Diebold-Mariano test: is one forecast's average log score really higher than another's, or could the gap be chance? Newey-West errors allow for overlapping daily forecasts. A positive difference means the first one scored better; p below 0.05 means the gap is probably real.",
    sc_base: "The benchmark is deliberately simple: the power-law trend line fitted only on prices up to each forecast date, with a band of the same width at every horizon. A model is only useful if it beats this.",
    sc_bt_p: "Same tests on past data. These p-values are optimistic, because the model was designed after seeing that data (and v3's band widths were estimated from it). Treat them as a sanity check, not proof.",
    v3: "v3 is the same fan as v2 with narrower bands (rescaled from the fan's own past errors), frozen on 2026-10-25 and tested side by side with v2. It replaces v2 only if it wins on live data under a rule set in advance.",
    method: "The full technical details: data sources, formulas, how the score and the fan are built, and how they were tested."
  };
  const pop = document.createElement("div"); pop.id = "tipPop"; pop.setAttribute("role", "tooltip"); pop.hidden = true;
  let cur = null, pinned = false;
  function show(btn, pin) {
    const k = btn.dataset.k; if (!T[k]) return;
    if (!pop.isConnected) document.body.appendChild(pop);
    pop.textContent = T[k]; pop.hidden = false; cur = k; pinned = pin;
    const r = btn.getBoundingClientRect(), vw = document.documentElement.clientWidth, w = Math.min(300, vw - 16);
    pop.style.width = w + "px"; const left = Math.max(8, Math.min(r.left + r.width / 2 - w / 2, vw - w - 8));
    pop.style.left = left + "px"; const h = pop.offsetHeight; let top = r.bottom + 6; if (top + h > window.innerHeight - 8 && r.top - h - 6 > 8) top = r.top - h - 6;
    pop.style.top = top + "px";
    document.querySelectorAll(".info.on").forEach((b) => b.classList.remove("on")); btn.classList.add("on");
  }
  function hide() { pop.hidden = true; cur = null; pinned = false; document.querySelectorAll(".info.on").forEach((b) => b.classList.remove("on")); }
  document.addEventListener("click", (e) => {
    const b = e.target.closest && e.target.closest(".info");
    if (b) { e.preventDefault(); e.stopPropagation(); if (cur === b.dataset.k && pinned) hide(); else show(b, true); return; }
    if (!e.target.closest || !e.target.closest("#tipPop")) hide();
  }, true);
  const fine = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (fine) {
    document.addEventListener("mouseover", (e) => { const b = e.target.closest && e.target.closest(".info"); if (b && !pinned) show(b, false); });
    document.addEventListener("mouseout", (e) => { const b = e.target.closest && e.target.closest(".info"); if (b && !pinned && !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest(".info"))) hide(); });
  }
  window.addEventListener("scroll", () => { if (cur) hide(); }, { passive: true });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
  const i = (k) => `<button type="button" class="info" data-k="${k}" aria-label="What is this?">i</button>`;
  window.Explain = { i, T, hide };
})();
