/* Header navigation: plain links on desktop, a hamburger menu on narrow screens.
   Links to a collapsed <details> section open it before scrolling. Display only. */
(function () {
  "use strict";
  const btn = document.getElementById("navBtn"), nav = document.getElementById("siteNav");
  const setOpen = (o) => { if (!nav || !btn) return; nav.classList.toggle("open", o); btn.setAttribute("aria-expanded", o ? "true" : "false"); };
  if (btn) btn.addEventListener("click", (e) => { e.stopPropagation(); setOpen(!nav.classList.contains("open")); });
  document.addEventListener("click", (e) => { if (nav && nav.classList.contains("open") && !nav.contains(e.target)) setOpen(false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });
  const openTarget = (id) => {
    const el = id && document.getElementById(id); if (!el) return null;
    let d = el.tagName === "DETAILS" ? el : el.closest("details");
    while (d) { d.open = true; d = d.parentElement && d.parentElement.closest("details"); }
    return el;
  };
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest('a[href^="#"]'); if (!a) return;
    const id = a.getAttribute("href").slice(1), el = openTarget(a.dataset.open || id) || document.getElementById(id);
    setOpen(false);
    if (el) { e.preventDefault(); el.scrollIntoView({ behavior: "smooth", block: "start" }); history.replaceState(null, "", "#" + id); }
  });
  const fromHash = () => { const id = location.hash.slice(1); if (id && openTarget(id)) document.getElementById(id).scrollIntoView({ block: "start" }); };
  window.addEventListener("hashchange", fromHash);
  if (location.hash) window.addEventListener("load", () => setTimeout(fromHash, 50));
})();
