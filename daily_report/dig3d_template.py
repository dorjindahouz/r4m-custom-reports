"""3D DIG VIEWER - a separate "sheet" (tab) of daily_report.html.

Pick a polygon and see where it was actually dug. Default model (2026-11-01, user: "as realistic dig
polygon as possible") = AS-DUG CUT: plan outline of the ground the bucket reached (dig points + 1.25 m,
gaps up to the "fill gaps" width closed), floor = the dig points (lowest bucket position per pass),
top of cut set so that volume = dispatched tonnes / density; compared with the planned polygon;
toe outline exportable as DXF, floor as CSV. Alternative model = bucket-pass spheres: every bucket pass position
that R4M's sensor_data carries for the polygon's hauling cycles is modelled as
a ~10 m3 volume, passes closer than the connect radius are joined into one
solid (nearest neighbours, not time order - 2026-11-01), and the whole dug area
is the union of everything that touches. Cycles whose loader HPGPS polygon differs from the
assigned polygon are flagged as dug OUTSIDE the polygon (R4M publishes no
polygon boundaries, so this is the same per-cycle rule as the Dig Compliance
section).

Everything here is assembled by build_combined.py:
  SHEETTABS_HTML  - the tab strip (prepended before <div class="sheet">)
  DIG3D_HTML      - the panel (<section id="dig3d">, sibling of .sheet)
  DIG3D_CSS       - styles (incl. print + sheet switching)
  DIG3D_JS        - third IIFE; needs window.THREE3D (vendor_three.min.js),
                    window.R4M_LIVE.{fetchParquet, fetchYearScopedEx, EXCLUDE_EQ}
                    and window.ATL.{contour, contourB64} (ground texture).
Data is fetched LIVE from the R4M cube the first time the tab is opened
(production + sensor_data + polygon + equipment parquet); nothing is baked.
"""

DIG3D_CSS = r"""
/* ================= 3D DIG VIEWER sheet ================= */
.sheettabs{position:sticky;top:0;z-index:60;display:flex;gap:4px;align-items:flex-end;height:44px;
  box-sizing:border-box;padding:6px 16px 0;background:var(--color-bg-dashboard);
  border-bottom:2px solid var(--color-primary)}
.sheettabs button{font:inherit;font-size:12.5px;font-weight:700;letter-spacing:.3px;padding:8px 18px;
  border:1px solid var(--color-border-medium);border-bottom:none;border-radius:8px 8px 0 0;
  background:var(--color-bg-tab-inactive);color:var(--color-text-secondary);cursor:pointer}
.sheettabs button:hover{background:var(--color-bg-tab-active);color:var(--color-text-primary)}
.sheettabs button.on{background:var(--color-bg-surface);color:var(--color-primary);border-color:var(--color-primary)}
.sheettabs .hint{margin-left:auto;font-size:11px;color:var(--color-text-tertiary);padding-bottom:8px}
nav.toc{top:44px}
body.sheet-dig3d .sheet{display:none}
body.sheet-dig3d #tip{display:none !important}
#dig3d{display:flex;height:calc(100vh - 44px);background:var(--color-bg-surface);
  color:var(--color-text-primary);font-size:12.5px}
#dig3d[hidden]{display:none}
.d3side{width:372px;flex:none;overflow:auto;border-right:1px solid var(--color-border-subtle);
  padding:10px 14px 18px;background:var(--color-bg-surface-secondary,#f6f7f9)}
.d3side h3{font-family:"Rubik",-apple-system,sans-serif;font-size:14px;letter-spacing:1.2px;margin:2px 0 8px;
  color:var(--color-primary)}
.d3side h4{font-size:10.5px;letter-spacing:1.2px;text-transform:uppercase;color:var(--color-text-secondary);
  margin:12px 0 4px}
.d3row{display:flex;gap:8px;align-items:center;margin:5px 0;flex-wrap:wrap}
.d3row label{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.d3side select,.d3side input[type=text],.d3side input[type=number],.d3side input[type=date]{
  font:inherit;font-size:12px;border:1px solid var(--color-border-medium);border-radius:4px;
  background:var(--color-bg-surface);color:var(--color-text-primary);padding:3px 5px}
.d3tblwrap.d3plist{max-height:30vh;margin-top:5px}
table.d3tbl tr.off td{color:var(--color-text-secondary);cursor:default}
table.d3tbl td input[type=checkbox]{margin:0;vertical-align:-1px}
.d3side button.mini{padding:2px 8px}
.d3hud:empty{display:none}
.d3side input#d3find{width:100%}
.d3side input[type=number]{width:60px}
.d3side input[type=range]{width:110px}
.d3side button{font:inherit;font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:5px;cursor:pointer;
  border:1px solid var(--color-primary);background:var(--color-bg-surface);color:var(--color-primary)}
.d3side button:hover{background:var(--state-hover-blue,#e6f0ff)}
.d3side button.pri{background:var(--color-primary);color:var(--color-text-on-primary)}
.d3status{font-size:11.5px;color:var(--color-text-secondary);min-height:16px;margin-bottom:6px}
.d3stats{background:var(--color-bg-surface);border:1px solid var(--color-border-subtle);border-radius:6px;
  padding:8px 10px;line-height:1.55;font-size:12px}
.d3stats b{font-size:13px}
.d3stats .k{color:var(--color-text-secondary)}
.d3stats .out{color:var(--color-error)}
.d3legend{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:11px;color:var(--color-text-secondary);margin:6px 0}
.d3legend i{width:11px;height:11px;display:inline-block;border-radius:2px;margin-right:4px;vertical-align:-1px}
.d3legend .grad{width:90px;height:10px;display:inline-block;vertical-align:-1px;border-radius:2px;
  background:linear-gradient(90deg,#1d4f91,#f0b429)}
.d3tblwrap{max-height:36vh;overflow:auto;border:1px solid var(--color-border-subtle);border-radius:6px;
  background:var(--color-bg-surface)}
table.d3tbl{border-collapse:collapse;width:100%;font-size:11px}
table.d3tbl th{position:sticky;top:0;background:var(--color-bg-metrics,#eef0f2);text-align:left;padding:4px 5px;
  font-weight:700;color:var(--color-text-secondary);border-bottom:1px solid var(--color-border-subtle);cursor:pointer}
table.d3tbl td{padding:3px 5px;border-bottom:1px solid var(--color-border-subtle);white-space:nowrap}
table.d3tbl td.n{text-align:right;font-variant-numeric:tabular-nums}
table.d3tbl tr{cursor:pointer}
table.d3tbl tr:hover{background:var(--state-hover-bg,#f1f4f8)}
table.d3tbl tr.out td{color:var(--color-error)}
table.d3tbl tr.sel{background:var(--color-bg-selected,#d1e7fd)}
table.d3tbl tr.oth td{color:#8e44ad}
table.d3tbl tr.oth td.tt{opacity:.6}
table.d3tbl tr.osep td{background:#f3ecf7;color:#6c3483;font-weight:700;font-size:11px;padding:4px 5px;cursor:default}
.d3note{font-size:11px;color:var(--color-text-secondary);line-height:1.5;margin-top:10px}
.d3main{flex:1;position:relative;min-width:0;background:#dfe6ec}
.d3main canvas{display:block;width:100%;height:100%;outline:none}
.d3navbox{position:absolute;right:10px;top:10px;width:120px;display:flex;flex-direction:column;align-items:flex-end;gap:2px;z-index:3}
.d3navbox canvas#d3nav{width:120px !important;height:120px !important;cursor:default}
.d3navbox button{font:inherit;font-size:15px;line-height:1;width:26px;height:24px;padding:0;border:1px solid var(--color-border-medium);
  border-radius:4px;background:rgba(255,255,255,.92);color:#33424d;cursor:pointer}
.d3navbox button:hover{border-color:var(--color-primary);color:var(--color-primary)}
.d3hud{position:absolute;left:10px;top:10px;background:rgba(255,255,255,.9);border:1px solid var(--color-border-subtle);
  border-radius:6px;padding:6px 10px;font-size:11.5px;line-height:1.5;pointer-events:none;max-width:46%}
.d3hud b{font-family:"Rubik",sans-serif}
.d3help{position:absolute;right:10px;bottom:8px;font-size:10.5px;color:#334;background:rgba(255,255,255,.75);
  padding:3px 8px;border-radius:4px;pointer-events:none}
.d3tip{position:absolute;pointer-events:none;background:#fff;border:1px solid var(--color-border-medium);
  padding:6px 9px;font-size:11.5px;line-height:1.45;border-radius:4px;box-shadow:var(--shadow-md);display:none;
  z-index:5;max-width:280px}
.d3msg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;
  padding:30px;background:rgba(223,230,236,.85);font-size:13.5px;color:var(--color-text-primary);z-index:4}
.d3msg.err{color:var(--color-error)}
.d3msg[hidden]{display:none}
#dig3d.mcut .blobonly,#dig3d:not(.mcut) .cutonly{display:none !important}
.d3legend .grad3{width:90px;height:10px;display:inline-block;vertical-align:-1px;border-radius:2px;
  background:linear-gradient(90deg,#2a9d8f,#c9a46a)}
.d3legend .grad2{width:90px;height:10px;display:inline-block;vertical-align:-1px;border-radius:2px;
  background:linear-gradient(90deg,#23408e,#2bb3a3,#f2d94e)}
@media print{.sheettabs,#dig3d{display:none !important}}
"""

SHEETTABS_HTML = """<div class="sheettabs noprint" id="sheettabs">
  <button data-sheet="main" class="on">Daily Report &amp; Mine Atlas</button>
  <button data-sheet="dig3d">3D Dig Viewer</button>
  <span class="hint">sheets &middot; the 3D viewer loads bucket GPS from R4M when first opened</span>
</div>
"""

DIG3D_HTML = """<section id="dig3d" class="noprint mcut" hidden>
  <div class="d3side">
    <h3>3D DIG VIEWER &mdash; POLYGON DIG POINTS</h3>
    <div class="d3status" id="d3status">idle</div>
    <h4>Shift</h4>
    <div class="d3row"><input type="date" id="d3day"><select id="d3shift"><option value="DS">Day (07&ndash;19)</option><option value="NS">Night (19&ndash;07)</option><option value="both">Both shifts</option><option value="all">All dates</option></select><button id="d3prev" class="mini" title="previous shift with digging">&lsaquo;</button><button id="d3next" class="mini" title="next shift with digging">&rsaquo;</button></div>
    <h4>Polygons <span id="d3pcount" style="font-weight:400;text-transform:none;letter-spacing:0"></span></h4>
    <input type="text" id="d3find" placeholder="filter polygons&hellip;" autocomplete="off">
    <div class="d3tblwrap d3plist"><table class="d3tbl" id="d3plist" title="click a name to show that polygon; tick boxes to show several together"></table></div>
    <div class="d3row"><button id="d3pall" class="mini">Select all</button><button id="d3pnone" class="mini">Clear</button></div>
    <div class="d3row" id="d3range" style="display:none"><label>From <input type="date" id="d3from"></label><label>To <input type="date" id="d3to"></label></div>
    <h4>Model</h4>
    <div class="d3row blobonly"><label>Connect radius <input type="range" id="d3conn" min="0" max="8" step="0.5" value="4"> <span id="d3connv">4.0 m</span></label></div>
    <div class="d3row blobonly"><label>Volume / pass <input type="number" id="d3vol" value="10" min="2" max="40" step="1"> m&sup3;</label></div>
    <div class="d3row"><label>Vertical &times; <input type="range" id="d3vex" min="1" max="3" step="0.25" value="1"> <span id="d3vexv">1.0</span></label></div>
    <h4>Display</h4>
    <div class="d3row"><label>Colour <select id="d3color">
      <option value="grade" selected>depth to grade</option><option value="elev">floor elevation</option><option value="cycle">by cycle</option>
      <option value="date">by date</option><option value="comp">compliance (outside = red)</option></select></label></div>
    <div class="d3row cutonly"><button id="d3dxf" title="toe outline (3-D polylines draped on the floor, holes on their own layer) + the planned polygon, UTM 47N, EGM96 heights">&#8681; Outline (DXF)</button><button id="d3csv" title="as-dug floor height per grid cell">&#8681; Floor (CSV)</button></div>
    <div class="d3legend" id="d3legend"></div>
    <h4>Cycles <span id="d3cyccount" style="font-weight:400;text-transform:none;letter-spacing:0"></span></h4>
    <div class="d3row"><button id="d3cyccsv" title="every cycle booked to this polygon in the chosen shift or From-To window, with or without bucket GPS, plus the purple rows below; all R4M cube columns: times, tonnes, distances, operators, locations, coordinates">&#8681; Cycles (CSV)</button></div>
    <div class="d3tblwrap"><table class="d3tbl" id="d3cycles"></table></div>
  </div>
  <div class="d3main" id="d3main">
    <canvas id="d3canvas"></canvas>
    <div class="d3navbox"><button id="d3home" title="home view (fit the polygon)">&#8962;</button><canvas id="d3nav" width="240" height="240" title="click a face, edge or corner to look from there"></canvas></div>
    <div class="d3hud" id="d3hud"></div>
    <div class="d3help">drag = orbit &middot; right-drag = pan &middot; wheel = zoom &middot; hover = cycle &middot; click = select</div>
    <div class="d3tip" id="d3tip"></div>
    <div class="d3msg" id="d3msg" hidden></div>
  </div>
</section>
"""

