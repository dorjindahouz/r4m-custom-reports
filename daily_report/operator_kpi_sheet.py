# -*- coding: utf-8 -*-
"""Sheet 4 of daily_report_v3: the C4M operator KPI page (../operator_kpi/operator_kpi.html).

Like the over-speed sheet: a separate snapshot (checklists, haul cycles, status hours per operator,
refreshed nightly on the R4M VM by operator_kpi/server/refresh_operator_kpi.sh), NOT baked into the
daily report. The sheet is an <iframe> that loads `operator_kpi.html?embed=1&theme=light` from the
same folder the first time the tab is opened. Deploy both files side by side.

Exports: OK_CSS, OK_TAB_HTML (the extra tab button), OK_HTML (the panel), OK_JS (IIFE 5).
build_combined.py also patches the 3D viewer's setSheet() so it knows about this sheet.
"""

OK_FILE = "operator_kpi.html"

OK_CSS = r"""
/* ================= OPERATOR KPI sheet (iframe to operator_kpi.html) ================= */
body.sheet-opkpi .sheet, body.sheet-opkpi nav.toc, body.sheet-opkpi #loadOverlay{display:none !important}
body.sheet-opkpi #tip{display:none !important}
#oksheet{display:flex;flex-direction:column;height:calc(100vh - 44px);background:var(--color-bg-dashboard)}
#oksheet[hidden]{display:none}
#oksheet iframe{flex:1;width:100%;border:none;background:var(--color-bg-dashboard)}
#oksheet .osbar{flex:none;display:flex;gap:14px;align-items:center;padding:5px 16px;font-size:11.5px;
  color:var(--color-text-secondary);border-bottom:1px solid var(--color-border-subtle);background:var(--color-bg-surface)}
#oksheet .osbar a{color:var(--color-primary);margin-left:auto}
#oksheet .osmsg{padding:40px 16px;text-align:center;color:var(--color-text-secondary);font-size:13px}
#oksheet .osmsg code{font-size:12px}
@media print{#oksheet{display:none !important}}
"""

OK_TAB_HTML = '  <button data-sheet="opkpi">Operator KPI</button>\n'

OK_HTML = f"""<section id="oksheet" class="noprint" hidden>
  <div class="osbar"><b>OPERATOR KPI</b> <span>shift sheet with ranked operators, over-speed and the daily PDFs (shift KPIs, checklists) &middot; period overview and trends (C4M) &middot; refreshed nightly</span>
    <a href="{OK_FILE}" target="_blank" rel="noopener" id="okOpen">open full page &#8599;</a></div>
  <div class="osmsg" id="okMsg" hidden>The operator KPI page could not be loaded. It must sit next to this file as <code>{OK_FILE}</code>
    (built by <code>operator_kpi/build_operator_kpi.py</code>).</div>
  <iframe id="okFrame" title="Operator KPI" loading="lazy"></iframe>
</section>
"""

OK_JS = r"""
/* ============================ OPERATOR KPI sheet (IIFE 5) ============================ */
const OK_FILE_ = "__OK_FILE__";
// cache-bust with the server's own ETag / Last-Modified (one HEAD request): the snapshot is rebuilt nightly and on demand,
// and browsers otherwise keep a stale copy of a static file for hours
function okSrc(){
  return fetch(OK_FILE_, {method: "HEAD", cache: "no-store"})
    .then(r => (r.headers.get("etag") || r.headers.get("last-modified") || String(Date.now())).replace(/\W/g, ""))
    .catch(() => String(Math.floor(Date.now() / 6e5)))
    .then(v => OK_FILE_ + "?embed=1&theme=light&v=" + v);
}
let loaded = false;
function open(){
  if (loaded) return;
  loaded = true;
  const f = document.getElementById("okFrame"), m = document.getElementById("okMsg");
  let ok = false;
  f.addEventListener("load", () => {
    try { ok = !f.contentDocument || !!f.contentDocument.querySelector("#kpis"); } catch (e) { ok = true; }
    if (!ok){ f.hidden = true; m.hidden = false; }
  });
  okSrc().then(src => { f.src = src; });
}
window.OKSHEET = {open: open};
if (location.hash === "#opkpi" && window.DIG3D && window.DIG3D.setSheet) window.DIG3D.setSheet("opkpi");
"""
