"""Build THE page: daily production report + mine atlas combined, skinned with
the R4M Aurora design schema (r4m-design-schema.css), light theme.

Assembled at build time from the two source templates (build_report.TEMPLATE and
atlas_template.TEMPLATE) so future edits to either keep flowing into the page:
  - one <style>: schema (verbatim) + report css + atlas css + token override layer
  - one body: masthead -> sticky toc -> report sections -> atlas sections -> inputs -> footer
  - scripts: report JS and atlas JS each wrapped in an IIFE (kills const
    collisions); header button exports the report half as PDF via window.print().

The output is deliberately one self-contained file (~2.3 MB): the contour-map
PNG (~900 KB), the vendored parquet/ZSTD decoder (~160 KB) and the embedded
Rubik font (~48 KB) are inlined so the page needs zero external requests.

Run:  python build_combined.py [--fetch]     ->  daily_report.html
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys

from customize_template import CUSTOM_JS
from xlsx_template import XLSX_JS
from build_report import (TEMPLATE as REPORT_TEMPLATE, LOGO_B64, load_joined, build_cube, apply_published,
                          build_rom, build_romcls, build_romout, build_exh, read_inputs, HERE)
import build_atlas
from atlas_template import TEMPLATE as ATLAS_TEMPLATE
from dig3d_template import DIG3D_CSS, SHEETTABS_HTML, DIG3D_HTML, DIG3D_JS
from overspeed_sheet import OS_CSS, OS_TAB_HTML, OS_HTML, OS_JS, OS_FILE
from operator_kpi_sheet import OK_CSS, OK_TAB_HTML, OK_HTML, OK_JS, OK_FILE
from master_template import MR_TAB_HTML

ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "daily_report_v3.html")   # the latest deliverable (v2 = the 2026-08-26 build, kept as-is)
SCHEMA_CSS = open(os.path.join(ROOT, "r4m-design-schema.css"), encoding="utf-8").read()
RUBIK_CSS = open(os.path.join(HERE, "vendor_rubik.css"), encoding="utf-8").read()
_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;700&display=swap');"
assert SCHEMA_CSS.count(_IMPORT) == 1, "Rubik @import not found in schema css"
SCHEMA_CSS = SCHEMA_CSS.replace(_IMPORT, RUBIK_CSS)
VENDOR_JS = open(os.path.join(HERE, "vendor_hyparquet.min.js"), encoding="utf-8").read()
THREE_JS = open(os.path.join(HERE, "vendor_three.min.js"), encoding="utf-8").read()   # three.js r170 + OrbitControls, global THREE3D


def _cut(s, a, b, incl_a=False, incl_b=False):
    i = s.index(a)
    j = s.index(b, i + len(a))
    start = i if incl_a else i + len(a)
    end = j + len(b) if incl_b else j
    return s[start:end]


def _rep(s, old, new, cnt=1, tag=""):
    assert s.count(old) == cnt, f"[{tag}] pattern x{s.count(old)} (want {cnt}): {old[:80]!r}"
    return s.replace(old, new)


# ---------------------------------------------------------------- CSS layers
OVERRIDE_CSS = r"""
/* ================= R4M Aurora skin override layer ================= */
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,Cantarell,
     "Fira Sans","Droid Sans","Helvetica Neue",sans-serif;
     background:var(--color-bg-dashboard);color:var(--color-text-primary)}
.sheet{background:var(--color-bg-surface);border:1px solid var(--color-border-subtle);
       box-shadow:var(--shadow-md)}
.titleblock{background:var(--color-bg-surface);color:var(--color-text-primary);
            border-bottom:3px solid var(--color-primary);border-radius:6px 6px 0 0}
.titleblock h1{font-family:"Rubik",-apple-system,BlinkMacSystemFont,sans-serif;
               color:var(--color-text-primary);letter-spacing:.4px}
.titleblock .sub{color:var(--color-primary);letter-spacing:2px}
.meta{color:var(--color-text-secondary)}
.period{color:var(--color-text-secondary)}
.period select{border:1px solid var(--color-primary);background:var(--color-bg-surface);
               color:var(--color-text-primary);border-radius:4px}
.themebtn{font:inherit;font-size:12.5px;font-weight:700;margin-top:10px;cursor:pointer;
          padding:7px 16px;border-radius:6px;border:1px solid var(--color-primary);
          background:var(--color-primary);color:var(--color-text-on-primary)}
.themebtn:hover{background:var(--color-primary-hover)}
nav.toc{background:var(--color-bg-surface);border-bottom:2px solid var(--color-primary)}
nav.toc a{color:var(--color-text-secondary)}
nav.toc a:hover{background:var(--state-hover-blue);color:var(--color-text-primary)}
nav.toc a.on{background:var(--color-primary);color:var(--color-text-on-primary)}
body{counter-reset:sec}
.banner{background:#1B7F8F;color:#fff;
        font-family:"Rubik",-apple-system,sans-serif;letter-spacing:1.4px;
        border:none;border-left:5px solid #103644;
        box-shadow:var(--shadow-sm)}
.banner::before{content:counter(sec,decimal-leading-zero) "  \00b7  ";
                color:rgba(255,255,255,.75);letter-spacing:2px}
.kpis .kpi{background:var(--color-bg-metrics);border:1px solid var(--color-border-subtle);
     border-left:4px solid var(--color-primary);box-shadow:var(--shadow-sm)}
.kpi .k{color:var(--color-text-secondary)}
.kpi .v{color:var(--color-text-kpi);font-family:"Rubik",-apple-system,sans-serif}
.kpi .s{color:var(--color-text-secondary)}
.kpi .s b.up{color:var(--color-success);background:color-mix(in srgb,var(--color-success) 14%,transparent)}
.kpi .s b.dn{color:var(--color-error);background:color-mix(in srgb,var(--color-error) 12%,transparent)}
.kpi svg.spark polyline{stroke:var(--color-primary)}
table.rep th,table.rep td{border-color:var(--color-border-strong);color:var(--color-text-primary)}
table.rep thead th{background:var(--color-primary-light);color:#05498c}
table.rep thead th.mon{background:var(--color-bg-selected);color:var(--color-text-primary)}
table.rep td.num.vpos{color:var(--color-success)} table.rep td.num.vneg{color:var(--color-error)}
table.x th,table.x td{border-color:var(--color-border-medium);color:var(--color-text-primary)}
table.x th{background:var(--color-primary-light);color:#05498c}
table.x tr:hover td{background:var(--state-hover-bg)}
table.x tr.sel td{background:var(--state-selected)}
.chart{background:var(--color-bg-surface);border:1px solid var(--color-border-subtle);
       box-shadow:var(--shadow-sm)}
.chart h4{color:var(--color-text-primary)}
.chart h4::after{background:var(--color-primary)}
.clegend{color:var(--color-text-secondary)}
.clegend i.dash{border-top-color:var(--color-text-primary)}
.chart svg text{fill:var(--color-text-secondary)}
.chart svg text[stroke]{stroke:var(--color-bg-surface);fill:var(--color-text-primary)}
.note,.hint,.tablectl,.maplegend{color:var(--color-text-secondary)}
.controls{background:var(--color-bg-surface-secondary);border-color:var(--color-border-subtle);
          color:var(--color-text-primary)}
.controls button,.btnrow button{background:var(--color-bg-surface);color:var(--color-text-primary);
          border:1px solid var(--color-border-strong);border-radius:4px}
.controls button:hover,.btnrow button:hover{background:var(--state-hover-bg)}
.controls select,.controls input[type=date]{background:var(--color-bg-surface);color:var(--color-text-primary);
                 border:1px solid var(--color-border-strong)}
details.inputs{background:var(--color-bg-surface-secondary);border-color:var(--color-border-subtle)}
details.inputs>summary{background:var(--color-bg-metrics);color:var(--color-text-primary)}
.inputs-body h3{color:var(--color-text-primary)}
table.edit th,table.edit td{border-color:var(--color-border-medium)}
table.edit thead th{background:var(--color-primary-light);color:#05498c}
table.edit td.lbl{background:var(--color-bg-surface);color:var(--color-text-primary)}
table.edit input{color:var(--color-text-primary)}
table.edit input:focus{outline:2px solid var(--color-primary);background:var(--color-primary-lighter)}
#mapwrap,#invwrap{background:var(--color-bg-surface-tertiary);border-color:var(--color-border-strong)}
#selchip{background:var(--color-bg-surface);color:var(--color-text-primary);
         border-color:var(--color-border-strong);box-shadow:var(--shadow-md)}
#sankeywrap{background:var(--color-bg-surface);border-color:var(--color-border-subtle)}
#sankeywrap svg text,#invmap text{fill:var(--color-text-secondary)}
#invmap text[stroke],#sankeywrap svg text[stroke]{stroke:var(--color-bg-surface);
         fill:var(--color-text-primary)}
.dbar{background:var(--color-bg-metrics)}
.hbars .lbl{color:var(--color-text-primary)}
.split .chart h4{color:var(--color-text-primary)}
[data-theme="dark"] #gContour{opacity:.55}
.loadoverlay{position:fixed;inset:0;z-index:100;display:flex;flex-direction:column;gap:14px;
  align-items:center;justify-content:center;font-size:14px;color:var(--color-text-primary);
  background:color-mix(in srgb,var(--color-bg-dashboard) 78%,transparent);backdrop-filter:blur(2px)}
.loadoverlay .spin{width:36px;height:36px;border:4px solid var(--color-primary-light);
  border-top-color:var(--color-primary);border-radius:50%;animation:r4mspin .8s linear infinite}
@keyframes r4mspin{to{transform:rotate(360deg)}}
.livechip{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:10px;
  font-weight:700;font-size:11px;background:var(--badge-bg);border:1px solid var(--badge-border);
  color:var(--badge-text)}
.livechip.ok::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--color-success)}
.livechip.err{background:color-mix(in srgb,var(--color-error) 10%,transparent);
  border-color:var(--color-error);color:var(--color-error)}
