# -*- coding: utf-8 -*-
"""Sheet 3 of daily_report_v3: the C4M over-speed report (../overspeed/overspeed_report.html).

The over-speed page is a separate snapshot (~10 MB of GPS-derived events refreshed by its own
fetch job), so it is NOT baked into the daily report. The sheet is an <iframe> that loads
`overspeed_report.html?embed=1&theme=light` from the same folder the first time the tab is
opened. Deploy both files side by side (locally in daily_report/ next to this build, on the
server in /opt/R4M/storage/www/r4m_custom_report/); refreshing the over-speed data = overwrite
overspeed_report.html only.

Exports: OS_CSS, OS_TAB_HTML (the extra tab button), OS_HTML (the panel), OS_JS (IIFE 4).
build_combined.py also patches the 3D viewer's setSheet() so it knows about this sheet.
"""

OS_FILE = "overspeed_report.html"

OS_CSS = r"""
/* ================= OVER-SPEED sheet (iframe to overspeed_report.html) ================= */
body.sheet-overspeed .sheet, body.sheet-overspeed nav.toc, body.sheet-overspeed #loadOverlay{display:none !important}
body.sheet-overspeed #tip{display:none !important}
#osheet{display:flex;flex-direction:column;height:calc(100vh - 44px);background:var(--color-bg-dashboard)}
#osheet[hidden]{display:none}
#osheet iframe{flex:1;width:100%;border:none;background:var(--color-bg-dashboard)}
#osheet .osbar{flex:none;display:flex;gap:14px;align-items:center;padding:5px 16px;font-size:11.5px;
  color:var(--color-text-secondary);border-bottom:1px solid var(--color-border-subtle);background:var(--color-bg-surface)}
#osheet .osbar a{color:var(--color-primary);margin-left:auto}
#osheet .osmsg{padding:40px 16px;text-align:center;color:var(--color-text-secondary);font-size:13px}
#osheet .osmsg code{font-size:12px}
@media print{#osheet{display:none !important}}
"""

OS_TAB_HTML = '  <button data-sheet="overspeed">Over-speed</button>\n'

OS_HTML = f"""<section id="osheet" class="noprint" hidden>
  <div class="osbar"><b>OVER-SPEED</b> <span>C4M GPS telemetry vs the mine limit (40 km/h, 30 km/h on steep roads) &middot; snapshot refreshed by its own job</span>
    <a href="{OS_FILE}" target="_blank" rel="noopener" id="osOpen">open full page &#8599;</a></div>
  <div class="osmsg" id="osMsg" hidden>The over-speed page could not be loaded. It must sit next to this file as <code>{OS_FILE}</code>
    (built by <code>overspeed/build_overspeed.py</code>).</div>
  <iframe id="osFrame" title="Over-speed report" loading="lazy"></iframe>
</section>
"""

OS_JS = r"""
/* ============================ OVER-SPEED sheet (IIFE 4) ============================ */
const OS_FILE_ = "__OS_FILE__";
// cache-bust with the server's own ETag / Last-Modified (one HEAD request): the snapshot is rebuilt nightly and on demand,
// and browsers otherwise keep a stale copy of a static file for hours
function osSrc(){
  return fetch(OS_FILE_, {method: "HEAD", cache: "no-store"})
    .then(r => (r.headers.get("etag") || r.headers.get("last-modified") || String(Date.now())).replace(/\W/g, ""))
    .catch(() => String(Math.floor(Date.now() / 6e5)))
    .then(v => OS_FILE_ + "?embed=1&theme=light&v=" + v);
}
let loaded = false;
function open(){
  if (loaded) return;
  loaded = true;
  const f = document.getElementById("osFrame"), m = document.getElementById("osMsg");
  let ok = false;
  f.addEventListener("load", () => {
    /* same-origin (http/https deploy): an error page has no #kpis; file:// is opaque -> trust it */
    try { ok = !f.contentDocument || !!f.contentDocument.querySelector("#kpis"); } catch (e) { ok = true; }
    if (!ok){ f.hidden = true; m.hidden = false; }
  });
  osSrc().then(src => { f.src = src; });
}
window.OSHEET = {open: open};
if (location.hash === "#overspeed" && window.DIG3D && window.DIG3D.setSheet) window.DIG3D.setSheet("overspeed");
"""