DIG3D_JS = r"""
/* ============================ 3D DIG VIEWER (IIFE 3) ============================ */
const T = window.THREE3D;
const el = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt0 = v => (v === null || v === undefined || !isFinite(v)) ? "-" : Math.round(v).toLocaleString("en-US");
const fmt1 = v => (v === null || v === undefined || !isFinite(v)) ? "-" : (Math.round(v * 10) / 10).toLocaleString("en-US", {minimumFractionDigits: 1, maximumFractionDigits: 1});
const tick = () => new Promise(r => setTimeout(r, 0));

/* mine window (UTM metres) - same clip as build_atlas */
const XLO = 482300, XHI = 485500, YLO = 4859400, YHI = 4863600, ZLO = 1100, ZHI = 1400;
const KNN = 4;             /* cross-cycle connections per pass within the connect radius */
const ISO = 0.01;          /* field iso-surface: 1 at the pass centre, 0 at radius r */
const EXCLUDE_EQ = (window.R4M_LIVE && window.R4M_LIVE.EXCLUDE_EQ) || new Set(["EX127"]);
const BENCH_H = 2.5;       /* drawn height of the planned-polygon prism above its bench (m; user 2026-11-03: 5 -> 2.5) */
const addDay = d => new Date(Date.parse(d + "T00:00:00Z") + 86400000).toISOString().slice(0, 10);

const S = {status: "idle", data: null, pid: null, model: null, sel: null, isolate: null,
           renderer: null, scene: null, camera: null, controls: null, group: null, mesh: null,
           wire: null, pts: null, ground: null, bench: null, grid: null, plan: null, dig: null, lid: null, outline: null, now: null, nowMesh: null, nowWall: null, nowIdx: null, nowFz: null, nowRaised: null, win: {mode: "shift", date: "", shift: "DS"}, picks: [], shiftKeys: [], other: null, otherIdx: null,
           digAll: null, digCount: 0, geo: null, geoLive: false, geoErr: null, loop: false, open: false};
window.DIG3D = S;

/* ------------------------------------------------------------- sheet switching */
function setSheet(name){
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
}
S.setSheet = setSheet;
document.querySelectorAll("#sheettabs button").forEach(b => b.addEventListener("click", () => setSheet(b.dataset.sheet)));

function status(msg){ el("d3status").textContent = msg; }
function overlay(html, isErr){
  const m = el("d3msg");
  if (!html){ m.hidden = true; return; }
  m.hidden = false; m.className = "d3msg" + (isErr ? " err" : ""); m.innerHTML = html;
}

function open(){
  S.open = true;
  if (!T){ overlay("&#9888; three.js failed to load &mdash; the 3D viewer cannot start.", true); return; }
  if (!S.renderer) initScene();
  resize();
  startLoop();
  if (S.status === "idle" || S.status === "error") loadData();
}
function close(){ S.open = false; S.loop = false; }
S.openSheet = open;

/* ------------------------------------------------------------- data (live R4M) */
async function loadData(){
  S.status = "loading";
  status("fetching R4M cube: production + sensor_data…");
  overlay("Fetching bucket GPS positions from the R4M cube<br><span style=\"font-size:12px;opacity:.8\">production + sensor_data parquet (≈ 8 MB) — once per page load</span>");
  try {
    const L = window.R4M_LIVE;
    if (!L || !L.cycleRows) throw new Error("live loader unavailable");
    /* one download shared with the ROM pad stockpile map (R4M_LIVE.cycleRows, memoised).
       Planned boundaries: live from the HPGPS backend (open + closed polygons);
       if that fails, fall back to the rings baked into the atlas at build time */
    const R = await L.cycleRows();
    S.geoErr = R.geoErr;
    if (R.geoErr) console.warn("DIG3D: polygon boundaries unavailable, using baked rings:", R.geoErr);
    S.geoLive = !!R.geo;
    S.geo = R.geo || bakedGeometry();
    status("parsing bucket positions…"); await tick();
    S.data = parse(R.prod, R.coors, R.poly, R.equip, S.geo, R.mat);
    S.status = "ready";
    const geoTxt = S.geo ? `${fmt0(S.geo.map.size)} polygon boundaries${S.geoLive ? "" : " (baked at build time)"}` : "no polygon boundaries";
    status(`ready · ${fmt0(S.data.nPoints)} pass points in ${fmt0(S.data.list.length)} polygons (year ${R.year}) · ${geoTxt}`);
    overlay("");
    initPicker();
  } catch (e) {
    console.warn("DIG3D data load failed:", e);
    S.status = "error";
    status("live data unavailable");
    overlay(`&#9888; The 3D viewer needs the live R4M cube (production + sensor_data) and could not fetch it: <b>${esc(e && e.auth ? "session expired — sign in to R4M" : (e && e.message) || "network error")}</b>.<br>Open the page from the R4M host (not file://) and switch sheets again to retry.`, true);
  }
}
S.load = loadData;

/* planned floor = the planners' uploaded level (C4M ts_poligono.level_real, e.g. 1192.5; nivel and the R4M register keep only
   the whole metre, and an edit in C4M empties level_real -> the original upload's), baked nightly (D.plevel: id -> level where it
   differs); polygons uploaded after the build fall back to the whole-metre level (user 2026-11-03) */
function realLevel(id, fb){
  const L = window.ATL && window.ATL.plevel, v = L ? L[id] : null;
  return v != null ? +v : (fb == null || fb === "" ? null : +fb);
}

/* rings baked by build_atlas (D.design: name -> [[id, bench, status, ring], ...]) */
function bakedGeometry(){
  const A = window.ATL, DS = A && A.design;
  if (!DS) return null;
  const map = new Map();
  for (const name in DS) for (const [id, bench, status, ring] of DS[name])
    map.set(+id, {name, bench: bench == null ? null : +bench, status, ring, mined: 0});
  return map.size ? {map, open: 0, closed: 0, baked: true} : null;
}
function pointInRing(x, y, ring){
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++){
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
function ringArea(ring){
  let a = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) a += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1]);
  return Math.abs(a) / 2;
}

const ORE_CODES = new Set(["HG", "MG", "LG1", "LG2", "SG"]);   /* mill ore classes; BAS/W/MW/FD/TS carry no gold grade */
function parse(prod, coorsIn, poly, equip, geo, mat){
  const mcode = new Map((mat || []).map(r => [r["Id Material"], String(r["Material Code"] || "")]));
  const pname = new Map(), pbench = new Map();
  for (const r of poly){ pname.set(r["Id Polygon"], String(r["Polygon"] || "")); pbench.set(r["Id Polygon"], r["Bench"]); }
  const eq = new Map(equip.map(r => [r["Id Equipment"], String(r["Equipment"] || "")]));
  /* bucket passes per cycle, already parsed and clipped to XLO..ZHI by R4M_LIVE.parseSensor */
  const coors = new Map();
  for (const [cid, c] of coorsIn) if (c.pts.length) coors.set(cid, c.pts);
  const SHIFT = {A: "DS", B: "NS"};
  const polys = new Map(), shiftIdx = new Map();   /* "date|DS" -> polygon name -> excavator cycles of that shift (with or without bucket GPS) */
  let nPoints = 0;
  for (const r of prod){
    if (r["It is reportable for production"] !== true) continue;
    const pid = r["Id Polygon"];
    if (pid === null || pid === undefined) continue;
    const loader = eq.get(r["Id Equipment Loading"]) || "";
    if (EXCLUDE_EQ.has(loader)) continue;
    /* group by polygon NAME: re-registrations (splits, per-shift finger stocks) get
       new ids in R4M but are the same physical polygon - same rule as the atlas */
    const name = pname.get(pid) || ("#" + pid);
    let P = polys.get(name);
    if (!P){ P = {pid, name, ids: new Set(), bench: realLevel(pid, pbench.get(pid)), cycles: [], total: 0, t: 0, pts: 0, matT: {}, mat: "?"}; polys.set(name, P); }
    P.ids.add(pid);
    if (P.bench == null) P.bench = realLevel(pid, pbench.get(pid));
    P.total++;
    const mc = mcode.get(r["Id Material"]) || "?";
    P.matT[mc] = (P.matT[mc] || 0) + (r["Dry Tonnes"] || 0);
    const sh0 = SHIFT[r["Hauling Shift"]];
    if (sh0 && loader.startsWith("EX")){   /* loaders log no bucket points and mostly reclaim stock: not "dug" here */
      const k0 = String(r["Date Cube Hauling"]).slice(0, 10) + "|" + sh0;
      let I = shiftIdx.get(k0); if (!I){ I = new Map(); shiftIdx.set(k0, I); }
      let e = I.get(name); if (!e){ e = {n: 0, t: 0, lo: new Set()}; I.set(name, e); }
      e.n++; e.t += r["Dry Tonnes"] || 0; e.lo.add(loader);
    }
    let pts = coors.get(r["C4M ID Hauling"]);
    if (!pts) continue;
    /* cycle time = shift date + Hauling Hour (hours 0-6 belong to the next calendar day) */
    const hh = +r["Hauling Hour"], d0 = String(r["Date Cube Hauling"]).slice(0, 10);
    const at = `${isFinite(hh) && hh < 7 ? addDay(d0) : d0} ${String(isFinite(hh) ? hh : 0).padStart(2, "0")}:00`;
    /* shovel heights before the 2026-10-31 19:03-19:29 geoid change = EGM96 + 0.62 m (copy: the arrays are shared) */
    if (at < DATUM_TO) pts = pts.map(p => [p[0], p[1], p[2] - DATUM_SHIFT]);
    const hpRaw = r["Polygon HPGPS"];
    const hp = (hpRaw !== null && hpRaw !== undefined && hpRaw > 0) ? hpRaw : null;
    const c = {cid: r["C4M ID Hauling"], date: String(r["Date Cube Hauling"]).slice(0, 10),
               shift: SHIFT[r["Hauling Shift"]] || String(r["Hauling Shift"] || ""),
               truck: eq.get(r["Id Equipment Hauling"]) || "", loader,
               t: r["Dry Tonnes"] || 0, passes: r["Number of passes"] || pts.length,
               hp, hpName: hp === null ? "" : (pname.get(hp) || ("#" + hp)), pts, at, zMix: at >= DATUM_TO && at < DATUM_MIX_TO};
    c.hpOut = hp !== null && c.hpName !== name;   /* same name (re-registered id) = still inside */
    c.out = c.hpOut;                              /* re-derived per rule in rebuild() */
    P.cycles.push(c); P.t += c.t; P.pts += pts.length; nPoints += pts.length;
  }
  /* planned boundaries: every ring registered under the polygon's ids, plus rings
     whose R4M name matches (re-registrations); a pass is inside if inside ANY ring */
  const byName = new Map();
  const inWindow = ring => ring.some(([x, y]) => x >= XLO && x <= XHI && y >= YLO && y <= YHI);
  if (geo) for (const [id, g] of geo.map){
    if (g.ring.length < 3 || !inWindow(g.ring)) continue;   /* skips R4M's test polygons (Polygon_Example @ 5900) */
    if (!byName.has(g.name)) byName.set(g.name, []);
    byName.get(g.name).push({pid: id, bench: realLevel(id, g.bench), ring: g.ring, status: g.status, mined: g.mined});
  }
  let geoPolys = 0;
  for (const P of polys.values()){
    P.mat = Object.entries(P.matT).sort((a, b) => b[1] - a[1])[0]?.[0] || "?";   /* dominant material code */
    const rings = [], seen = new Set();
    for (const id of P.ids){
      const g = geo && geo.map.get(id);
      if (g && g.ring.length >= 3 && inWindow(g.ring)){ rings.push({pid: id, bench: realLevel(id, g.bench), ring: g.ring, status: g.status, mined: g.mined}); seen.add(id); }
    }
    for (const g of (byName.get(P.name) || [])) if (!seen.has(g.pid)){ rings.push(g); seen.add(g.pid); }
    P.rings = rings;
    P.area = rings.reduce((s, R) => s + ringArea(R.ring), 0);
    if (rings.length && P.cycles.length) geoPolys++;
    for (const c of P.cycles){
      c.inMask = new Uint8Array(c.pts.length); c.nOut = 0;
      if (rings.length){
        c.pts.forEach((p, i) => {
          const ok = rings.some(R => pointInRing(p[0], p[1], R.ring));
          c.inMask[i] = ok ? 1 : 0; if (!ok) c.nOut++;
        });
        c.geoOut = c.nOut * 2 > c.pts.length;     /* majority of the passes beyond the boundary */
      } else { c.inMask.fill(1); c.geoOut = false; }
    }
  }
  const list = [...polys.values()].filter(P => P.cycles.length).sort((a, b) => b.pts - a.pts);
  for (const P of list) P.cycles.sort((a, b) => a.date < b.date ? -1 : a.date > b.date ? 1 : a.cid - b.cid);
  return {polys, list, nPoints, geoPolys, shiftIdx};
}

/* date + shift -> the polygons dug in that shift -> tick the ones to draw (user 2026-11-09). One pick = that polygon; several =
   one merged polygon under the key MULTI (its rings keep their own levels), so every model, table and export path stays the same.
   "All dates" = the previous behaviour: any polygon, whole history, From/To. */
const MULTI = "\u0001multi";
const skey = c => c.date + "|" + c.shift;
const SHIFT_NAME = {DS: "day shift", NS: "night shift", both: "day and night shifts"};
const winKey = () => S.win.date + "|" + S.win.shift;
const inKey = (c, k) => k.endsWith("|both") ? c.date === k.slice(0, 10) : skey(c) === k;   /* key "date|DS", "date|NS" or "date|both" */
const shW = () => S.win.shift === "both" ? "these shifts" : "this shift";
const shortLo = L => { const a = [...L].sort(); return a.map((x, i) => i && x.startsWith("EX") ? x.slice(2) : x).join("/"); };
function pickerRows(){
  if (S.win.mode === "all") return S.data.list.map(P => {
    if (!P.lo) P.lo = shortLo(new Set(P.cycles.map(c => c.loader)));
    return {name: P.name, n: P.cycles.length, t: P.t, lo: P.lo, off: false, nd: 0, why: ""};
  });
  const k = winKey(), out = [], I = new Map();
  for (const key of (S.win.shift === "both" ? [S.win.date + "|DS", S.win.date + "|NS"] : [k])){
    const J = S.data.shiftIdx.get(key);
    if (J) for (const [name, e] of J){ const a = I.get(name); if (!a) I.set(name, {n: e.n, t: e.t, lo: new Set(e.lo)}); else { a.n += e.n; a.t += e.t; for (const x of e.lo) a.lo.add(x); } }
  }
  for (const [name, e] of I){
    const P = S.data.polys.get(name), cyc = P ? P.cycles.filter(c => inKey(c, k)) : [], ok = cyc.filter(c => !badTip(c)).length;
    out.push({name, n: e.n, t: e.t, lo: shortLo(e.lo), off: !ok, nd: e.n - ok, why: ok ? "" : cyc.length ? "bucket sensor fault: cannot be drawn" : "no bucket positions recorded: cannot be drawn"});
  }
  return out.sort((a, b) => b.t - a.t || (a.name < b.name ? -1 : 1));
}
function renderPicker(){
  const q = el("d3find").value.trim().toLowerCase(), rows = pickerRows().filter(r => !q || r.name.toLowerCase().includes(q));
  let h = `<tr><th></th><th>Polygon</th><th>Cyc</th><th>t</th><th>Loader</th></tr>`;
  for (const r of rows){
    const on = S.picks.includes(r.name), tip = r.why || (r.nd ? `${r.nd} of ${r.n} cycles cannot be drawn (no bucket positions or a sensor fault)` : "");
    h += `<tr data-n="${esc(r.name)}" class="${on ? "sel" : ""}${r.off ? " off" : ""}"${tip ? ` title="${esc(tip)}"` : ""}><td><input type="checkbox"${on ? " checked" : ""}${r.off ? " disabled" : ""}></td><td>${esc(r.name)}</td><td class="n">${fmt0(r.n)}</td><td class="n">${fmt0(r.t)}</td><td>${esc(r.lo)}</td></tr>`;
  }
  if (!rows.length) h += `<tr class="off"><td colspan="5">${q ? "No polygon matches the filter" : `No polygon was dug in ${shW()}`}</td></tr>`;
  el("d3plist").innerHTML = h;
  pickerCount(rows.length);
  el("d3pall").disabled = S.win.mode === "all";
}
function pickerCount(n){
  const rows = n === undefined ? el("d3plist").querySelectorAll("tr[data-n]").length : n;
  el("d3pcount").textContent = `(${fmt0(rows)}${S.win.mode === "shift" ? ` dug in ${shW()}` : ""}${S.picks.length ? ` · ${S.picks.length} selected` : ""})`;
}
function syncPicker(){
  el("d3plist").querySelectorAll("tr[data-n]").forEach(tr => {
    const on = S.picks.includes(tr.dataset.n);
    tr.classList.toggle("sel", on); tr.querySelector("input").checked = on;
  });
  pickerCount();
}
function shiftUi(){
  const all = S.win.mode === "all", both = S.win.shift === "both", d = S.win.date, k = winKey(), K = S.shiftKeys;
  el("d3day").disabled = all;
  el("d3prev").disabled = all || !K.some(x => both ? x.slice(0, 10) < d : x < k);
  el("d3next").disabled = all || !K.some(x => both ? x.slice(0, 10) > d : x > k);
  el("d3range").style.display = all ? "" : "none";
}
function showNothing(){
  clearModel(); S.model = null; S.statsHtml = "";
  for (const id of ["d3cycles", "d3legend", "d3hud"]) el(id).innerHTML = "";
  el("d3cyccount").textContent = ""; el("d3tip").style.display = "none";
  overlay(el("d3plist").querySelector("tr[data-n]:not(.off)") ? "Pick one or more polygons on the left" : `No polygon to draw for ${shW()}`);
}
function mergedPoly(names){
  const Ps = names.map(n => S.data.polys.get(n)), rings = [], seen = new Set(), ids = new Set(), matT = {};
  for (const P of Ps){
    for (const id of P.ids) ids.add(id);
    for (const R of (P.rings || [])) if (!seen.has(R.pid)){ seen.add(R.pid); rings.push(Object.assign({}, R, {pname: P.name})); }
    for (const k in P.matT) matT[k] = (matT[k] || 0) + P.matT[k];
  }
  const cycles = [];
  for (const P of Ps) for (const c of P.cycles){     /* copies: "beyond the line" now means outside ALL the picked polygons */
    const inMask = new Uint8Array(c.pts.length); let nOut = 0;
    c.pts.forEach((p, i) => { const ok = !rings.length || rings.some(R => pointInRing(p[0], p[1], R.ring)); inMask[i] = ok ? 1 : 0; if (!ok) nOut++; });
    cycles.push(Object.assign({}, c, {pname: P.name, inMask, nOut, geoOut: rings.length ? nOut * 2 > c.pts.length : false}));
  }
  cycles.sort((a, b) => a.date < b.date ? -1 : a.date > b.date ? 1 : a.cid - b.cid);
  const lv = new Set(rings.map(R => R.bench).filter(b => b != null)), sum = f => Ps.reduce((v, P) => v + f(P), 0);
  return {pid: Ps[0].pid, name: `${Ps.length} polygons`, ids, bench: lv.size === 1 ? [...lv][0] : null, cycles, total: sum(P => P.total), t: sum(P => P.t), pts: sum(P => P.pts),
          matT, mat: Object.entries(matT).sort((a, b) => b[1] - a[1])[0]?.[0] || "?", rings, area: sum(P => P.area || 0), members: new Set(names)};
}
function applyPicks(resetView){
  S.sel = null; S.isolate = null;
  S.data.polys.delete(MULTI);
  const names = S.picks.filter(n => S.data.polys.has(n));
  clearTimeout(buildTimer);
  if (!names.length){ S.pid = null; showNothing(); return; }
  if (names.length > 1) S.data.polys.set(MULTI, mergedPoly(names));
  S.pid = names.length > 1 ? MULTI : names[0];
  if (S.win.mode === "all"){
    const C = S.data.polys.get(S.pid).cycles, d0 = C[0].date, d1 = C[C.length - 1].date;
    el("d3from").min = d0; el("d3from").max = d1; el("d3from").value = d0;
    el("d3to").min = d0; el("d3to").max = d1; el("d3to").value = d1;
  }
  scheduleBuild(resetView);
}
function setWindow(){
  const v = el("d3shift").value, before = S.picks.slice();
  S.win = v === "all" ? {mode: "all", date: el("d3day").value, shift: S.win.shift} : {mode: "shift", date: el("d3day").value, shift: v};
  shiftUi();
  renderPicker();
  /* polygons still dug in the new shift stay picked, so ‹ › follows them shift by shift */
  const avail = new Set([...el("d3plist").querySelectorAll("tr[data-n]:not(.off)")].map(tr => tr.dataset.n));
  S.picks = before.filter(n => avail.has(n));
  syncPicker();
  applyPicks(true);
}
function stepShift(dir){
  const k = winKey(), K = S.shiftKeys;
  if (S.win.shift === "both"){   /* whole days: previous / next date with digging */
    const d = S.win.date, days = [...new Set(K.map(x => x.slice(0, 10)))], td = dir < 0 ? days.filter(x => x < d).pop() : days.find(x => x > d);
    if (td){ el("d3day").value = td; setWindow(); }
    return;
  }
  const t = dir < 0 ? K.filter(x => x < k).pop() : K.find(x => x > k);
  if (!t) return;
  el("d3day").value = t.slice(0, 10); el("d3shift").value = t.slice(11);
  setWindow();
}
function initPicker(){
  const K = S.shiftKeys = [...S.data.shiftIdx.keys()].sort(), last = K[K.length - 1];
  if (last){
    el("d3day").min = K[0].slice(0, 10); el("d3day").max = last.slice(0, 10); el("d3day").value = last.slice(0, 10);
    el("d3shift").value = last.slice(11);
  } else el("d3shift").value = "all";
  S.picks = [];
  el("d3find").value = "";
  S.win = last ? {mode: "shift", date: last.slice(0, 10), shift: last.slice(11)} : {mode: "all", date: "", shift: "DS"};
  shiftUi();
  renderPicker();
  applyPicks(true);
}
el("d3find").addEventListener("input", () => renderPicker());
el("d3day").addEventListener("change", setWindow);
el("d3shift").addEventListener("change", setWindow);
el("d3prev").addEventListener("click", () => stepShift(-1));
el("d3next").addEventListener("click", () => stepShift(1));
el("d3pall").addEventListener("click", () => {
  S.picks = [...el("d3plist").querySelectorAll("tr[data-n]:not(.off)")].map(tr => tr.dataset.n);
  syncPicker(); applyPicks(true);
});
el("d3pnone").addEventListener("click", () => { S.picks = []; syncPicker(); applyPicks(true); });
el("d3plist").addEventListener("click", e => {
  const tr = e.target.closest("tr[data-n]");
  if (!tr || tr.classList.contains("off")) return;
  const n = tr.dataset.n;
  if (e.target.matches("input[type=checkbox]")) S.picks = e.target.checked ? [...S.picks.filter(x => x !== n), n] : S.picks.filter(x => x !== n);
  else S.picks = [n];
  syncPicker(); applyPicks(true);
});

function selectPoly(name){          /* whole history of one polygon; S.pid holds the polygon NAME (the map key) */
  const P = S.data && S.data.polys.get(name);
  if (!P) return;
  S.win = {mode: "all", date: S.win.date, shift: S.win.shift};
  el("d3shift").value = "all";
  S.picks = [name];
  shiftUi(); renderPicker(); applyPicks(true);
}
S.selectPoly = selectPoly;

/* outside rule: planned boundary per pass when the polygon has one, else HPGPS per cycle */
/* outside = planned boundary, per pass (user 2026-11-02: always; the HPGPS-mismatch rule and its picker were removed) */
const useGeo = P => !!(P && P.rings && P.rings.length);
const isOut = c => c.geoOut;
function polyGrades(P){
  const G = window.R4M_POLYGRADES;
  let au = null, ag = null;
  if (G) for (const id of P.ids){ const g = G.get(id); if (g){ if (au == null && g.au != null) au = g.au; if (ag == null && g.ag != null) ag = g.ag; } }
  return {au, ag};
}

/* ------------------------------------------------------------- sparse voxel grid */
const CH = 16, CH3 = CH * CH * CH;
class Grid {
  constructor(res, ox, oy, oz){
    this.res = res; this.ox = ox; this.oy = oy; this.oz = oz;
    this.chunks = new Map(); this.list = [];
    this._k = -1; this._c = null;
  }
  static key(cx, cy, cz){ return (cx * 1024 + cy) * 1024 + cz; }
  chunk(cx, cy, cz, create){
    const k = Grid.key(cx, cy, cz);
    if (k === this._k) return this._c;
    let c = this.chunks.get(k);
    if (!c && create){
      c = {cx, cy, cz, f: new Float32Array(CH3), o: new Int32Array(CH3).fill(-1), l: new Int32Array(CH3).fill(-1)};
      this.chunks.set(k, c); this.list.push(c);
    }
    if (c){ this._k = k; this._c = c; }
    return c || null;
  }
  get(i, j, k){
    if (i < 0 || j < 0 || k < 0) return 0;
    const c = this.chunk(i >> 4, j >> 4, k >> 4, false);
    return c ? c.f[((i & 15) * CH + (j & 15)) * CH + (k & 15)] : 0;
  }
  ownerAt(i, j, k){
    if (i < 0 || j < 0 || k < 0) return -1;
    const c = this.chunk(i >> 4, j >> 4, k >> 4, false);
    return c ? c.o[((i & 15) * CH + (j & 15)) * CH + (k & 15)] : -1;
  }
  labelAt(i, j, k){
    if (i < 0 || j < 0 || k < 0) return -1;
    const c = this.chunk(i >> 4, j >> 4, k >> 4, false);
    return c ? c.l[((i & 15) * CH + (j & 15)) * CH + (k & 15)] : -1;
  }
  /* raise the field at lattice point (i,j,k) to v, recording the owner */
  stamp(i, j, k, v, owner){
    const c = this.chunk(i >> 4, j >> 4, k >> 4, true);
    const idx = ((i & 15) * CH + (j & 15)) * CH + (k & 15);
    if (v > c.f[idx]){ c.f[idx] = v; c.o[idx] = owner; }
  }
}

function stampSphere(G, x, y, z, r, owner){
  const res = G.res, r2 = r * r;
  const i0 = Math.max(0, Math.ceil((x - r - G.ox) / res)), i1 = Math.floor((x + r - G.ox) / res);
  const j0 = Math.max(0, Math.ceil((y - r - G.oy) / res)), j1 = Math.floor((y + r - G.oy) / res);
  const k0 = Math.max(0, Math.ceil((z - r - G.oz) / res)), k1 = Math.floor((z + r - G.oz) / res);
  for (let i = i0; i <= i1; i++){
    const dx = G.ox + i * res - x;
    for (let j = j0; j <= j1; j++){
      const dy = G.oy + j * res - y, dxy = dx * dx + dy * dy;
      if (dxy > r2) continue;
      for (let k = k0; k <= k1; k++){
        const dz = G.oz + k * res - z, d2 = dxy + dz * dz;
        if (d2 < r2) G.stamp(i, j, k, 1 - Math.sqrt(d2) / r, owner);
      }
    }
  }
}

function stampCapsule(G, ax, ay, az, bx, by, bz, r, ownerA, ownerB){
  const res = G.res, r2 = r * r;
  const vx = bx - ax, vy = by - ay, vz = bz - az, L2 = vx * vx + vy * vy + vz * vz || 1e-9;
  const i0 = Math.max(0, Math.ceil((Math.min(ax, bx) - r - G.ox) / res)), i1 = Math.floor((Math.max(ax, bx) + r - G.ox) / res);
  const j0 = Math.max(0, Math.ceil((Math.min(ay, by) - r - G.oy) / res)), j1 = Math.floor((Math.max(ay, by) + r - G.oy) / res);
  const k0 = Math.max(0, Math.ceil((Math.min(az, bz) - r - G.oz) / res)), k1 = Math.floor((Math.max(az, bz) + r - G.oz) / res);
  for (let i = i0; i <= i1; i++){
    const px = G.ox + i * res;
    for (let j = j0; j <= j1; j++){
      const py = G.oy + j * res;
      for (let k = k0; k <= k1; k++){
        const pz = G.oz + k * res;
        let t = ((px - ax) * vx + (py - ay) * vy + (pz - az) * vz) / L2;
        t = t < 0 ? 0 : t > 1 ? 1 : t;
        const dx = px - (ax + t * vx), dy = py - (ay + t * vy), dz = pz - (az + t * vz);
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 < r2) G.stamp(i, j, k, 1 - Math.sqrt(d2) / r, t < 0.5 ? ownerA : ownerB);
      }
    }
  }
}

/* 26-connected components over lattice points with f > ISO */
function labelIslands(G){
  const sizes = [];
  let n = 0;
  const stack = [];
  for (const c of G.list){
    for (let idx = 0; idx < CH3; idx++){
      if (c.f[idx] <= ISO || c.l[idx] >= 0) continue;
      const id = n++;
      let size = 0;
      c.l[idx] = id;
      stack.push(c.cx * CH + ((idx / (CH * CH)) | 0), c.cy * CH + (((idx / CH) | 0) & 15), c.cz * CH + (idx & 15));
      while (stack.length){
        const k = stack.pop(), j = stack.pop(), i = stack.pop();
        size++;
        for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) for (let dk = -1; dk <= 1; dk++){
          if (!di && !dj && !dk) continue;
          const ii = i + di, jj = j + dj, kk = k + dk;
          if (ii < 0 || jj < 0 || kk < 0) continue;
          const cc = G.chunk(ii >> 4, jj >> 4, kk >> 4, false);
          if (!cc) continue;
          const id2 = ((ii & 15) * CH + (jj & 15)) * CH + (kk & 15);
          if (cc.f[id2] > ISO && cc.l[id2] < 0){ cc.l[id2] = id; stack.push(ii, jj, kk); }
        }
      }
      sizes.push(size);
    }
  }
  return sizes;   /* lattice points per island, index = island id */
}

/* naive surface nets over the sparse field (one vertex per mixed cell, quads across sign-changing edges) */
function surfaceNets(G){
  const res = G.res;
  const vmap = new Map();          /* cell key -> vertex index */
  const pos = [], vOwner = [], vIsland = [];
  const corner = [[0,0,0],[1,0,0],[0,1,0],[1,1,0],[0,0,1],[1,0,1],[0,1,1],[1,1,1]];
  const EDGES = [[0,1],[2,3],[4,5],[6,7],[0,2],[1,3],[4,6],[5,7],[0,4],[1,5],[2,6],[3,7]];
  const cellKey = (i, j, k) => (i * 4096 + j) * 4096 + k;
  const v = new Float64Array(8);
  const cells = [];                /* [i,j,k,mask] for the face pass */
  for (const c of G.list){
    const bi = c.cx * CH, bj = c.cy * CH, bk = c.cz * CH;
    for (let i = bi - 1; i < bi + CH; i++){
      if (i < 0) continue;
      for (let j = bj - 1; j < bj + CH; j++){
        if (j < 0) continue;
        for (let k = bk - 1; k < bk + CH; k++){
          if (k < 0) continue;
          const key = cellKey(i, j, k);
          if (vmap.has(key)) continue;      /* halo cells are shared between chunks */
          let mask = 0, best = -1, bestv = -1;
          for (let q = 0; q < 8; q++){
            const val = G.get(i + corner[q][0], j + corner[q][1], k + corner[q][2]);
            v[q] = val;
            if (val > ISO) mask |= 1 << q;
            if (val > bestv){ bestv = val; best = q; }
          }
          if (mask === 0 || mask === 255) continue;
          let sx = 0, sy = 0, sz = 0, cnt = 0;
          for (const [a, b] of EDGES){
            const va = v[a] - ISO, vb = v[b] - ISO;
            if ((va > 0) === (vb > 0)) continue;
            const t = va / (va - vb);
            sx += corner[a][0] + t * (corner[b][0] - corner[a][0]);
            sy += corner[a][1] + t * (corner[b][1] - corner[a][1]);
            sz += corner[a][2] + t * (corner[b][2] - corner[a][2]);
            cnt++;
          }
          const vi = pos.length / 3;
          pos.push(G.ox + (i + sx / cnt) * res, G.oy + (j + sy / cnt) * res, G.oz + (k + sz / cnt) * res);
          const bq = corner[best];
          vOwner.push(G.ownerAt(i + bq[0], j + bq[1], k + bq[2]));
          vIsland.push(G.labelAt(i + bq[0], j + bq[1], k + bq[2]));
          vmap.set(key, vi);
          cells.push(i, j, k, mask);
        }
      }
    }
  }
  const idx = [], fOwner = [];
  for (let n = 0; n < cells.length; n += 4){
    const i = cells[n], j = cells[n + 1], k = cells[n + 2], mask = cells[n + 3];
    const inside0 = (mask & 1) !== 0;
    const v0 = vmap.get(cellKey(i, j, k));
    /* edges from corner 0: along x (0->1), y (0->2), z (0->4); each is shared by
       the cell and its three neighbours at -1 along the other two axes */
    if (((mask >> 1) & 1) !== (mask & 1)){            /* x-edge: neighbours at -y, -z */
      const a = vmap.get(cellKey(i, j - 1, k)), b = vmap.get(cellKey(i, j - 1, k - 1)), c = vmap.get(cellKey(i, j, k - 1));
      if (a !== undefined && b !== undefined && c !== undefined) quad(v0, a, b, c, inside0);
    }
    if (((mask >> 2) & 1) !== (mask & 1)){            /* y-edge: neighbours at -z, -x */
      const a = vmap.get(cellKey(i, j, k - 1)), b = vmap.get(cellKey(i - 1, j, k - 1)), c = vmap.get(cellKey(i - 1, j, k));
      if (a !== undefined && b !== undefined && c !== undefined) quad(v0, a, b, c, inside0);
    }
    if (((mask >> 4) & 1) !== (mask & 1)){            /* z-edge: neighbours at -x, -y */
      const a = vmap.get(cellKey(i - 1, j, k)), b = vmap.get(cellKey(i - 1, j - 1, k)), c = vmap.get(cellKey(i, j - 1, k));
      if (a !== undefined && b !== undefined && c !== undefined) quad(v0, a, b, c, inside0);
    }
  }
  function quad(a, b, c, d, inside0){
    if (inside0){ idx.push(a, b, c, a, c, d); } else { idx.push(a, d, c, a, c, b); }
    fOwner.push(vOwner[a], vOwner[a]);
  }
  return {pos: new Float32Array(pos), idx: new Uint32Array(idx), vOwner: Int32Array.from(vOwner),
          vIsland: Int32Array.from(vIsland), fOwner: Int32Array.from(fOwner)};
}

/* ------------------------------------------------------------- model build */
function buildModel(P, o){
  const cycles = P.cycles.filter(c => (!o.from || c.date >= o.from) && (!o.to || c.date <= o.to)
                                   && (!o.outOnly || c.out) && (o.isolate === null || c.cid === o.isolate));
  const px = [], py = [], pz = [], pc = [], pin = [];
  cycles.forEach((c, ci) => { for (let k = 0; k < c.pts.length; k++){ const p = c.pts[k]; px.push(p[0]); py.push(p[1]); pz.push(p[2]); pc.push(ci); pin.push(c.inMask[k]); } });
  const n = px.length;
  if (!n) return null;
  const r = Math.cbrt(3 * o.vol / (4 * Math.PI));
  const res = CELL_M;
  /* segments, all limited to the connect radius D (user, 2026-11-01: links "stretch very far, almost a line"):
     passes of one cycle -> nearest-neighbour tree (Prim MST), NOT the time order - the bucket goes back and forth
     along the face, so time order drew 5-12 m pipes across ground no bucket dug; then k nearest passes of other
     cycles within D. D = 0 -> separate spheres only. */
  const D = o.conn, segs = [];
  let base = 0, nWithin = 0;
  for (const c of cycles){
    const m = c.pts.length;
    if (D > 0 && m > 1){
      const inT = new Uint8Array(m), best = new Float64Array(m).fill(Infinity), from = new Int32Array(m).fill(-1);
      best[0] = 0;
      for (let it = 0; it < m; it++){
        let u = -1;
        for (let v = 0; v < m; v++) if (!inT[v] && (u < 0 || best[v] < best[u])) u = v;
        inT[u] = 1;
        if (from[u] >= 0 && best[u] <= D){ segs.push(base + from[u], base + u); nWithin++; }
        for (let v = 0; v < m; v++) if (!inT[v]){
          const a = base + u, b = base + v, d = Math.hypot(px[a] - px[b], py[a] - py[b], pz[a] - pz[b]);
          if (d < best[v]){ best[v] = d; from[v] = u; }
        }
      }
    }
    base += m;
  }
  let nCross = 0;
  if (D > 0){
    const cell = D, hmap = new Map();
    const hk = (a, b, c) => (a * 8192 + b) * 8192 + c;
    const cx = new Int32Array(n), cy = new Int32Array(n), cz = new Int32Array(n);
    for (let i = 0; i < n; i++){
      cx[i] = Math.floor((px[i] - XLO) / cell); cy[i] = Math.floor((py[i] - YLO) / cell); cz[i] = Math.floor((pz[i] - ZLO) / cell);
      const k = hk(cx[i], cy[i], cz[i]);
      let arr = hmap.get(k); if (!arr){ arr = []; hmap.set(k, arr); }
      arr.push(i);
    }
    const D2 = D * D, done = new Set(), cand = [];
    for (let i = 0; i < n; i++){
      cand.length = 0;
      for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) for (let c = -1; c <= 1; c++){
        const arr = hmap.get(hk(cx[i] + a, cy[i] + b, cz[i] + c));
        if (!arr) continue;
        for (const j of arr){
          if (j === i || pc[j] === pc[i]) continue;
          const d2 = (px[i] - px[j]) ** 2 + (py[i] - py[j]) ** 2 + (pz[i] - pz[j]) ** 2;
          if (d2 <= D2) cand.push([d2, j]);
        }
      }
      if (!cand.length) continue;
      cand.sort((u, w) => u[0] - w[0]);
      for (let q = 0; q < Math.min(KNN, cand.length); q++){
        const j = cand[q][1], key = i < j ? i * n + j : j * n + i;
        if (done.has(key)) continue;
        done.add(key); segs.push(i, j); nCross++;
      }
    }
  }
  /* grid: origin below the bbox (lattice indices stay >= 0) */
  let minx = Infinity, maxx = -Infinity, miny = Infinity, maxy = -Infinity, minz = Infinity, maxz = -Infinity;
  for (let i = 0; i < n; i++){
    if (px[i] < minx) minx = px[i]; if (px[i] > maxx) maxx = px[i];
    if (py[i] < miny) miny = py[i]; if (py[i] > maxy) maxy = py[i];
    if (pz[i] < minz) minz = pz[i]; if (pz[i] > maxz) maxz = pz[i];
  }
  const m = r + 2 * res;
  const G = new Grid(res, Math.floor((minx - m) / res) * res, Math.floor((miny - m) / res) * res, Math.floor((minz - m) / res) * res);
  for (let i = 0; i < n; i++) stampSphere(G, px[i], py[i], pz[i], r, i);
  for (let s = 0; s < segs.length; s += 2){
    const a = segs[s], b = segs[s + 1];
    stampCapsule(G, px[a], py[a], pz[a], px[b], py[b], pz[b], r, a, b);
  }
  const islands = labelIslands(G);
  /* volumes: lattice points inside, per cycle by owner */
  const cycVox = new Int32Array(cycles.length);
  let inside = 0, outside = 0;
  for (const c of G.list) for (let q = 0; q < CH3; q++) if (c.f[q] > ISO){ inside++; if (c.o[q] >= 0){ cycVox[pc[c.o[q]]]++; if (!pin[c.o[q]]) outside++; } }
  const mesh = surfaceNets(G);
  /* island of each pass point (nearest lattice point) */
  const ptIsland = new Int32Array(n);
  for (let i = 0; i < n; i++) ptIsland[i] = G.labelAt(Math.round((px[i] - G.ox) / res), Math.round((py[i] - G.oy) / res), Math.round((pz[i] - G.oz) / res));
  const islPts = new Int32Array(islands.length);
  for (let i = 0; i < n; i++) if (ptIsland[i] >= 0) islPts[ptIsland[i]]++;
  const dates = [...new Set(cycles.map(c => c.date))].sort();
  const dateRank = new Map(dates.map((d, i) => [d, i]));
  /* display bbox = passes + planned rings (+ bench elevations) so the boundary is always framed */
  const BA = {minx, maxx, miny, maxy, minz, maxz};
  for (const R of (P.rings || [])){
    for (const [x, y] of R.ring){ if (x < BA.minx) BA.minx = x; if (x > BA.maxx) BA.maxx = x; if (y < BA.miny) BA.miny = y; if (y > BA.maxy) BA.maxy = y; }
    if (R.bench != null){ if (R.bench < BA.minz) BA.minz = R.bench; if (R.bench + BENCH_H > BA.maxz) BA.maxz = R.bench + BENCH_H; }
  }
  return {name: P.name, cycles, n, r, res, nSegs: segs.length / 2, nWithin, nCross, px, py, pz, pc, pin: Uint8Array.from(pin), G, islands, islPts, ptIsland,
          cycVox, voxVol: res * res * res, unionVol: inside * res * res * res, outVol: outside * res * res * res,
          bbox: {minx, maxx, miny, maxy, minz, maxz}, bboxAll: BA, geo: !!o.geo, mesh, dates, dateRank};
}

/* ------------------------------------------------------------- as-dug cut model (user, 2026-11-01: "as realistic dig polygon as possible")
   Plan outline = the ground the bucket reached: every dig point counts EDGE_B m around it (about half a bucket width)
   and gaps up to the "fill gaps" width between dig points are closed (morphological closing on a 2-D grid via exact
   distance transforms); holes and separate pieces stay. Floor = the dig points themselves (lowest bucket position per
   pass, R4M sensor_data): Gaussian-weighted low quantile of the dig heights near each cell. Top of cut = not measured by
   the FMS - set so that the cut volume equals the dispatched tonnes / density (flat or parallel to the floor), or a fixed
   height. Data hygiene: only the lowest-point dig rule (live 2026-10-30 18:31) by default, heights before the
   2026-10-31 geoid change lowered by 0.62 m, EX215 left out while its bucket sensor is dead, stray / height-outlier
   passes dropped. */
/* display layers are fixed (user 2026-11-02: the Display checkboxes were removed) */
const VIEW = {pts: false, edges: true, ground: true, bench: true, out: false, plan: true, dig: false, lid: false};   /* lid = cut solid, hidden since 2026-11-03 (user: the floor is enough) */
const DATUM_TO = "2026-10-31 19:00";       /* before: z = receiver geoid + 1.08 m = EGM96 + 0.62 m */
const DATUM_MIX_TO = "2026-10-31 20:00";   /* 19:03-19:29 the five ControlBoxes switched geoid -> heights of that hour not used */
const DATUM_SHIFT = 0.62;
const BAD_TIP = [{eq: "EX215", from: "2026-10-30 08:00", to: "2026-11-14 13:00", why: "EX215 bucket inclinometer dead 30 Oct 08:38 - 14 Nov (bucket angle locked to the stick); healthy again by 14 Nov 13:00"}];
const EDGE_B = 1.25;     /* m of ground counted as dug around a dig point (half a bucket width) */
const GAP_M = 5;         /* gaps between dig points up to this width are closed (user 2026-11-02: fixed 5 m, slider removed) */
const CELL_M = 0.5;      /* grid / voxel size: fine always (user 2026-11-02, Detail select removed) */
const STRAY_M = 10;      /* pass farther than this from its cycle's median position = stray */
const ZOUT_M = 3;        /* pass more than this above/below the median of its neighbours (4 m) = height outlier */
const FLOOR_Q = 0.3, FLOOR_SIG = 1.2, FLOOR_R = 3;   /* floor = weighted 30 % quantile of dig heights within 3 m (sigma 1.2 m) */
const BIG = 1e20;

const badTip = c => BAD_TIP.some(b => b.eq === c.loader && c.at >= b.from && (!b.to || c.at < b.to));

/* exact 1-D squared distance transform (Felzenszwalb-Huttenlocher) carrying the source index */
function edt1(f, src, n, out, srcOut, v, z){
  let k = -1;
  for (let q = 0; q < n; q++){
    if (f[q] >= BIG) continue;
    if (k < 0){ k = 0; v[0] = q; z[0] = -Infinity; z[1] = Infinity; continue; }
    let s = 0;
    for (;;){
      const p = v[k];
      s = ((f[q] + q * q) - (f[p] + p * p)) / (2 * q - 2 * p);
      if (s <= z[k]){ k--; if (k < 0) break; } else break;
    }
    if (k < 0){ k = 0; v[0] = q; z[0] = -Infinity; z[1] = Infinity; continue; }
    k++; v[k] = q; z[k] = s; z[k + 1] = Infinity;
  }
  if (k < 0){ for (let q = 0; q < n; q++){ out[q] = BIG; srcOut[q] = -1; } return; }
  let j = 0;
  for (let q = 0; q < n; q++){
    while (z[j + 1] < q) j++;
    const p = v[j];
    out[q] = (q - p) * (q - p) + f[p]; srcOut[q] = src[p];
  }
}
/* 2-D: seeds = cells with seed[idx] >= 0 (value = source id); returns squared distance in cells + nearest source */
function edt2(W, H, seed){
  const N = W * H, d = new Float64Array(N), s = new Int32Array(N);
  const L = Math.max(W, H), f = new Float64Array(L), src = new Int32Array(L), out = new Float64Array(L), so = new Int32Array(L);
  const v = new Int32Array(L), z = new Float64Array(L + 1);
  for (let i = 0; i < W; i++){
    for (let j = 0; j < H; j++){ const id = seed[j * W + i]; f[j] = id >= 0 ? 0 : BIG; src[j] = id; }
    edt1(f, src, H, out, so, v, z);
    for (let j = 0; j < H; j++){ d[j * W + i] = out[j]; s[j * W + i] = so[j]; }
  }
  for (let j = 0; j < H; j++){
    const o = j * W;
    for (let i = 0; i < W; i++){ f[i] = d[o + i]; src[i] = s[o + i]; }
    edt1(f, src, W, out, so, v, z);
    for (let i = 0; i < W; i++){ d[o + i] = out[i]; s[o + i] = so[i]; }
  }
  return {d, s};
}
/* even-odd scanline fill of a ring onto the grid (cell centres) */
function fillRing(mask, W, H, ox, oy, cs, ring){
  const xs = [];
  for (let j = 0; j < H; j++){
    const y = oy + (j + 0.5) * cs;
    xs.length = 0;
    for (let a = 0, b = ring.length - 1; a < ring.length; b = a++){
      const ya = ring[a][1], yb = ring[b][1];
      if ((ya > y) !== (yb > y)) xs.push(ring[a][0] + (y - ya) / (yb - ya) * (ring[b][0] - ring[a][0]));
    }
    xs.sort((p, q) => p - q);
    for (let k = 0; k + 1 < xs.length; k += 2){
      const i0 = Math.max(0, Math.ceil((xs[k] - ox) / cs - 0.5)), i1 = Math.min(W - 1, Math.floor((xs[k + 1] - ox) / cs - 0.5));
      for (let i = i0; i <= i1; i++) mask[j * W + i] ^= 1;
    }
  }
}
/* boundary loops of a cell mask (inside on the left), then Chaikin-smoothed + simplified, in world metres */
function maskLoops(F, W, H, ox, oy, cs){
  const out = new Map();     /* start vertex key -> [end vertex keys] */
  const vk = (i, j) => j * (W + 1) + i;
  const add = (a, b) => { let l = out.get(a); if (!l){ l = []; out.set(a, l); } l.push(b); };
  const inF = (i, j) => i >= 0 && j >= 0 && i < W && j < H && F[j * W + i] === 1;
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++){
    if (!F[j * W + i]) continue;
    if (!inF(i, j - 1)) add(vk(i, j), vk(i + 1, j));
    if (!inF(i + 1, j)) add(vk(i + 1, j), vk(i + 1, j + 1));
    if (!inF(i, j + 1)) add(vk(i + 1, j + 1), vk(i, j + 1));
    if (!inF(i - 1, j)) add(vk(i, j + 1), vk(i, j));
  }
  const loops = [];
  const xy = k => [ox + (k % (W + 1)) * cs, oy + Math.floor(k / (W + 1)) * cs];
  for (const [start] of out){
    while (out.get(start) && out.get(start).length){
      const ring = [start];
      let prev = start, cur = out.get(start).pop();
      while (cur !== start){
        ring.push(cur);
        const l = out.get(cur);
        if (!l || !l.length) break;
        let pick = 0;
        if (l.length > 1){   /* pinch vertex: take the left turn so diagonal pieces stay separate */
          const [px, py] = xy(prev), [cx, cy] = xy(cur), dx = cx - px, dy = cy - py;
          pick = l.findIndex(nk => { const [nx, ny] = xy(nk); return dx * (ny - cy) - dy * (nx - cx) > 0; });
          if (pick < 0) pick = 0;
        }
        prev = cur; cur = l.splice(pick, 1)[0];
      }
      if (ring.length >= 4) loops.push(ring.map(xy));
    }
  }
  return loops.map(r => {
    let p = r;
    for (let it = 0; it < 2; it++){
      const q = [];
      for (let a = 0; a < p.length; a++){
        const A = p[a], B = p[(a + 1) % p.length];
        q.push([0.75 * A[0] + 0.25 * B[0], 0.75 * A[1] + 0.25 * B[1]], [0.25 * A[0] + 0.75 * B[0], 0.25 * A[1] + 0.75 * B[1]]);
      }
      p = q;
    }
    return simplify(p, cs * 0.25);
  });
}
function simplify(pts, tol){
  if (pts.length < 8) return pts;
  const keep = new Uint8Array(pts.length); keep[0] = 1; keep[pts.length - 1] = 1;
  const st = [[0, pts.length - 1]];
  while (st.length){
    const [a, b] = st.pop();
    let best = -1, bd = tol;
    const [ax, ay] = pts[a], [bx, by] = pts[b], L = Math.hypot(bx - ax, by - ay) || 1e-9;
    for (let k = a + 1; k < b; k++){
      const d = Math.abs((bx - ax) * (ay - pts[k][1]) - (ax - pts[k][0]) * (by - ay)) / L;
      if (d > bd){ bd = d; best = k; }
    }
    if (best > 0){ keep[best] = 1; st.push([a, best], [best, b]); }
  }
  return pts.filter((_, k) => keep[k]);
}
function signedArea(r){ let a = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]); return -a / 2; }

function buildCut(P, o){
  const inWin = c => (!o.from || c.date >= o.from) && (!o.to || c.date <= o.to) && (!o.until || skey(c) <= o.until) && (!o.only || inKey(c, o.only)) && (!o.outOnly || c.out) && (o.isolate === null || c.cid === o.isolate);
  const win = P.cycles.filter(inWin);
  const drop = {old: 0, oldT: 0, bad: 0, badT: 0, stray: 0, zout: 0, zmix: 0};
  const cycles = [];
  for (const c of win){
    if (badTip(c)){ drop.bad++; drop.badT += c.t; continue; }
    cycles.push(c);
  }
  /* passes: stray test per cycle (median position), datum already applied in parse() */
  const px = [], py = [], pz = [], pc = [], zok = [], pin = [], pday = [];
  const dayIx = d => Math.round(Date.parse(d + "T00:00:00Z") / 86400000);
  cycles.forEach((c, ci) => {
    const mx = c.pts.map(p => p[0]).sort((a, b) => a - b)[c.pts.length >> 1], my = c.pts.map(p => p[1]).sort((a, b) => a - b)[c.pts.length >> 1];
    c.pts.forEach((p, k) => {
      if (Math.hypot(p[0] - mx, p[1] - my) > STRAY_M){ drop.stray++; return; }
      px.push(p[0]); py.push(p[1]); pz.push(p[2]); pc.push(ci); zok.push(c.zMix ? 0 : 1); pday.push(dayIx(c.date));
      pin.push(c.inMask[k]);
      if (c.zMix) drop.zmix++;
    });
  });
  /* height outliers vs the passes around them (4 m) */
  const hash = new Map(), HC = 4, hk = (x, y) => Math.floor(x / HC) * 1000003 + Math.floor(y / HC);
  for (let i = 0; i < px.length; i++){ const k = hk(px[i], py[i]); let a = hash.get(k); if (!a){ a = []; hash.set(k, a); } a.push(i); }
  const near = (x, y, R, fn) => {
    const gx = Math.floor(x / HC), gy = Math.floor(y / HC), n = Math.ceil(R / HC);
    for (let a = -n; a <= n; a++) for (let b = -n; b <= n; b++){
      const arr = hash.get((gx + a) * 1000003 + gy + b); if (!arr) continue;
      for (const j of arr){ const d2 = (px[j] - x) ** 2 + (py[j] - y) ** 2; if (d2 <= R * R) fn(j, d2); }
    }
  };
  const keep = new Uint8Array(px.length).fill(1);
  for (let i = 0; i < px.length; i++){
    if (!zok[i]) continue;
    const zs = [];
    near(px[i], py[i], 4, j => { if (j !== i && zok[j] && Math.abs(pday[j] - pday[i]) <= 2) zs.push(pz[j]); });
    if (zs.length >= 4){ zs.sort((a, b) => a - b); if (Math.abs(pz[i] - zs[zs.length >> 1]) > ZOUT_M){ keep[i] = 0; drop.zout++; } }
  }
  const K = []; for (let i = 0; i < px.length; i++) if (keep[i]) K.push(i);
  if (!K.length) return {empty: true, drop, nWin: win.length};
  const kx = K.map(i => px[i]), ky = K.map(i => py[i]), kz = K.map(i => pz[i]), kc = K.map(i => pc[i]), kok = K.map(i => zok[i]), kin = K.map(i => pin[i]);
  const n = K.length;
  /* grid over the passes + planned rings */
  const r = o.gap / 2, a = r + EDGE_B;
  let minx = Infinity, maxx = -Infinity, miny = Infinity, maxy = -Infinity, minz = Infinity, maxz = -Infinity;
  for (let i = 0; i < n; i++){ minx = Math.min(minx, kx[i]); maxx = Math.max(maxx, kx[i]); miny = Math.min(miny, ky[i]); maxy = Math.max(maxy, ky[i]); minz = Math.min(minz, kz[i]); maxz = Math.max(maxz, kz[i]); }
  let gx0 = minx, gx1 = maxx, gy0 = miny, gy1 = maxy;
  for (const R of (P.rings || [])) for (const [x, y] of R.ring){ gx0 = Math.min(gx0, x); gx1 = Math.max(gx1, x); gy0 = Math.min(gy0, y); gy1 = Math.max(gy1, y); }
  const span = (gx1 - gx0 + 2 * a + 4) * (gy1 - gy0 + 2 * a + 4);
  const cs = Math.max(CELL_M, Math.sqrt(span / 4000000));   /* 0.5 m; coarser only past 4 M cells (> 1 km2 window) */
  const pad = a + 2 * cs;
  const ox = Math.floor((gx0 - pad) / cs) * cs, oy = Math.floor((gy0 - pad) / cs) * cs;
  const W = Math.ceil((gx1 + pad - ox) / cs) + 1, H = Math.ceil((gy1 + pad - oy) / cs) + 1, N = W * H;
  const seed = new Int32Array(N).fill(-1);
  for (let i = 0; i < n; i++) seed[Math.floor((ky[i] - oy) / cs) * W + Math.floor((kx[i] - ox) / cs)] = i;
  const E1 = edt2(W, H, seed);
  const lim1 = (a / cs) ** 2, X = new Int32Array(N).fill(-1);
  for (let q = 0; q < N; q++) if (E1.d[q] > lim1) X[q] = 0;   /* seeds of the second transform = cells outside the dilation */
  const E2 = edt2(W, H, X);
  const lim2 = (r / cs) ** 2, F = new Uint8Array(N);
  let nF = 0;
  for (let q = 0; q < N; q++) if (E1.d[q] <= lim1 && E2.d[q] > lim2){ F[q] = 1; nF++; }
  if (!nF) return {empty: true, drop, nWin: win.length};
  /* floor: weighted low quantile of trusted dig heights near each cell */
  const floor = new Float32Array(N).fill(NaN), near1 = E1.s;
  const pairs = [];
  hash.clear();
  for (let i = 0; i < n; i++) if (kok[i]){ const k = hk(kx[i], ky[i]); let arr = hash.get(k); if (!arr){ arr = []; hash.set(k, arr); } arr.push(i); }
  const nearK = (x, y, R, fn) => {
    const gx = Math.floor(x / HC), gy = Math.floor(y / HC), m = Math.ceil(R / HC);
    for (let aa = -m; aa <= m; aa++) for (let bb = -m; bb <= m; bb++){
      const arr = hash.get((gx + aa) * 1000003 + gy + bb); if (!arr) continue;
      for (const j of arr){ const d2 = (kx[j] - x) ** 2 + (ky[j] - y) ** 2; if (d2 <= R * R) fn(j, d2); }
    }
  };
  const allZ = []; for (let i = 0; i < n; i++) if (kok[i]) allZ.push(kz[i]);
  allZ.sort((p, q) => p - q);
  const zMed = allZ.length ? allZ[allZ.length >> 1] : (minz + maxz) / 2;
  for (let q = 0; q < N; q++){
    if (!F[q]) continue;
    const x = ox + (q % W + 0.5) * cs, y = oy + (Math.floor(q / W) + 0.5) * cs;
    let R = FLOOR_R;
    for (let tries = 0; tries < 3; tries++, R *= 2){
      pairs.length = 0;
      nearK(x, y, R, (j, d2) => pairs.push([kz[j], Math.exp(-d2 / (2 * FLOOR_SIG * FLOOR_SIG * (R / FLOOR_R) ** 2))]));
      if (pairs.length) break;
    }
    if (!pairs.length){ floor[q] = zMed; continue; }
    pairs.sort((p, w) => p[0] - w[0]);
    let tw = 0; for (const p of pairs) tw += p[1];
    let acc = 0, z = pairs[pairs.length - 1][0];
    for (const p of pairs){ acc += p[1]; if (acc >= FLOOR_Q * tw){ z = p[0]; break; } }
    floor[q] = z;
  }
  /* volume to match: tonnes of the cycles that kept at least one pass */
  const used = new Uint8Array(cycles.length); for (let i = 0; i < n; i++) used[kc[i]] = 1;
  let tUsed = 0, nUsed = 0; cycles.forEach((c, ci) => { if (used[ci]){ tUsed += c.t; nUsed++; } });
  const cellA = cs * cs, V = tUsed / o.dens;
  const fl = []; for (let q = 0; q < N; q++) if (F[q]) fl.push(floor[q]);
  fl.sort((p, w) => p - w);
  const pct = f => fl[Math.min(fl.length - 1, Math.floor(f * fl.length))];
  const th = new Float32Array(N);
  let topZ = null, H0 = null;
  if (o.top === "flat" && V > 0){
    let lo = fl[0], hi = fl[fl.length - 1] + 60;
    const vol = Z => { let s = 0; for (const f of fl) if (Z > f) s += Z - f; return s * cellA; };
    for (let it = 0; it < 60; it++){ const mid = (lo + hi) / 2; if (vol(mid) < V) lo = mid; else hi = mid; }
    topZ = (lo + hi) / 2;
    for (let q = 0; q < N; q++) if (F[q]) th[q] = Math.max(0, topZ - floor[q]);
  } else {
    H0 = o.top === "fix" || !(V > 0) ? o.fixH : V / (nF * cellA);
    for (let q = 0; q < N; q++) if (F[q]) th[q] = H0;
  }
  /* planned polygon raster, comparison */
  const plan = new Uint8Array(N);
  for (const R of (P.rings || [])){ const m = new Uint8Array(N); fillRing(m, W, H, ox, oy, cs, R.ring); for (let q = 0; q < N; q++) if (m[q]) plan[q] = 1; }
  let nPlan = 0, nIn = 0, volAll = 0, volOut = 0, nThin = 0;
  for (let q = 0; q < N; q++){
    if (plan[q]) nPlan++;
    if (!F[q]) continue;
    volAll += th[q] * cellA;
    if (th[q] < 0.05) nThin++;
    if (plan[q]) nIn++; else volOut += th[q] * cellA;
  }
  /* pieces (4-connected) */
  const piece = new Int32Array(N).fill(-1), pieceA = [];
  for (let q = 0; q < N; q++){
    if (!F[q] || piece[q] >= 0) continue;
    const id = pieceA.length; let cnt = 0; const st = [q]; piece[q] = id;
    while (st.length){
      const u = st.pop(); cnt++;
      const i = u % W, j = (u - i) / W;
      if (i > 0 && F[u - 1] && piece[u - 1] < 0){ piece[u - 1] = id; st.push(u - 1); }
      if (i < W - 1 && F[u + 1] && piece[u + 1] < 0){ piece[u + 1] = id; st.push(u + 1); }
      if (j > 0 && F[u - W] && piece[u - W] < 0){ piece[u - W] = id; st.push(u - W); }
      if (j < H - 1 && F[u + W] && piece[u + W] < 0){ piece[u + W] = id; st.push(u + W); }
    }
    pieceA.push(cnt * cellA);
  }
  const ptIsland = new Int32Array(n);
  for (let i = 0; i < n; i++) ptIsland[i] = piece[Math.floor((ky[i] - oy) / cs) * W + Math.floor((kx[i] - ox) / cs)];
  const loops = maskLoops(F, W, H, ox, oy, cs).map(ring => ({ring, outer: signedArea(ring) > 0}));
  const cellsIdx = []; for (let q = 0; q < N; q++) if (F[q]) cellsIdx.push(q);
  const dates = [...new Set(cycles.map(c => c.date))].sort();
  const dateRank = new Map(dates.map((d, i) => [d, i]));
  const zTop = topZ != null ? topZ : pct(0.99) + H0;
  const BA = {minx: gx0, maxx: gx1, miny: gy0, maxy: gy1, minz: Math.min(fl[0], ...(P.rings || []).map(R => R.bench).filter(b => b != null)), maxz: Math.max(zTop, fl[fl.length - 1])};
  return {kind: "cut", name: P.name, cycles, n, px: kx, py: ky, pz: kz, pc: kc, zok: kok, pin: Uint8Array.from(kin), ptIsland,
          islands: pieceA, cs, W, H, ox, oy, F, floor, th, plan, near1, piece, cellsIdx, loops, drop, nWin: win.length,
          nUsed, tUsed, V, topZ, H0, nF, area: nF * cellA, inArea: nIn * cellA, outArea: (nF - nIn) * cellA, planArea: nPlan * cellA,
          vol: volAll, volOut, thinArea: nThin * cellA, gap: o.gap, top: o.top, dens: o.dens,
          floorP: [pct(0.1), pct(0.5), pct(0.9)], geo: !!o.geo, hasPlan: nPlan > 0,
          bbox: {minx, maxx, miny, maxy, minz: fl[0], maxz: zTop}, bboxAll: BA, dates, dateRank};
}

/* digging inside this polygon's plan that was booked to OTHER polygons (user 2026-11-03: e.g. 1200_027_L0_MW-1 was finished
   under the waste polygon 1200_027_L0_W-1 from 15:00, so it looked half dug). Up to the same To date, from any earlier date unless From was moved later than the polygon's first day (user 2026-11-09), dig points within
   +-3 m of the planned levels (another lift is not counted), same outline + floor rules (buildCut on those cycles); only
   planned cells this polygon's own digging did not reach. */
const C_OTHER = new T.Color(0x8e44ad);
function buildOther(P, M, o){
  if (!M.hasPlan || !S.data) return null;
  const bs = (P.rings || []).map(R => R.bench).filter(b => b != null);
  const zlo = (bs.length ? Math.min(...bs) : M.floorP[1]) - 3, zhi = (bs.length ? Math.max(...bs) + BENCH_H : M.floorP[1]) + 3;
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const R of P.rings) for (const [x, y] of R.ring){ x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  x0 -= EDGE_B; x1 += EDGE_B; y0 -= EDGE_B; y1 += EDGE_B;
  const inWin = c => (!o.otherFrom || c.date >= o.otherFrom) && (!o.to || c.date <= o.to) && (!o.until || skey(c) <= o.until);
  /* several picked polygons can sit on different levels: a point must be within +-3 m of the level of the ring it is in */
  const lvlOk = p => { if (!P.members) return true; let inAny = false; for (const R of P.rings){ if (!pointInRing(p[0], p[1], R.ring)) continue; inAny = true; if (R.bench == null || (p[2] >= R.bench - 3 && p[2] <= R.bench + BENCH_H + 3)) return true; } return !inAny; };
  const cyc = [];
  for (const Q of S.data.polys.values()){
    if (Q === P || Q.members || (P.members && P.members.has(Q.name))) continue;
    for (const c of Q.cycles){
      if (!inWin(c) || badTip(c)) continue;
      const pts = c.pts.filter(p => p[0] >= x0 && p[0] <= x1 && p[1] >= y0 && p[1] <= y1 && p[2] >= zlo && p[2] <= zhi && lvlOk(p));
      if (!pts.length) continue;
      cyc.push(Object.assign({}, c, {pts, inMask: new Uint8Array(pts.length), pname: Q.name, nAll: c.pts.length}));
    }
  }
  if (!cyc.length) return null;
  const Mo = buildCut({name: P.name, rings: P.rings, cycles: cyc}, Object.assign({}, o, {from: null, to: null, until: null, outOnly: false, isolate: null}));
  if (!Mo || Mo.empty || Math.abs(Mo.cs - M.cs) > 1e-9) return null;
  const di = Math.round((M.ox - Mo.ox) / M.cs), dj = Math.round((M.oy - Mo.oy) / M.cs);
  const N = M.W * M.H, O = new Uint8Array(N), fz = new Float32Array(N).fill(NaN), own = new Int32Array(N).fill(-1), cells = [];
  for (let q = 0; q < N; q++){
    if (!M.plan[q] || M.F[q]) continue;
    const i = q % M.W, j = (q - i) / M.W, ii = i + di, jj = j + dj;
    if (ii < 0 || jj < 0 || ii >= Mo.W || jj >= Mo.H) continue;
    const q2 = jj * Mo.W + ii;
    if (!Mo.F[q2]) continue;
    O[q] = 1; fz[q] = Mo.floor[q2]; const pi = Mo.near1[q2]; own[q] = pi >= 0 ? Mo.pc[pi] : -1; cells.push(q);
  }
  /* per booked polygon and per cycle: dig points inside this plan (a cycle is listed when any of its points is inside,
     even if this polygon's own digging also reached that ground) */
  const by = new Map(), inside = new Map();
  for (let k = 0; k < Mo.n; k++){
    const i = Math.floor((Mo.px[k] - M.ox) / M.cs), j = Math.floor((Mo.py[k] - M.oy) / M.cs);
    if (i < 0 || j < 0 || i >= M.W || j >= M.H || !M.plan[j * M.W + i]) continue;
    const c = Mo.cycles[Mo.pc[k]];
    let b = by.get(c.pname); if (!b){ b = {pts: 0, cyc: new Set(), first: c.at, last: c.at}; by.set(c.pname, b); }
    b.pts++; b.cyc.add(c.cid); if (c.at < b.first) b.first = c.at; if (c.at > b.last) b.last = c.at;
    inside.set(Mo.pc[k], (inside.get(Mo.pc[k]) || 0) + 1);
  }
  if (!cells.length && !inside.size) return null;
  const list = [...inside.entries()].map(([ci, n]) => ({c: Mo.cycles[ci], ci, nIn: n}));
  return {O, fz, own, cells, cycles: Mo.cycles, area: cells.length * M.cs * M.cs, by, list, px: Mo.px, py: Mo.py, pz: Mo.pz, pc: Mo.pc, n: Mo.n};
}

/* shift view: the model holds everything dug up to the end of the shift (the bench as it stood then); this marks the cells THIS shift
   dug, with the same outline rules on the shift's own cycles, and the shift cycle nearest to each cell */
const C_BEFORE = new T.Color(0x9fa7ae);
function buildFocus(P, M, o){
  const N = M.W * M.H, cellA = M.cs * M.cs, isF = c => inKey(c, o.focus), own = M.cycles.filter(isF);
  const F = {key: o.focus, mask: new Uint8Array(N), ci: new Int32Array(N).fill(-1), loops: [], area: 0, outArea: 0, otherArea: 0, cycles: own.length, t: own.reduce((v, c) => v + c.t, 0)};
  const X = M.other;
  if (X) X.cells.forEach(q => { const k = X.own[q]; if (k >= 0 && isF(X.cycles[k])) F.otherArea += cellA; });
  const Mf = buildCut(P, Object.assign({}, o, {only: o.focus}));
  if (!Mf || Mf.empty) return F;
  F.loops = Mf.loops;
  const idx = new Map(M.cycles.map((c, i) => [c, i])), same = Math.abs(Mf.cs - M.cs) < 1e-9;
  const di = Math.round((M.ox - Mf.ox) / M.cs), dj = Math.round((M.oy - Mf.oy) / M.cs);
  for (let q = 0; q < N; q++){
    if (!M.F[q]) continue;
    let ci = -1, hit = false;
    if (same){
      const i = q % M.W, j = (q - i) / M.W, ii = i + di, jj = j + dj;
      if (ii < 0 || jj < 0 || ii >= Mf.W || jj >= Mf.H) continue;
      const q2 = jj * Mf.W + ii;
      if (!Mf.F[q2]) continue;
      hit = true; const pi = Mf.near1[q2];
      if (pi >= 0){ const v = idx.get(Mf.cycles[Mf.pc[pi]]); if (v !== undefined) ci = v; }
    } else {   /* very wide selection on a coarser grid: nearest dig decides */
      const pi = M.near1[q]; if (pi < 0) continue;
      ci = M.pc[pi]; hit = isF(M.cycles[ci]);
    }
    if (!hit) continue;
    F.mask[q] = 1; F.ci[q] = ci; F.area += cellA;
    if (M.hasPlan && !M.plan[q]) F.outArea += cellA;
  }
  return F;
}
const focusOn = (M, q) => !M.focus || (M.F[q] ? !!M.focus.mask[q] : !!(M.other && M.other.own[q] >= 0 && inKey(M.other.cycles[M.other.own[q]], M.focus.key)));

/* cut meshes: floor (opaque, pickable, one quad per cell), lid + walls (translucent), toe outline */
function showCut(M){
  const {W, H, ox, oy, cs, F, floor, th, cellsIdx} = M;
  const corner = new Map();
  const cz = (i, j) => {     /* floor height at lattice corner (i, j) = mean of the dug cells touching it */
    const key = j * (W + 1) + i;
    let v = corner.get(key);
    if (v === undefined){
      let s = 0, c = 0;
      for (const [di, dj] of [[-1, -1], [0, -1], [-1, 0], [0, 0]]){ const ii = i + di, jj = j + dj; if (ii >= 0 && jj >= 0 && ii < W && jj < H && F[jj * W + ii]){ s += floor[jj * W + ii]; c++; } }
      v = c ? s / c : NaN; corner.set(key, v);
    }
    return v;
  };
  const nc = cellsIdx.length;
  const pos = new Float32Array(nc * 12), idx = new Uint32Array(nc * 6);
  for (let k = 0; k < nc; k++){
    const q = cellsIdx[k], i = q % W, j = (q - i) / W;
    const C = [[i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1]];
    C.forEach(([ii, jj], m) => { const b = 12 * k + 3 * m; pos[b] = sx(ox + ii * cs); pos[b + 1] = sy(cz(ii, jj)); pos[b + 2] = sz(oy + jj * cs); });
    const v = 4 * k; idx.set([v, v + 1, v + 2, v, v + 2, v + 3], 6 * k);
  }
  const g = new T.BufferGeometry();
  g.setAttribute("position", new T.BufferAttribute(pos, 3));
  g.setAttribute("color", new T.BufferAttribute(new Float32Array(nc * 12), 3));
  g.setIndex(new T.BufferAttribute(idx, 1));
  g.computeVertexNormals();
  S.mesh = new T.Mesh(g, new T.MeshLambertMaterial({vertexColors: true, side: T.DoubleSide}));
  S.group.add(S.mesh);
  S.wire = new T.Mesh(g, new T.MeshBasicMaterial({color: 0x1b2a33, wireframe: true, transparent: true, opacity: 0.12}));
  S.wire.visible = VIEW.edges; S.group.add(S.wire);
  /* lid + walls */
  const lp = [];
  const tz = (ii, jj, q) => M.topZ != null ? M.topZ : cz(ii, jj) + th[q];
  for (const q of cellsIdx){
    if (th[q] < 0.05) continue;
    const i = q % W, j = (q - i) / W;
    const c = [[i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1]].map(([ii, jj]) => [sx(ox + ii * cs), sy(tz(ii, jj, q)), sz(oy + jj * cs), sy(cz(ii, jj))]);
    lp.push(c[0][0], c[0][1], c[0][2], c[1][0], c[1][1], c[1][2], c[2][0], c[2][1], c[2][2], c[0][0], c[0][1], c[0][2], c[2][0], c[2][1], c[2][2], c[3][0], c[3][1], c[3][2]);
    const side = (a, b) => { lp.push(a[0], a[3], a[2], b[0], b[3], b[2], b[0], b[1], b[2], a[0], a[3], a[2], b[0], b[1], b[2], a[0], a[1], a[2]); };
    if (j === 0 || !F[q - W] || th[q - W] < 0.05) side(c[0], c[1]);
    if (i === W - 1 || !F[q + 1] || th[q + 1] < 0.05) side(c[1], c[2]);
    if (j === H - 1 || !F[q + W] || th[q + W] < 0.05) side(c[2], c[3]);
    if (i === 0 || !F[q - 1] || th[q - 1] < 0.05) side(c[3], c[0]);
  }
  const lg = new T.BufferGeometry();
  lg.setAttribute("position", new T.BufferAttribute(new Float32Array(lp), 3));
  lg.computeVertexNormals();
  S.lid = new T.Mesh(lg, new T.MeshLambertMaterial({color: 0xc9a227, transparent: true, opacity: 0.22, side: T.DoubleSide, depthWrite: false}));
  S.lid.visible = VIEW.lid; S.lid.renderOrder = 2; S.group.add(S.lid);
  /* toe outline (smoothed loops) draped on the floor */
  const og = new T.Group();
  const fz = (x, y) => {
    const i = Math.min(W - 1, Math.max(0, Math.floor((x - ox) / cs))), j = Math.min(H - 1, Math.max(0, Math.floor((y - oy) / cs)));
    if (isFinite(floor[j * W + i])) return floor[j * W + i];
    let s = 0, c = 0;   /* smoothed loops can cut a corner of an undug cell: use the dug cells next to it, not the polygon's median */
    for (let dj = -2; dj <= 2; dj++) for (let di = -2; di <= 2; di++){ const ii = i + di, jj = j + dj; if (ii >= 0 && jj >= 0 && ii < W && jj < H && isFinite(floor[jj * W + ii])){ s += floor[jj * W + ii]; c++; } }
    return c ? s / c : M.floorP[1];
  };
  for (const L of (M.focus ? M.focus.loops : M.loops)){
    const pts = L.ring.map(([x, y]) => new T.Vector3(sx(x), sy(fz(x, y)) + 0.08, sz(y)));
    og.add(new T.LineLoop(new T.BufferGeometry().setFromPoints(pts), new T.LineBasicMaterial({color: L.outer ? 0x10202a : 0x7a1f1f})));
  }
  S.outline = og; S.group.add(og);
  showOther(M);
  showBenchNow(M);
}

/* purple floor of the planned cells dug under other polygons (as-dug view) */
function showOther(M){
  const X = M.other; if (!X) return;
  const {W, H, ox, oy, cs} = M, {O, fz, cells} = X;
  const corner = new Map();
  const cz = (i, j) => {
    const key = j * (W + 1) + i;
    let v = corner.get(key);
    if (v === undefined){
      let s = 0, c = 0;
      for (const [di, dj] of [[-1, -1], [0, -1], [-1, 0], [0, 0]]){ const ii = i + di, jj = j + dj; if (ii >= 0 && jj >= 0 && ii < W && jj < H && O[jj * W + ii]){ s += fz[jj * W + ii]; c++; } }
      v = c ? s / c : NaN; corner.set(key, v);
    }
    return v;
  };
  const nc = cells.length; if (!nc) return;
  const pos = new Float32Array(nc * 12), idx = new Uint32Array(nc * 6);
  for (let k = 0; k < nc; k++){
    const q = cells[k], i = q % W, j = (q - i) / W;
    [[i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1]].forEach(([ii, jj], m) => { const b = 12 * k + 3 * m; pos[b] = sx(ox + ii * cs); pos[b + 1] = sy(cz(ii, jj)); pos[b + 2] = sz(oy + jj * cs); });
    const v = 4 * k; idx.set([v, v + 1, v + 2, v, v + 2, v + 3], 6 * k);
  }
  const g = new T.BufferGeometry();
  g.setAttribute("position", new T.BufferAttribute(pos, 3));
  g.setAttribute("color", new T.BufferAttribute(new Float32Array(nc * 12), 3));
  g.setIndex(new T.BufferAttribute(idx, 1));
  g.computeVertexNormals();
  S.other = new T.Mesh(g, new T.MeshLambertMaterial({vertexColors: true, side: T.DoubleSide}));
  S.otherIdx = cells; S.group.add(S.other);
  recolorOther();
}
/* purple, greyed like the own floor when another cycle is selected */
function recolorOther(){
  const X = S.model && S.model.other; if (!X || !S.other) return;
  const col = S.other.geometry.getAttribute("color"), tmp = new T.Color();
  X.cells.forEach((q, k) => {
    const ci = X.own[q], c = ci >= 0 ? X.cycles[ci] : null;
    tmp.copy(C_OTHER); if (S.sel !== null && (!c || c.cid !== S.sel)) tmp.lerp(C_GREY, 0.75);
    for (let m = 0; m < 4; m++) col.setXYZ(4 * k + m, tmp.r, tmp.g, tmp.b);
  });
  col.needsUpdate = true;
}
function otherHtml(q){
  const M = S.model, X = M.other, ci = X.own[q], c = ci >= 0 ? X.cycles[ci] : null;
  return `<b>${esc(S.data.polys.get(S.pid).name)}</b> &middot; <span style="color:#8e44ad;font-weight:700">dug inside this plan, booked to ${esc(c ? c.pname : "another polygon")}</span>` +
    `<br>floor ${fmt1(X.fz[q])} m` + (c ? ` &middot; nearest dig: cycle ${c.cid} &middot; ${esc(c.date)} ${esc(c.shift)} &middot; ${esc(c.truck)} loaded by ${esc(c.loader)}` : "");
}

/* ------------------------------------------------------------- one model (user 2026-11-05; "bench now" 2026-11-03): the planned block
   (planned floor .. + BENCH_H, the floor = the planners' level) with the as-dug floor subtracted = how the bench looks
   today. Undug planned cells stay at the block top, dug cells drop to the as-dug floor (never above the block top); digging
   beyond the planned line stays outside the block at its own floor (red in every colour mode), digging booked to other polygons
   is purple in every colour mode. Smooth surface (corner heights = mean of the touching cells) + walls down to the planned floor
   around the block. A polygon with no planned ring has no block: S.now stays null and the plain as-dug floor (S.mesh) is shown. */
const GRADE_TOL = 0.5;   /* m: as-dug floor within this of the planned floor = at grade (dig points are ~0.5 m) */
const C_FULL = new T.Color(0xc9a46a), C_GRADE = new T.Color(0x2a9d8f), C_OVER = new T.Color(0x1d4f91), C_WALL = new T.Color(0xa8875a);
function benchNowGrid(M){
  const {W, H, ox, oy, cs, F, floor, plan} = M, N = W * H, X = M.other;
  const P = S.data.polys.get(S.pid);
  /* overlapping planned rings with different levels (multi-lift names, e.g. 1217.5_037 = #694 @ 1225 + #949 @ 1217.5):
     floor = the lowest level, block top = the highest level + BENCH_H */
  const base = new Float32Array(N).fill(NaN), topB = new Float32Array(N).fill(NaN);
  for (const R of (P.rings || [])){
    const b = R.bench != null ? +R.bench : M.floorP[1];
    const m = new Uint8Array(N); fillRing(m, W, H, ox, oy, cs, R.ring);
    for (let q = 0; q < N; q++) if (m[q] && plan[q]){
      if (!(base[q] <= b)) base[q] = b;
      if (!(topB[q] >= b + BENCH_H)) topB[q] = b + BENCH_H;
    }
  }
  /* st: 0 not shown, 1 untouched, 2 partly dug (floor still above grade), 3 at grade, 4 below the planned floor, 5 dug beyond the planned line
     fz: the real as-dug floor of a dug cell (z is capped at the block top) */
  const z = new Float32Array(N).fill(NaN), fzs = new Float32Array(N).fill(NaN), st = new Uint8Array(N), A = [0, 0, 0, 0, 0, 0];
  const cellA = cs * cs;
  let volPlan = 0, volLeft = 0, otherA = 0;
  for (let q = 0; q < N; q++){
    if (plan[q] && isFinite(base[q])){
      const b = base[q], top = topB[q];
      volPlan += (top - b) * cellA;
      const dugO = !F[q] && X && X.O[q];   /* dug, but booked to another polygon */
      if (!F[q] && !dugO){ z[q] = top; st[q] = 1; }
      else { const fz = F[q] ? floor[q] : X.fz[q]; fzs[q] = fz; z[q] = Math.min(top, fz); st[q] = fz > b + GRADE_TOL ? 2 : fz >= b - GRADE_TOL ? 3 : 4; if (dugO) otherA += cellA; }
      volLeft += Math.max(0, z[q] - b) * cellA;
    } else if (F[q]){ fzs[q] = z[q] = floor[q]; st[q] = 5; }
    if (st[q]) A[st[q]] += cellA;
  }
  return {base, top: topB, z, fz: fzs, st, A, volPlan, volLeft, otherA};
}
function benchCellColor(G, q, tmp){
  const s = G.st[q];
  if (s === 5) return tmp.copy(C_OUT);
  if (s === 4) return tmp.copy(C_OVER);
  return tmp.copy(C_GRADE).lerp(C_FULL, Math.max(0, Math.min(1, (G.z[q] - G.base[q]) / ((G.top[q] - G.base[q]) || BENCH_H))));
}
function showBenchNow(M){
  if (!M.hasPlan) return;
  const G = M.now || (M.now = benchNowGrid(M));
  const {W, H, ox, oy, cs} = M, {z, st, base, fz} = G;
  const idxs = []; for (let q = 0; q < W * H; q++) if (st[q]) idxs.push(q);
  if (!idxs.length) return;
  /* a corner touching an undug cell stays at the block top, so the top is flat and the cut face lies in the first row of dug cells */
  const corner = new Map(), onTop = new Set();
  const cz = (i, j) => {
    const key = j * (W + 1) + i;
    let v = corner.get(key);
    if (v === undefined){
      let s = 0, c = 0, su = 0, cu = 0;
      for (const [di, dj] of [[-1, -1], [0, -1], [-1, 0], [0, 0]]){ const ii = i + di, jj = j + dj; if (ii >= 0 && jj >= 0 && ii < W && jj < H && st[jj * W + ii]){ const qq = jj * W + ii; s += z[qq]; c++; if (st[qq] === 1){ su += z[qq]; cu++; } } }
      v = cu ? su / cu : c ? s / c : NaN; corner.set(key, v);
      if (cu) onTop.add(key);
    }
    return v;
  };
  /* corner floor height for the elevation colours: mean of the DUG cells touching it, so the ramp up to the block does not tint the floor */
  const cf = (i, j) => {
    let s = 0, c = 0;
    for (const [di, dj] of [[-1, -1], [0, -1], [-1, 0], [0, 0]]){ const ii = i + di, jj = j + dj; if (ii >= 0 && jj >= 0 && ii < W && jj < H && isFinite(fz[jj * W + ii])){ s += fz[jj * W + ii]; c++; } }
    return c ? s / c : NaN;
  };
  const nc = idxs.length;
  const pos = new Float32Array(nc * 12), idx = new Uint32Array(nc * 6), fzv = new Float32Array(nc * 4), raised = new Uint8Array(nc * 4);
  const wp = [], wc = [];
  const open = n => !st[n] || st[n] === 5;   /* the block needs a wall on this side (the digging beyond the line has no block under it) */
  for (let k = 0; k < nc; k++){
    const q = idxs[k], i = q % W, j = (q - i) / W;
    const C = [[i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1]];
    C.forEach(([ii, jj], m) => { const b = 12 * k + 3 * m; pos[b] = sx(ox + ii * cs); pos[b + 1] = sy(cz(ii, jj)); pos[b + 2] = sz(oy + jj * cs); fzv[4 * k + m] = st[q] > 1 ? cf(ii, jj) : NaN; raised[4 * k + m] = onTop.has(jj * (W + 1) + ii) ? 1 : 0; });
    const v = 4 * k; idx.set([v, v + 1, v + 2, v, v + 2, v + 3], 6 * k);
    /* walls of the planned block down to the planned floor where the neighbour is not shown */
    if (st[q] >= 1 && st[q] <= 4){
      const b0 = base[q];
      const wall = (A, B) => {
        const za = cz(A[0], A[1]), zb = cz(B[0], B[1]);
        if (!(za > b0 + 0.05 || zb > b0 + 0.05)) return;
        const xa = sx(ox + A[0] * cs), ya = sz(oy + A[1] * cs), xb = sx(ox + B[0] * cs), yb = sz(oy + B[1] * cs);
        const lo = sy(b0);
        wp.push(xa, lo, ya, xb, lo, yb, xb, sy(Math.max(zb, b0)), yb, xa, lo, ya, xb, sy(Math.max(zb, b0)), yb, xa, sy(Math.max(za, b0)), ya);
        for (let m = 0; m < 6; m++) wc.push(C_WALL.r, C_WALL.g, C_WALL.b);
      };
      if (j === 0 || open(q - W)) wall(C[0], C[1]);
      if (i === W - 1 || open(q + 1)) wall(C[1], C[2]);
      if (j === H - 1 || open(q + W)) wall(C[2], C[3]);
      if (i === 0 || open(q - 1)) wall(C[3], C[0]);
    }
  }
  const grp = new T.Group();
  const g = new T.BufferGeometry();
  g.setAttribute("position", new T.BufferAttribute(pos, 3));
  g.setAttribute("color", new T.BufferAttribute(new Float32Array(nc * 12), 3));
  g.setIndex(new T.BufferAttribute(idx, 1));
  g.computeVertexNormals();
  const surf = new T.Mesh(g, new T.MeshLambertMaterial({vertexColors: true, side: T.DoubleSide}));
  grp.add(surf);
  let wallMesh = null;
  if (wp.length){
    const wg = new T.BufferGeometry();
    wg.setAttribute("position", new T.BufferAttribute(new Float32Array(wp), 3));
    wg.setAttribute("color", new T.BufferAttribute(new Float32Array(wc), 3));
    wg.computeVertexNormals();
    wallMesh = new T.Mesh(wg, new T.MeshLambertMaterial({vertexColors: true, side: T.DoubleSide}));
    grp.add(wallMesh);
  }
  grp.visible = false;
  S.now = grp; S.nowMesh = surf; S.nowWall = wallMesh; S.nowIdx = idxs; S.nowFz = fzv; S.nowRaised = raised; S.group.add(grp);
  /* toe outline: stays at the floor (the foot of the cut face) and is drawn through the block's walls */
  if (S.outline) S.outline.children.forEach(line => { line.material.depthTest = false; line.renderOrder = 3; });
}
function applyView(){
  const now = !!S.now;   /* the block needs a planned ring; without one the plain as-dug floor stays */
  if (S.mesh) S.mesh.visible = !now;
  if (S.wire) S.wire.visible = !now && VIEW.edges;
  if (S.now) S.now.visible = now;
  if (S.other) S.other.visible = !now;   /* its cells are part of the surface, in purple */
  if (S.plan) S.plan.children.forEach(o => { if (o.userData.prism) o.visible = !now; });   /* the block replaces the orange prism */
}
/* surface colours: not dug = tan, booked to another polygon = purple, beyond the planned line = red, in every mode; the rest of the dug floor follows the Colour picker */
function recolorNow(){
  const M = S.model, G = M.now, X = M.other, mode = el("d3color").value, tmp = new T.Color();
  const col = S.nowMesh.geometry.getAttribute("color");
  const z0 = M.floorP[0] - 0.3, z1 = M.floorP[2] + 0.3;
  S.nowIdx.forEach((q, k) => {
    const s = G.st[q], dugO = !M.F[q] && !!X && !!X.O[q];
    const inS = s === 1 || focusOn(M, q);
    const pi = M.F[q] ? M.near1[q] : -1, fi = M.focus && M.F[q] ? M.focus.ci[q] : -1, ci = fi >= 0 ? fi : pi >= 0 ? M.pc[pi] : -1;
    const c = dugO ? (X.own[q] >= 0 ? X.cycles[X.own[q]] : null) : ci >= 0 ? M.cycles[ci] : null;
    for (let m = 0; m < 4; m++){
      if (s === 1 || S.nowRaised[4 * k + m]){ col.setXYZ(4 * k + m, C_FULL.r, C_FULL.g, C_FULL.b); continue; }   /* block top; a cut face shades from tan to the floor's colour */
      if (!inS){ col.setXYZ(4 * k + m, C_BEFORE.r, C_BEFORE.g, C_BEFORE.b); continue; }   /* dug before this shift */
      if (dugO) tmp.copy(C_OTHER);
      else if (s === 5) tmp.copy(C_OUT);
      else if (mode === "grade") benchCellColor(G, q, tmp);
      else if (mode === "elev") elevColor((S.nowFz[4 * k + m] - z0) / (z1 - z0), tmp);
      else if (mode === "comp") tmp.copy(C_IN);
      else if (mode === "date") tmp.copy(C_D0).lerp(C_D1, c ? M.dateRank.get(c.date) / Math.max(1, M.dates.length - 1) : 0);
      else tmp.copy(ci >= 0 ? PAL[ci % PAL.length] : C_GREY);
      if (S.sel !== null && (!c || c.cid !== S.sel)) tmp.lerp(C_GREY, 0.75);
      col.setXYZ(4 * k + m, tmp.r, tmp.g, tmp.b);
    }
  });
  col.needsUpdate = true;
}
function cellTitle(P, M, q, own){
  if (!P.members) return P.name;
  const i = q % M.W, j = (q - i) / M.W, x = M.ox + (i + 0.5) * M.cs, y = M.oy + (j + 0.5) * M.cs;
  for (const R of P.rings) if (pointInRing(x, y, R.ring)) return R.pname;
  return own && own.pname ? own.pname : P.name;
}
function benchHtml(q){
  const M = S.model, G = M.now, s = G.st[q], b = G.base[q], f = G.fz[q];
  const P = S.data.polys.get(S.pid);
  const sg = v => (v >= 0 ? "+" : "&minus;") + fmt1(Math.abs(v));
  const txt = s === 1 ? `not dug yet &middot; ${fmt1(G.top[q] - b)} m of the planned block above the planned floor ${fmt1(b)} m`
    : s === 2 ? `partly dug &middot; floor ${fmt1(f)} m, still ${fmt1(f - b)} m above the planned floor ${fmt1(b)} m`
    : s === 3 ? `dug to grade &middot; floor ${fmt1(f)} m (planned ${fmt1(b)} m, ${sg(f - b)} m)`
    : s === 4 ? `<span style="color:#1d4f91;font-weight:700">dug below the planned floor</span> &middot; floor ${fmt1(f)} m, ${fmt1(b - f)} m under ${fmt1(b)} m`
    : `<span style="color:#d62828;font-weight:700">dug beyond the planned line</span> &middot; floor ${fmt1(f)} m`;
  const pi = M.F[q] ? M.near1[q] : -1, X = M.other, oc = !M.F[q] && X && X.O[q] && X.own[q] >= 0 ? X.cycles[X.own[q]] : null;
  const fi = M.focus && M.F[q] ? M.focus.ci[q] : -1, c = fi >= 0 ? M.cycles[fi] : pi >= 0 ? M.cycles[M.pc[pi]] : oc;
  return `<b>${esc(cellTitle(P, M, q, oc ? null : c))}</b> &middot; ${txt}` + (s !== 1 && !focusOn(M, q) ? `<br><b>dug before ${shW()}</b>` : "") + (oc ? `<br><span style="color:#8e44ad;font-weight:700">booked to ${esc(oc.pname)}</span>` : "") +
    (c ? `<br>nearest dig: cycle ${c.cid} &middot; ${esc(c.date)} ${esc(c.shift)} &middot; ${esc(c.truck)} loaded by ${esc(c.loader)}` +
         (oc ? "" : `<br>${c.pts.length} passes &middot; ${fmt1(c.t)} t`) : "");
}
const C_E0 = new T.Color(0x23408e), C_E1 = new T.Color(0x2bb3a3), C_E2 = new T.Color(0xf2d94e);
function elevColor(t, tmp){ t = Math.max(0, Math.min(1, t)); return t < 0.5 ? tmp.copy(C_E0).lerp(C_E1, t * 2) : tmp.copy(C_E1).lerp(C_E2, (t - 0.5) * 2); }
function recolorCut(){
  const M = S.model, tmp = new T.Color(), sel = el("d3color").value, mode = sel === "grade" ? "elev" : sel;   /* no plan = no grade to compare with */
  const col = S.mesh.geometry.getAttribute("color"), pos = S.mesh.geometry.getAttribute("position");
  const z0 = M.floorP[0] - 0.3, z1 = M.floorP[2] + 0.3;
  M.cellsIdx.forEach((q, k) => {
    const pi = M.near1[q], ci = pi >= 0 ? M.pc[pi] : -1, c = ci >= 0 ? M.cycles[ci] : null;
    for (let m = 0; m < 4; m++){
      if (mode === "elev"){ elevColor((pos.getY(4 * k + m) + ORG.z - z0) / (z1 - z0), tmp); }
      else if (mode === "comp") tmp.copy(!M.hasPlan ? C_IN : (M.plan[q] ? C_IN : C_OUT));
      else if (mode === "island") tmp.copy(PAL[M.piece[q] % PAL.length]);
      else if (mode === "date") tmp.copy(C_D0).lerp(C_D1, c ? M.dateRank.get(c.date) / Math.max(1, M.dates.length - 1) : 0);
      else tmp.copy(ci >= 0 ? PAL[ci % PAL.length] : C_GREY);
      if (M.focus && !M.focus.mask[q]) tmp.copy(C_BEFORE);
      if (S.sel !== null && (!c || c.cid !== S.sel)) tmp.lerp(C_GREY, 0.75);
      col.setXYZ(4 * k + m, tmp.r, tmp.g, tmp.b);
    }
  });
  col.needsUpdate = true;
}

/* exports for the surveyors: toe outline as 3-D DXF polylines (+ planned polygon), floor grid as CSV */
function download(name, text, type){
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], {type}));
  a.download = name; document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}
function cutFileBase(M){ return `asdug_${M.name.replace(/[^\w.-]+/g, "_")}_${M.focus ? `${S.win.date}_${S.win.shift}` : `${M.dates[0]}_${M.dates[M.dates.length - 1]}`}`; }
function exportDxf(){
  const M = S.model; if (!M || M.kind !== "cut") return;
  const P = S.data.polys.get(S.pid);
  const f = (x) => x.toFixed(3);
  let s = "0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n0\nENDSEC\n0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n3\n";
  for (const [ly, c] of [["ASDUG_TOE", 1], ["ASDUG_HOLE", 6], ["PLANNED", 30]]) s += `0\nLAYER\n2\n${ly}\n70\n0\n62\n${c}\n6\nCONTINUOUS\n`;
  s += "0\nENDTAB\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n";
  const poly = (ly, ring, zf) => {
    s += `0\nPOLYLINE\n8\n${ly}\n66\n1\n10\n0.0\n20\n0.0\n30\n0.0\n70\n9\n`;
    for (const [x, y] of ring) s += `0\nVERTEX\n8\n${ly}\n10\n${f(x)}\n20\n${f(y)}\n30\n${f(zf(x, y))}\n70\n32\n`;
    s += `0\nSEQEND\n8\n${ly}\n`;
  };
  const fz = (x, y) => { const i = Math.min(M.W - 1, Math.max(0, Math.floor((x - M.ox) / M.cs))), j = Math.min(M.H - 1, Math.max(0, Math.floor((y - M.oy) / M.cs))); const v = M.floor[j * M.W + i]; return isFinite(v) ? v : M.floorP[1]; };
  for (const L of (M.focus ? M.focus.loops : M.loops)) poly(L.outer ? "ASDUG_TOE" : "ASDUG_HOLE", L.ring, fz);
  for (const R of (P.rings || [])) poly("PLANNED", R.ring, () => R.bench != null ? R.bench : M.floorP[1]);
  s += "0\nENDSEC\n0\nEOF\n";
  download(cutFileBase(M) + ".dxf", s, "application/dxf");
}
function exportCsv(){
  const M = S.model; if (!M || M.kind !== "cut") return;
  let s = `# as-dug floor of ${M.name}, ${M.focus ? `cells dug in the ${S.win.date} ${SHIFT_NAME[S.win.shift]}` : `${M.dates[0]}..${M.dates[M.dates.length - 1]}`}; UTM 47N (WGS84), heights EGM96 m (C4M shovel datum since 2026-10-31); cell ${M.cs} m\n`;
  s += "x,y,floor_z,inside_planned,last_dug,cycle\n";
  for (const q of M.cellsIdx){
    if (M.focus && !M.focus.mask[q]) continue;
    const i = q % M.W, j = (q - i) / M.W, pi = M.near1[q], fi = M.focus ? M.focus.ci[q] : -1, c = fi >= 0 ? M.cycles[fi] : pi >= 0 ? M.cycles[M.pc[pi]] : null;
    s += `${(M.ox + (i + 0.5) * M.cs).toFixed(2)},${(M.oy + (j + 0.5) * M.cs).toFixed(2)},${M.floor[q].toFixed(2)},${M.hasPlan ? M.plan[q] : ""},${c ? c.date : ""},${c ? c.cid : ""}\n`;
  }
  download(cutFileBase(M) + "_floor.csv", s, "text/csv");
}

/* Cycles CSV (user 2026-11-06, R4M cube only): every cycle booked to the chosen polygon (same name group and filters as parse()) in
   the From/To window, with or without bucket GPS, then the cycles booked elsewhere that dug inside this plan (the table's purple
   rows). production + dimensions come from the shared cycleRows(); cycle_times + raw sensor_data are fetched per export and not kept
   in memory (about 16 MB). Coordinates in metres; heights as recorded (no 0.62 m correction for before the 2026-10-31 geoid change). */
const csvTime = d => isNaN(d) ? "" : new Date(d.getTime() + 8 * 3600000).toISOString().slice(0, 23).replace("T", " ");   /* mine time, UTC+8 */
function csvCell(v){
  if (v === null || v === undefined) return "";
  const s = v instanceof Date ? csvTime(v) : typeof v === "number" ? String(+v.toFixed(6)) : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
const cmToM = v => v === null || v === undefined ? null : v / 100;
function coorsM(s){   /* [{"x":..,"y":..,"z":..} in cm, ...] -> "x y z; x y z" in metres */
  if (!s) return null;
  try { return JSON.parse(s).filter(p => p && p.x != null && p.y != null && p.z != null).map(p => `${p.x / 100} ${p.y / 100} ${p.z / 100}`).join("; "); }
  catch (e){ return s; }
}
function cycleCsvColumns(R, emp, crew, timeKeys){
  const by = (rows, id) => new Map((rows || []).map(r => [r[id], r]));
  const polyD = by(R.poly, "Id Polygon"), eqD = by(R.equip, "Id Equipment"), matD = by(R.mat, "Id Material"),
        empD = by(emp, "Id Employee"), crewD = by(crew, "Id Crew"), loadD = by(R.lload, "Id Location Load"), dumpD = by(R.dump, "Id Location Dump");
  const pr = k => [k, x => x.r[k]];
  const dm = (label, D, id, f) => [label, x => { const d = D.get(x.r[id]); return d ? d[f] : null; }];
  const sn = (label, f) => [label, x => x.se ? f(x.se) : null];
  return [
    ["Booked To", x => x.group],
    ...["C4M ID Hauling", "Date Cube Loading", "Loading Shift", "Loading Hour", "Loading Hour position",
        "Date Cube Hauling", "Hauling Shift", "Hauling Hour", "Hauling Hour position"].map(pr),
    pr("Id Polygon"), ...["Polygon", "Polygon Detail Name", "Bench", "Lithology", "Disturbance", "Is Split", "Initial Tonnes", "Mined Tonnes"].map(f => dm(f, polyD, "Id Polygon", f)),
    pr("Polygon HPGPS"), dm("Polygon HPGPS Name", polyD, "Polygon HPGPS", "Polygon"),
    pr("Id Material"), ...["Material Code", "Material Name", "Material Group Name", "Material Group Description"].map(f => dm(f, matD, "Id Material", f)),
    pr("Id Equipment Loading"), dm("Loading Equipment", eqD, "Id Equipment Loading", "Equipment"), dm("Loading Fleet Type", eqD, "Id Equipment Loading", "Fleet Type"), dm("Loading Fleet Category", eqD, "Id Equipment Loading", "Fleet Category"),
    pr("Id Employee Loading"), dm("Loading Operator", empD, "Id Employee Loading", "Complete Name"),
    pr("Id Crew Loading"), dm("Loading Crew", crewD, "Id Crew Loading", "Crew"),
    pr("Id Equipment Hauling"), dm("Hauling Equipment", eqD, "Id Equipment Hauling", "Equipment"), dm("Hauling Fleet Type", eqD, "Id Equipment Hauling", "Fleet Type"), dm("Hauling Fleet Category", eqD, "Id Equipment Hauling", "Fleet Category"),
    pr("Id Employee Hauling"), dm("Hauling Operator", empD, "Id Employee Hauling", "Complete Name"),
    pr("Id Crew Hauling"), dm("Hauling Crew", crewD, "Id Crew Hauling", "Crew"),
    pr("Id Location Load"), ...[["Load Mine", "Mine"], ["Load Zone", "Zone"], ["Load Region", "Region"], ["Location Load", "Location Load"], ["Load Level", "Level"]].map(([l, f]) => dm(l, loadD, "Id Location Load", f)),
    pr("Id Location Dump"), ...[["Dump Mine", "Mine"], ["Dump Zone", "Zone"], ["Dump Region", "Region"], ["Location Dump", "Location Dump"], ["Dump Level", "Level"]].map(([l, f]) => dm(l, dumpD, "Id Location Dump", f)),
    ...["Combination ID", "It is reportable for production", "It is real times", "Dry Tonnes", "Nominal Tonnes", "Sensor Tonnes", "Factor Tonnes", "Number of passes", "Angle of rotation",
        "Distance Loaded (m)", "Distance Empty (m)", "Loaded EFH (Km)", "Empty EFH (Km)", "Loaded Speed (Km/h)", "Empty Speed (Km/h)"].map(pr),
    ...timeKeys.map(k => [k, x => x.tm ? x.tm[k] : null]),
    sn("Hauling X at Dump (m)", s => cmToM(s["Hauling Coor X at Dump"])), sn("Hauling Y at Dump (m)", s => cmToM(s["Hauling Coor Y at Dump"])), sn("Hauling Z at Dump (m)", s => cmToM(s["Hauling Coor Z at Dump"])),
    sn("Loading Bucket X (m)", s => s["Loading Bucket X Coordinate"]), sn("Loading Bucket Y (m)", s => s["Loading Bucket Y Coordinate"]), sn("Loading Bucket Z (m)", s => s["Loading Bucket Z Coordinate"]),
    sn("Loading Bucket Passes, x y z (m)", s => coorsM(s["Loading Bucket Coors"])),
    sn("Loading Equipment X (m)", s => s["Loading Equipment X Coordinate"]), sn("Loading Equipment Y (m)", s => s["Loading Equipment Y Coordinate"]), sn("Loading Equipment Z (m)", s => s["Loading Equipment Z Coordinate"]),
    sn("Loading Equipment At Passes, x y z (m)", s => coorsM(s["Loading Equipment Coors"])),
    ["In 3D Model", x => x.inModel], ["Dig Points", x => x.nPts], ["Dig Points Inside Plan", x => x.nIn]
  ];
}
async function exportCycles(){
  const P = S.data && S.data.polys.get(S.pid);
  if (!P){ status("cycle CSV: the cycle data is not loaded yet"); return; }
  const M = S.model && S.model.name === P.name ? S.model : null;
  const shiftW = S.win.mode === "shift", wk = winKey();
  const from = shiftW ? "" : el("d3from").value, to = shiftW ? "" : el("d3to").value;
  const btn = el("d3cyccsv"); btn.disabled = true;
  try {
    const L = window.R4M_LIVE, R = await L.cycleRows();
    status(`cycle CSV: fetching cycle times + sensor data for ${P.name}…`);
    const [tmR, seR, emp, crew] = await Promise.all([
      L.fetchYearScopedEx("cycle_times", "facts", {month: "all"}), L.fetchYearScopedEx("sensor_data", "facts", {month: "all"}),
      L.fetchDim("employee"), L.fetchDim("crew")]);
    const eq = new Map(R.equip.map(r => [r["Id Equipment"], String(r["Equipment"] || "")]));
    const vc = new Map(P.cycles.map(c => [c.cid, c]));
    const inModel = new Set(M ? M.cycles.map(c => c.cid) : []);
    const other = new Map((M && M.other ? M.other.list : []).filter(o => !shiftW || inKey(o.c, wk)).map(o => [o.c.cid, o]));
    const own = [], oth = [];
    for (const r of R.prod){
      const cid = r["C4M ID Hauling"];
      if (other.has(cid)){
        const o = other.get(cid);
        oth.push({r, group: `other polygon (${o.c.pname}), dug inside this plan`, inModel: "yes, other polygon", nPts: o.c.nAll, nIn: o.nIn});
        continue;
      }
      if (r["It is reportable for production"] !== true || !P.ids.has(r["Id Polygon"]) || EXCLUDE_EQ.has(eq.get(r["Id Equipment Loading"]) || "")) continue;
      const d = String(r["Date Cube Hauling"]).slice(0, 10);
      if ((from && d < from) || (to && d > to)) continue;
      if (shiftW && !inKey({date: d, shift: {A: "DS", B: "NS"}[r["Hauling Shift"]] || r["Hauling Shift"]}, wk)) continue;
      const c = vc.get(cid);
      own.push({r, group: "this polygon", inModel: inModel.has(cid) ? "yes" : !c ? "no, no bucket GPS" : badTip(c) ? "no, bucket sensor fault" : "no",
                nPts: c ? c.pts.length : null, nIn: c && P.rings.length ? c.pts.length - c.nOut : null});
    }
    if (!own.length && !oth.length){ status(`cycle CSV: no cycles of ${P.name} in this window`); return; }
    const want = new Map([...own, ...oth].map(x => [x.r["C4M ID Hauling"], x]));
    for (const t of tmR.rows){ const x = want.get(t["C4M ID Hauling"]); if (x) x.tm = t; }
    for (const s of seR.rows){ const x = want.get(s["C4M ID Hauling"]); if (x) x.se = s; }
    const timeKeys = tmR.rows.length ? Object.keys(tmR.rows[0]).filter(k => k !== "C4M ID Hauling") : [];
    const LOADED = "Cycle Hauling (06) Time Loading Register Date";
    const key = x => String((x.tm && x.tm[LOADED]) || x.r["Date Cube Hauling"] || "");
    const order = (a, b) => key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : a.r["C4M ID Hauling"] - b.r["C4M ID Hauling"];
    const cols = cycleCsvColumns(R, emp, crew, timeKeys);
    const lines = [cols.map(c => csvCell(c[0])).join(",")];
    for (const x of [...own.sort(order), ...oth.sort(order)]) lines.push(cols.map(c => csvCell(c[1](x))).join(","));
    const base = P.name.replace(/[^\w.-]+/g, "_");
    download(`cycles_${base}_${shiftW ? `${S.win.date}_${S.win.shift}` : `${from || "start"}_${to || "end"}`}.csv`, "﻿" + lines.join("\r\n") + "\r\n", "text/csv;charset=utf-8");
    status(`cycle CSV: ${fmt0(own.length)} cycles of ${P.name}` + (oth.length ? ` + ${fmt0(oth.length)} booked to other polygons` : ""));
  } catch (e){
    console.warn("DIG3D cycle CSV failed:", e);
    status(`cycle CSV failed: ${e && e.auth ? "session expired, sign in to R4M" : (e && e.message) || "network error"}`);
  } finally { btn.disabled = false; }
}

function benchTxt(M){
  if (!M.hasPlan) return "";
  const G = M.now || (M.now = benchNowGrid(M));
  if (!G.volPlan) return "";
  return `<span class="k">Bench now</span> <b>${fmt0((1 - G.volLeft / G.volPlan) * 100)}%</b> of the planned block removed ` +
    `<span class="k">(planned floor + ${fmt1(BENCH_H)} m)</span> &middot; at grade ${fmt0(G.A[3])} m&sup2; &middot; partly dug ${fmt0(G.A[2])} m&sup2; &middot; ` +
    `not dug ${fmt0(G.A[1])} m&sup2;${G.A[4] ? ` &middot; <span style="color:#1d4f91">below the planned floor ${fmt0(G.A[4])} m&sup2;</span>` : ""}` +
    `${G.otherA ? ` <span class="k">(incl. ${fmt0(G.otherA)} m&sup2; dug under other polygons)</span>` : ""}<br>`;
}
function renderCutStats(M){
  const P = S.data.polys.get(S.pid), D = M.drop;
  const bench = P.bench != null ? +P.bench : null;
  const rel = z => bench != null ? ` <span class="k">(bench ${z - bench >= 0 ? "+" : "&minus;"}${fmt1(Math.abs(z - bench))})</span>` : "";
  const dropTxt = [D.bad ? `${fmt0(D.bad)} EX215 cycles (bucket sensor dead, ${fmt0(D.badT)} t)` : "",
                   D.stray ? `${fmt0(D.stray)} stray passes (&gt; ${STRAY_M} m from their load)` : "", D.zout ? `${fmt0(D.zout)} height outliers (&gt; ${ZOUT_M} m off)` : "",
                   D.zmix ? `${fmt0(D.zmix)} passes of 31 Oct 19 h used for the outline only (geoid switch)` : ""].filter(Boolean).join(" &middot; ");
  const X = M.other;
  const otherTxt = X ? `<span class="k">Dug under other polygons</span> <b style="color:#8e44ad">${fmt0(X.area)} m&sup2;</b> of this plan &middot; booked to ` +
      [...X.by.entries()].sort((a, b) => b[1].pts - a[1].pts).slice(0, 4).map(([n, b]) => `<b>${esc(n)}</b> (${fmt0(b.cyc.size)} cycles, ${fmt0(b.pts)} dig points, ${esc(b.first.slice(5))}&ndash;${esc(b.last.slice(11))})`).join(", ") + "<br>" : "";
  const planTxt = M.hasPlan
    ? `<span class="k">Planned polygon (R4M)</span> ${fmt0(M.planArea)} m&sup2; &middot; <b>${fmt0(M.inArea / M.planArea * 100)}%</b> of it dug in this window` +
      `${X ? ` <span class="k">(${fmt0((M.inArea + X.area) / M.planArea * 100)}% with the digging booked to other polygons)</span>` : ""}<br>` + otherTxt +
      `<span class="k">Dug beyond the planned line</span> <b class="${M.outArea > 0.02 * M.area ? "out" : ""}">${fmt0(M.outArea)} m&sup2; (${fmt1(M.outArea / M.area * 100)}% of the dug area)</b><br>`
    : `<span class="k">Planned polygon (R4M)</span> <span class="out">no boundary in the HPGPS register</span> &mdash; no comparison<br>`;
  S.statsHtml =   /* summary box removed 2026-11-03 (user); text kept for the checks only */
    `<b>${esc(P.name)}</b> <span class="k">&middot; Id ${[...P.ids].join(", ")}${bench != null ? ` &middot; bench ${bench} m` : ""} &middot; ${esc(P.mat)}</span><br>` +
    `<span class="k">As-dug area</span> <b>${fmt0(M.area)} m&sup2;</b> in ${M.islands.length} piece${M.islands.length > 1 ? "s" : ""}${M.loops.some(L => !L.outer) ? ` (${M.loops.filter(L => !L.outer).length} holes)` : ""} &middot; <span class="k">gaps &le; ${fmt1(M.gap)} m filled, ${EDGE_B} m around each dig point, ${M.cs} m cells</span><br>` +
    `<span class="k">Floor (dig points)</span> median <b>${fmt1(M.floorP[1])} m</b>${rel(M.floorP[1])} &middot; p10&ndash;p90 ${fmt1(M.floorP[0])}&ndash;${fmt1(M.floorP[2])} m<br>` +
    planTxt + benchTxt(M) +
    `<span class="k">Data</span> ${fmt0(M.nUsed)} of ${fmt0(M.nWin)} cycles &middot; ${fmt0(M.n)} dig points used${dropTxt ? ` &middot; <span class="k">left out: ${dropTxt}</span>` : ""}<br>` +
    `<span class="k">Coverage</span> ${fmt0(P.cycles.length)} of ${fmt0(P.total)} assigned cycles have bucket GPS this year; loader-only digging (LO214/LO215) is invisible`;
  el("d3hud").innerHTML = `<b>${esc(P.name)}</b> &middot; as-dug ${fmt0(M.area)} m&sup2;` +
    (M.hasPlan && M.outArea > 0.02 * M.area ? ` &middot; <span style="color:#d62828;font-weight:700">${fmt0(M.outArea)} m&sup2; beyond the line</span>` : "") +
    (M.other && M.other.area ? ` &middot; <span style="color:#8e44ad;font-weight:700">${fmt0(M.other.area)} m&sup2; booked to other polygons</span>` : "") +
    `<br><span style="opacity:.75">${esc(M.dates[0])} &rarr; ${esc(M.dates[M.dates.length - 1])} &middot; dark line = toe of the dug area &middot; N is away from you at the default view</span>`;
  if (M.focus){
    const F = M.focus;
    el("d3hud").innerHTML = `<b>${esc(P.name)}</b> &middot; ${esc(S.win.date)} ${SHIFT_NAME[S.win.shift]} &middot; dug ${shW()} ${fmt0(F.area)} m&sup2;` +
      (M.hasPlan && F.outArea > 0.02 * F.area ? ` &middot; <span style="color:#d62828;font-weight:700">${fmt0(F.outArea)} m&sup2; beyond the line</span>` : "") +
      (F.otherArea ? ` &middot; <span style="color:#8e44ad;font-weight:700">${fmt0(F.otherArea)} m&sup2; booked to other polygons</span>` : "") +
      `<br><span style="opacity:.75">${fmt0(F.cycles)} cycles &middot; ${fmt0(F.t)} t &middot; dark line = toe of ${S.win.shift === "both" ? "these shifts'" : "this shift's"} digging &middot; N is away from you at the default view</span>`;
  }
}

/* ------------------------------------------------------------- scene */
function initScene(){
  const canvas = el("d3canvas");
  S.renderer = new T.WebGLRenderer({canvas, antialias: true, alpha: false});
  S.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  S.scene = new T.Scene();
  S.scene.background = new T.Color(0xdfe6ec);
  S.camera = new T.PerspectiveCamera(50, 1, 0.5, 20000);
  S.camera.position.set(80, 60, 120);
  S.controls = new T.OrbitControls(S.camera, canvas);
  S.controls.enableDamping = true; S.controls.dampingFactor = 0.12;
  S.controls.screenSpacePanning = false; S.controls.maxPolarAngle = Math.PI;   /* full orbit: the bottom can be seen (user 2026-11-03) */
  S.scene.add(new T.HemisphereLight(0xffffff, 0x8a9096, 0.9));
  const sun = new T.DirectionalLight(0xffffff, 1.1); sun.position.set(-120, 200, 80); S.scene.add(sun);
  const fill = new T.DirectionalLight(0xffffff, 0.35); fill.position.set(150, 80, -120); S.scene.add(fill);
  const under = new T.DirectionalLight(0xffffff, 0.9); under.position.set(60, -200, 90); S.scene.add(under);   /* lights the undersides when looking from below (nav cube BOTTOM) */
  S.group = new T.Group(); S.scene.add(S.group);
  new ResizeObserver(resize).observe(el("d3main"));
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("click", onClick);
  canvas.addEventListener("pointerleave", () => { el("d3tip").style.display = "none"; });
  initNav();
}
function resize(){
  if (!S.renderer) return;
  const box = el("d3main").getBoundingClientRect();
  const w = Math.max(10, box.width | 0), h = Math.max(10, box.height | 0);
  S.renderer.setSize(w, h, false);
  S.camera.aspect = w / h; S.camera.updateProjectionMatrix();
}
function startLoop(){
  if (S.loop) return;
  S.loop = true;
  const step = () => {
    if (!S.loop) return;
    if (NAV.anim) navStep(); else S.controls.update();
    /* from below the opaque ground map would hide everything: drop it (and the grid) while the camera is under it */
    if (S.ground){ const below = S.camera.position.y < S.ground.position.y * S.group.scale.y; S.ground.visible = VIEW.ground && !below; if (S.grid) S.grid.visible = VIEW.ground && !below; }
    S.renderer.render(S.scene, S.camera);
    navRender();
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* ------------------------------------------------------------- nav cube (user 2026-11-03: "a nav cube similar to AutoCAD")
   A small cube in the top-right corner turns with the camera. Each face is split 3 x 3 like AutoCAD's ViewCube: the middle
   = look from that face, the edge strips = from that edge (45 deg), the corners = from that corner (isometric). Click to
   swing the camera there (same target and distance); the house button = home view. Scene axes: +x east, +y up, +z south. */
const NAV = {anim: null, hot: null};
function navFaceTex(label){
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d");
  g.fillStyle = "#eef1f4"; g.fillRect(0, 0, 128, 128);
  g.strokeStyle = "#8a96a0"; g.lineWidth = 4; g.strokeRect(2, 2, 124, 124);
  g.fillStyle = "#33424d"; g.font = `bold ${label.length > 5 ? 22 : 26}px Rubik, Arial, sans-serif`; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(label, 64, 66);
  const t = new T.CanvasTexture(c); t.colorSpace = T.SRGBColorSpace; t.anisotropy = 4;
  return t;
}
function initNav(){
  const cv = el("d3nav");
  NAV.r = new T.WebGLRenderer({canvas: cv, antialias: true, alpha: true});
  NAV.r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  NAV.r.setSize(120, 120, false);
  NAV.scene = new T.Scene();
  NAV.cam = new T.OrthographicCamera(-1.9, 1.9, 1.9, -1.9, 0.1, 50);
  /* BoxGeometry material order: +x, -x, +y, -y, +z, -z */
  const mats = ["EAST", "WEST", "TOP", "BOTTOM", "SOUTH", "NORTH"].map(l => new T.MeshBasicMaterial({map: navFaceTex(l)}));
  NAV.cube = new T.Mesh(new T.BoxGeometry(2, 2, 2), mats);
  NAV.scene.add(NAV.cube);
  NAV.scene.add(new T.LineSegments(new T.EdgesGeometry(NAV.cube.geometry), new T.LineBasicMaterial({color: 0x5a6570})));
  NAV.hl = new T.Mesh(new T.BoxGeometry(1, 1, 1), new T.MeshBasicMaterial({color: 0x2f7de1, transparent: true, opacity: 0.45, depthTest: false}));
  NAV.hl.visible = false; NAV.hl.renderOrder = 5; NAV.scene.add(NAV.hl);
  NAV.ray = new T.Raycaster(); NAV.p = new T.Vector2();
  cv.addEventListener("pointermove", ev => { const h = navHit(ev); navHot(h); cv.style.cursor = h ? "pointer" : "default"; });
  cv.addEventListener("pointerleave", () => navHot(null));
  cv.addEventListener("click", ev => { const h = navHit(ev); if (h) navView(h); });
  el("d3home").addEventListener("click", () => { NAV.anim = null; S.controls.enabled = true; frameCamera(true); });
}
/* hotspot under the pointer -> direction from the target to the camera, e.g. [0, 1, 0] = top, [1, 1, -1] = top-east-north corner */
function navHit(ev){
  const r = el("d3nav").getBoundingClientRect();
  NAV.p.x = ((ev.clientX - r.left) / r.width) * 2 - 1; NAV.p.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
  NAV.ray.setFromCamera(NAV.p, NAV.cam);
  const h = NAV.ray.intersectObject(NAV.cube, false)[0];
  if (!h) return null;
  const n = h.face.normal, P = h.point, d = [0, 0, 0];
  ["x", "y", "z"].forEach((k, a) => { d[a] = Math.round(n[k]) !== 0 ? Math.round(n[k]) : (P[k] > 0.34 ? 1 : P[k] < -0.34 ? -1 : 0); });
  return d;
}
function navHot(d){
  NAV.hot = d;
  if (!d){ NAV.hl.visible = false; return; }
  const s = [0, 0, 0], c = [0, 0, 0];
  d.forEach((v, a) => { if (v === 0){ s[a] = 1.32; c[a] = 0; } else { s[a] = 0.34; c[a] = v * 0.86; } });
  NAV.hl.scale.set(s[0] * 1.03, s[1] * 1.03, s[2] * 1.03); NAV.hl.position.set(c[0] * 1.03, c[1] * 1.03, c[2] * 1.03);
  NAV.hl.visible = true;
}
function navView(d){
  if (!S.camera) return;
  const to = new T.Vector3(d[0], d[1], d[2]);
  if (Math.abs(to.x) < 1e-9 && Math.abs(to.z) < 1e-9) to.z = 0.002;   /* straight up/down: keep north at the top of the screen */
  to.normalize();
  const off = new T.Vector3().subVectors(S.camera.position, S.controls.target);
  const from = off.clone().normalize();
  NAV.anim = {t0: performance.now(), dur: 450, dist: off.length(), from, q: new T.Quaternion().setFromUnitVectors(from, to)};
  S.controls.enabled = false;
}
function navStep(){
  const A = NAV.anim, u = Math.min(1, (performance.now() - A.t0) / A.dur), e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
  const q = new T.Quaternion().slerp(A.q, e);
  const dir = A.from.clone().applyQuaternion(q);
  S.camera.position.copy(S.controls.target).addScaledVector(dir, A.dist);
  S.camera.lookAt(S.controls.target);
  if (u >= 1){ NAV.anim = null; S.controls.enabled = true; S.controls.update(); }
}
function navRender(){
  if (!NAV.r || !S.camera) return;
  const off = new T.Vector3().subVectors(S.camera.position, S.controls.target).normalize();
  NAV.cam.position.copy(off).multiplyScalar(6);
  NAV.cam.up.copy(S.camera.up);
  NAV.cam.lookAt(0, 0, 0);
  NAV.r.render(NAV.scene, NAV.cam);
}
S.navView = navView; S.navHot = () => NAV.hot;   /* test hooks */

/* world (UTM) -> scene: x east, y up, z south (so -z = north) */
let ORG = {x: 0, y: 0, z: 0};
const sx = x => x - ORG.x, sy = z => z - ORG.z, sz = y => -(y - ORG.y);

function disposeObj(o){
  o.traverse(x => {
    if (x.geometry) x.geometry.dispose();
    if (x.material){ if (x.material.map) x.material.map.dispose(); x.material.dispose(); }
  });
}
function clearModel(){
  for (const k of ["mesh", "wire", "pts", "ground", "bench", "grid", "arrow", "plan", "dig", "lid", "outline", "now", "other"]){
    const o = S[k];
    if (o){ S.group.remove(o); disposeObj(o); S[k] = null; }
  }
  S.nowMesh = null; S.nowWall = null; S.nowIdx = null; S.nowFz = null; S.nowRaised = null; S.otherIdx = null;
}

function hsl(h, s, l){ const c = new T.Color(); c.setHSL(h, s, l); return c; }
const PAL = [];
for (let i = 0; i < 64; i++) PAL.push(hsl((i * 0.61803398875) % 1, 0.62, 0.48));
const C_IN = new T.Color(0x2a9d8f), C_OUT = new T.Color(0xd62828), C_D0 = new T.Color(0x1d4f91), C_D1 = new T.Color(0xf0b429);
const C_GREY = new T.Color(0xb9c0c6);

function vertexColor(mode, ownerPt, island, tmp, z){
  const M = S.model;
  const ci = ownerPt >= 0 ? M.pc[ownerPt] : -1;
  const c = ci >= 0 ? M.cycles[ci] : null;
  if (mode === "elev"){ const z0 = M.kind === "cut" ? M.floorP[0] - 0.3 : M.bbox.minz, z1 = M.kind === "cut" ? M.floorP[2] + 0.3 : M.bbox.maxz; elevColor((z - z0) / ((z1 - z0) || 1), tmp); }
  else if (mode === "comp"){ tmp.copy(ownerPt >= 0 ? (M.pin[ownerPt] ? C_IN : C_OUT) : C_GREY); }
  else if (mode === "island"){ tmp.copy(island >= 0 ? PAL[island % PAL.length] : C_GREY); }
  else if (mode === "date"){ tmp.copy(C_D0).lerp(C_D1, c ? (M.dateRank.get(c.date) / Math.max(1, M.dates.length - 1)) : 0); }
  else { tmp.copy(ci >= 0 ? PAL[ci % PAL.length] : C_GREY); }
  if (S.sel !== null && (!c || c.cid !== S.sel)) tmp.lerp(C_GREY, 0.75);
  return tmp;
}
function recolor(){
  const M = S.model; if (!M || !S.mesh) return;
  const mode = el("d3color").value, tmp = new T.Color();
  if (M.kind === "cut"){ if (S.nowMesh) recolorNow(); else { recolorCut(); recolorOther(); } }
  else {
    const col = S.mesh.geometry.getAttribute("color"), pos = S.mesh.geometry.getAttribute("position");
    for (let i = 0; i < M.mesh.vOwner.length; i++){
      vertexColor(mode, M.mesh.vOwner[i], M.mesh.vIsland[i], tmp, pos.getY(i) + ORG.z);
      col.setXYZ(i, tmp.r, tmp.g, tmp.b);
    }
    col.needsUpdate = true;
  }
  if (S.pts){
    const pcol = S.pts.geometry.getAttribute("color");
    for (let i = 0; i < M.n; i++){ vertexColor(mode, i, M.ptIsland[i], tmp, M.pz[i]); pcol.setXYZ(i, tmp.r, tmp.g, tmp.b); }
    pcol.needsUpdate = true;
  }
  drawLegend(mode);
}

function drawLegend(mode){
  const M = S.model, L = el("d3legend");
  if (!M){ L.innerHTML = ""; return; }
  if (M.kind !== "cut"){ drawLegendBase(mode); return; }
  const before = M.focus ? `<span><i style="background:#9fa7ae"></i>dug before ${shW()}</span>` : "";
  if (!S.now){
    drawLegendBase(mode === "grade" ? "elev" : mode);
    if (mode === "grade") L.insertAdjacentHTML("beforeend", `<span>no planned polygon in the register &mdash; no block to compare with, coloured by floor elevation</span>`);
    L.insertAdjacentHTML("beforeend", before);
    return;
  }
  if (mode === "grade") L.innerHTML = `<span><span class="grad3"></span> at the planned floor &rarr; ${fmt1(BENCH_H)} m still to dig</span><span><i style="background:#1d4f91"></i>below the planned floor</span>`;
  else { drawLegendBase(mode); L.insertAdjacentHTML("afterbegin", `<span><i style="background:#c9a46a"></i>not dug yet</span>`); }
  if (mode !== "comp" && M.now.A[5]) L.insertAdjacentHTML("beforeend", `<span><i style="background:#d62828"></i>dug beyond the planned line</span>`);
  if (M.other && M.other.area) L.insertAdjacentHTML("beforeend", `<span><i style="background:#8e44ad"></i>dug inside this plan, booked to another polygon</span>`);
  L.insertAdjacentHTML("beforeend", before);
}
function drawLegendBase(mode){
  const M = S.model, L = el("d3legend");
  if (mode === "elev"){ const z0 = M.kind === "cut" ? M.floorP[0] - 0.3 : M.bbox.minz, z1 = M.kind === "cut" ? M.floorP[2] + 0.3 : M.bbox.maxz;
    L.innerHTML = `<span>${M.kind === "cut" ? "floor" : "height"} ${fmt1(z0)} m <span class="grad2"></span> ${fmt1(z1)} m</span>`; }
  else if (M.kind === "cut" && mode === "comp") L.innerHTML = M.hasPlan
    ? `<span><i style="background:#2a9d8f"></i>dug inside the planned polygon</span><span><i style="background:#d62828"></i>dug beyond the planned line</span>`
    : `<span>no planned boundary in the register &mdash; nothing to compare</span>`;
  else if (M.kind === "cut" && mode === "island") L.innerHTML = `<span>${M.islands.length} separate dug piece${M.islands.length > 1 ? "s" : ""}, one colour each</span>`;
  else if (M.kind === "cut" && mode === "cycle") L.innerHTML = `<span>each cell coloured by the cycle of its nearest dig point &middot; click to select</span>`;
  else if (mode === "comp") L.innerHTML = M.geo
    ? `<span><i style="background:#2a9d8f"></i>pass inside the planned boundary</span><span><i style="background:#d62828"></i>pass outside the planned boundary</span>`
    : `<span>no planned boundary in the register &mdash; nothing to compare</span>`;
  else if (mode === "date") L.innerHTML = `<span>${esc(M.dates[0])} <span class="grad"></span> ${esc(M.dates[M.dates.length - 1])}</span>`;
  else if (mode === "island") L.innerHTML = `<span>${M.islands.length} islands, one colour each (touching material = one island)</span>`;
  else L.innerHTML = `<span>${M.cycles.length} cycles, one colour each &middot; click a cycle to highlight it</span>`;
}

function showModel(M){
  clearModel();
  const B = M.bbox;
  ORG = {x: (B.minx + B.maxx) / 2, y: (B.miny + B.maxy) / 2, z: B.minz};
  /* mesh */
  if (M.kind === "cut") showCut(M);
  else {
    const g = new T.BufferGeometry();
    const P = M.mesh.pos, n = P.length / 3, pos = new Float32Array(P.length);
    for (let i = 0; i < n; i++){ pos[3 * i] = sx(P[3 * i]); pos[3 * i + 1] = sy(P[3 * i + 2]); pos[3 * i + 2] = sz(P[3 * i + 1]); }
    g.setAttribute("position", new T.BufferAttribute(pos, 3));
    g.setAttribute("color", new T.BufferAttribute(new Float32Array(n * 3), 3));
    g.setIndex(new T.BufferAttribute(M.mesh.idx, 1));
    g.computeVertexNormals();
    S.mesh = new T.Mesh(g, new T.MeshLambertMaterial({vertexColors: true, side: T.DoubleSide}));
    S.group.add(S.mesh);
    S.wire = new T.Mesh(g, new T.MeshBasicMaterial({color: 0x1b2a33, wireframe: true, transparent: true, opacity: 0.18}));
    S.wire.visible = VIEW.edges; S.group.add(S.wire);
  }
  /* pass points */
  const pp = new Float32Array(M.n * 3);
  for (let i = 0; i < M.n; i++){ pp[3 * i] = sx(M.px[i]); pp[3 * i + 1] = sy(M.pz[i]) + 0.02; pp[3 * i + 2] = sz(M.py[i]); }
  const pg = new T.BufferGeometry();
  pg.setAttribute("position", new T.BufferAttribute(pp, 3));
  pg.setAttribute("color", new T.BufferAttribute(new Float32Array(M.n * 3), 3));
  S.pts = new T.Points(pg, new T.PointsMaterial({size: 0.45, vertexColors: true, sizeAttenuation: true}));
  S.pts.visible = VIEW.pts; S.group.add(S.pts);
  /* ground (contour raster crop) + grid + bench + north arrow */
  const pad = 25, BA = M.bboxAll || B;
  const gx0 = BA.minx - pad, gx1 = BA.maxx + pad, gy0 = BA.miny - pad, gy1 = BA.maxy + pad;
  const gw = gx1 - gx0, gh = gy1 - gy0, gy = sy(Math.min(B.minz, BA.minz) - 1.5);
  const ground = new T.Mesh(new T.PlaneGeometry(gw, gh), new T.MeshLambertMaterial({color: 0xcfd6dc, side: T.DoubleSide}));
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(sx((gx0 + gx1) / 2), gy, sz((gy0 + gy1) / 2));
  ground.visible = VIEW.ground;
  S.ground = ground; S.group.add(ground);
  groundTexture(ground, gx0, gx1, gy0, gy1);
  const grid = new T.GridHelper(Math.max(gw, gh), Math.round(Math.max(gw, gh) / 10), 0x5a6570, 0x9aa5ad);
  grid.position.set(sx((gx0 + gx1) / 2), gy + 0.05, sz((gy0 + gy1) / 2));
  grid.material.transparent = true; grid.material.opacity = 0.35;
  grid.visible = VIEW.ground;
  S.grid = grid; S.group.add(grid);
  const P0 = S.data.polys.get(S.pid);
  if (P0 && P0.bench != null){
    const bench = new T.Mesh(new T.PlaneGeometry(gw, gh), new T.MeshBasicMaterial({color: 0x005aed, transparent: true, opacity: 0.13, side: T.DoubleSide, depthWrite: false}));
    bench.rotation.x = -Math.PI / 2;
    bench.position.set(sx((gx0 + gx1) / 2), sy(P0.bench), sz((gy0 + gy1) / 2));
    bench.visible = VIEW.bench;
    S.bench = bench; S.group.add(bench);
  }
  drawPlan(M);
  drawDig(M);
  if (M.kind === "cut") applyView();
  const arrow = new T.ArrowHelper(new T.Vector3(0, 0, -1), new T.Vector3(sx(gx1 - 8), gy + 0.3, sz(gy0 + 8)), 14, 0x1b2a33, 5, 3);
  S.arrow = arrow; S.group.add(arrow);
  applyVex();
  recolor();
  frameCamera(true);
}

/* planned polygon: translucent prism (bench .. bench + BENCH_H) + bold outline at the bench */
function drawPlan(M){
  const P = S.data.polys.get(S.pid);
  if (!P || !P.rings.length) return;
  const grp = new T.Group();
  for (const R of P.rings){
    const z0 = R.bench != null ? R.bench : M.bbox.minz;
    /* Shape lives in XY; rotation.x = -90deg maps (X, Y, depth) -> scene (X, depth, -Y) */
    const shape = new T.Shape(R.ring.map(([x, y]) => new T.Vector2(sx(x), y - ORG.y)));
    const geo = new T.ExtrudeGeometry(shape, {depth: BENCH_H, bevelEnabled: false});
    const prism = new T.Mesh(geo, new T.MeshBasicMaterial({color: 0xff8c00, transparent: true, opacity: 0.10, side: T.DoubleSide, depthWrite: false}));
    prism.rotation.x = -Math.PI / 2; prism.position.y = sy(z0); prism.userData.prism = true;
    grp.add(prism);
    const edges = new T.LineSegments(new T.EdgesGeometry(geo, 1), new T.LineBasicMaterial({color: 0xff6a00, transparent: true, opacity: 0.6}));
    edges.rotation.x = -Math.PI / 2; edges.position.y = sy(z0); edges.userData.prism = true;
    grp.add(edges);
    const loop = R.ring.map(([x, y]) => new T.Vector3(sx(x), sy(z0) + 0.08, sz(y)));
    grp.add(new T.LineLoop(new T.BufferGeometry().setFromPoints(loop), new T.LineBasicMaterial({color: 0xff4d00})));
  }
  grp.visible = VIEW.plan;
  S.plan = grp; S.group.add(grp);
}

/* HPGPS dig lines (loader onboard system): fetched once on first use, drawn near the model */
async function ensureDig(){
  if (S.digAll) return S.digAll;
  const L = window.R4M_LIVE;
  if (!L || !L.fetchJson) throw new Error("live loader unavailable");
  status("fetching HPGPS dig lines…");
  const rows = await L.fetchJson("/dimensions/digline/getDigLineGlobal/", "dig lines");
  S.digAll = (Array.isArray(rows) ? rows : []).map(r => ({
    id: r.id, z: r.nivel == null ? null : +r.nivel, sup: r.is_superior,
    pts: (r.coors || []).filter(c => Array.isArray(c) && isFinite(c[0]) && isFinite(c[1])).map(c => L.llToUtm(+c[0], +c[1])),
  })).filter(d => d.pts.length >= 2);
  return S.digAll;
}
function drawDig(M){
  if (S.dig){ S.group.remove(S.dig); disposeObj(S.dig); S.dig = null; }
  S.digCount = 0;
  if (!VIEW.dig || !S.digAll) return;
  const B = M.bboxAll || M.bbox, pad = 30;
  const grp = new T.Group();
  for (const d of S.digAll){
    if (d.z != null && (d.z < B.minz - 6 || d.z > B.maxz + 6)) continue;   /* same bench (+-6 m) only */
    if (!d.pts.some(p => p[0] >= B.minx - pad && p[0] <= B.maxx + pad && p[1] >= B.miny - pad && p[1] <= B.maxy + pad)) continue;
    const z = (d.z != null ? d.z : M.bbox.minz) + 0.3;
    const pts = d.pts.map(([x, y]) => new T.Vector3(sx(x), sy(z), sz(y)));
    grp.add(new T.Line(new T.BufferGeometry().setFromPoints(pts),
      new T.LineBasicMaterial({color: d.sup === true ? 0xb5179e : d.sup === false ? 0x0b7a75 : 0x6c757d})));
  }
  S.dig = grp; S.group.add(grp); S.digCount = grp.children.length;
}

function groundTexture(mesh, x0, x1, y0, y1){
  const A = window.ATL;
  if (!A || !A.contourB64 || !A.contour) return;
  const CM = A.contour;
  const img = new Image();
  img.onload = () => {
    const u0 = (x0 - CM.x0) / (CM.x1 - CM.x0), u1 = (x1 - CM.x0) / (CM.x1 - CM.x0);
    const v0 = (CM.y1 - y1) / (CM.y1 - CM.y0), v1 = (CM.y1 - y0) / (CM.y1 - CM.y0);
    const cw = 1024, chh = Math.max(64, Math.round(1024 * (y1 - y0) / (x1 - x0)));
    const cv = document.createElement("canvas"); cv.width = cw; cv.height = chh;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#cfd6dc"; ctx.fillRect(0, 0, cw, chh);
    ctx.drawImage(img, u0 * img.width, v0 * img.height, (u1 - u0) * img.width, (v1 - v0) * img.height, 0, 0, cw, chh);
    const tex = new T.CanvasTexture(cv);
    tex.colorSpace = T.SRGBColorSpace;
    if (mesh.material.map) mesh.material.map.dispose();
    mesh.material.map = tex; mesh.material.color.set(0xffffff); mesh.material.needsUpdate = true;
  };
  img.src = "data:image/png;base64," + A.contourB64;
}

function applyVex(){
  const v = +el("d3vex").value;
  el("d3vexv").textContent = v.toFixed(2).replace(/0$/, "");
  if (S.group) S.group.scale.set(1, v, 1);
}
function frameCamera(reset){
  const M = S.model; if (!M) return;
  const B = M.bboxAll || M.bbox, v = +el("d3vex").value;
  const cx = sx((B.minx + B.maxx) / 2), cy = ((B.minz + B.maxz) / 2 - ORG.z) * v, cz = sz((B.miny + B.maxy) / 2);
  const rad = Math.max(12, 0.5 * Math.hypot(B.maxx - B.minx, B.maxy - B.miny, (B.maxz - B.minz) * v));
  const dist = rad / Math.sin((S.camera.fov * Math.PI / 180) / 2) * 1.05;
  S.controls.target.set(cx, cy, cz);
  if (reset) S.camera.position.set(cx - dist * 0.55, cy + dist * 0.62, cz + dist * 0.6);
  S.camera.near = Math.max(0.2, dist / 500); S.camera.far = dist * 40; S.camera.updateProjectionMatrix();
  S.controls.update();
}
function focusCycle(cid){
  const M = S.model; if (!M) return;
  let ci = M.cycles.findIndex(c => c.cid === cid), src = M;
  if (ci < 0 && M.other){ ci = M.other.cycles.findIndex(c => c.cid === cid); src = M.other; }   /* booked to another polygon */
  if (ci < 0) return;
  let x = 0, y = 0, z = 0, n = 0;
  for (let i = 0; i < src.n; i++) if (src.pc[i] === ci){ x += src.px[i]; y += src.py[i]; z += src.pz[i]; n++; }
  if (!n) return;
  const v = +el("d3vex").value;
  const tgt = new T.Vector3(sx(x / n), sy(z / n) * v, sz(y / n));
  const dir = new T.Vector3().subVectors(S.camera.position, S.controls.target).normalize();
  S.controls.target.copy(tgt);
  S.camera.position.copy(tgt).addScaledVector(dir, 45);
  S.controls.update();
}

/* ------------------------------------------------------------- picking */
const ray = new T.Raycaster(), ptr = new T.Vector2();
let hoverPending = false;
function pick(ev){
  if (!S.mesh) return null;
  const r = el("d3canvas").getBoundingClientRect();
  ptr.x = ((ev.clientX - r.left) / r.width) * 2 - 1; ptr.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
  ray.setFromCamera(ptr, S.camera);
  if (S.nowMesh){
    const h = ray.intersectObjects(S.nowWall ? [S.nowMesh, S.nowWall] : [S.nowMesh], false)[0];
    if (!h || h.object === S.nowWall) return null;   /* a wall in front: nothing to report for what is behind it */
    const M = S.model, q = S.nowIdx[h.faceIndex >> 1], pi = M.F[q] ? M.near1[q] : -1, inS = focusOn(M, q);
    const ci = M.focus ? (inS && M.F[q] ? M.focus.ci[q] : -1) : pi >= 0 ? M.pc[pi] : -1;   /* ground dug before the shift has no row in the table */
    return {now: true, other: inS && !M.F[q] && !!M.other && !!M.other.O[q], q, ci, ev};
  }
  const hit = ray.intersectObjects(S.other ? [S.mesh, S.other] : [S.mesh], false)[0];
  if (!hit) return null;
  if (hit.object === S.other) return {other: true, q: S.otherIdx[hit.faceIndex >> 1], ci: -1, ev};
  if (S.model.kind === "cut"){
    const q = S.model.cellsIdx[hit.faceIndex >> 1], pi = q === undefined ? -1 : S.model.near1[q];
    if (pi < 0) return null;
    return {ci: S.model.pc[pi], island: S.model.piece[q], q, ev};
  }
  const owner = S.model.mesh.fOwner[hit.faceIndex];
  if (owner < 0) return null;
  return {ci: S.model.pc[owner], island: S.model.ptIsland[owner], ev};
}
function cycleHtml(c, ci, island, q){
  const M = S.model;
  if (M.kind === "cut" && q !== undefined)
    return `<b>${esc(S.data.polys.get(S.pid).name)}</b> &middot; floor ${fmt1(M.floor[q])} m` +
      (M.hasPlan ? (M.plan[q] ? " &middot; inside plan" : ` &middot; <span style="color:#d62828;font-weight:700">beyond the planned line</span>`) : "") +
      `<br>nearest dig: cycle ${c.cid} &middot; ${esc(c.date)} ${esc(c.shift)} &middot; ${esc(c.truck)} loaded by ${esc(c.loader)}<br>${c.pts.length} passes &middot; ${fmt1(c.t)} t &middot; piece #${island + 1}`;
  return `<b>${esc(S.data.polys.get(S.pid).name)}</b> &middot; cycle ${c.cid}<br>` +
    `${esc(c.date)} ${esc(c.shift)} &middot; ${esc(c.truck)} loaded by ${esc(c.loader)}<br>` +
    `${c.pts.length} passes (dispatch: ${c.passes}) &middot; ${fmt1(c.t)} t<br>` +
    `modelled ${fmt0(M.cycVox[ci] * M.voxVol)} m&sup3; &middot; island #${island + 1}` +
    (M.geo ? `<br><span style="${c.nOut ? "color:#d62828;font-weight:700" : ""}">${c.nOut} of ${c.pts.length} passes outside the planned boundary</span>` : "") +
    (c.hpOut ? `<br><span style="color:#d62828;font-weight:700">HPGPS in ${esc(c.hpName)}</span>` : (c.hp === null ? "<br>no HPGPS polygon" : "<br>HPGPS agrees"));
}
function onPointerMove(ev){
  if (hoverPending) return;
  hoverPending = true;
  requestAnimationFrame(() => {
    hoverPending = false;
    const h = pick(ev), tip = el("d3tip");
    if (!h){ tip.style.display = "none"; return; }
    tip.innerHTML = h.now ? benchHtml(h.q) : h.other ? otherHtml(h.q) : cycleHtml(S.model.cycles[h.ci], h.ci, h.island, h.q);
    const r = el("d3main").getBoundingClientRect();
    tip.style.display = "block";
    tip.style.left = Math.min(r.width - 300, ev.clientX - r.left + 14) + "px";
    tip.style.top = Math.max(4, ev.clientY - r.top - 10) + "px";
  });
}
function onClick(ev){
  const h = pick(ev);
  const X = S.model && S.model.other;
  const cid = !h ? null : h.other ? (X && X.own[h.q] >= 0 ? X.cycles[X.own[h.q]].cid : null) : h.ci >= 0 ? S.model.cycles[h.ci].cid : null;
  selectCycle(cid, false);
}
function selectCycle(cid, focus){
  S.sel = cid;
  recolor();
  document.querySelectorAll("#d3cycles tr[data-cid]").forEach(tr => tr.classList.toggle("sel", +tr.dataset.cid === cid));
  if (cid !== null){
    const row = document.querySelector(`#d3cycles tr[data-cid="${cid}"]`);
    if (row) row.scrollIntoView({block: "nearest"});
    if (focus) focusCycle(cid);
  }
}

/* ------------------------------------------------------------- stats + table */
function renderStats(M){
  if (M.kind === "cut") return renderCutStats(M);
  const P = S.data.polys.get(S.pid);
  const dens = 2.64;
  const t = M.cycles.reduce((s, c) => s + c.t, 0);
  const outC = M.cycles.filter(c => c.out), outT = outC.reduce((s, c) => s + c.t, 0), outP = outC.reduce((s, c) => s + c.pts.length, 0);
  const seen = {};
  for (const c of M.cycles) if (c.hpOut) seen[c.hpName] = (seen[c.hpName] || 0) + 1;
  const seenTxt = Object.entries(seen).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, v]) => `${esc(k)} (${v})`).join(", ");
  const sizes = M.islPts.length ? Array.from(M.islPts) : [];
  const biggest = sizes.length ? Math.max(...sizes) : 0;
  const isoTxt = S.isolate !== null ? ` &middot; <span class="out">isolated cycle ${S.isolate}</span>` : "";
  const gr = polyGrades(P);
  const grTxt = (gr.au != null || gr.ag != null)
    ? `Au <b>${gr.au != null ? gr.au.toFixed(2) : "-"}</b> / Ag <b>${gr.ag != null ? gr.ag.toFixed(2) : "-"}</b> g/t`
    : (ORE_CODES.has(P.mat)
        ? `<span class="out">none registered</span> <span class="k">(ore polygon uploaded to R4M without Au/Ag &mdash; fix it in the polygon register)</span>`
        : `<span class="k">none registered (${esc(P.mat)} = waste-class polygon, no grade expected)</span>`);
  const hpC = M.cycles.filter(c => c.hpOut), hpT = hpC.reduce((s, c) => s + c.t, 0);
  let geoTxt;
  if (P.rings.length){
    const benches = [...new Set(P.rings.map(R => R.bench).filter(b => b != null))].join(" / ");
    const nOutP = M.cycles.reduce((s, c) => s + c.nOut, 0);
    const outEst = M.cycles.reduce((s, c) => s + c.t * (c.pts.length ? c.nOut / c.pts.length : 0), 0);
    geoTxt = `<span class="k">Planned polygon (R4M)</span> ${P.rings.length} ring${P.rings.length > 1 ? "s" : ""}${benches ? ` &middot; bench ${esc(benches)} m` : ""} &middot; ${fmt0(P.area)} m&sup2; &middot; ${P.rings.some(R => R.status === "open") ? "open" : "closed"}<br>` +
             `<span class="k">Outside planned boundary</span> <b class="${nOutP ? "out" : ""}">${fmt0(nOutP)} of ${fmt0(M.n)} passes (${fmt1(M.n ? nOutP / M.n * 100 : 0)}%) &middot; ~${fmt0(outEst)} t &middot; ${fmt0(M.outVol)} m&sup3; modelled</b>` +
             `<br>`;
  } else {
    geoTxt = `<span class="k">Planned polygon (R4M)</span> <span class="out">no boundary in the HPGPS register</span> <span class="k">(closed before 2026-05-12 or never uploaded) &mdash; nothing to compare</span><br>`;
  }
  S.statsHtml =   /* summary box removed 2026-11-03 (user); text kept for the checks only */
    `<b>${esc(P.name)}</b> <span class="k">&middot; Id ${[...P.ids].join(", ")}${P.bench != null ? ` &middot; bench ${P.bench} m` : ""} &middot; ${esc(P.mat)}</span>${isoTxt}<br>` +
    `<span class="k">Grades (R4M)</span> ${grTxt}<br>` +
    geoTxt +
    `<span class="k">Cycles shown</span> <b>${fmt0(M.cycles.length)}</b> &middot; ${fmt0(M.n)} passes &middot; ${fmt0(t)} t<br>` +
    `<span class="k">Polygon coverage</span> ${fmt0(P.cycles.length)} of ${fmt0(P.total)} assigned cycles have bucket GPS (${fmt0(P.cycles.length / Math.max(1, P.total) * 100)}%)<br>` +
    `<span class="k">Nominal dug volume</span> ${fmt0(M.n)} &times; ${el("d3vol").value} m&sup3; = <b>${fmt0(M.n * +el("d3vol").value)} m&sup3;</b><br>` +
    `<span class="k">Modelled solid (union)</span> <b>${fmt0(M.unionVol)} m&sup3;</b> at ${M.res} m voxels &middot; <span class="k">bank from tonnes</span> ${fmt0(t)} / ${dens} = ${fmt0(t / dens)} m&sup3;<br>` +
    `<span class="k">Islands</span> <b>${M.islands.length}</b> (largest ${fmt0(biggest)} passes, ${fmt0(Math.max(0, ...Array.from(M.islands)) * M.voxVol)} m&sup3;) &middot; joins &le; ${el("d3conn").value} m: ${fmt0(M.nWithin)} within cycles, ${fmt0(M.nCross)} across cycles<br>` +
    `<span class="k">Outside (cycles with most passes beyond the planned boundary)</span> <b class="${outC.length ? "out" : ""}">${fmt0(outC.length)} cycles &middot; ${fmt0(outP)} passes &middot; ${fmt0(outT)} t (${fmt1(t ? outT / t * 100 : 0)}%)</b><br>` +
    `<span class="k">HPGPS mismatch</span> ${fmt0(hpC.length)} cycles &middot; ${fmt0(hpT)} t` +
    (seenTxt ? ` &middot; <span class="k">GPS actually in:</span> ${seenTxt}` : "") +
    (S.digCount ? `<br><span class="k">HPGPS dig lines drawn</span> ${fmt0(S.digCount)}` : "");
  el("d3hud").innerHTML = `<b>${esc(P.name)}</b> &middot; ${fmt0(M.cycles.length)} cycles &middot; ${fmt0(M.n)} passes &middot; ${M.islands.length} islands` +
    (outC.length ? ` &middot; <span style="color:#d62828;font-weight:700">${outC.length} outside</span>` : "") +
    `<br><span style="opacity:.75">${esc(M.dates[0])} &rarr; ${esc(M.dates[M.dates.length - 1])} &middot; N is away from you at the default view (arrow)</span>`;
}
let sortKey = "date", sortDir = -1;
function renderTable(M){
  const foc = M.kind === "cut" && M.focus ? M.focus.key : null, multi = !!(S.data.polys.get(S.pid) || {}).members;
  const rows = M.cycles.map((c, ci) => ({c, ci})).filter(r => !foc || inKey(r.c, foc));   /* m3 column + Density box removed 2026-11-03 (user) */
  const key = sortKey;
  rows.sort((a, b) => {
    const kv = r => key === "pts" ? r.c.pts.length : key === "outx" ? (r.c.pts.length ? r.c.nOut / r.c.pts.length : 0) + (r.c.hpOut ? 10 : 0) : r.c[key];
    const va = kv(a), vb = kv(b);
    return (va < vb ? -1 : va > vb ? 1 : a.c.cid - b.c.cid) * sortDir;
  });
  const cap = 600;
  const bothS = !!foc && foc.endsWith("|both");   /* one date, two shifts: the hour alone would be ambiguous */
  const cols = [...(foc ? [...(bothS ? [["shift", "Sh"]] : []), ["at", "Hour"]] : [["date", "Date"], ["shift", "Sh"]]), ...(multi ? [["pname", "Polygon"]] : []),
                ["truck", "Truck"], ["loader", "Loader"], ["pts", "Passes"], ["t", "t"], ["outx", M.geo ? "Out / HPGPS" : "HPGPS polygon"]];
  const head = (c, other) => (foc ? `${bothS ? `<td>${esc(c.shift)}</td>` : ""}<td>${esc(c.at.slice(11))}</td>` : `<td>${esc(c.date)}</td><td>${esc(c.shift)}</td>`) + (multi ? `<td>${other ? "" : esc(c.pname || "")}</td>` : "");
  let h = "<tr>" + cols.map(([k, l]) => `<th data-k="${k}">${l}${sortKey === k ? (sortDir < 0 ? " ▾" : " ▴") : ""}</th>`).join("") + "</tr>";
  for (const {c} of rows.slice(0, cap)){
    h += `<tr data-cid="${c.cid}" class="${c.out ? "out" : ""}${S.sel === c.cid ? " sel" : ""}">${head(c, false)}<td>${esc(c.truck)}</td><td>${esc(c.loader)}</td>` +
         `<td class="n">${c.pts.length}</td><td class="n">${fmt1(c.t)}</td><td>${M.geo ? `<span style="${c.nOut ? "color:#d62828;font-weight:700" : ""}">${c.nOut}/${c.pts.length}</span>${c.hpOut ? ` · ${esc(c.hpName)}` : ""}` : (c.hpOut ? esc(c.hpName) : (c.hp === null ? "<i>no fix</i>" : "✓"))}</td></tr>`;
  }
  /* cycles booked to OTHER polygons that dug inside this plan (user 2026-11-03): purple rows at the bottom, passes = inside
     this plan / all, tonnes shown but not counted for this polygon; same sort as the own rows */
  const X = M.kind === "cut" && M.other ? M.other : null;
  const orows = X ? X.list.filter(o => !foc || inKey(o.c, foc)) : [];
  orows.sort((a, b) => {
    const kv = r => key === "pts" ? r.nIn : key === "outx" ? r.c.pname : r.c[key];
    const va = kv(a), vb = kv(b);
    return (va < vb ? -1 : va > vb ? 1 : a.c.cid - b.c.cid) * sortDir;
  });
  const room = Math.max(0, cap - Math.min(cap, rows.length));
  if (orows.length && room){
    h += `<tr class="osep"><td colspan="${cols.length}">Booked to other polygons, dug inside this plan (${fmt0(orows.length)}) &mdash; their tonnes count for that polygon, not this one</td></tr>`;
    for (const {c, nIn} of orows.slice(0, room)){
      h += `<tr data-cid="${c.cid}" class="oth${S.sel === c.cid ? " sel" : ""}" title="booked to ${esc(c.pname)}: ${nIn} of its ${c.nAll} dig points are inside this plan">${head(c, true)}<td>${esc(c.truck)}</td><td>${esc(c.loader)}</td>` +
           `<td class="n">${nIn}/${c.nAll}</td><td class="n tt">${fmt1(c.t)}</td><td>&rarr; ${esc(c.pname)}</td></tr>`;
    }
  }
  el("d3cycles").innerHTML = h;
  const shown = Math.min(cap, rows.length) + Math.min(room, orows.length), total = rows.length + orows.length;
  el("d3cyccount").textContent = (orows.length ? `(${fmt0(rows.length)} + ${fmt0(orows.length)} booked to other polygons)` : `(${rows.length})`) +
    (total > shown ? ` — showing ${fmt0(shown)}, narrow the dates` : "");
  el("d3cycles").querySelectorAll("th").forEach(th => th.addEventListener("click", () => {
    if (sortKey === th.dataset.k) sortDir = -sortDir; else { sortKey = th.dataset.k; sortDir = th.dataset.k === "date" ? -1 : -1; }
    renderTable(M);
  }));
  el("d3cycles").querySelectorAll("tr[data-cid]").forEach(tr => tr.addEventListener("click", () => selectCycle(+tr.dataset.cid, true)));
}

/* ------------------------------------------------------------- build orchestration */
let buildTimer = null;
function scheduleBuild(resetView){
  clearTimeout(buildTimer);
  buildTimer = setTimeout(() => rebuild(resetView), 200);
}
async function rebuild(resetView){
  const P = S.data && S.data.polys.get(S.pid);
  if (!P) return;
  const geoRule = useGeo(P);
  for (const c of P.cycles) c.out = c.geoOut;
  const mode = "cut";   /* as-dug cut always (user 2026-11-02 evening: model picker removed; the sphere model's code stays unused) */
  /* shift view: everything up to the end of that shift, so the block shows the bench as it stood then */
  const focus = S.win.mode === "shift" ? winKey() : null, until = focus && S.win.shift === "both" ? S.win.date + "|NS" : focus;
  const o = {conn: +el("d3conn").value, vol: +el("d3vol").value, geo: geoRule, until, focus,
             from: until ? "" : el("d3from").value, to: until ? "" : el("d3to").value, outOnly: VIEW.out, isolate: S.isolate,
             gap: GAP_M, top: "flat", fixH: 2.5,
             dens: 2.64};   /* internal only (hidden flat top); the Density box was removed 2026-11-03 */
  /* other polygons may have dug this ground before this polygon's first cycle, so From limits them only when moved later than that day */
  o.otherFrom = o.from && o.from > P.cycles[0].date ? o.from : "";
  el("d3tip").style.display = "none";
  overlay(`Building the 3D model of <b>${esc(P.name)}</b>&hellip;`);
  status(`building ${P.name}…`);
  await tick();
  const t0 = performance.now();
  let M = null;
  try { M = mode === "cut" ? buildCut(P, o) : buildModel(P, o); }
  catch (e){ console.error("DIG3D build failed:", e); overlay(`&#9888; model build failed: ${esc(e.message || e)}`, true); return; }
  if (!M || M.empty){
    clearModel(); S.model = null;
    const why = M && M.empty && M.drop.bad ? `only EX215 cycles, whose bucket sensor is dead` : `no bucket-GPS passes in this window`;
    S.statsHtml = `<b>${esc(P.name)}</b><br>${why}.`;
    el("d3cycles").innerHTML = ""; el("d3legend").innerHTML = ""; el("d3hud").innerHTML = "";
    overlay(`Nothing to draw for <b>${esc(P.name)}</b>: ${why}.`);
    return;
  }
  if (M.kind === "cut"){ try { M.other = buildOther(P, M, o); } catch (e){ console.error("DIG3D other-polygon digging failed:", e); M.other = null; } }
  if (M.kind === "cut" && until) M.focus = buildFocus(P, M, o);
  S.model = M;
  showModel(M);
  if (!resetView) frameCamera(false);
  renderStats(M);
  renderTable(M);
  overlay("");
  status(M.kind === "cut"
    ? `ready · ${P.name}: as-dug ${fmt0(M.area)} m², ${fmt0(M.n)} dig points, ${M.islands.length} piece${M.islands.length > 1 ? "s" : ""} (${Math.round(performance.now() - t0)} ms)`
    : `ready · ${P.name}: ${fmt0(M.n)} passes, ${fmt0(M.mesh.idx.length / 3)} triangles, ${M.islands.length} islands (${Math.round(performance.now() - t0)} ms)`);
}
S.rebuild = rebuild;

/* ------------------------------------------------------------- UI wiring */
for (const id of ["d3from", "d3to", "d3vol"]) el(id).addEventListener("change", () => scheduleBuild(false));
el("d3conn").addEventListener("input", () => { el("d3connv").textContent = (+el("d3conn").value).toFixed(1) + " m"; });
el("d3conn").addEventListener("change", () => scheduleBuild(false));
el("d3dxf").addEventListener("click", exportDxf);
el("d3csv").addEventListener("click", exportCsv);
el("d3cyccsv").addEventListener("click", exportCycles);
el("d3color").addEventListener("change", recolor);
el("d3vex").addEventListener("input", () => { applyVex(); frameCamera(false); });

if (location.hash === "#dig3d") setSheet("dig3d");
"""