.livechip button{font:inherit;border:none;background:var(--color-primary);color:#fff;
  border-radius:4px;padding:1px 9px;cursor:pointer;margin-left:4px}
.snapchip{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.6px;
  color:var(--color-text-tertiary);border:1px solid var(--color-border-medium);
  border-radius:9px;padding:1px 9px;margin:8px 0 0}
@media print{.loadoverlay,.livechip,.snapchip{display:none !important}}
[data-theme="dark"] .sheet{box-shadow:0 2px 14px #00000066}
@media print{
  .atlaspart,nav.toc,.themebtn{display:none !important}
  body{background:#fff}
  .sheet{border:none;box-shadow:none}
  .titleblock{background:#fff;color:#111}
  .kpis .kpi{background:#fff;border:1px solid #999}
  .kpi .v{color:#111}
  .banner{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
"""

LIVE_JS = r"""
<script>
"use strict";
/* ---- R4M live data loader: fetches the documented parquet exports plus
   the R4M app's polygon-grades endpoint and rebuilds CUBE / ROM / EXH
   client-side (same joins & rounding as the build-time python).
   Origin-relative, credentials included. Nothing but r4m.example.local is
   ever contacted.

   AUTENTICACIÓN (desde ~2026-09 R4M exige sesión en /cube, /duckdb, /dimensions):
   - Cookie r4m_session (la envía el navegador: credentials "include") MÁS
     una prueba DPoP por petición (RFC 9449), firmada con la clave ECDSA P-256
     que la app R4M Aurora guarda en IndexedDB (r4m_crypto_db / keys /
     session_keypair) - misma clave, cabecera y claims que el fetch de Aurora.
     Funciona porque la página se sirve desde el mismo origen que R4M. Sin
     clave (p.ej. serve_local.py) no se firma y firma el proxy.
   - Un 401/403 muestra el chip "sesión expirada" con botón Reintentar.

   AUTHENTICATION (since ~2026-09 R4M requires a session on /cube, /duckdb,
   /dimensions):
   - the r4m_session cookie (sent by the browser: credentials "include") PLUS
     a per-request DPoP proof (RFC 9449) signed with the ECDSA P-256 key the
     R4M Aurora app keeps in IndexedDB (r4m_crypto_db / keys / session_keypair)
     - the same key, header and claims Aurora's own fetch wrapper uses. This
     works because the page is served from R4M's origin. No key (e.g. on
     serve_local.py) -> no proof; the local proxy signs instead.
   - A 401/403 renders the session-expired chip with a Retry button. ---- */
window.R4M_LIVE = (function(){
  const API = "/cube/dynamic/api/export";
  /* R4M app endpoint behind its "Grades / Leyes" report: per hauling cycle, the
     source polygon's registered grades {au, ag} (BOTH metals - the cube's
     polygon_grades export carries only one grade per polygon) + block-model
     grades (unused). Query: startDate/endDate (YYYY-MM-DD, inclusive). */
  const GRADES_API = "/duckdb/sensor/getGradeBlockAndPolygonData/";
  const DATA_START_YEAR = 2026;   /* API ref section 2: year < 2026 -> 404 */
  const EXCLUDE_EQ = new Set(["EX127"]);   /* deleted test units, keep in sync with build_report.EXCLUDE_EQUIP */

  function err(msg, kind){
    const e = new Error(msg);
    if (kind === "auth"){ e.auth = true; dpopKey = null; }   /* re-read the key on Retry (new login = new key) */
    return e;
  }

  /* ---- DPoP (see AUTHENTICATION above). Opens Aurora's key store read-only
     and never creates it: an upgrade here would leave Aurora a v1 database
     without its "keys" store. */
  let dpopKey = null;
  function loadDpopKey(){
    if (dpopKey) return dpopKey;
    dpopKey = new Promise(res => {
      try {
        if (!window.indexedDB) return res(null);
        const rq = indexedDB.open("r4m_crypto_db");
        rq.onupgradeneeded = () => { try { rq.transaction.abort(); } catch (e) {} };
        rq.onerror = rq.onblocked = () => res(null);
        rq.onsuccess = () => {
          const db = rq.result;
          if (!db.objectStoreNames.contains("keys")){ db.close(); return res(null); }
          const g = db.transaction("keys", "readonly").objectStore("keys").get("session_keypair");
          g.onsuccess = () => { db.close(); const k = g.result; res(k && k.privateKey && k.publicKey ? k : null); };
          g.onerror = () => { db.close(); res(null); };
        };
      } catch (e) { res(null); }
    });
    return dpopKey;
  }
  const b64u = buf => {
    let s = "";
    for (const b of new Uint8Array(buf)) s += String.fromCharCode(b);
    return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  };
  const b64uJson = o => b64u(new TextEncoder().encode(JSON.stringify(o)));
  const uuid = () => crypto.randomUUID ? crypto.randomUUID()
    : [...crypto.getRandomValues(new Uint8Array(16))].map(b => b.toString(16).padStart(2, "0")).join("");
  async function dpopProof(method, url){
    const k = await loadDpopKey();
    if (!k || !window.crypto || !crypto.subtle) return null;
    try {
      const {crv, kty, x, y} = await crypto.subtle.exportKey("jwk", k.publicKey);
      const head = {typ: "dpop+jwt", alg: "ES256", jwk: {crv, kty, x, y}};
      const claims = {jti: uuid(), htm: method, htu: new URL(url, location.origin).href,
                      iat: Math.floor(Date.now() / 1000)};
      const si = b64uJson(head) + "." + b64uJson(claims);
      const sig = await crypto.subtle.sign({name: "ECDSA", hash: {name: "SHA-256"}},
                                           k.privateKey, new TextEncoder().encode(si));
      return si + "." + b64u(sig);
    } catch (e) { return null; }
  }
  /* every R4M GET goes through here: cookie + DPoP (+ bearer if a host sets one) */
  async function r4mFetch(url, headers){
    const h = {...(headers || {})};
    if (window.R4M_TOKEN) h["Authorization"] = "Bearer " + window.R4M_TOKEN;
    const proof = await dpopProof("GET", url);
    if (proof) h["DPoP"] = proof;
    return fetch(url, {credentials: "include", headers: h});
  }

  async function fetchParquet(name, type, params){
    const q = new URLSearchParams({type, name, format: "parquet", ...(params || {})});
    let resp;
    try {
      resp = await r4mFetch(`${API}?${q}`);
    } catch (e) {
      throw err(`network error fetching ${name}`);
    }
    if (resp.status === 401 || resp.status === 403)
      throw err(`${resp.status} on ${name}`, "auth");
    if (resp.status === 404) { const e = err(`404 on ${name}`); e.notFound = true; throw e; }
    if (!resp.ok) throw err(`HTTP ${resp.status} on ${name}`);
    const buf = await resp.arrayBuffer();
    const magic = new Uint8Array(buf, 0, 4);
    if (String.fromCharCode(...magic) !== "PAR1")
      throw err(`${name}: response is not parquet`);
    return HYP.parquetReadObjects({file: buf, compressors: HYP.compressors});
  }

  async function fetchYearScopedEx(name, type, params){
    const y = new Date().getFullYear();
    try {
      return {rows: await fetchParquet(name, type, {...params, year: y}), year: y};
    } catch (e) {
      if (e.notFound && y - 1 >= DATA_START_YEAR)
        return {rows: await fetchParquet(name, type, {...params, year: y - 1}), year: y - 1};
      throw e;
    }
  }
  const fetchYearScoped = (name, type, params) => fetchYearScopedEx(name, type, params).then(r => r.rows);

  /* dimension tables are small and shared by the report and the 3D viewer: fetch once */
  const dimCache = new Map();
  function fetchDim(name){
    if (!dimCache.has(name)) dimCache.set(name, fetchParquet(name, "dimensions").catch(e => { dimCache.delete(name); throw e; }));
    return dimCache.get(name);
  }

  /* sensor_data rows -> Map cid -> {pts: [[x,y,z], ...] bucket passes (x100 in the cube) clipped to
     the mine window, eq: [x,y] loading unit's own GPS position (metres) | null, dump: [x,y] truck dump
     position | null}. The loaders (LO214/LO215) log no bucket passes (null x/y/z), only eq.
     Parsed once, the JSON strings dropped. */
  function parseSensor(rows){
    const m = new Map();
    for (const r of rows){
      let pts = [];
      const s = r["Loading Bucket Coors"];
      if (s){
        try { for (const p of JSON.parse(s)) if (p && p.x != null && p.y != null && p.z != null) pts.push([p.x / 100, p.y / 100, p.z / 100]); }
        catch (e) { /* malformed - fall back below */ }
      }
      if (!pts.length && r["Loading Bucket X Coordinate"] > 1000 && r["Loading Bucket Y Coordinate"] > 1000 && r["Loading Bucket Z Coordinate"] != null)
        pts.push([r["Loading Bucket X Coordinate"], r["Loading Bucket Y Coordinate"], r["Loading Bucket Z Coordinate"]]);
      pts = pts.filter(p => p[0] >= 482300 && p[0] <= 485500 && p[1] >= 4859400 && p[1] <= 4863600 && p[2] >= 1100 && p[2] <= 1400);
      const dx = r["Hauling Coor X at Dump"], dy = r["Hauling Coor Y at Dump"];
      const dump = (dx > 100000 && dy > 100000) ? [dx / 100, dy / 100] : null;
      const ex = r["Loading Equipment X Coordinate"], ey = r["Loading Equipment Y Coordinate"];
      const eq = (ex >= 482300 && ex <= 485500 && ey >= 4859400 && ey <= 4863600) ? [ex, ey] : null;
      if (pts.length || dump || eq) m.set(r["C4M ID Hauling"], {pts, eq, dump});
    }
    return m;
  }

  /* per-cycle rows for the 3D viewer and the ROM pad stockpile map: one download per page load */
  let cycleMemo = null;
  function cycleRows(){
    if (!cycleMemo) cycleMemo = (async () => {
      const geoP = fetchPolygonGeometry(new Date().getFullYear()).then(g => ({geo: g})).catch(e => ({geo: null, err: e}));
      const [prodR, sensR, poly, equip, mat, dump, lload, G] = await Promise.all([
        fetchYearScopedEx("production", "facts", {month: "all"}),
        fetchYearScopedEx("sensor_data", "facts", {month: "all"}),
        fetchDim("polygon"), fetchDim("equipment"), fetchDim("material").catch(() => []),
        fetchYearScoped("location_dump", "dimensions").catch(() => []),
        fetchYearScoped("location_load", "dimensions").catch(() => []),
        geoP]);
      return {year: prodR.year, prod: prodR.rows, coors: parseSensor(sensR.rows), poly, equip, mat, dump, lload,
              geo: G.geo, geoErr: G.err || null};
    })().catch(e => { cycleMemo = null; throw e; });   /* a retry after an auth/network failure refetches */
    return cycleMemo;
  }

  /* generic JSON GET with the same auth/network contract as the parquet export */
  async function fetchJson(url, label){
    let resp;
    try { resp = await r4mFetch(url, {"Accept": "application/json"}); }
    catch (e) { throw err(`network error fetching ${label}`); }
    if (resp.status === 401 || resp.status === 403) throw err(`${resp.status} on ${label}`, "auth");
    if (!resp.ok) throw err(`HTTP ${resp.status} on ${label}`);
    return resp.json();
  }

  /* ---- polygon BOUNDARIES: R4M's HPGPS backend (the endpoints behind the embedded
     /fronts/r4m_hpgps/ and /fronts/r4m_adherence… apps; the Aurora SPA itself never
     calls them). Rings arrive as WGS84 [lat, lon]; "id" == cube "Id Polygon". ---- */
  const POLY_API = "/dimensions/polygon/getAllPolygonData/";              /* currently OPEN polygons */
  const POLY_HIST_API = "/dimensions/polygon/getAllPolygonDataByDate/";   /* CLOSED in ?dateIni&dateFin */
  const UTM_ZONE = 47;   /* R4M MAP_CONFIG zone 47T - the mine grid every other coordinate uses */
  function llToUtm(lat, lon){
    const a = 6378137, f = 1 / 298.257223563, k0 = 0.9996, e2 = f * (2 - f), ep2 = e2 / (1 - e2);
    const lon0 = ((UTM_ZONE - 1) * 6 - 180 + 3) * Math.PI / 180;
    const phi = lat * Math.PI / 180, lam = lon * Math.PI / 180 - lon0;
    const sp = Math.sin(phi), cp = Math.cos(phi);
    const N = a / Math.sqrt(1 - e2 * sp * sp), T = (sp / cp) ** 2, C = ep2 * cp * cp, A = cp * lam;
    const M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi
                   - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * Math.sin(2 * phi)
                   + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * Math.sin(4 * phi)
                   - (35 * e2 ** 3 / 3072) * Math.sin(6 * phi));
    const E = 500000 + k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T * T + 72 * C - 58 * ep2) * A ** 5 / 120);
    const Nn = k0 * (M + N * (sp / cp) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * A ** 4 / 24
                                          + (61 - 58 * T + T * T + 600 * C - 330 * ep2) * A ** 6 / 720));
    return [E, Nn];
  }
  /* open register + everything closed since Jan 1 of the previous calendar year
     (a window with no closures is simply empty); open wins when an id is in both */
  async function fetchPolygonGeometry(year){
    const until = isoDate(new Date(Date.now() + 86400000));
    const [open, closed] = await Promise.all([
      fetchJson(POLY_API, "polygon boundaries"),
      fetchJson(`${POLY_HIST_API}?dateIni=${year - 1}-01-01&dateFin=${until}`, "closed polygon boundaries"),
    ]);
    const map = new Map();
    const add = (rows, status) => {
      for (const p of (Array.isArray(rows) ? rows : [])){
        const id = +p.id;
        if (!isFinite(id) || map.has(id)) continue;
        const ring = (p.coors || []).filter(c => Array.isArray(c) && isFinite(c[0]) && isFinite(c[1])).map(c => llToUtm(+c[0], +c[1]));
        map.set(id, {name: String(p.name || ""), bench: (p.nivel === null || p.nivel === undefined) ? null : +p.nivel,
                     ring, status, mined: +p.actualmined || 0, color: String(p.color || "")});
      }
    };
    add(open, "open"); add(closed, "closed");
    return {map, open: Array.isArray(open) ? open.length : 0, closed: Array.isArray(closed) ? closed.length : 0};
  }

  const pad2 = n => String(n).padStart(2, "0");
  const isoDate = d => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;

  async function fetchGradesRange(start, end){
    let resp;
    try {
      resp = await r4mFetch(`${GRADES_API}?startDate=${start}&endDate=${end}`, {"Accept": "application/json"});
    } catch (e) {
      throw err(`network error fetching grades ${start}..${end}`);
    }
    if (resp.status === 401 || resp.status === 403)
      throw err(`${resp.status} on grades ${start}..${end}`, "auth");
    if (!resp.ok) throw err(`HTTP ${resp.status} on grades ${start}..${end}`);
    const data = await resp.json();
    return (data && Array.isArray(data.polygon)) ? data.polygon : [];
  }

  /* polygon grades for the whole mine year: one request per calendar month
     (Jan 1 .. tomorrow), in parallel, gzip on the wire. Grades are constant
     per Id Polygon, so the result is a per-polygon map. */
  async function loadPolygonGrades(year){
    const until = new Date(Date.now() + 86400000);
    const months = [];
    for (let m = 0; m < 12; m++){
      const s = new Date(year, m, 1);
      if (s > until) break;
      let e = new Date(year, m + 1, 0);
      if (e > until) e = until;
      months.push([isoDate(s), isoDate(e)]);
    }
    const parts = await Promise.all(months.map(([s, e]) => fetchGradesRange(s, e)));
    const map = new Map();
    let cycles = 0;
    for (const rows of parts) for (const r of rows){
      cycles++;
      const pid = r["Id Polygon"], g = r.grades || {};
      if (pid === null || pid === undefined) continue;
      const cur = map.get(pid) || {};
      if (cur.au == null && g.au != null) cur.au = g.au;
      if (cur.ag == null && g.ag != null) cur.ag = g.ag;
      map.set(pid, cur);
    }
    return {map, cycles, months: months.length};
  }

  const r2 = v => Math.round(v * 100) / 100;
  const r1 = v => Math.round(v * 10) / 10;

  async function load(lcm){
    const prodP = fetchYearScopedEx("production", "facts", {month: "all"});
    /* grades cover the same mine year as production; failure degrades to the
       cube's polygon_grades (Ag only) and is flagged on the status chip */
    let gradesErr = null;
    const r4mP = prodP.then(p => loadPolygonGrades(p.year))
                      .catch(e => { gradesErr = e; console.warn("R4M grades endpoint unavailable - cube polygon_grades only:", e); return null; });
    const [prodR, mat, dump, grades, equip, r4m, polyDim, load] = await Promise.all([
      prodP,
      fetchDim("material"),
      fetchYearScoped("location_dump", "dimensions"),
      fetchDim("polygon_grades"),
      fetchDim("equipment"),
      r4mP,
      fetchDim("polygon").catch(() => []),   /* names for the ungraded-polygon diagnostic only */
      fetchYearScoped("location_load", "dimensions"),   /* rehandle flag (mine production) + ROM reclaim */
    ]);
    const prod = prodR.rows;

    const codeOf = new Map(mat.map(r => [r["Id Material"], r["Material Code"]]));
    const dumpOf = new Map(dump.map(r => [r["Id Location Dump"],
      {name: String(r["Location Dump"] || ""), region: String(r["Region"] || "")}]));
    const loadOf = new Map((load || []).map(r => [r["Id Location Load"],
      {name: String(r["Location Load"] || ""), region: String(r["Region"] || ""), zone: String(r["Zone"] || "")}]));
    const REHANDLE_ZONES = new Set(["StockPile Zone", "Dumping Zone"]);   /* = build_report.REHANDLE_ZONES */
    const eqOf = new Map(equip.map(r => [r["Id Equipment"], String(r["Equipment"] || "")]));
    const gp = new Map();                       /* Id Polygon -> {au, ag} (max, TRIMmed names) */
    for (const r of grades){
      const nm = String(r["Polygon Grade Name"] || "").trim();
      const v = r["Polygon Grade Value"];
      if (v === null || v === undefined) continue;
      const g = gp.get(r["Id Polygon"]) || {};
      if (nm === "Gold grade") g.au = Math.max(g.au ?? -Infinity, v);
      if (nm === "Silver grade") g.ag = Math.max(g.ag ?? -Infinity, v);
      gp.set(r["Id Polygon"], g);
    }
    /* overlay the R4M app's polygon grades (both metals) - they win; the cube
       export only fills Ag for polygons the endpoint never lists */
    if (r4m){
      for (const [pid, g] of r4m.map){
        const cur = gp.get(pid) || {};
        if (g.au != null) cur.au = g.au;
        if (g.ag != null) cur.ag = g.ag;
        gp.set(pid, cur);
      }
    }

    const SHIFT = {A: "DS", B: "NS"};
    const dens = c => { const l = (lcm || {})[c]; return l && l.density > 0 ? l.density : 2.64; };
    const cube = {}, rom = {}, exh = {}, romcls = {}, romout = {};
    let rows = 0, sumT = 0, sumTau = 0, sumTag = 0;
    /* ore polygons hauled without ANY registered Au: the polygon was uploaded
       to R4M/GI with empty grades - a registration gap, not a source gap */
    const ORE_CODES = new Set(["HG", "MG", "LG1", "LG2", "SG"]);
    const ungraded = new Map();

    for (const r of prod){
      if (r["It is reportable for production"] !== true) continue;
      rows++;
      const date = String(r["Date Cube Hauling"]).slice(0, 10);
      const shift = SHIFT[r["Hauling Shift"]] || String(r["Hauling Shift"]);
      const code = codeOf.get(r["Id Material"]) || "?";
      const t = r["Dry Tonnes"] || 0;
      const g = gp.get(r["Id Polygon"]);
      const au = t * ((g && g.au != null) ? g.au : 0);
      const ag = t * ((g && g.ag != null) ? g.ag : 0);
      const d = dumpOf.get(r["Id Location Dump"]) || {name: "", region: ""};
      const isCrush = /crush|үйлдвэр/i.test(d.name) && !/^dump/i.test(d.name);   /* "Crusher" to 2026-08-25, "Үйлдвэр" (plant) since; "dump_crushed" is not the pad; = build_report.MILL_FEED_RE */
      const isIwf = d.region === "IWF";
      const isRom = d.region === "ROM Pad";
      const lo = loadOf.get(r["Id Location Load"]);
      /* loaded off a stockpile/dump, or a crusher delivery not loaded in the pit = build_report is_reh */
      const isReh = !!(lo && REHANDLE_ZONES.has(lo.zone)) || (isCrush && !(lo && lo.zone === "Loading Zone"));

      sumT += t;
      if (g && g.au != null) sumTau += t;
      if (g && g.ag != null) sumTag += t;
      if (ORE_CODES.has(code) && !(g && g.au != null)){
        const u = ungraded.get(r["Id Polygon"]) || {t: 0, code};
        u.t += t; ungraded.set(r["Id Polygon"], u);
      }

      const slot = ((cube[date] = cube[date] || {})[shift] =
                    cube[date][shift] || {})[code] =
                    cube[date][shift][code] || [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
      slot[0] += t; slot[1] += au; slot[2] += ag;
      if (isCrush){ slot[3] += t; slot[4] += au; slot[5] += ag;
                    if (g && g.au != null) slot[10] += t;     /* crusher t with an Au grade registered */
                    if (g && g.ag != null) slot[11] += t; }
      if (isIwf) slot[6] += t;
      if (isReh){ slot[7] += t; slot[8] += au; slot[9] += ag; }

      if (isRom){
        const pr = ((rom[d.name] = rom[d.name] || {})[date] =
                    rom[d.name][date] || [0, 0, 0]);
        pr[0] += t; pr[1] += au; pr[2] += ag;
        const rc = (romcls[d.name] = romcls[d.name] || {});
        rc[code] = (rc[code] || 0) + t;
      }
      if (lo && lo.region === "ROM Pad" && t > 0){     /* reclaim out of a ROM-pad location */
        const po = (romout[lo.name] = romout[lo.name] || {});
        po[date] = (po[date] || 0) + t;
      }

      const eq = eqOf.get(r["Id Equipment Loading"]);
      if (eq && eq.toUpperCase().startsWith("EX") && !EXCLUDE_EQ.has(eq)){
        const h = Number(r["Hauling Hour"]);
        if (h >= 0 && h <= 23){
          const arr = (((exh[eq] = exh[eq] || {})[date] =
                        exh[eq][date] || {})[shift] =
                        exh[eq][date][shift] || new Array(24).fill(0));
          arr[h] += t / dens(code);
        }
      }
    }
    /* final rounding, matching the build-time python */
    for (const d in cube) for (const s in cube[d]) for (const c in cube[d][s]){
      const v = cube[d][s][c];
      cube[d][s][c] = [r2(v[0]), r1(v[1]), r1(v[2]), r2(v[3]), r1(v[4]), r1(v[5]), r2(v[6]),
                       r2(v[7]), r1(v[8]), r1(v[9]), r2(v[10]), r2(v[11])];
    }
    for (const p in rom) for (const d in rom[p]){
      const v = rom[p][d];
      rom[p][d] = [r2(v[0]), r1(v[1]), r1(v[2])];
    }
    for (const p in romcls) for (const c in romcls[p]) romcls[p][c] = r1(romcls[p][c]);
    for (const p in romout) for (const d in romout[p]) romout[p][d] = r2(romout[p][d]);
    for (const e in exh) for (const d in exh[e]) for (const s in exh[e][d])
      exh[e][d][s] = exh[e][d][s].map(r1);

    const auCov = sumT ? sumTau / sumT * 100 : 0;
    const agCov = sumT ? sumTag / sumT * 100 : 0;
    const pnameOf = new Map((polyDim || []).map(r => [r["Id Polygon"], String(r["Polygon"] || "")]));
    const ungradedList = [...ungraded].map(([pid, u]) => [pnameOf.get(pid) || ("#" + pid), r1(u.t), u.code]).sort((a, b) => b[1] - a[1]);
    const ungradedT = ungradedList.reduce((s, x) => s + x[1], 0);

    const now = new Date();
    return {cube, rom, exh, romcls, romout, grades: gp,
            meta: {rows, auCov, agCov,
                   ungraded: {n: ungradedList.length, t: r1(ungradedT), top: ungradedList.slice(0, 10)},
                   gradesOk: !!r4m,
                   gradesCycles: r4m ? r4m.cycles : 0,
                   gradesAuth: !!(gradesErr && gradesErr.auth),
                   fetchedAt: now.toTimeString().slice(0, 5)}};
  }

  /* fetch helpers + exclusion list are shared with the 3D dig viewer (IIFE 3) */
  return {load, fetchParquet, fetchYearScopedEx, fetchDim, fetchJson, fetchPolygonGeometry, llToUtm, EXCLUDE_EQ, cycleRows, parseSensor};
})();
</script>
"""

BOOT_JS = r"""
const _lvSt = document.getElementById("liveStatus");
function _chip(cls, html){ if (_lvSt){ _lvSt.className = "livechip " + cls; _lvSt.innerHTML = html; } }
async function boot(){
  await fetchPublished();            /* the published plan, from next to the page */
  inputs = loadInputs();
  try {
    const live = await window.R4M_LIVE.load(inputs.lcm);
    CUBE = live.cube; ROM = live.rom; ROMCLS = live.romcls; ROMOUT = live.romout; EXH = live.exh;
    DATES = Object.keys(CUBE).sort();
    window.R4M_POLYGRADES = live.grades;      /* Id Polygon -> {au, ag}; read by the 3D viewer */
    window.R4M_LIVE_META = live.meta;
    const gchip = live.meta.gradesOk
      ? `polygon grades R4M &#10003;`
      : `<span style="color:var(--color-error)">&#9888; grades endpoint ${live.meta.gradesAuth ? "session expired" : "unavailable"} &mdash; cube Ag only</span>`;
    const ug = live.meta.ungraded;
    const ugchip = (ug && ug.n)
      ? ` &middot; <span style="color:#b26b00;cursor:help" title="${esc(ug.top.map(x => `${x[0]} (${x[2]}): ${Math.round(x[1]).toLocaleString("en-US")} t`).join("\n"))}">&#9888; ${ug.n} ore polygons hauled with no registered grade (${(ug.t / 1000).toFixed(1)} kt) &mdash; hover</span>`
      : "";
    _chip("ok", `LIVE &middot; fetched ${live.meta.fetchedAt} &middot; ${live.meta.rows.toLocaleString("en-US")} cycles &middot; ${gchip}${ugchip}`);
  } catch (e) {
    console.warn("R4M live fetch failed - showing baked snapshot:", e);
    const why = e && e.auth
      ? "session expired &mdash; sign in to R4M, then retry"
      : esc((e && e.message) || "network error");
    _chip("err", `&#9888; SNAPSHOT (built __BUILT_AT__) &mdash; live fetch failed: ${why} <button onclick="location.reload()">Retry</button>`);
  } finally {
    const ov = document.getElementById("loadOverlay");
    if (ov) ov.remove();
    init();
  }
}
boot();
"""

INTEGRATION_DOC_ES = """<!--
════════════════════════════════════════════════════════════════════════════════
  R4M AURORA — INFORME DIARIO DE OPERACIONES + ATLAS DE MINA (Bayankhundii)
  GUÍA DE INTEGRACIÓN PARA EL EQUIPO R4M
════════════════════════════════════════════════════════════════════════════════

QUÉ ES ESTE ARCHIVO
  Una sola página HTML totalmente autónoma: estilos (schema R4M Aurora), fuente
  Rubik, decodificador Parquet, mapa de contornos y un snapshot de datos van
  embebidos — por eso pesa ~2.8 MB. No carga NADA de internet ni de CDNs.

CÓMO INTEGRARLA
  1. Servir este archivo desde el MISMO ORIGEN que el cubo, es decir junto a
     /cube/dynamic/api/export  (las peticiones usan rutas RELATIVAS y
     credentials:"include" — no hay ningún hostname fijo en el código).
  2. Agregar un ítem de navegación que apunte a la página. Nada más: no
     necesita backend propio, base de datos ni proceso servidor.
  3. NO funciona abierta como file:// — sin origen no puede llamar al cubo y
     mostrará el snapshot horneado con un aviso.

AUTENTICACIÓN
  Hoy el cubo no exige autenticación en la red interna (ver referencia del API,
  sección 3). Cuando IT active el bearer token, la app anfitriona debe definir
     window.R4M_TOKEN = "<token>";
  ANTES de que corran los scripts de esta página; se envía como header
  "Authorization: Bearer". Un 401/403 muestra el chip "sesión expirada" con
  botón Reintentar (location.reload()).

COMPORTAMIENTO AL ABRIR
  - Descarga en paralelo 5 datasets parquet del cubo (production, material,
    location_dump, polygon_grades, equipment) y recalcula las secciones 01-03
    EN VIVO. Éxito -> chip verde "LIVE · fetched HH:MM · N cycles".
  - Además consulta el endpoint de LEYES de la propia app R4M Aurora (el que
    alimenta su reporte "Leyes / Grades"):
       GET /duckdb/sensor/getGradeBlockAndPolygonData/?startDate=&endDate=
       (prefijo en MINÚSCULAS: desde 2026-08-26 nginx ya no enruta /duckDB/)
    una petición por mes calendario del año minero, en paralelo (gzip). De
    ahí salen las leyes Au y Ag por polígono (AMBOS metales; el export
    polygon_grades del cubo solo trae una ley por polígono, casi siempre Ag,
    y queda como respaldo). Chip "· polygon grades R4M [check]". Si ese
    endpoint falla, el chip lo avisa y se usan solo las leyes del cubo.
  - ÚNICO ORIGEN DE DATOS: r4m.example.local. La página ya NO consulta el
    registro GI (gi.example.local); nada externo, ningún otro host.
  - Si la descarga falla (red, auth, file://), la página NUNCA queda en blanco:
    muestra el snapshot horneado en la compilación, con chip de aviso
    "SNAPSHOT (built __BUILT_AT__)".
  - Las secciones 06-13 (Atlas de Mina: sankey, polígonos, inventario,
    equipos, ciclos...) son SNAPSHOT de compilación (geometrías GPS, sankey,
    tiempos de equipos...). Se refrescan regenerando la página.
  - Pilas del ROM (tabla 02): R4M no tiene estado abierto/cerrado para
    acopios; la tabla lista solo las pilas con al menos un ciclo descargado en
    ellas o cargado desde ellas (Id Location Load en la región "ROM Pad") entre
    la fecha de inicio y la de fin del periodo seleccionado. El inventario del
    atlas (mapa de acopios) muestra exactamente la misma lista para el mismo
    periodo (window.RPT.romActive); las geometrías GPS son del snapshot.

GEOMETRÍA DE POLÍGONOS (backend HPGPS de R4M)
  - La página también consume los endpoints del backend HPGPS de R4M (los que
    usan los fronts embebidos /fronts/r4m_hpgps/ y /fronts/r4m_adherence*/;
    el SPA de Aurora no los llama):
       GET /dimensions/polygon/getAllPolygonData/               (polígonos ABIERTOS)
       GET /dimensions/polygon/getAllPolygonDataByDate/?dateIni=&dateFin=
                                                                 (polígonos CERRADOS en el rango)
       GET /dimensions/digline/getDigLineGlobal/                (líneas de excavación HPGPS)
    Devuelven anillos [lat, lon] WGS84 que la página convierte a UTM 47N;
    "id" == "Id Polygon" del cubo. Mismo contrato de auth y rutas relativas
    (el proxy/nginx debe exponer /dimensions/* junto a /cube/* y /duckdb/*).
  - El atlas dibuja los límites planificados horneados en el build diario
    (fetch_data.py -> data/r4m_polygons.json); el visor 3D los descarga EN VIVO
    al abrir la pestaña (abiertos + cerrados desde el 1 de enero, ~275 KB gzip)
    y clasifica cada pase del balde dentro/fuera del límite. Si el endpoint
    falla, el visor usa los anillos horneados y lo indica en su estado.

HOJA "3D DIG VIEWER" (pestaña aparte, arriba de la página)
  - La barra de pestañas conmuta entre "Daily Report & Mine Atlas" y el
    "3D Dig Viewer" (ancla #dig3d). El visor NO va en el PDF.
  - Al abrirla por primera vez descarga EN VIVO del cubo (mismas rutas
    relativas, mismo contrato de auth) production + sensor_data + polygon +
    equipment en parquet (~8 MB) y modela en 3D las posiciones de cada pase
    del balde (sensor_data."Loading Bucket Coors", JSON x100) del polígono
    elegido: cada pase = esfera de ~10 m3, pases cercanos se unen (radio de
    conexión ajustable) y forman "islas"; el límite planificado del polígono
    (registro HPGPS de R4M) se dibuja como prisma naranja y cada pase se
    clasifica dentro/fuera de él (regla alternativa seleccionable: polígono
    HPGPS del ciclo distinto del asignado).
  - Sin conexión al cubo la pestaña muestra un aviso y el resto de la página
    no se ve afectado. Renderiza con three.js r170 (vendor_three.min.js,
    empaquetado en la página; nada externo).

PERIODO Y TURNO (solicitud Erdene 01, 2026-08-13)
  - La cabecera tiene tres controles: #startSel (inicio), #dateSel (fin, mismo
    id de antes para no romper render_pdf.py) y #shiftSel ("", "DS", "NS").
  - Las columnas "Today/DS/NS/Daily" describen la fecha FIN; las columnas STD
    (start-to-date, antes MTD) suman todo el periodo. "Monthly Target" sigue
    siendo el plan del mes natural.
  - El filtro de turno solo alcanza los ciclos de R4M. Los objetivos, los datos
    de planta (PP), el histórico mensual del molino, el inventario ROM y todo el
    atlas NO tienen dimensión de turno: se avisa bajo el selector, las celdas de
    objetivo se atenúan y la varianza STD se deja en blanco.
  - El selector "Period" del mapa es independiente (el payload del atlas está
    preagregado por mes/semana/día en build time).

CAPAS NUEVAS EN LA PÁGINA (solicitudes 03-12)
  - window.XLSXIO (SCRIPT 3a): lector/escritor .xlsx SIN librerías, usando
    CompressionStream/DecompressionStream("deflate-raw") de Chrome. Alimenta los
    botones "Excel template" / "Import Excel" del panel de insumos; la
    importación muestra una vista previa antes de aplicar nada.
  - window.TC (SCRIPT 3b): capa de personalización. Guarda en su PROPIA clave
    localStorage `erd_report_custom_v1` (nunca dentro del paquete de insumos,
    que se comparte entre personas). Oculta/reordena/renombra columnas y filas,
    oculta gráficos y los amplía a página completa. Ojo: dentro del IIFE del
    informe existe una constante `TC = 3` (índice del cubo), por lo que hay que
    escribir siempre `window.TC`, nunca `TC` a secas.
  - Datos manuales (equipos auxiliares, topografía, cifras fuera del sistema) e
    informes con fotos: viven en `inputs.manual` / `inputs.aux` y en IndexedDB
    (`erd_report_notes`) respectivamente. Las fotos se reescalan a 1600 px y se
    recodifican a JPEG antes de guardarse, y viajan en el JSON de exportación.

OTROS CONTRATOS
  - Tema: la página se muestra siempre en tema claro (sin selector).
  - Imprimir / PDF: botón "Export PDF" en la cabecera (llama a window.print());
    solo se imprime la mitad del informe (el atlas y los controles llevan
    clases noprint / @media print). Lo que el usuario oculte con window.TC
    también desaparece del PDF; render_pdf.py espera window.__notesReady.
  - Insumos editables (coeficientes LCM y objetivos diarios/mensuales): se
    guardan en localStorage del navegador del usuario; botones de exportar/
    importar JSON y restablecer incluidos.
  - Unidades de prueba eliminadas (p. ej. EX127) se excluyen vía EXCLUDE_EQ.
  - Regenerar la página: python build_combined.py  en el repo fuente
    (carpeta daily_report/; opción --fetch para bajar datos frescos del cubo).

════════════════════════════════════════════════════════════════════════════════
-->"""

TOC_HTML = """
  <nav class="toc noprint">
    <a href="#secProd">Mining</a><a href="#secRomT">ROM</a><a href="#secMillT">Mill Feeding</a>
    <a href="#secNotes">Notes</a><a href="#secManual">Manual data</a>
    <a href="#secSankey">Life-cycle</a><a href="#secPoly">Polygons</a>
    <a href="#secDigc">Compliance</a><a href="#secInv">Ore Inventory</a>
    <a href="#secEquip">Equipment</a><a href="#secCrew">Crew</a>
    <a href="#secCycle">Cycles</a><a href="#secHaul">Haul</a>
    <span class="spring"></span><a href="#inputsPanel">Inputs</a>
  </nav>
"""

PRELUDE_JS = r"""
<script>
"use strict";
/* light theme only; the array stays because both IIFEs register retint hooks */
window.__onTheme = [];
document.documentElement.removeAttribute("data-theme");
</script>
"""

PDF_BTN_WIRE = r"""
(function(){
  const b = document.getElementById("pdfBtn");
  if (b) b.addEventListener("click", () => window.print());
})();
"""

REPORT_RETINT = r"""let C_ACT, C_TGT = "#b7bfc6", C_CUM, C_CUMT, C_AU, C_HG, C_MG, C_LG, C_PP, C_INK;
function retint(){
  const dk = document.documentElement.getAttribute("data-theme") === "dark";
  C_ACT = dk ? "#2f6fe0" : "#005aed";  C_PP   = dk ? "#12a3cc" : "#1a97d4";
  C_CUM = dk ? "#199a52" : "#0d8a68";  C_AU   = dk ? "#8d6708" : "#c98500";
  C_HG  = dk ? "#d95f27" : "#f06b32";  C_MG   = C_ACT;
  C_LG  = dk ? "#4e9a2e" : "#55a630";  C_CUMT = dk ? "#8a93a3" : "#8a8f94";
  C_INK = dk ? "#d5d9de" : "#222";
}
retint();"""

ATLAS_RETINT = r"""let C_ACT, C_TGT = "#b7bfc6", C_CUM, C_CUMT, C_AU, C_INK;
function retint(){
  const dk = document.documentElement.getAttribute("data-theme") === "dark";
  C_ACT = dk ? "#2f6fe0" : "#005aed";  C_CUM  = dk ? "#199a52" : "#0d8a68";
  C_AU  = dk ? "#8d6708" : "#c98500";  C_CUMT = dk ? "#8a93a3" : "#8a8f94";
  C_INK = dk ? "#d5d9de" : "#222";
  const HG = dk ? "#d95f27" : "#f06b32", LG = dk ? "#4e9a2e" : "#55a630",
        AMB = dk ? "#8d6708" : "#c98500", CY = dk ? "#12a3cc" : "#1a97d4";
  Object.assign(CLASS_COLOR, {HG, MG: C_ACT, LG1: LG, LG2: LG, SG: AMB,
    MW: dk ? "#7a5a06" : "#b26e00", EW: CY});
  Object.assign(GRP_COLOR, {"Ore": C_ACT, "Marginal": AMB, "Waste": "#8a8f94", "Mill feed": HG});
  Object.assign(SEG_COLORS, {"Travel empty": "#8a8f94", "Queue & spot": HG, "Loading": C_ACT,
    "Haul loaded": C_CUM, "At dump": AMB, "Dumping": CY});
}"""


def assemble():
    # ------- split the two templates -------
    r_css = _cut(REPORT_TEMPLATE, "<style>", "</style>")
    r_body = _cut(REPORT_TEMPLATE, "<body>", "<script>")
    r_js = _cut(REPORT_TEMPLATE, '<script>\n"use strict";', "</script>")
    a_css = _cut(ATLAS_TEMPLATE, "<style>", "</style>")
    a_body = _cut(ATLAS_TEMPLATE, "<body>", "<script>")
    a_js = _cut(ATLAS_TEMPLATE, '<script>\n"use strict";', "</script>")

    # ------- report body surgery -------
    r_body = _rep(r_body, '<div class="noprint"><a class="bigbtn" href="mine_atlas.html"><span class="glyph">&#128506;</span> OPEN MINE ATLAS &rarr;</a></div>',
                  '<div class="noprint"><button id="pdfBtn" class="themebtn">&#10515; Export PDF</button></div>',
                  tag="pdf button")
    r_body = _rep(r_body, '<div class="meta">__GRADE_COV__</div>',
                  '<div class="meta"><span id="liveStatus" class="livechip">connecting to R4M cube&hellip;</span></div>',
                  tag="live chip")
    tabs = _rep(SHEETTABS_HTML, '  <button data-sheet="main" class="on">', MR_TAB_HTML + '  <button data-sheet="main" class="on">',
                tag="master tab")
    tabs = _rep(tabs, '  <span class="hint">', OS_TAB_HTML + OK_TAB_HTML + '  <span class="hint">', tag="overspeed tab")
    tabs = _rep(tabs, 'sheets &middot; the 3D viewer loads bucket GPS from R4M when first opened',
                'sheets &middot; the 3D viewer loads bucket GPS from R4M when first opened &middot; Over-speed and Operator KPI are C4M snapshots',
                tag="tabs hint")
    r_body = (tabs
              + '<div id="loadOverlay" class="loadoverlay noprint">'
              '<div class="spin"></div><div>Fetching live data from the R4M cube&hellip;</div></div>'
              + r_body)
    r_body = _rep(r_body, '<div class="banner">MINING</div>',
                  '<div class="banner" id="secProd">MINING</div>', tag="prod id")
    r_body = _rep(r_body, '<div class="banner">MILL FEEDING</div>',
                  '<div class="banner" id="secMillT">MILL FEEDING</div>', tag="mill id")
    r_body = _rep(r_body, '<div class="banner">ROM INVENTORIES (received on C4M ROM Pad)</div>',
                  '<div class="banner" id="secRomT">ROM INVENTORIES (received on C4M ROM Pad)</div>',
                  tag="rom id")
    r_body = _rep(r_body, '<div class="kpis" id="kpis"></div>',
                  TOC_HTML + '\n  <div class="kpis" id="kpis"></div>', tag="toc insert")
    split_at = r_body.index('  <details class="inputs')
    r_body_a, r_body_b = r_body[:split_at], r_body[split_at:]

    # ------- atlas body surgery -------
    a_core_start = a_body.index('  <div class="banner" id="secSankey">')
    a_foot_start = a_body.index('  <div style="margin-top:36px;padding-top:10px;border-top:1px solid #e4e1d6')
    a_core = a_body[a_core_start:a_foot_start]
    a_core = _rep(a_core, '<div class="banner" id="secSankey">MATERIAL LIFE-CYCLE — PIT &rarr; DESTINATION &rarr; MILL (ribbon)</div>',
                  '''<div class="banner" id="secSankey">MATERIAL LIFE-CYCLE — PIT &rarr; DESTINATION &rarr; MILL (ribbon)</div>
  <div class="snapchip">ANALYTICS SNAPSHOT &middot; BUILT __BUILT_AT__ &middot; sections 06-13 refresh with each page rebuild &middot; their daily charts follow the report&rsquo;s start&ndash;end period (never split by shift) &middot; the <b>Period</b> control below is the ribbon&rsquo;s own monthly window</div>
  <div class="controls"><label><b>Period</b> <select id="periodSel"></select></label></div>''',
                  tag="atlas snapshot chip")
    a_core = '\n  <div class="atlaspart">\n' + a_core + '\n  </div><!-- /atlaspart -->\n'

    # ------- report js surgery -------
    r_js = _rep(r_js, '''const C_ACT = "#2a78d6", C_TGT = "#b7bfc6", C_CUM = "#1baf7a",
      C_CUMT = "#8a8f94", C_AU = "#c9a227",
      C_HG = "#eb6834", C_MG = "#2a78d6", C_LG = "#1baf7a";''', REPORT_RETINT, tag="report colors")
    r_js = r_js.replace('color: "#7a4dd8"', "color: C_PP")
    r_js = r_js.replace('color: "#b39ddb"', "color: C_PP")
    r_js = r_js.replace('color: "#1b1e21"', "color: C_INK")
    r_js = _rep(r_js, 'const INK="#1b1e21";',
                'const INK = (typeof C_INK !== "undefined" && C_INK) || "#1b1e21";', tag="report ink")

    r_js = _rep(r_js, 'const CUBE = __CUBE__;', 'let CUBE = __CUBE__;   /* snapshot fallback */', tag="cube let")
    r_js = _rep(r_js, 'const ROM  = __ROM__;', 'let ROM  = __ROM__;', tag="rom let")
    r_js = _rep(r_js, 'const ROMCLS = __ROMCLS__;', 'let ROMCLS = __ROMCLS__;', tag="romcls let")
    r_js = _rep(r_js, 'const ROMOUT = __ROMOUT__;', 'let ROMOUT = __ROMOUT__;', tag="romout let")
    r_js = _rep(r_js, 'const EXH  = __EXH__;', 'let EXH  = __EXH__;', tag="exh let")
    r_js = _rep(r_js, 'const DATES = Object.keys(CUBE).sort();',
                'let DATES = Object.keys(CUBE).sort();', tag="dates let")
    r_js = _rep(r_js, "\nstart();", BOOT_JS, tag="boot")
    r_js += '''
window.__onTheme.push(() => { retint(); refresh(false); });
/* extend, never replace: build_report already published the automation surface */
Object.assign(window.RPT, {refresh: refresh, ppT: ppT, ppAu: ppAu});
'''

    # ------- atlas js surgery -------
    a_js = _rep(a_js, 'const C_ACT="#2a78d6", C_TGT="#b7bfc6", C_CUM="#1baf7a", C_CUMT="#8a8f94", C_AU="#c9a227";',
                ATLAS_RETINT, tag="atlas colors")
    a_js = _rep(a_js, '''function flowColor(dst, cls){
  if (dst === "Crusher" || dst === "Crusher (mill feed)") return "#eb6834";
  if (["HG","MG","LG2"].includes(cls)) return "#2a78d6";
  if (["SG","MW","LG1"].includes(cls)) return "#e08b00";
  return "#8a8f94";
}''', '''function flowColor(dst, cls){
  if (dst === "Crusher" || dst === "Crusher (mill feed)") return GRP_COLOR["Mill feed"];
  if (["HG","MG","LG2"].includes(cls)) return C_ACT;
  if (["SG","MW","LG1"].includes(cls)) return GRP_COLOR["Marginal"];
  return "#8a8f94";
}''', tag="flowColor")
    a_js = _rep(a_js, 'const INK="#1b1e21";',
                'const INK = (typeof C_INK !== "undefined" && C_INK) || "#1b1e21";', tag="atlas ink")
    a_js = _rep(a_js, '''document.getElementById("builtAt").textContent = D.built;
document.getElementById("builtFoot").textContent = D.built;
document.getElementById("dataThrough").textContent = D.dates[D.dates.length-1];''',
                '/* masthead meta set by the report script */', tag="atlas meta setters")
    a_js = _rep(a_js, 'refreshPeriod();\ndrawPTable();', 'retint();\nrefreshPeriod();\ndrawPTable();',
                tag="atlas retint init")
    a_js += '''
window.__onTheme.push(() => {
  retint();
  refreshPeriod();
  drawPTable(); drawPDetail(); redrawCharts();
});
window.ATL = { selectPile: selectPile, refreshPeriod: refreshPeriod, refreshInv: refreshInv, redrawCharts: redrawCharts, contour: D.contour, contourB64: CONTOUR_B64, design: D.design || null, plevel: D.plevel || null,
  invLoad: invLoadLive, inv: invState, setInvWindow: invSetWindow };
'''

    # ------- 3D viewer js surgery: setSheet() drives all three sheets -------
    d3_js = _rep(DIG3D_JS, '''function setSheet(name){
  const on = name === "dig3d";
  document.body.classList.toggle("sheet-dig3d", on);
  el("dig3d").hidden = !on;
  document.querySelectorAll("#sheettabs button").forEach(b =>
    b.classList.toggle("on", b.dataset.sheet === (on ? "dig3d" : "main")));
  if (on){
    if (history.replaceState) history.replaceState(null, "", "#dig3d");
    open();
  } else {
    if (location.hash === "#dig3d" && history.replaceState) history.replaceState(null, "", location.pathname + location.search);
    close();
  }
}''', '''function setSheet(name){
  const on = name === "dig3d", os = name === "overspeed", ok = name === "opkpi", ms = name === "master";
  if (window.RPT && window.RPT.master) window.RPT.master.show(ms);
  document.body.classList.toggle("sheet-dig3d", on);
  document.body.classList.toggle("sheet-overspeed", os);
  document.body.classList.toggle("sheet-opkpi", ok);
  el("dig3d").hidden = !on;
  el("osheet").hidden = !os;
  el("oksheet").hidden = !ok;
  document.querySelectorAll("#sheettabs button").forEach(b => b.classList.toggle("on", b.dataset.sheet === name));
  if (history.replaceState) history.replaceState(null, "", on ? "#dig3d" : os ? "#overspeed" : ok ? "#opkpi" : ms ? "#master" : location.pathname + location.search);
  if (on) open(); else close();
  if (os && window.OSHEET) window.OSHEET.open();
  if (ok && window.OKSHEET) window.OKSHEET.open();
}''', tag="setSheet 4 sheets")
    d3_js = _rep(d3_js, 'if (location.hash === "#dig3d") setSheet("dig3d");',
                'if (location.hash === "#dig3d") setSheet("dig3d");\nelse if (location.hash === "#master") setSheet("master");',
                tag="master hash")

    # ------- compose -------
    html = f"""<!DOCTYPE html>
{INTEGRATION_DOC_ES}
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>R4M Aurora — Daily Operations Report</title>
<!-- ================= ESTILOS: schema R4M Aurora (literal) + informe + atlas + capa override ================= -->
<style>
{SCHEMA_CSS}
{r_css}
{a_css}
{OVERRIDE_CSS}
{DIG3D_CSS}
{OS_CSS}
{OK_CSS}
</style>
<script>
/* served from the browser cache while the server has a newer build? reload once (ETag check, one HEAD request) */
(function(){{ try {{
  if (location.protocol === "file:") return;
  const nav = performance.getEntriesByType("navigation")[0], K = "erd_report_etag:" + location.pathname;
  fetch(location.pathname, {{method: "HEAD", cache: "no-store"}}).then(r => {{
    const tag = r.headers.get("etag") || r.headers.get("last-modified") || "";
    if (!tag) return;
    const seen = localStorage.getItem(K);
    if (nav && nav.transferSize === 0 && seen && seen !== tag && sessionStorage.getItem(K) !== tag) {{
      sessionStorage.setItem(K, tag); localStorage.setItem(K, tag); location.reload();
    }} else localStorage.setItem(K, tag);
  }}).catch(() => {{}});
}} catch (e) {{}} }})();
/* R4M's menu shows custom reports inside a scale(0.74) wrapper (1 / Windows display scaling), so the page renders
   on a ~2,500 px canvas shrunk to fit: give our own iframe the inverse scale -> the report shows at 100 %.
   Only our iframe element is touched (same origin); nothing happens on file://, in a normal tab or without a scale. */
(function(){{ try {{
  const fe = window.frameElement, p = fe && fe.parentElement;
  if (!p) return;
  const par = window.parent, st = fe.style, old = st.cssText;
  const fit = () => {{ try {{
    const s = p.getBoundingClientRect().width / (p.offsetWidth || 1);
    if (!(s > 0.2) || Math.abs(s - 1) < 0.02){{ if (st.transform){{ st.cssText = old; }} return; }}
    const w = Math.round(p.clientWidth * s) + "px", h = Math.round(p.clientHeight * s) + "px", tf = "scale(" + (1 / s).toFixed(5) + ")";
    if (st.transform !== tf || st.width !== w || st.height !== h){{
      st.transformOrigin = "0 0"; st.transform = tf; st.width = w; st.height = h;
    }}
  }} catch (e) {{}} }};
  fit();
  par.addEventListener("resize", fit);
  const ro = par.ResizeObserver ? new par.ResizeObserver(fit) : null;
  if (ro) ro.observe(p);
  const iv = setInterval(fit, 3000);                 /* R4M re-renders its wrapper when the menu opens/closes */
  window.addEventListener("pagehide", () => {{ try {{
    clearInterval(iv); if (ro) ro.disconnect(); par.removeEventListener("resize", fit); st.cssText = old;
  }} catch (e) {{}} }});
}} catch (e) {{}} }})();
</script>
</head>
<body>
<!-- ═══════════ MITAD 1: INFORME DIARIO (secciones 01-03; datos EN VIVO del cubo, con snapshot de respaldo) ═══════════ -->
{r_body_a}
<!-- ═══════════ MITAD 2: ATLAS DE MINA (secciones 06-13; snapshot de compilación, se refresca al reconstruir) ═══════════ -->
{a_core}
<!-- ═══════════ panel de insumos editables (LCM / objetivos; se guardan en localStorage) + pie ═══════════ -->
{r_body_b}
<!-- ═══════════ HOJA 2: VISOR 3D DE PUNTOS DE EXCAVACIÓN (pestaña aparte; datos EN VIVO de sensor_data al abrirla) ═══════════ -->
{DIG3D_HTML}
<!-- ═══════════ HOJA 3: EXCESOS DE VELOCIDAD (iframe a overspeed_report.html, misma carpeta; se carga al abrir la pestaña) ═══════════ -->
{OS_HTML}
<!-- ═══════════ HOJA 4: KPI DE OPERADORES (iframe a operator_kpi.html, misma carpeta; se carga al abrir la pestaña) ═══════════ -->
{OK_HTML}
<div id="tip"></div>
<!-- ═══════════ SCRIPT 1: decodificador Parquet (hyparquet + zstd, empaquetado; global HYP) ═══════════ -->
<script>
{VENDOR_JS}
</script>
<!-- ═══════════ SCRIPT 1b: three.js r170 + OrbitControls (empaquetado; global THREE3D) — solo lo usa el visor 3D ═══════════ -->
<script>
{THREE_JS}
</script>
<!-- ═══════════ SCRIPT 2: cargador en vivo window.R4M_LIVE (descarga y agrega los parquet del cubo) ═══════════ -->
{LIVE_JS}
<!-- ═══════════ SCRIPT 3: preludio (tema claro fijo) ═══════════ -->
{PRELUDE_JS}
<!-- ═══════════ SCRIPT 3a: lector/escritor .xlsx sin librerías, window.XLSXIO (plantilla e importación de insumos) ═══════════ -->
<script>
{XLSX_JS}
</script>
<!-- ═══════════ SCRIPT 3b: capa de personalización window.TC (mostrar/ocultar y ampliar gráficos, columnas de tabla) ═══════════ -->
<script>
{CUSTOM_JS}
</script>
<!-- ═══════════ SCRIPT 4: informe (IIFE 1) + atlas (IIFE 2) + visor 3D (IIFE 3) + arranque boot() ═══════════ -->
<script>
"use strict";
;(function(){{
{r_js}
}})();
;(function(){{
{a_js}
}})();
;(function(){{
{d3_js}
}})();
;(function(){{
{OS_JS.replace('__OS_FILE__', OS_FILE)}
}})();
;(function(){{
{OK_JS.replace('__OK_FILE__', OK_FILE)}
}})();
{PDF_BTN_WIRE}
</script>
</body>
</html>
"""
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    args = ap.parse_args()
    if args.fetch:
        rc = subprocess.call([sys.executable, os.path.join(HERE, "fetch_data.py")])
        if rc != 0:
            print("fetch failed - building from cache", file=sys.stderr)

    df = load_joined()
    cube = build_cube(df)
    rom = build_rom(df)
    defaults = apply_published(read_inputs())
    exh = build_exh(df, defaults.get("lcm"))
    payload, b64 = build_atlas.atlas_payload(df)

    dates = sorted(cube)
    print(f"combined build: {len(df):,} cycles, {dates[0]}..{dates[-1]}")

    j = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False)
    html = (assemble()
            .replace("__CUBE__", j(cube))
            .replace("__ROM__", j(rom))
            .replace("__ROMCLS__", j(build_romcls(df)))
            .replace("__ROMOUT__", j(build_romout(df)))
            .replace("__EXH__", j(exh))
            .replace("__DEFAULTS__", j(defaults))
            .replace("__PAYLOAD__", j(payload))
            .replace("__CONTOUR_B64__", b64)
            .replace("__LOGO_B64__", LOGO_B64)
            .replace("__BUILT_AT__", dt.datetime.now().strftime("%Y-%m-%d %H:%M")))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024/1024:.1f} MB)")

    # sheet 3 loads ../overspeed/overspeed_report.html from NEXT TO this file: keep a copy in sync
    src = os.path.join(ROOT, "overspeed", OS_FILE)
    if os.path.exists(src):
        import shutil
        shutil.copyfile(src, os.path.join(HERE, OS_FILE))
        print(f"copied {OS_FILE} next to the report ({os.path.getsize(src)/1024/1024:.1f} MB) - deploy both files together")
    else:
        print(f"WARNING: {src} not found - sheet 3 will show its fallback message", file=sys.stderr)
    # sheet 4 (operator KPI) works the same way
    src = os.path.join(ROOT, "operator_kpi", OK_FILE)
    if os.path.exists(src):
        import shutil
        shutil.copyfile(src, os.path.join(HERE, OK_FILE))
        print(f"copied {OK_FILE} next to the report ({os.path.getsize(src)/1024/1024:.1f} MB) - deploy all three files together")
    else:
        print(f"WARNING: {src} not found - sheet 4 will show its fallback message", file=sys.stderr)

    for stale in ("mine_atlas.html", "daily_report.html"):
        p = os.path.join(HERE, stale)
        if os.path.exists(p):
            os.remove(p)
            print("removed %s (superseded by %s)" % (stale, os.path.basename(OUT)))


if __name__ == "__main__":
    main()
