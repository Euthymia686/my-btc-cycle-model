"""Headless check: no JS errors, feeds connect, values tick; screenshots of the page and of the hero charts.
Usage: python test_live.py [url]"""
import sys, json, time
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
import os; OUT = os.environ.get("OUT_DIR", "./")
JS = """() => ({...(window.__app.last||{}), ticks: window.__app.ticks, errors: window.__app.errors.slice(),
  status: document.getElementById('liveTxt').textContent, statusCls: document.getElementById('liveSt').className, score: document.getElementById('score').textContent,
  heroLine: document.getElementById('heroLine').textContent, heroAlt: (document.getElementById('heroAlt').textContent||'').slice(0,160),
  tilesPending: [...document.querySelectorAll('.tile .val.pending')].length,
  fwd: window.__app.fwd ? {n: window.__app.fwd.n, last: window.__app.fwd.last && window.__app.fwd.last.t} : null,
  feeds: (window.__app.feeds||[]).map(f => f.src.name + ' ' + f.status())})"""
with sync_playwright() as pw:
    _exe = os.environ.get("CHROME"); b = pw.chromium.launch(args=["--no-sandbox"], **({"executable_path": _exe} if _exe else {}))
    res = {}
    for name, vp in [("desktop", {"width": 1440, "height": 900}), ("mobile", {"width": 400, "height": 860})]:
        pg = b.new_page(viewport=vp, device_scale_factor=1 if name == "desktop" else 2)
        errs = []; pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: errs.append(str(e)))
        ws = []; pg.on("websocket", lambda w: ws.append(w.url))
        t0 = time.time(); pg.goto(URL, wait_until="load"); pg.wait_for_function("() => window.__app && window.__app.ticks > 0", timeout=30000)
        first = round(time.time() - t0, 2); samples = []
        for i in range(5 if name == "desktop" else 3):
            time.sleep(3); samples.append(pg.evaluate(JS))
        pg.screenshot(path=f"{OUT}preview_{name}.png", full_page=True)
        if name == "desktop":
            for sel, fn in [(".hero", "hero_live.png")]:
                el = pg.locator(sel).first
                (el.locator("xpath=..") if sel.startswith("#") else el).screenshot(path=OUT + fn)
        res[name] = {"console_errors": errs, "websockets": ws, "first_tick_s": first, "samples": samples}
    print(json.dumps(res, indent=1)); b.close()
