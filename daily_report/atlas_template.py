"""HTML template for the Mine Atlas (imported by build_atlas.py).

Placeholders: __PAYLOAD__ (JSON), __CONTOUR_B64__ (PNG base64).
"""

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bayankhundii Mine Atlas</title>
<style>
  *{box-sizing:border-box}
  body{font-family:Calibri,'Segoe UI',Arial,sans-serif;color:#111;background:#f1efe9;margin:0;padding:16px 0 80px}
  .sheet{width:1280px;max-width:97vw;margin:0 auto;background:#fff;border-radius:6px;padding:22px 28px 40px;box-shadow:0 2px 14px rgba(16,24,32,.14)}
  .bigbtn{display:inline-flex;align-items:center;gap:9px;background:linear-gradient(180deg,#d7b23a,#9a7b17);
          color:#1b1e21 !important;font-weight:700;font-size:14px;letter-spacing:.8px;
          font-family:Bahnschrift,'Segoe UI Semibold','Segoe UI',Arial,sans-serif;
          padding:9px 20px;border-radius:6px;text-decoration:none;
          box-shadow:0 2px 7px rgba(154,123,23,.5);border:1px solid #8a6e10}
  .bigbtn:hover{background:linear-gradient(180deg,#c9a227,#84690e)}
  .titleblock{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;
              background:#262c31;color:#fff;margin:-22px -28px 0;padding:22px 28px 16px;
              border-radius:6px 6px 0 0;border-bottom:3px solid #c9a227}
  h1{font-size:23px;margin:0;font-family:Bahnschrift,'Segoe UI Semibold','Segoe UI',Arial,sans-serif;letter-spacing:1.2px;color:#fff}
  .titleblock .meta{color:#9aa1a7}
  .titleblock .meta b, .titleblock .navlink a{color:#d7b23a}
  .meta{font-size:11px;color:#666}
  .navlink{font-size:13px;font-weight:700}
  nav.toc{position:sticky;top:0;z-index:40;background:#fff;border-bottom:2px solid #c9a227;
          display:flex;flex-wrap:wrap;gap:4px 6px;padding:8px 2px;font-size:12px;margin-bottom:4px;align-items:center}
  nav.toc a{color:#3a4147;font-weight:700;text-decoration:none;white-space:nowrap;
            padding:4px 11px;border-radius:13px;transition:background .12s}
  nav.toc a:hover{background:#f4ecd6}
  nav.toc a.on{background:#c9a227;color:#1b1e21}
  nav.toc .spring{flex:1}
  body{counter-reset:sec}
  .banner{background:#262c31;color:#fff;font-weight:700;font-size:14.5px;text-align:left;
          font-family:Bahnschrift,'Segoe UI Semibold','Segoe UI',Arial,sans-serif;
          padding:7px 12px 7px 14px;letter-spacing:1.8px;margin-top:30px;border:1px solid #454b50;
          border-left:5px solid #c9a227;counter-increment:sec;
          box-shadow:0 1px 3px rgba(16,24,32,.18);scroll-margin-top:48px}
  .banner::before{content:"0" counter(sec) "  ·  ";color:#d7b23a;letter-spacing:2px}
  .controls{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;font-size:12.5px;margin:8px 0;padding:8px 10px;background:#f7fafa;border:1px solid #dfe5e5}
  .controls label{display:inline-flex;align-items:center;gap:5px;cursor:pointer}
  .controls select,.controls input[type=range]{font:inherit}
  .controls button{font:inherit;font-size:12px;padding:3px 12px;cursor:pointer;border:1px solid #888;background:#fff}
  .controls button:hover{background:#eef7f7}
  .controls .sep{color:#bbb}
  .controls input[type=date]{font:inherit;font-size:12px;padding:1px 4px;border:1px solid #888;background:#fff}
  .controls .hh{width:70px}
  .controls button[hidden]{display:none}
  .invchip{font-size:11.5px;padding:1px 8px;border-radius:9px;background:#eef1f2;color:#3b464d}
  .invchip.live{background:#e3f3ec;color:#17694a;font-weight:600}
  .invchip.warn{background:#fbeee0;color:#8a4b12}
  #gInvDig path{cursor:pointer}
  .clegend i.dot{width:9px;height:9px;border-radius:50%}
  .clegend i.ring{width:7px;height:7px;border-radius:50%;background:#fff !important;border:2.4px solid #1d2a33}
  #tip{position:fixed;pointer-events:none;background:rgba(20,24,28,.92);color:#fff;font-size:11.5px;padding:6px 9px;border-radius:4px;max-width:300px;display:none;z-index:50;line-height:1.45}
  .pchip{display:inline-block;padding:2px 8px;border-radius:10px;border:1px solid #c9ced2;background:#fff;font-size:11px;cursor:pointer;line-height:1.5}
  .pchip.sel{background:#1b1e21;color:#fff;border-color:#1b1e21}
  .pchip.nogeo{border-style:dashed;color:#666}
  .charts{display:grid;grid-template-columns:1fr;gap:16px;margin-top:12px}
  .subhead{font-size:13px;font-weight:700;letter-spacing:1.6px;margin:18px 0 0;
           color:var(--color-text-secondary,#5b666d)}
  .subhead small{font-weight:400;letter-spacing:.4px;color:var(--color-text-tertiary,#8a939a)}
  .charts.three{grid-template-columns:1fr}
  .chart{border:1px solid #e2e7ea;border-radius:6px;padding:12px 14px 6px;background:#fff;break-inside:avoid;box-shadow:0 1px 3px rgba(16,24,32,.08)}
  .chart h4{margin:0 0 7px;font-size:13px;font-weight:600;letter-spacing:.2px;position:relative;padding-bottom:6px}
  .chart h4::after{content:"";position:absolute;left:0;bottom:0;width:34px;height:2px;background:#c9a227}
  .chart svg{width:100%;height:auto;display:block}
  .clegend{display:flex;flex-wrap:wrap;gap:3px 14px;font-size:11px;color:#444;margin:1px 0 5px}
  .clegend span{display:inline-flex;align-items:center;gap:5px}
  .clegend i{width:11px;height:11px;display:inline-block;border-radius:2px}
  .clegend i.line{height:3px;border-radius:1px}
  .clegend i.out{background:#fff !important;border:1.6px solid #7f8a92}
  .clegend i.dash{width:13px;height:0;border-top:2.6px solid #1b1e21;border-radius:0;background:transparent !important}
  .note{font-size:11.5px;color:#555;margin-top:6px;font-style:italic}
  #sankeywrap{border:1px solid #d7dbde;background:#fff;padding:6px;overflow-x:auto}
  table.x{border-collapse:collapse;font-size:12px;width:100%}
  table.x th,table.x td{border:1px solid #c9cfd2;padding:3px 8px;text-align:right;white-space:nowrap}
  table.x th{background:#f6efdb;cursor:pointer;user-select:none}
  table.x td:first-child,table.x th:first-child{text-align:left}
  table.x tr:hover td{background:#f2fbfb}
  table.x tr.sel td{background:#e2f5f5}
  .dbar{height:9px;background:#e5e8ea;border-radius:2px;min-width:110px;overflow:hidden}
  .dbar i{display:block;height:100%;background:#2a78d6}
  .split{display:grid;grid-template-columns:1fr;gap:16px;margin-top:10px}
  .scrolly{max-height:430px;overflow:auto}
  .hbars{font-size:11.5px}
  .hbars .row{display:flex;align-items:center;gap:8px;margin:3px 0}
  .hbars .lbl{width:190px;text-align:right;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .hbars .val{width:78px}
</style>
</head>
<body>
<div class="sheet">
  <div class="titleblock">
    <div>
      <h1>BAYANKHUNDII MINE ATLAS</h1>
      <div class="meta">Movement geometry, material life-cycle &amp; operating analytics from the R4M cube &middot; built <span id="builtAt"></span> &middot; data through <span id="dataThrough"></span></div>
    </div>
    <div style="text-align:right">
      <a class="bigbtn" href="daily_report.html">&larr; DAILY PRODUCTION REPORT</a>
      <div class="meta" style="margin-top:6px">Period: <select id="periodSel"></select></div>
    </div>
  </div>
  <nav class="toc">
    <a href="#secSankey">Life-cycle</a><a href="#secPoly">Polygons</a>
    <a href="#secDigc">Dig compliance</a><a href="#secInv">Ore Inventory</a><a href="#secEquip">Equipment time</a><a href="#secCrew">Crew</a><a href="#secCycle">Cycle anatomy</a>
    <a href="#secHaul">Haul</a>
    <span class="spring"></span>
    <a href="daily_report.html" style="background:#e6f5f5">&larr; Daily Report</a>
  </nav>

  <div class="banner" id="secSankey">MATERIAL LIFE-CYCLE — PIT &rarr; DESTINATION &rarr; MILL (ribbon)</div>
  <div id="sankeywrap"><svg id="sankey" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <div class="note">Ribbon width &prop; dry tonnes for the selected period. Left: source pit polygons. Middle-left: material class. Middle-right: where it was dumped (ROM piles, IWF, topsoil...). Right: reclaim from stockpile buffers into the crusher (mill feed). Hover any ribbon or node.</div>

  <div class="banner" id="secPoly">POLYGON DEPLETION EXPLORER</div>
  <div class="split">
    <div class="scrolly"><table class="x" id="ptable"></table></div>
    <div>
      <div class="chart" data-ck="atl.poly.detail"><h4 id="pdTitle">Select a polygon</h4><div id="pdChart"></div></div>
      <div class="chart" data-ck="atl.poly.dest" style="margin-top:12px"><h4>Destinations of hauled tonnage</h4><div id="pdDest"></div></div>
    </div>
  </div>
  <div class="note">Initial/Mined come from the R4M polygon model; "Hauled (cycles)" is what trucks actually carried in the fetched period. Click a column header to sort; click a row to inspect.</div>

  <div class="banner" id="secDigc">DIG COMPLIANCE — GPS vs DISPATCH POLYGON</div>
  <div class="charts" id="chartsDigc"></div>
  <div class="split">
    <div class="scrolly"><table class="x" id="digcTable"></table></div>
    <div class="chart" data-ck="atl.digc.loader"><h4>Off-polygon share by loading unit</h4><div id="digcLoader"></div></div>
  </div>
  <div class="note">Every cycle carries two polygon ids: the one the dispatcher assigned and the one the loader's high-precision GPS actually stood in (<b>Polygon HPGPS</b>). Where they disagree, the bucket may be taking material from the neighbouring polygon &mdash; an early warning for <b>dilution and ore loss</b> (an ore polygon dug as waste, or vice versa). GPS covers ~3 of 4 cycles; the grey band is tonnage with no GPS fix to check.</div>

  <div class="banner" id="secInv">ORE INVENTORY &mdash; ROM PAD STOCKPILES</div>
  <div class="controls" id="invCtl">
    <label><b>From</b> <input type="date" id="invFromD"> <select id="invFromH" class="hh"></select></label>
    <span class="sep">&rarr;</span>
    <label><b>To</b> <input type="date" id="invToD"> <select id="invToH" class="hh"></select></label>
    <button type="button" id="invSync" hidden title="Follow the report's start-end period again">&#8634; report period</button>
    <span class="sep">|</span>
    <span id="invLive" class="invchip"></span>
  </div>
  <div class="split">
    <div>
      <div id="invwrap" style="position:relative;border:1px solid #3d3d3d;background:#fbfaf8;overflow:hidden">
        <svg id="invmap" xmlns="http://www.w3.org/2000/svg" style="display:block;width:100%;height:520px;cursor:grab"></svg>
      </div>
      <div id="invDigSum" class="clegend" style="margin-top:6px"></div>
      <div id="invList"></div>
    </div>
    <div id="invCard" class="chart" data-ck="atl.inv.card"><h4>Select a stockpile</h4></div>
  </div>

  <div class="banner" id="secEquip">EQUIPMENT TIME MODEL</div>
  <h3 class="subhead" id="eqLoadHead">LOADING UNITS</h3>
  <div class="charts" id="chartsEquipLoad"></div>
  <h3 class="subhead" id="eqHaulHead">HAULING UNITS</h3>
  <div class="charts" id="chartsEquipHaul"></div>
  <div class="note" id="equipNote"><b>Scheduled is not a roster input</b> &mdash; R4M logs a calendar 24 h &times; unit grid and dispatch classifies every hour (Ready / Delay / Standby / Maintenance / Out of plan); Scheduled = 24 h &minus; "out of plan". When dispatch doesn't park idle units as out-of-plan, Scheduled reads as the full fleet around the clock and un-rostered time shows up as <b>Standby</b> instead &mdash; read Standby as "logged but not rostered" on those days. Availability = (scheduled &minus; maintenance) / scheduled. Utilization = operating (Ready) / available. Loading/Hauling classification comes from the R4M equipment dimension (Type R4M); auxiliary units are excluded.
  <br><b>Status hours vs engine hours</b> &mdash; the stacked bars are dispatch clock time (they add up to about 24 h per unit-day); the gold line is the machine&rsquo;s own hourmeter. The gap between the engine line and the Ready block is time the engine ran without the unit being dispatched as productive. Caveats: the hourmeter starts 2026-05-19, three weeks after the status log, it covers 25 of the 27 machines and <b>not the crusher CH01</b>, and ~2% of its readings are bad entries (screened out at 0.2&ndash;24 h per day). Erdene&rsquo;s request to show motor hours inside FLEET MANAGEMENT &rarr; HISTOGRAM STATUS is a change to the R4M Aurora product itself &mdash; this pair is the equivalent this report can build.</div>

  <div class="banner" id="secCrew">CREW &amp; OPERATOR PERFORMANCE</div>
  <div class="charts" id="chartsCrew"></div>
  <div class="split">
    <div class="scrolly"><table class="x" id="opsHaulTable"></table></div>
    <div class="scrolly"><table class="x" id="opsLoadTable"></table></div>
  </div>
  <div class="note">First table: truck (hauling) operators; second: excavator/loader operators &mdash; top 30 by hauled tonnage over the fetched history. Queue and hang minutes are per-cycle averages and depend heavily on route and bench assignment: read them as <b>context, not a ranking</b>. Operators come from the R4M crew roster; crews A&ndash;D are the mine's shift rotations.</div>

  <div class="banner" id="secCycle">CYCLE ANATOMY — WHERE A TRUCK'S MINUTES GO</div>
  <div class="charts" id="chartsCycle"></div>
  <div class="note">Cycle segments from R4M cycle timestamps, averaged per cycle per day. Trucks queueing = not enough loading capacity; excavators hanging = not enough trucks. Whichever line is higher tells you which side of the match is starving.</div>

  <div class="banner" id="secHaul">HAUL EFFICIENCY</div>
  <div class="note"><b>Haulage work (t&middot;km)</b> = for every reportable R4M haul cycle of the day, its dry tonnes &times; its loaded <b>equivalent flat haul</b> (R4M &ldquo;Loaded EFH&rdquo;, km: the loaded route length with uphill ramps converted to the flat distance that costs the same truck effort), summed over the day. It measures transport work rather than tonnes: the same tonnage hauled further or up a steeper ramp gives a taller bar. Every cycle counts, pit loads and rehandle alike. A low bar with normal tonnes means short hauls; a dip in both means fewer cycles (shift change, weather, breakdowns).</div>
  <div class="charts" id="chartsHaul"></div>


  <div style="margin-top:36px;padding-top:10px;border-top:1px solid #e4e1d6;font-size:10.5px;color:#8a9097;display:flex;justify-content:space-between">
    <span>ERDENE MONGOL LLC &middot; BAYANKHUNDII GOLD MINE &middot; generated from the R4M dispatch cube</span>
    <span>built <span id="builtFoot"></span></span>
  </div>
</div>
<div id="tip"></div>

<script>
"use strict";
const D = __PAYLOAD__;
const CONTOUR_B64 = "__CONTOUR_B64__";

/* ---------------------------------------------------------------- colors */
const C_ACT="#2a78d6", C_TGT="#b7bfc6", C_CUM="#1baf7a", C_CUMT="#8a8f94", C_AU="#c9a227";
const CLASS_COLOR = {HG:"#eb6834", MG:"#2a78d6", LG1:"#1baf7a", LG2:"#1baf7a",
  SG:"#eda100", MW:"#c98500", W:"#8a8f94", FD:"#6f7478", BAS:"#a58b5e", TS:"#b5a642",
  EW:"#7a4dd8", TL:"#e87ba4", ROM:"#999", "?":"#999"};
const CLASS_ORDER = ["TS","W","FD","BAS","EW","TL","MW","SG","LG1","LG2","MG","HG"];
const GRP_COLOR = {"Ore":"#2a78d6","Marginal":"#e08b00","Waste":"#8a8f94","Mill feed":"#eb6834"};
function flowColor(dst, cls){
  if (dst === "Crusher" || dst === "Crusher (mill feed)") return "#eb6834";
  if (["HG","MG","LG2"].includes(cls)) return "#2a78d6";
  if (["SG","MW","LG1"].includes(cls)) return "#e08b00";
  return "#8a8f94";
}
function seqRamp(t){ t=Math.max(0,Math.min(1,t));
  const a=[234,241,251], b=[18,81,143];
  const c=a.map((v,i)=>Math.round(v+(b[i]-v)*t)); return `rgb(${c[0]},${c[1]},${c[2]})`; }
function purRamp(t){ t=Math.max(0,Math.min(1,t));
  const a=[240,237,249], b=[74,58,167];
  const c=a.map((v,i)=>Math.round(v+(b[i]-v)*t)); return `rgb(${c[0]},${c[1]},${c[2]})`; }
function elevRamp(t){ const a=[148,168,154], b=[196,176,148];
  const c=a.map((v,i)=>Math.round(v+(b[i]-v)*t)); return `rgb(${c[0]},${c[1]},${c[2]})`; }
const fmt0 = v => (v==null||!isFinite(v))?"":Math.round(v).toLocaleString("en-US");
const fmt1 = v => (v==null||!isFinite(v))?"":v.toLocaleString("en-US",{minimumFractionDigits:1,maximumFractionDigits:1});
const fmt2 = v => (v==null||!isFinite(v))?"":v.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
const esc = s => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/"/g,"&quot;");

/* ---------------------------------------------------------------- tooltip */
const tip = document.getElementById("tip");
function showTip(ev, html){ tip.innerHTML = html; tip.style.display = "block"; moveTip(ev); }
function moveTip(ev){ tip.style.left = Math.min(ev.clientX+14, innerWidth-320)+"px"; tip.style.top = (ev.clientY+12)+"px"; }
function hideTip(){ tip.style.display = "none"; }
document.addEventListener("mousemove", ev => { if (tip.style.display === "block") moveTip(ev); });

/* ------------------------------------------------------------- period sel */
const periodSel = document.getElementById("periodSel");
for (const m of ["all", ...D.months]){
  const o = document.createElement("option"); o.value = m;
  o.textContent = m === "all" ? "All history" : m;
  periodSel.appendChild(o);
}
periodSel.value = D.months[D.months.length-1];
document.getElementById("builtAt").textContent = D.built;
document.getElementById("builtFoot").textContent = D.built;
document.getElementById("dataThrough").textContent = D.dates[D.dates.length-1];
function periodDates(){
  const p = periodSel.value;
  return p === "all" ? D.dates : D.dates.filter(d => d.slice(0,7) === p);
}

/* ============================================= map geometry (shared) */
/* the contour frame: world metres -> SVG units for the stockpile map; the 3D viewer reads
   D.contour + CONTOUR_B64 through window.ATL (the main corridor map was removed 2026-10-27) */
const CM = D.contour, MW_ = CM.x1-CM.x0, MH_ = CM.y1-CM.y0;
const wx = x => x - CM.x0, wy = y => CM.y1 - y;
/* map text carries data-px (screen px) + data-sw (screen px halo); after every
   viewBox change we re-derive the world font-size so labels keep a constant
   on-screen size instead of blowing up as the user zooms in */
function rescaleTexts(svg){
  const bb = svg.getBoundingClientRect();
  const vbb = svg.viewBox.baseVal;
  if (!vbb || !vbb.width || !bb.width || !bb.height) return;
  const k = Math.max(vbb.width / bb.width, vbb.height / bb.height); /* world units per CSS px (meet) */
  for (const t of svg.querySelectorAll("text[data-px]")){
    t.setAttribute("font-size", (+t.dataset.px * k).toFixed(2));
    if (t.dataset.sw) t.setAttribute("stroke-width", (+t.dataset.sw * k).toFixed(2));
    if (t.dataset.ww){ /* cull labels wider than their feature (zoom reveals them) */
      const est = t.textContent.length * +t.dataset.px * 0.62 * k;
      t.style.display = est <= +t.dataset.ww * 1.3 ? "" : "none";
    }
  }
}
window.addEventListener("resize", () => { for (const s of document.querySelectorAll("svg[viewBox]")) if (s.querySelector("text[data-px]")) rescaleTexts(s); });
const NS = "http://www.w3.org/2000/svg";

/* ====================================================== ORE INVENTORY */
/* R4M stock polygons (bench 1237) as shown on the C4M map: a polygon is drawn
   when it was OPEN at any time in the window - o (estimated open date) <= end
   and (c (close date) is null or c >= start), on shift days.
   The window = From / To date + hour above the map (To excluded). It follows the
   report's start-end as shift days (07:00 -> 07:00; one day with DS / NS = that
   shift) until the user edits it (INV_WIN), else the atlas Period (standalone).
   Snapshot: D.pileinfo[key].days[date] = [t dumped in via C4M's stockpile link (dump area -> polygon,
   ts_stockpiles), t loaded out, Au g, Ag g, loads out] per whole shift day.
   Live: R4M_LIVE.cycleRows() (production + sensor_data, shared with the 3D viewer)
   -> the window's dumped in / loaded out per cycle to the hour (cycle time = shift
   date + Hauling Hour, same date key as the snapshot) and the dig points of the
   ROM-pad loadings in the window. Cumulative tonnes and grades stay baked. */
let INV = {rows: new Map(), label: "", s: "", e: "", cov: null, live: false, dots: [], mis: new Map(), loaders: new Map(), npts: 0, capped: false};
let INV_WIN = null;                         /* null = follow the report period; else {s, e} wall-clock ms */
const INVL = {state: "idle", year: null, cycles: null, err: null, noHour: 0, note: ""};
const H1 = 3600e3, DAY1 = 86400e3, INV_DOT_CAP = 15000, MIS_M = 15;
/* wall-clock times as UTC ms: no time-zone dependency wherever the page is opened */
const utcMs = (d, h) => { const [y, m, dd] = d.split("-").map(Number); return Date.UTC(y, m - 1, dd, h || 0); };
const isoDay = ms => new Date(ms).toISOString().slice(0, 10);
const nextDay = d => isoDay(utcMs(d, 0) + DAY1);
const shiftDay = ms => isoDay(ms - 7 * H1);                  /* the shift day an hour belongs to (07:00 start) */
const fmtTs = ms => { const s = new Date(ms).toISOString(); return s.slice(0, 10) + " " + s.slice(11, 13) + ":00"; };
const cycTs = (d, h) => utcMs(d, h) + (h < 7 ? DAY1 : 0);   /* shift date + clock hour -> wall clock */

function invDefaultWin(){
  const p = window.RPT && window.RPT.period ? window.RPT.period() : null;
  if (p && p.start && p.end){                   /* the report sets its period after the atlas has run once */
    if (p.start === p.end && p.shift === "DS") return {s: utcMs(p.start, 7), e: utcMs(p.start, 19)};
    if (p.start === p.end && p.shift === "NS") return {s: utcMs(p.start, 19), e: utcMs(nextDay(p.start), 7)};
    return {s: utcMs(p.start, 7), e: utcMs(nextDay(p.end), 7)};
  }
  const ds = periodDates();
  return {s: utcMs(ds[0], 7), e: utcMs(nextDay(ds[ds.length - 1]), 7)};
}
const invWin = () => INV_WIN || invDefaultWin();
const invFromD = document.getElementById("invFromD"), invFromH = document.getElementById("invFromH");
const invToD = document.getElementById("invToD"), invToH = document.getElementById("invToH");
for (const sel of [invFromH, invToH]) for (let h = 0; h < 24; h++){
  const o = document.createElement("option"); o.value = String(h); o.textContent = String(h).padStart(2, "0") + ":00";
  sel.appendChild(o);
}
function invWriteControls(w){
  invFromD.value = isoDay(w.s); invFromH.value = String(new Date(w.s).getUTCHours());
  invToD.value = isoDay(w.e); invToH.value = String(new Date(w.e).getUTCHours());
}
function invReadControls(){
  const ok = v => /^\d{4}-\d{2}-\d{2}$/.test(v);
  if (!ok(invFromD.value) || !ok(invToD.value)){ invWriteControls(invWin()); return; }
  const s = utcMs(invFromD.value, +invFromH.value);
  let e = utcMs(invToD.value, +invToH.value);
  if (e <= s) e = s + H1;                                    /* To must be after From */
  INV_WIN = {s, e};
  refreshInv();
}
[invFromD, invFromH, invToD, invToH].forEach(el => el.addEventListener("change", invReadControls));
document.getElementById("invSync").addEventListener("click", () => { INV_WIN = null; refreshInv(); });

/* geometry: stock polygon rings (UTM), point-in-polygon (even-odd across rings, as drawn) */
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
const inRings = (x, y, rings) => rings.reduce((n, r) => n + (pointInRing(x, y, r) ? 1 : 0), 0) % 2 === 1;
function distToRings(x, y, rings){             /* metres to the nearest edge */
  let best = Infinity;
  for (const r of rings) for (let i = 0, j = r.length - 1; i < r.length; j = i++){
    const ax = r[j][0], ay = r[j][1], dx = r[i][0] - ax, dy = r[i][1] - ay, L = dx * dx + dy * dy;
    const t = L ? Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / L)) : 0;
    const ex = ax + t * dx - x, ey = ay + t * dy - y;
    best = Math.min(best, ex * ex + ey * ey);
  }
  return Math.sqrt(best);
}
/* C4M writes a new polygon id at every edit and keeps the original in id_poligono (SMG-1C-21 #4166
   -> #4169, #4195, #4245, ...); the map's piles carry the original (R4M register) id, the cycles the
   version: D.pver maps version -> original (C4M ts_poligono, baked at build time) */
const PVER = new Map(Object.entries(D.pver || {}).map(([v, r]) => [+v, +r]));
/* when each original was on the C4M map, to the second (UTC+8 wall clock, as the cycles):
   dispatchers create a stock polygon for a new pile and close it once the pile is depleted */
const tsMs = t => { const m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/.exec(t || "");
  return m ? Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]) : null; };
const PLIFE = new Map(Object.entries(D.plife || {}).map(([id, v]) => [+id, v[1].map(([a, b]) => [tsMs(a), b ? tsMs(b) : Infinity])]));
const onMapIn = (pid, ws, we) => { const L = PLIFE.get(+pid); return L ? L.some(([a, b]) => a < we && b > ws) : null; };
/* each version's own time on the C4M map: which outline to draw for a window */
const PVLIFE = new Map(Object.entries(D.pvlife || {}).map(([id, v]) => [+id, [tsMs(v[0]), v[1] ? tsMs(v[1]) : Infinity]]));
/* one pile per ORIGINAL id (PID2KEY); every version outline in D.pilegeo[k].v */
const PID2KEY = new Map();
function addOutline(k, vid, ring){ const geo = D.pilegeo[k]; (geo.v = geo.v || {})[vid] = ring; }
function addStock(k){                      /* a pile may have no outline (not in R4M's register) */
  const inf = D.pileinfo[k], geo = D.pilegeo[k];
  if (!inf) return;
  PID2KEY.set(+inf.pid, k);
  if (!geo) return;
  const v = geo.v || {[inf.pid]: geo.c};
  geo.v = {};
  for (const vid in v) addOutline(k, vid, v[vid]);
}
for (const k in D.pileinfo) addStock(k);
const rootOf = pid => PVER.has(pid) ? PVER.get(pid) : pid;
const pileOf = pid => pid === null ? null : (PID2KEY.get(rootOf(pid)) || null);
/* the outline on the C4M map during [ws, we): the latest version alive in it, else the newest one */
function verRing(k, ws, we){
  const v = D.pilegeo[k].v || {};
  let best = null, bs = -Infinity, top = -1;
  for (const vid in v){
    const L = PVLIFE.get(+vid);
    if (L && L[0] < we && L[1] > ws && L[0] > bs){ best = v[vid]; bs = L[0]; }
    if (+vid > top) top = +vid;
  }
  return best || (top >= 0 ? v[top] : D.pilegeo[k].c);
}
/* stock polygons created after this build: from R4M's live polygon register (same download as
   the 3D viewer), with their C4M lifetime when the build knew it; no snapshot history. Outlines of
   further versions of known piles are added to those piles. */
function addLivePiles(geo){
  if (!geo || !geo.map) return 0;
  let n = 0;
  for (const [id, g] of geo.map){
    if (String(g.bench) !== String(D.stockbench) || !g.ring || g.ring.length < 3) continue;
    if (!g.ring.some(([x, y]) => x >= CM.x0 && x <= CM.x1 && y >= CM.y0 && y <= CM.y1)) continue;
    const root = rootOf(+id), ring = g.ring.map(([x, y]) => [+x.toFixed(1), +y.toFixed(1)]);
    const known = PID2KEY.get(root);
    if (known){
      if (!D.pilegeo[known]) D.pilegeo[known] = {c: ring, rings: [ring], v: {}};
      if (!D.pilegeo[known].v[id]) addOutline(known, id, ring);
      continue;
    }
    const L = PLIFE.get(root);
    if (!L && g.status !== "open") continue;          /* closed and unknown to the build: no lifetime */
    let k = g.name || ("#" + root);
    if (D.pileinfo[k]) k = `${k} #${root}`;
    const o = L ? isoDay(L[0][0]) : isoDay(Date.now() + 8 * H1);
    const c = L ? (isFinite(L[L.length - 1][1]) ? isoDay(L[L.length - 1][1]) : null) : null;
    D.pileinfo[k] = {pid: root, name: g.name || ("#" + root), st: c ? "closed" : "open", k: g.color || "", o, c, x: !!L,
                     cls: "", n: 0, days: {}, srcs: [], locs: [], live: true};
    D.pilegeo[k] = {c: ring, rings: [ring], v: {[id]: ring}};
    addStock(k); n++;
  }
  return n;
}
/* the pile a ROM-pad dump went into = C4M's stockpile assignment (ts_stockpiles, baked at build
   time): the stock polygon the cycle's dump area fed at that moment; none -> unassigned */
const DROOT = new Map(Object.entries(D.droot || {}).map(([k, v]) => [+k, +v]));
const DLINK = new Map(Object.entries(D.dlink || {}).map(([d, L]) => [+d, L.map(([p, a, b]) => [+p, tsMs(a), b ? tsMs(b) : Infinity])]));
function linkedPile(dumpId, t){
  const L = DLINK.get(DROOT.has(dumpId) ? DROOT.get(dumpId) : dumpId);
  if (L) for (const [p, a, b] of L) if (a <= t && t < b) return PID2KEY.get(rootOf(p)) || null;
  return null;
}

/* live cycles -> [{ts, ..., key (assigned stock polygon), inKey (pile dumped into), dig}] sorted by ts */
function invParse(R){
  const L = window.R4M_LIVE || {};
  const EX = L.EXCLUDE_EQ || new Set(["EX127"]);
  const eqn = new Map((R.equip || []).map(r => [r["Id Equipment"], String(r["Equipment"] || "")]));
  const pname = new Map((R.poly || []).map(r => [r["Id Polygon"], String(r["Polygon"] || "")]));
  const mcode = new Map((R.mat || []).map(r => [r["Id Material"], String(r["Material Code"] || "")]));
  const dloc = new Map((R.dump || []).map(r => [r["Id Location Dump"], {name: String(r["Location Dump"] || ""), rom: r["Region"] === "ROM Pad"}]));
  const lloc = new Map((R.lload || []).map(r => [r["Id Location Load"], {name: String(r["Location Load"] || ""), rom: r["Region"] === "ROM Pad"}]));
  const SH = {A: "DS", B: "NS"}, out = [], maxP = new Map();
  let noHour = 0;
  for (const r of R.prod){
    if (r["It is reportable for production"] !== true) continue;
    const loader = eqn.get(r["Id Equipment Loading"]) || "";
    if (EX.has(loader)) continue;
    const h = r["Hauling Hour"], date = String(r["Date Cube Hauling"] || "").slice(0, 10);
    if (h === null || h === undefined || !(h >= 0 && h <= 23) || !/^\d{4}-\d{2}-\d{2}$/.test(date)){ noHour++; continue; }
    const co = R.coors.get(r["C4M ID Hauling"]) || null;
    const pid = (r["Id Polygon"] === null || r["Id Polygon"] === undefined) ? null : +r["Id Polygon"];
    const key = pileOf(pid);
    const dl = dloc.get(r["Id Location Dump"]) || {name: "", rom: false};
    const ll = lloc.get(r["Id Location Load"]) || {name: "", rom: false};
    const c = {cid: r["C4M ID Hauling"], ts: cycTs(date, +h), date, ver: pid !== null && PVER.has(pid) ? PVER.get(pid) : null,
      shift: SH[r["Hauling Shift"]] || String(r["Hauling Shift"] || ""),
      loader, truck: eqn.get(r["Id Equipment Hauling"]) || "", t: r["Dry Tonnes"] || 0, pid, key,
      pname: pid === null ? "" : (pname.get(pid) || ("#" + pid)), mat: mcode.get(r["Id Material"]) || "",
      passes: r["Number of passes"] || 0, dumpName: dl.name, isRom: dl.rom, loadName: ll.name,
      inKey: dl.rom ? linkedPile(+r["Id Location Dump"], cycTs(date, +h) + H1 / 2) : null, dig: null, romLoad: false};
    /* dig point(s) of a ROM-pad loading (load location in the ROM Pad region, or a stock polygon
       assigned): bucket passes when logged, else the loading unit's own GPS position */
    const dkey = key;
    c.romLoad = ll.rom || !!dkey;
    if ((ll.rom || dkey) && co && (co.pts.length || co.eq)){
      const pts = co.pts.length ? co.pts.map(p => [p[0], p[1]]) : [co.eq];
      const mx = pts.reduce((a, p) => a + p[0], 0) / pts.length, my = pts.reduce((a, p) => a + p[1], 0) / pts.length;
      let off = null;                                   /* metres outside the assigned polygon */
      if (dkey && D.pilegeo[dkey]){                     /* the cycle's own version outline, else the one on the map then */
        const rg = [D.pilegeo[dkey].v[pid] || verRing(dkey, c.ts, c.ts + H1)];
        off = inRings(mx, my, rg) ? 0 : distToRings(mx, my, rg);
      }
      c.dig = {pts, bucket: co.pts.length > 0, key: dkey, off, mis: off !== null && off > MIS_M};
    }
    out.push(c);
    if (c.passes > (maxP.get(loader) || 0)) maxP.set(loader, c.passes);
  }
  out.sort((a, b) => a.ts - b.ts || a.cid - b.cid);
  /* the loaders' pass count is always 1 in C4M (no bucket detection): count bucket passes only
     for units that ever logged more than one */
  for (const c of out) c.bk = (maxP.get(c.loader) || 0) > 1;
  /* class of a pile the build did not know = dominant material loaded out of it */
  const mt = new Map();
  for (const c of out) if (c.key && D.pileinfo[c.key].live && c.mat){
    const m = mt.get(c.key) || {}; m[c.mat] = (m[c.mat] || 0) + c.t; mt.set(c.key, m); }
  for (const [k, m] of mt) D.pileinfo[k].cls = Object.entries(m).sort((a, b) => b[1] - a[1])[0][0];
  return {cycles: out, noHour};
}
function invStatus(){
  const el = document.getElementById("invLive");
  if (!el) return;
  const st = INVL.state;
  el.className = "invchip" + (st === "ready" ? " live" : st === "error" ? " warn" : "");
  if (st === "ready") el.textContent = `LIVE R4M cycles · ${fmt0(INVL.cycles.length)} cycles · ${INVL.year}`;
  else if (st === "loading") el.textContent = "fetching R4M cycles + loader GPS (≈ 11 MB)…";
  else if (st === "error"){
    el.innerHTML = `&#9888; live cycles unavailable: ${esc(INVL.err && INVL.err.auth ? "R4M session expired — sign in" : (INVL.err && INVL.err.message) || "network error")} &middot; snapshot, whole days <button type="button" id="invRetry" style="font-size:11px;padding:0 8px">Retry</button>`;
    const b = document.getElementById("invRetry");
    if (b) b.addEventListener("click", invLoadLive);
  } else el.textContent = INVL.note || "snapshot · whole shift days";
}
async function invLoadLive(){
  const L = window.R4M_LIVE;
  if (INVL.state === "loading" || INVL.state === "ready") return;
  if (location.protocol === "file:" || !L || !L.cycleRows || L.demo){
    INVL.state = "none";
    INVL.note = L && L.demo ? "snapshot · whole shift days (demo build)" : "snapshot · whole shift days (live cycles need the R4M host)";
    invStatus(); return;
  }
  INVL.state = "loading"; INVL.err = null; invStatus(); refreshInv();
  try {
    const R = await L.cycleRows();
    INVL.added = addLivePiles(R.geo);
    const P = invParse(R);
    INVL.cycles = P.cycles; INVL.noHour = P.noHour; INVL.year = R.year; INVL.state = "ready";
  } catch (e){
    console.warn("stockpile map: live cycles unavailable:", e);
    INVL.state = "error"; INVL.err = e;
  }
  invStatus(); refreshInv();
}
/* load when the section comes near the viewport (it is far down the page) */
if ("IntersectionObserver" in window){
  const io_ = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)){ io_.disconnect(); invLoadLive(); } }, {rootMargin: "800px 0px"});
  io_.observe(document.getElementById("secInv"));
} else setTimeout(invLoadLive, 0);
invStatus();                                    /* "snapshot" until the live cycles are in */

function invRange(){
  const w = invWin();
  const s = shiftDay(w.s), e = shiftDay(w.e - H1);             /* shift days the window touches */
  const y = String(INVL.year);
  const live = INVL.state === "ready" && s.slice(0, 4) === y && e.slice(0, 4) === y;
  return {s, e, ws: w.s, we: w.e, live, label: `${fmtTs(w.s)} → ${fmtTs(w.e)}`};
}
function invActive(){
  const R = invRange(), rows = new Map();
  for (const k in D.pileinfo){
    let per = 0, out = 0, cum = 0, au = 0, ag = 0, first = null, last = null;
    let n = 0;
    for (const d in D.pileinfo[k].days){
      if (d > R.e) continue;
      const v = D.pileinfo[k].days[d];
      cum += v[0]; au += v[2]; ag += v[3];
      if (v[0] > 0){ if (first === null || d < first) first = d; if (last === null || d > last) last = d; }
      if (d >= R.s){ per += v[0]; out += v[1]; n += v[4] || 0; }
    }
    const inf = D.pileinfo[k];
    /* shown = on the C4M map at any moment of the window (C4M's create / close times); piles the
       build has no lifetime for fall back to R4M's open / close dates (shift days) */
    const on = onMapIn(inf.pid, R.ws, R.we);
    if (on === null ? (inf.o <= R.e && (!inf.c || inf.c >= R.s)) : on)
      rows.set(k, {per: R.live ? 0 : per, out: R.live ? 0 : out, n: R.live ? 0 : n, cum, au, ag, first, last, byL: new Map()});
  }
  for (const k of rows.keys()){                     /* draw the outline that was on the C4M map in the window */
    if (!D.pilegeo[k]) continue;
    const rg = verRing(k, R.ws, R.we); D.pilegeo[k].c = rg; D.pilegeo[k].rings = [rg];
  }
  const res = {rows, label: R.label, s: R.s, e: R.e, live: R.live, cov: null, dots: [], mis: new Map(),
               loaders: new Map(), npts: 0, capped: false, noGps: 0, unl: new Map()};
  let all = 0, ins = 0;
  if (R.live){
    const C = INVL.cycles;
    let lo = 0, hi = C.length;                                  /* first cycle at or after the start */
    while (lo < hi){ const m = (lo + hi) >> 1; if (C[m].ts < R.ws) lo = m + 1; else hi = m; }
    for (let i = lo; i < C.length && C[i].ts < R.we; i++){
      const c = C[i];
      if (c.key && rows.has(c.key)){
        const r = rows.get(c.key), u = r.byL.get(c.loader) || {n: 0, t: 0, p: 0, bk: c.bk};
        r.out += c.t; r.n++; u.n++; u.t += c.t; u.p += c.passes; r.byL.set(c.loader, u);
      }
      if (c.inKey && rows.has(c.inKey)) rows.get(c.inKey).per += c.t;
      if (c.isRom){ all += c.t; if (c.inKey) ins += c.t; else res.unl.set(c.dumpName, (res.unl.get(c.dumpName) || 0) + c.t); }
      if (!c.dig){ if (c.romLoad) res.noGps++; continue; }
      res.dots.push(c); res.npts += c.dig.pts.length;
      const lw = res.loaders.get(c.loader) || {n: 0, mis: 0};
      lw.n++; if (c.dig.mis) lw.mis++; res.loaders.set(c.loader, lw);
      if (c.dig.key){ const m = res.mis.get(c.dig.key) || {n: 0, out: 0}; m.n++; if (c.dig.mis) m.out++; res.mis.set(c.dig.key, m); }
    }
    if (res.dots.length > INV_DOT_CAP){ res.dots = res.dots.slice(-INV_DOT_CAP); res.capped = true; }
  } else {
    for (const d in (D.romday || {}))
      if (d >= R.s && d <= R.e){ all += D.romday[d][0]; ins += D.romday[d][1]; }
  }
  res.cov = all > 0 ? ins / all * 100 : null;
  return res;
}
const invT = k => { const r = INV.rows.get(k); return r ? r.per + r.out : 0; };
const fmtMin = ms => { const s = new Date(ms).toISOString(); return s.slice(0, 10) + " " + s.slice(11, 16); };
const invOpen = inf => {
  const L = PLIFE.get(+inf.pid);
  if (L) return L.map(([a, b]) => `${fmtMin(a)} → ${isFinite(b) ? fmtMin(b) : "still open"}`).join(", ");
  return `${inf.o === inf.c ? "" : "~"}${esc(inf.o)} → ${inf.c ? esc(inf.c) : "still open"}`;
};
const invWinTxt = () => INV.live ? "in the window" : "in the window's shift days";
function refreshInv(){
  INV = invActive();
  invWriteControls(invWin());
  document.getElementById("invSync").hidden = !INV_WIN;
  const lab = document.getElementById("invPeriod");
  if (lab) lab.textContent = INV.label + (INV.live ? " · live R4M cycles" : ` · snapshot, whole shift days ${INV.s} → ${INV.e}`);
  const cv = document.getElementById("invCov");
  if (cv) cv.textContent = INV.cov === null ? `no ROM-pad tonnage ${invWinTxt()}`
    : `${INV.cov.toFixed(0)}% of the ROM-pad tonnage ${invWinTxt()} went to a dump area C4M had assigned to a stock polygon`;
  const best = [...INV.rows.keys()].sort((a, b) => invT(b) - invT(a))[0];
  const keep = selPile && INV.rows.has(selPile) ? selPile : best;
  if (keep) selectPile(keep);
  else {
    selPile = null;
    drawInvMap(); drawInvList();
    document.getElementById("invCard").innerHTML =
      `<h4>No stock polygon on the map</h4><div class="note">No stock polygon was on the C4M map in ${esc(INV.label)}.</div>`;
  }
  drawInvDig();
}
function pileTip(k){
  const inf = D.pileinfo[k] || {}, r = INV.rows.get(k) || {};
  let h = `<b>${esc(inf.name)}</b> &middot; ${esc(inf.cls || "")} &middot; open ${invOpen(inf)}` +
    `<br>In the window${INV.live ? "" : " (whole shift days)"}: dumped in <b>${fmt0(r.per)} t</b> &middot; loaded out <b>${fmt0(r.out)} t</b> in <b>${fmt0(r.n)}</b> loads` +
    `<br>Dumped in to end date: ${fmt0(r.cum)} t @ Au ${fmt2(r.cum ? r.au / r.cum : 0)} / Ag ${fmt2(r.cum ? r.ag / r.cum : 0)} g/t`;
  if (inf.live) h += `<br><i>created after this page was built: window figures only</i>`;
  if (inf.locs && inf.locs.length)
    h += `<br><u>C4M dump areas</u>: ${inf.locs.slice(0, 3).map(x => esc(x[0])).join(", ")}`;
  return h + `<br><i>click to inspect</i>`;
}
function pilePath(geo){
  return (geo.rings || [geo.c]).map(r =>
    "M" + r.map(c => wx(c[0]).toFixed(1) + " " + wy(c[1]).toFixed(1)).join("L") + "Z").join("");
}
let selPile = null;
function drawPilesInto(layer, labelSize, clickFn){
  layer.innerHTML = "";
  const entries = Object.entries(D.pilegeo).filter(([k]) => INV.rows.has(k));
  for (const [pile, geo] of entries){
    const inf = D.pileinfo[pile];
    const baseOp = "0.55";
    const el = document.createElementNS(NS, "path");
    el.setAttribute("d", pilePath(geo));
    el.setAttribute("fill", (inf && (inf.k || CLASS_COLOR[inf.cls])) || "#9aa5aa");   /* C4M's own polygon colour */
    el.setAttribute("fill-rule", "evenodd");
    el.setAttribute("fill-opacity", pile === selPile ? "0.85" : baseOp);
    el.setAttribute("stroke", "#2d3438");
    el.setAttribute("stroke-width", pile === selPile ? "2.5" : "1.3");
    el.setAttribute("vector-effect", "non-scaling-stroke");
    el.style.cursor = "pointer";
    el.addEventListener("mouseenter", ev => { el.setAttribute("fill-opacity", "0.9"); showTip(ev, pileTip(pile)); });
    el.addEventListener("mouseleave", () => { el.setAttribute("fill-opacity", pile === selPile ? "0.85" : baseOp); hideTip(); });
    el.addEventListener("click", ev => { ev.stopPropagation(); clickFn(pile); });
    layer.appendChild(el);
    if (labelSize){   /* labelSize = constant SCREEN px (rescaled on zoom) */
      const cx = geo.c.reduce((a, c) => a + c[0], 0) / geo.c.length;
      const cy = geo.c.reduce((a, c) => a + c[1], 0) / geo.c.length;
      const t_ = document.createElementNS(NS, "text");
      t_.setAttribute("x", wx(cx)); t_.setAttribute("y", wy(cy));
      t_.dataset.px = labelSize; t_.dataset.sw = labelSize / 4.5;
      const xs = geo.c.map(c => c[0]);
      t_.dataset.ww = (Math.max(...xs) - Math.min(...xs)).toFixed(0);
      t_.setAttribute("font-weight", "700");
      t_.setAttribute("text-anchor", "middle");
      t_.setAttribute("fill", "#1d2a33");
      t_.setAttribute("stroke", "#fff");
      t_.setAttribute("paint-order", "stroke");
      t_.setAttribute("pointer-events", "none");
      t_.textContent = (inf ? inf.name : pile).replace(/^1237[_ ]/, "");  /* finger short names, full name in tooltip */
      layer.appendChild(t_);
    }
  }
  rescaleTexts(layer.ownerSVGElement);
}
function invBars(title, list, colorOf){
  if (!list || !list.length) return "";
  const mx = Math.max(1, ...list.map(x => x[1]));
  let h = `<div style="font-size:12px;font-weight:700;margin:8px 0 4px">${title}</div><div class="hbars">`;
  for (const x of list){
    h += `<div class="row"><span class="lbl" title="${esc(x[0])}">${esc(x[0])}</span>
      <div class="dbar" style="flex:1"><i style="width:${(x[1]/mx*100).toFixed(0)}%;background:${colorOf(x)}"></i></div>
      <span class="val">${fmt0(x[1])} t</span></div>`;
  }
  return h + "</div>";
}
/* loads / tonnes / bucket passes moved out of a pile in the window, per loading unit (live only) */
function unitTable(r){
  if (!INV.live || !r.byL || !r.byL.size) return "";
  const rows = [...r.byL.entries()].sort((a, b) => b[1].t - a[1].t);
  const td = 'style="padding:1px 8px;text-align:right"';
  return `<table style="font-size:12px;border-collapse:collapse;margin:3px 0 5px"><tr style="color:#5b666d">
    <th style="text-align:left;padding:1px 8px 1px 0">Loading unit</th><th ${td}>Loads</th><th ${td}>Tonnes</th><th ${td}>Bucket passes</th></tr>` +
    rows.map(([l, u]) => `<tr><td style="padding:1px 8px 1px 0"><b>${esc(l || "?")}</b></td><td ${td}>${fmt0(u.n)}</td><td ${td}>${fmt0(u.t)}</td>` +
      `<td ${td}>${u.bk ? fmt0(u.p) : `<span style="opacity:.7" title="C4M records one pass per load for this unit (no bucket detection)">not recorded</span>`}</td></tr>`).join("") +
    `</table>`;
}
function selectPile(pile){
  selPile = pile;
  drawInvMap(); drawInvList();
  const inf = D.pileinfo[pile] || {};
  const r = INV.rows.get(pile) || {per: 0, out: 0, cum: 0, au: 0, ag: 0};
  const mi = INV.live ? INV.mis.get(pile) : null;
  const card = document.getElementById("invCard");
  let h = `<h4>${esc(inf.name || pile)} — ${esc(inf.cls || "stock polygon")}</h4>
    <div style="font-size:10.5px;font-weight:700;letter-spacing:1px;color:#9a7b17;margin:6px 0 2px">R4M STOCK POLYGON &middot; ${esc(String(inf.st || "").toUpperCase())} NOW &middot; ID ${inf.pid}</div>
    <div style="font-size:12.5px;margin-bottom:2px">On the C4M map: <b>${invOpen(inf)}</b>${PLIFE.has(+inf.pid) ? "" : ` <span style="opacity:.7">(~ = estimated open date)</span>`}</div>
    <div style="font-size:12.5px;line-height:1.65;margin-bottom:4px">
    ${INV.live ? "In the window" : "In the window&rsquo;s shift days"} (${esc(INV.live ? INV.label : INV.s + " → " + INV.e)}):<br>
    loaded out <b style="font-size:15px">${fmt0(r.out)} t</b> in <b style="font-size:15px">${fmt0(r.n)}</b> loads &middot; dumped in <b>${fmt0(r.per)} t</b><br>
    ${unitTable(r)}
    ${mi ? `Dig points: <b>${fmt0(mi.n)}</b> loadings from it in the window, <b>${fmt0(mi.out)}</b> more than ${MIS_M} m outside the polygon<br>` : ""}
    ${D.pilegeo[pile] ? "" : `<span style="opacity:.75">No outline in R4M&rsquo;s polygon register: listed (dashed chip), not drawn on the map.</span><br>`}
    ${inf.live ? `<span style="opacity:.75">Created after this page was built (data to ${esc(D.dates[D.dates.length - 1])}): no history, grades or sources here.</span><br>` : ""}
    Dumped in up to ${esc(INV.e)}: <b>${fmt0(r.cum)} t</b>${D.dates[D.dates.length - 1] < INV.e ? ` <span style="opacity:.7">(snapshot to ${esc(D.dates[D.dates.length - 1])})</span>` : ""}<br>
    Grade: <b>Au ${fmt2(r.cum ? r.au / r.cum : 0)}</b> &middot; <b>Ag ${fmt2(r.cum ? r.ag / r.cum : 0)}</b> g/t
      &middot; contained <b>${fmt1(r.au / 1000)} kg</b> Au &middot; <b>${fmt1(r.ag / 1000)} kg</b> Ag<br>
    ${r.first ? `First dump in: <b>${esc(r.first)}</b> &middot; last: <b>${esc(r.last)}</b><br>` : ""}
    <span style="opacity:.75">Loaded out = cycles loaded from this polygon (any of its C4M versions; one load = one truck, or one bucket carried by LO215); dumped in = ROM-pad cycles at the dump area C4M assigned to it at the time (C4M stockpile link).</span>
    </div>`;
  h += invBars("C4M dump area assigned to it (all history)", inf.locs, () => "#8a8f94");
  const cr = inf.cr;
  h += invBars(cr && cr.n ? `Dumped from (pit polygons of ${esc(cr.o)}, weighted to this crushed pile's ${fmt0(cr.t)} t, all history)` : "Dumped from (pit polygons, all history)", inf.srcs, x => CLASS_COLOR[x[2]] || "#9aa5aa");
  if (cr && cr.n && cr.b === "out") h += `<div style="font-size:11.5px;opacity:.75;margin-top:4px">C4M records almost no dumps into crushed piles, so this pile's tonnes are the tonnes loaded out of it.</div>`;
  if (cr && !cr.n) h += `<div style="font-size:12px;margin-top:8px">Crushed from <b>${esc(cr.o)}</b>: C4M has no pit source polygons recorded for it.</div>`;
  card.innerHTML = h;
}
/* chip list of every stock polygon active in the period */
function drawInvList(){
  const el = document.getElementById("invList");
  if (!el) return;
  const ks = [...INV.rows.keys()].sort((a, b) => (INV.rows.get(b).out - INV.rows.get(a).out) || invT(b) - invT(a) || a.localeCompare(b));
  el.innerHTML = ks.map(k => {
    const r = INV.rows.get(k), nm = (D.pileinfo[k] || {}).name || k;
    return `<span class="pchip${k === selPile ? " sel" : ""}${D.pilegeo[k] ? "" : " nogeo"}" data-p="${esc(k)}"` +
      ` style="border-left:6px solid ${esc((D.pileinfo[k] || {}).k || "#9aa5aa")}"` +
      ` title="${esc(nm)} — open ${invOpen(D.pileinfo[k] || {})}; ${fmt0(r.per)} t dumped in, ${fmt0(r.out)} t loaded out ${invWinTxt()} (${esc(INV.label)})">` +
      `${esc(nm)} <span style="opacity:.7">${r.out > 0.01 ? `${fmt0(r.out)} t out · ${fmt0(r.n)} loads` : "no loading"}${r.per > 0.01 ? ` / ${fmt0(r.per)} t in` : ""}</span></span>`;
  }).join(" ");
  el.querySelectorAll(".pchip").forEach(c => c.addEventListener("click", () => selectPile(c.dataset.p)));
}
/* mini-map with its own viewport */
const invmap = document.getElementById("invmap");
const RB = D.rombox;
let ivb = [wx(RB[0]), wy(RB[3]), RB[2] - RB[0], RB[3] - RB[1]];
function applyIVB(){ invmap.setAttribute("viewBox", ivb.join(" ")); rescaleTexts(invmap); }
const gInvBg = document.createElementNS(NS, "g"), gInvPiles = document.createElementNS(NS, "g");
const gInvDig = document.createElementNS(NS, "g"); gInvDig.id = "gInvDig";
invmap.appendChild(gInvBg); invmap.appendChild(gInvPiles); invmap.appendChild(gInvDig);
if (CONTOUR_B64){
  const im = document.createElementNS(NS, "image");
  im.setAttribute("href", "data:image/png;base64," + CONTOUR_B64);
  im.setAttribute("x", 0); im.setAttribute("y", 0);
  im.setAttribute("width", MW_); im.setAttribute("height", MH_);
  im.setAttribute("preserveAspectRatio", "none");
  gInvBg.appendChild(im);
}
function drawInvMap(){ drawPilesInto(gInvPiles, 10.5, selectPile); }
/* dig points of the window's ROM-pad loadings: one <path> per cycle, a zero-length
   round-capped segment per point (constant on-screen size at any zoom). Colour = the
   stock polygon C4M assigned the cycle to; grey = none; a red ring = the point lies
   more than MIS_M metres outside its assigned polygon */
const pileColor = k => { const i = D.pileinfo[k] || {}; return i.k || CLASS_COLOR[i.cls] || "#9aa5aa"; };
function digTip(c){
  const g = c.dig;
  let h = `<b>${esc(fmtTs(c.ts))}</b> &middot; shift ${esc(c.date)} ${esc(c.shift)}` +
    `<br>loader <b>${esc(c.loader || "?")}</b> &middot; truck ${esc(c.truck || "?")} &middot; ${fmt1(c.t)} t ${esc(c.mat)}` +
    `<br>assigned: <b>${esc(c.pname || "no polygon")}</b>${c.pid !== null ? ` (#${c.pid}${c.ver ? `, C4M version of #${c.ver}` : ""})` : ""}` +
    (c.key || c.pid === null ? "" : " &middot; not a stock polygon on this map") +
    (c.loadName ? `<br>C4M load area: ${esc(c.loadName)}` : "") +
    `<br>dumped at: ${esc(c.dumpName || "?")}` +
    `<br>${g.bucket ? `${g.pts.length} bucket pass${g.pts.length === 1 ? "" : "es"} (GPS)` : "loader&rsquo;s own GPS position (no bucket GPS)"}`;
  if (g.off !== null) h += g.off > 0 ? `<br>${fmt1(g.off)} m outside the assigned polygon` : "<br>inside the assigned polygon";
  if (g.mis) h += `<br><b style="color:#ff8a8a">&#9888; more than ${MIS_M} m outside &mdash; wrong polygon booked or GPS off</b>`;
  return h;
}
/* ROM-pad dumps whose dump area C4M had not assigned to any stock polygon (not counted for a pile) */
function unlTxt(){
  if (!INV.unl || !INV.unl.size) return "";
  const L = [...INV.unl.entries()].sort((a, b) => b[1] - a[1]), tot = L.reduce((a, x) => a + x[1], 0);
  return `<span><b>${fmt0(tot)} t</b> dumped at ROM-pad dump areas C4M had not assigned to a stock polygon: ` +
    L.slice(0, 4).map(([n, t]) => `${esc(n || "?")} ${fmt0(t)} t`).join(", ") + (L.length > 4 ? ", &hellip;" : "") + `</span>`;
}
function drawInvDig(){
  gInvDig.innerHTML = "";
  const sum = document.getElementById("invDigSum");
  if (!INV.live){
    if (sum) sum.innerHTML = INVL.state === "loading" ? "<span>dig points: loading the live R4M cycles…</span>"
      : `<span style="font-style:italic">dig points need the live R4M cycles${INVL.state === "ready" ? ` (they cover ${INVL.year} only)` : ""}</span>`;
    return;
  }
  const frag = document.createDocumentFragment();
  INV.dots.forEach((c, i) => {
    const d = c.dig.pts.map(p => "M" + wx(p[0]).toFixed(1) + " " + wy(p[1]).toFixed(1) + "h0").join("");
    const mk = (stroke, w, op) => {
      const el = document.createElementNS(NS, "path");
      el.setAttribute("d", d); el.setAttribute("fill", "none"); el.setAttribute("stroke", stroke);
      el.setAttribute("stroke-width", w); el.setAttribute("stroke-linecap", "round");
      el.setAttribute("stroke-opacity", op); el.setAttribute("vector-effect", "non-scaling-stroke");
      el.dataset.i = i; frag.appendChild(el);
    };
    if (c.dig.mis) mk("#d1273a", 10, "0.95");
    mk("#1d2a33", c.dig.bucket ? 6 : 7.5, "0.9");                /* dark edge; loader positions slightly larger */
    mk(c.dig.key ? pileColor(c.dig.key) : "#9aa5aa", c.dig.bucket ? 4 : 4.5, "1");
  });
  gInvDig.appendChild(frag);
  if (!sum) return;
  const n = INV.dots.length, nmis = INV.dots.filter(c => c.dig.mis).length, nb = INV.dots.filter(c => c.dig.bucket).length;
  const lw = [...INV.loaders.entries()].sort((a, b) => b[1].n - a[1].n)
    .map(([l, v]) => `${esc(l || "?")} ${fmt0(v.n)}${v.mis ? ` (${fmt0(v.mis)} &gt; ${MIS_M} m out)` : ""}`).join(", ");
  sum.innerHTML = n ? `<span><i class="dot" style="background:#5b8fd6"></i><b>${fmt0(n)}</b> ROM-pad loadings in the window` +
      ` (${fmt0(n - nb)} loader position${n - nb === 1 ? "" : "s"}${nb ? `, ${fmt0(nb)} with ${fmt0(INV.npts - (n - nb))} bucket passes` : ""})` +
      (INV.noGps ? ` &middot; <b>${fmt0(INV.noGps)}</b> more without a GPS position (not drawn)` : "") + `</span>` +
      `<span><i class="ring" style="border-color:#d1273a"></i><b>${fmt0(nmis)}</b> (${(nmis / n * 100).toFixed(1)}%) more than ${MIS_M} m outside the assigned polygon</span>` +
      `<span><i class="dot" style="background:#9aa5aa"></i>assigned polygon not a stock polygon on this map</span>` +
      `<span>by loader: ${lw}</span>` +
      (INV.capped ? `<span><b>showing the latest ${fmt0(INV_DOT_CAP)}</b> &mdash; narrow the window to see all</span>` : "") + unlTxt()
    : `<span style="font-style:italic">no ROM-pad loading with a GPS position in the window${INV.noGps ? ` (${fmt0(INV.noGps)} without one)` : ""}</span>` + unlTxt();
}
gInvDig.addEventListener("mousemove", ev => {
  const el = ev.target.closest("path[data-i]");
  if (el) showTip(ev, digTip(INV.dots[+el.dataset.i]));
});
gInvDig.addEventListener("mouseleave", hideTip);
gInvDig.addEventListener("click", ev => {
  const el = ev.target.closest("path[data-i]"), c = el && INV.dots[+el.dataset.i];
  if (c && c.dig.key && INV.rows.has(c.dig.key)){ ev.stopPropagation(); selectPile(c.dig.key); }
});
let idrag = null;
invmap.addEventListener("mousedown", ev => { idrag = [ev.clientX, ev.clientY, ...ivb]; });
window.addEventListener("mouseup", () => { idrag = null; });
window.addEventListener("mousemove", ev => {
  if (!idrag) return;
  const r = invmap.getBoundingClientRect();
  ivb[0] = idrag[2] - (ev.clientX - idrag[0]) * ivb[2] / r.width;
  ivb[1] = idrag[3] - (ev.clientY - idrag[1]) * ivb[3] / r.height;
  applyIVB();
});
invmap.addEventListener("wheel", ev => {
  ev.preventDefault();
  const r = invmap.getBoundingClientRect();
  const px = ivb[0] + (ev.clientX - r.left) / r.width * ivb[2];
  const py = ivb[1] + (ev.clientY - r.top) / r.height * ivb[3];
  const k = ev.deltaY > 0 ? 1.25 : 0.8;
  ivb = [px - (px - ivb[0]) * k, py - (py - ivb[1]) * k, ivb[2] * k, ivb[3] * k];
  applyIVB();
}, {passive: false});
/* ================================================================ SANKEY */
function drawSankey(){
  const links = D.sankey[periodSel.value] || [];
  const svg = document.getElementById("sankey");
  svg.innerHTML = "";
  const PAD = 10, NW = 14, GAP = 6, MINH = 7;
  const nodes = [new Map(), new Map(), new Map(), new Map()];
  const add = (c, name, t, dir) => {
    const n = nodes[c].get(name) || {name, in: 0, out: 0};
    n[dir] += t; nodes[c].set(name, n);
  };
  for (const l of links){
    const [st, a, b, t] = l;
    if (st === 0){ add(0, a, t, "out"); add(1, b, t, "in"); }
    if (st === 1){ add(1, a, t, "out"); add(2, b, t, "in"); }
    if (st === 2){ add(2, a, t, "out"); add(3, b, t, "in"); }
  }
  const order = c => {
    let arr = [...nodes[c].values()];
    if (c === 1) arr.sort((x, y) => CLASS_ORDER.indexOf(x.name) - CLASS_ORDER.indexOf(y.name));
    else arr.sort((x, y) => Math.max(y.in, y.out) - Math.max(x.in, x.out));
    return arr;
  };
  const cols = [0, 1, 2, 3].map(order);
  /* the pit column lists ~45 named polygons / blasts: grow the canvas so every
     node gets a readable label (min height MINH) */
  const reserve = Math.max(...cols.map((c, ci) => (GAP + (ci === 0 ? MINH : 2)) * c.length));
  const W = 1220, H = Math.max(640, reserve + 420);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", W); svg.setAttribute("height", H);
  const colX = [PAD, 360, 730, 1080];
  const totalT = Math.max(1, ...cols.map(col => col.reduce((s, n) => s + Math.max(n.in, n.out), 0)));
  const kk = (H - 2 * PAD - reserve) / totalT;
  for (const [ci, col] of cols.entries()){
    let y = PAD;
    for (const n of col){
      n.h = Math.max(ci === 0 ? MINH : 2, Math.max(n.in, n.out) * kk);
      n.x = colX[ci]; n.y = y; n.oin = 0; n.oout = 0;
      y += n.h + GAP;
    }
  }
  const find = (c, name) => cols[c].find(n => n.name === name);
  const sorted = [...links].sort((a, b) => b[3] - a[3]);
  for (const l of sorted){
    const [st, a, b, t] = l;
    const cls = st === 0 ? b : (st === 1 ? a : (l[4] || ""));
    const s = find(st, a), e = find(st + 1, b);
    if (!s || !e) continue;
    const h1 = t * kk, x0 = s.x + NW, x1 = e.x;
    const y0 = s.y + s.oout, y1 = e.y + e.oin;
    s.oout += h1; e.oin += h1;
    const cxa = x0 + (x1 - x0) * 0.45, cxb = x0 + (x1 - x0) * 0.55;
    const p = document.createElementNS(NS, "path");
    p.setAttribute("d",
      `M${x0} ${y0} C${cxa} ${y0} ${cxb} ${y1} ${x1} ${y1}` +
      ` L${x1} ${y1 + h1} C${cxb} ${y1 + h1} ${cxa} ${y0 + h1} ${x0} ${y0 + h1} Z`);
    p.setAttribute("fill", CLASS_COLOR[cls] || "#9aa5aa");
    p.setAttribute("fill-opacity", "0.45");
    p.addEventListener("mouseenter", ev => {
      p.setAttribute("fill-opacity", "0.8");
      showTip(ev, `<b>${esc(a)} &rarr; ${esc(b)}</b><br>${esc(cls)} &middot; ${fmt0(t)} t`);
    });
    p.addEventListener("mouseleave", () => { p.setAttribute("fill-opacity", "0.45"); hideTip(); });
    svg.appendChild(p);
  }
  for (const [ci, col] of cols.entries()){
    for (const n of col){
      const r = document.createElementNS(NS, "rect");
      r.setAttribute("x", n.x); r.setAttribute("y", n.y);
      r.setAttribute("width", NW); r.setAttribute("height", n.h);
      r.setAttribute("fill", ci === 1 ? (CLASS_COLOR[n.name] || "#666") : "#262c31");
      r.addEventListener("mouseenter", ev =>
        showTip(ev, `<b>${esc(n.name)}</b><br>in ${fmt0(n.in)} t &middot; out ${fmt0(n.out)} t`));
      r.addEventListener("mouseleave", hideTip);
      svg.appendChild(r);
      const t_ = document.createElementNS(NS, "text");
      const left = ci === 0;
      t_.setAttribute("x", left ? n.x + NW + 5 : n.x - 5);
      t_.setAttribute("y", n.y + Math.min(n.h / 2 + 3.5, n.h + 9));
      t_.setAttribute("font-size", "10.5");
      t_.setAttribute("fill", "#222");
      t_.setAttribute("text-anchor", left ? "start" : "end");
      if (ci === 0 || ci === 1 || ci === 3 || n.h >= 7 || Math.max(n.in, n.out) / totalT > 0.01){
        t_.textContent = `${n.name} ${fmt0(Math.max(n.in, n.out))}`;
        svg.appendChild(t_);
      }
    }
  }
  const caps = ["PIT POLYGON", "MATERIAL CLASS", "DESTINATION", "MILL"];
  caps.forEach((c, i) => {
    const t_ = document.createElementNS(NS, "text");
    t_.setAttribute("x", colX[i] + NW / 2);
    t_.setAttribute("y", H - 2);
    t_.setAttribute("font-size", "10"); t_.setAttribute("font-weight", "700");
    t_.setAttribute("fill", "#888");
    t_.setAttribute("text-anchor", i === 0 ? "start" : (i === 3 ? "end" : "middle"));
    t_.textContent = c;
    svg.appendChild(t_);
  });
}

/* ==================================================== chart engine (bars+lines) */
function niceMax(v){ if(!isFinite(v)||v<=0) return 1;
  const p=Math.pow(10,Math.floor(Math.log10(v))), n=v/p;
  return (n<=1?1:n<=2?2:n<=2.5?2.5:n<=5?5:10)*p; }
const fmtAxis = v => Math.abs(v)>=1e6?(Math.round(v/1e4)/100)+"M":Math.abs(v)>=1e3?Math.round(v/1e2)/10+"k":""+Math.round(v*100)/100;
function drawChart(host, cfg){
  /* chart language v3: bullet-tick targets, capped gradient bars, slot hover
     tooltip, month separators, area wash under cumulative lines, end badges */
  /* size is a contract: cfg.W/H/fs let the same cfg be re-drawn full-page.
     Label density is width-aware - with 16 seven-character month labels in a
     620-unit chart the old fixed n/16 rule overlapped every one of them. */
  const W=cfg.W||1220,H=cfg.H||300,ml=48,mt=14,anyR=(cfg.lines||[]).some(l=>l.right),mr=anyR?46:10,
        cats=cfg.cats,n=cats.length,
        FS=cfg.fs||9.5, FZ=FS/9.5, fz=v=>+(v*FZ).toFixed(1),
        catW=Math.max(1,...cats.map(c=>String(c).length))*FS*0.57+6,
        slot0=(W-ml-mr)/Math.max(n,1),
        rot=(catW>slot0&&n<=40)?-40:0,
        step=rot?1:Math.max(1,Math.ceil(catW/slot0)),
        mb=cfg.mb||(rot?Math.min(52,catW*0.72+12):22),
        pw=W-ml-mr,ph=H-mt-mb;
  const INK="#1b1e21";
  const allBars=cfg.bars||[], lines=cfg.lines||[];
  const isTgt=b=>b.tgt||b.color==="#b7bfc6";
  const ticks=allBars.filter(isTgt), bars=allBars.filter(b=>!isTgt(b));
  const groups=[];
  for (const b of bars){ const key=b.stack===undefined?"g"+groups.length:b.stack;
    let g_=groups.find(x=>x.key===key); if(!g_){g_={key,members:[]};groups.push(g_);} g_.members.push(b); }
  let lMax=cfg.lMax||0;
  for(let i=0;i<n;i++){
    for(const g_ of groups){ let s=0; for(const b of g_.members) s+=Math.max(0,b.values[i]||0); lMax=Math.max(lMax,s); }
    for(const tk of ticks) lMax=Math.max(lMax,tk.values[i]||0);
    for(const l of lines) if(!l.right) lMax=Math.max(lMax,l.values[i]||0);
  }
  lMax=cfg.pct?1:(cfg.lMax||niceMax(lMax));
  let rMax=0; for(const l of lines) if(l.right) for(const v of l.values) rMax=Math.max(rMax,v||0);
  rMax=niceMax(rMax);
  const x=i=>ml+pw*(i+0.5)/n, slotW=pw/n, yL=v=>mt+ph*(1-v/lMax), yR=v=>mt+ph*(1-v/rMax);
  const dark=c=>{const m=c.match(/^#(..)(..)(..)$/); if(!m) return c;
    return "#"+m.slice(1).map(h=>Math.max(0,Math.round(parseInt(h,16)*0.86)).toString(16).padStart(2,"0")).join("");};
  const gid=c=>"g"+c.replace("#","");
  let defs="", seen={};
  for(const b of bars) if(!seen[b.color]){ seen[b.color]=1;
    defs+=`<linearGradient id="${gid(b.color)}" x1="0" y1="0" x2="0" y2="1">`+
          `<stop offset="0" stop-color="${b.color}"/><stop offset="1" stop-color="${dark(b.color)}"/></linearGradient>`; }
  let s=`<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg"><defs>${defs}</defs>`;
  /* grid + axis labels */
  for(let g_=0;g_<=4;g_++){ const yy=mt+ph*g_/4, lv=lMax*(1-g_/4);
    s+=`<line x1="${ml}" y1="${yy}" x2="${ml+pw}" y2="${yy}" stroke="#e9ecef"/>`;
    s+=`<text x="${ml-4}" y="${yy+3.5}" text-anchor="end" font-size="${fz(9)}" fill="#5c6166">${cfg.pct?Math.round(lv*100)+"%":fmtAxis(lv)}</text>`;
    if(anyR) s+=`<text x="${ml+pw+4}" y="${yy+3.5}" font-size="${fz(9)}" fill="#5c6166">${fmtAxis(rMax*(1-g_/4))}</text>`; }
  /* unit caption from title tail (", t" / ", %", " min/cycle" ...) */
  const um=(cfg.title||"").match(/,\s*([\w³·\/%&; ]{1,14})$/);
  if(um) s+=`<text x="${ml}" y="${mt-4}" font-size="${fz(9)}" fill="#8a9097" font-style="italic">${esc(um[1])}</text>`;
  /* month separators when cats look like MM-DD */
  const isDates=typeof cats[0]==="string"&&/^\d{2}-\d{2}$/.test(cats[0]);
  if(isDates){
    for(let i=1;i<n;i++){
      if(cats[i].slice(0,2)!==cats[i-1].slice(0,2)){
        const xx=ml+pw*i/n;
        s+=`<line x1="${xx}" y1="${mt-2}" x2="${xx}" y2="${mt+ph}" stroke="#c9ccd0" stroke-width="1"/>`;
        s+=`<text x="${xx+3}" y="${mt+7}" font-size="${fz(8.5)}" fill="#8a9097" font-weight="700">M${+cats[i].slice(0,2)}</text>`;
      }
    }
  }
  /* thin, or tilt, so labels never collide; the last category is always shown,
     and the regular label before it is dropped when it would sit too close */
  const axIdx=[];
  for(let i=0;i<n;i+=step) axIdx.push(i);
  if(n && axIdx[axIdx.length-1]!==n-1){
    if(n-1-axIdx[axIdx.length-1] < step) axIdx.pop();
    axIdx.push(n-1);
  }
  for(const i of axIdx){
    const xx=x(i).toFixed(1);
    s += rot
      ? `<text class="axl" x="${xx}" y="${(mt+ph+11).toFixed(1)}" text-anchor="end" font-size="${fz(9.5)}" fill="#5c6166" transform="rotate(${rot} ${xx} ${(mt+ph+11).toFixed(1)})">${esc(cats[i])}</text>`
      : `<text class="axl" x="${xx}" y="${(mt+ph+16).toFixed(1)}" text-anchor="middle" font-size="${fz(9.5)}" fill="#5c6166">${esc(cats[i])}</text>`;
  }
  /* area wash under cumulative-looking lines */
  for(const l of lines){
    if(!(l.area||/^(STD|MTD|Cum)/i.test(l.name))) continue;
    const yf=l.right?yR:yL; let pts=[];
    for(let i=0;i<n;i++){ const v=l.values[i];
      if(v===null||v===undefined||!isFinite(v)) continue;
      pts.push([x(i),yf(v)]); }
    if(pts.length>1){
      s+=`<path d="M${pts[0][0].toFixed(1)} ${(mt+ph).toFixed(1)} `+
         pts.map(p=>`L${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ")+
         ` L${pts[pts.length-1][0].toFixed(1)} ${(mt+ph).toFixed(1)} Z" fill="${l.color}" fill-opacity="0.09"/>`;
    }
  }
  /* bars: capped width, rounded top, square base, gradient fill */
  const nG=Math.max(groups.length,1), bw=Math.min(24,Math.max(3,slotW*0.64/nG-1));
  for(let i=0;i<n;i++){
    groups.forEach((g_,gi)=>{ let base=0, stackSum=0;   /* pct: each group is its own 100% stack */
      if(cfg.pct) for(const b of g_.members) stackSum+=Math.max(0,b.values[i]||0);
      const bx=x(i)-(nG*(bw+1))/2+gi*(bw+1)+0.5;
      for(const b of g_.members){ let v=Math.max(0,b.values[i]||0);
        if(cfg.pct) v=stackSum?v/stackSum:0; if(v<=0) continue;
        const y1=yL(base+v), hh=Math.max(yL(base)-yL(base+v),0.6);
        const r=Math.min(4,bw/2,hh), isTop=true;
        if(b.outline){     /* plan / target stacks: white fill, class-coloured outline */
          s+=`<rect x="${(bx+0.7).toFixed(1)}" y="${(y1+0.7).toFixed(1)}" width="${Math.max(bw-1.4,0.5).toFixed(1)}" height="${Math.max(hh-1.4,0.4).toFixed(1)}" fill="#fff" stroke="${b.color}" stroke-width="1.4"/>`;
        } else if(base===0&&r>0.5){
          s+=`<path d="M${bx} ${(y1+hh).toFixed(1)} L${bx} ${(y1+r).toFixed(1)} Q${bx} ${y1.toFixed(1)} ${(bx+r).toFixed(1)} ${y1.toFixed(1)} L${(bx+bw-r).toFixed(1)} ${y1.toFixed(1)} Q${(bx+bw).toFixed(1)} ${y1.toFixed(1)} ${(bx+bw).toFixed(1)} ${(y1+r).toFixed(1)} L${(bx+bw).toFixed(1)} ${(y1+hh).toFixed(1)} Z" fill="url(#${gid(b.color)})"/>`;
        } else {
          s+=`<rect x="${bx}" y="${y1.toFixed(1)}" width="${bw}" height="${hh.toFixed(1)}" fill="url(#${gid(b.color)})"/>`;
          s+=`<line x1="${bx}" y1="${y1.toFixed(1)}" x2="${(bx+bw).toFixed(1)}" y2="${y1.toFixed(1)}" stroke="#fff" stroke-width="1.6"/>`;
        }
        base+=v; } }); }
  /* bullet ticks for targets */
  for(const tk of ticks){
    for(let i=0;i<n;i++){ const v=tk.values[i];
      if(v===null||v===undefined||!isFinite(v)||v<=0) continue;
      const yy=yL(Math.min(v,lMax)), half=slotW*0.31;
      s+=`<line x1="${(x(i)-half).toFixed(1)}" y1="${yy.toFixed(1)}" x2="${(x(i)+half).toFixed(1)}" y2="${yy.toFixed(1)}" stroke="${INK}" stroke-width="2.4"/>`;
    }
  }
  /* lines + ringed points + end badges */
  const badge=[];
  for(const l of lines){ const yf=l.right?yR:yL; let path="",pts="",started=false,lastIdx=-1;
    for(let i=0;i<n;i++){ const v=l.values[i];
      if(v===null||v===undefined||!isFinite(v)){started=false;continue;}
      path+=(started?"L":"M")+x(i).toFixed(1)+" "+yf(v).toFixed(1)+" "; started=true; lastIdx=i;
      pts+=`<circle cx="${x(i).toFixed(1)}" cy="${yf(v).toFixed(1)}" r="2.4" fill="${l.color}" stroke="#fff" stroke-width="1.4"/>`; }
    s+=`<path d="${path}" fill="none" stroke="${l.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"${l.dash?' stroke-dasharray="5 4"':""}/>`+pts;
    if(lastIdx>=0&&lines.length<=3){
      const v=l.values[lastIdx];
      const clip=x(lastIdx)+35>W;  /* anchor end at the plot edge instead of spilling out */
      badge.push(`<text x="${(x(lastIdx)+(clip?-5:5)).toFixed(1)}" y="${(yf(v)-5).toFixed(1)}"${clip?' text-anchor="end"':""} font-size="${fz(9.5)}" font-weight="700" fill="${INK}" stroke="#fff" stroke-width="3" paint-order="stroke">${fmtAxis(v)}</text>`);
    }
  }
  s+=badge.join("");
  s+=`<line x1="${ml}" y1="${mt+ph}" x2="${ml+pw}" y2="${mt+ph}" stroke="#6b747b" stroke-width="1.2"/>`;
  /* slot hover: band highlight + combined tooltip */
  s+=`<rect class="hoverband" x="0" y="${mt}" width="0" height="${ph}" fill="#1b1e21" fill-opacity="0.05" style="display:none"/>`;
  for(let i=0;i<n;i++){
    s+=`<rect class="hit" data-i="${i}" x="${(ml+pw*i/n).toFixed(1)}" y="${mt}" width="${slotW.toFixed(2)}" height="${ph}" fill="transparent"/>`;
  }
  s+=`</svg>`;
  let leg='<div class="clegend">';
  for(const b of bars) leg+=b.outline?`<span><i class="out" style="border-color:${b.color}"></i>${esc(b.name)}</span>`:`<span><i style="background:${b.color}"></i>${esc(b.name)}</span>`;
  for(const tk of ticks) leg+=`<span><i class="dash"></i>${esc(tk.name)}</span>`;
  for(const l of lines) leg+=`<span><i class="line" style="background:${l.color}"></i>${esc(l.name)}${l.right?" (right)":""}</span>`;
  leg+="</div>";
  const div=document.createElement("div"); div.className="chart";
  div.innerHTML=`<h4>${esc(cfg.title)}</h4>${leg}${s}`;
  /* identity + renderer travel with the node, so the full-page view re-draws
     the same cfg through the drawChart of whichever half owns this chart */
  /* an untitled sub-chart (the polygon detail panel draws one) still needs a
     stable key, so fall back to the host it is drawn into */
  div.dataset.ck = cfg.key || String(cfg.title||"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")
                   || ((host && host.id) ? host.id + ".c" : "");
  div.__cfg = cfg; div.__draw = drawChart;
  host.appendChild(div);
  /* window.TC, never a bare TC: build_report's cube-slot const TC=3 shadows it */
  if (window.TC) window.TC.registerChart(div);
  /* interactivity */
  const svg=div.querySelector("svg"), band=svg.querySelector(".hoverband");
  const fmtV=v=>(v==null||!isFinite(v))?"–":(cfg.pct?Math.round(v*1000)/10+"%":v.toLocaleString("en-US",{maximumFractionDigits:Math.abs(v)<10?2:1}));
  /* a pct chart's tooltip shows each bar's share of its own stack, not raw tonnes */
  const pctOf=b=>{ if(!cfg.pct) return b.values; const g_=groups.find(g=>g.members.includes(b));
    return b.values.map((v,i)=>{ let tt=0; for(const m of g_.members) tt+=Math.max(0,m.values[i]||0); return tt?Math.max(0,v||0)/tt:null; }); };
  const series=[...bars.map(b=>({n:b.name,c:b.color,v:pctOf(b)})),
                ...ticks.map(t=>({n:t.name,c:"#1b1e21",v:t.values})),
                ...lines.map(l=>({n:l.name,c:l.color,v:l.values}))];
  svg.querySelectorAll(".hit").forEach(hit=>{
    hit.addEventListener("mousemove",ev=>{
      const i=+hit.dataset.i;
      band.setAttribute("x",(ml+pw*i/n).toFixed(1));
      band.setAttribute("width",slotW.toFixed(2));
      band.style.display="";
      let h=`<b>${esc(String(cats[i]))}</b>`;
      for(const sr of series){
        const v=sr.v[i];
        if(v===null||v===undefined||(!v&&v!==0)) continue;
        h+=`<br><span style="color:${sr.c}">&#9632;</span> ${esc(sr.n)}: <b>${fmtV(v)}</b>`;
      }
      ctipShow(ev,h);
    });
    hit.addEventListener("mouseleave",()=>{ band.style.display="none"; ctipHide(); });
  });
  return div;
}
function ctipEl(){
  let t=document.getElementById("ctip");
  if(!t){ t=document.createElement("div"); t.id="ctip";
    t.style.cssText="position:fixed;pointer-events:none;background:rgba(27,30,33,.94);color:#fff;font-size:11.5px;padding:7px 10px;border-radius:4px;max-width:280px;display:none;z-index:60;line-height:1.5";
    document.body.appendChild(t); }
  return t;
}
function ctipShow(ev,html){ const t=ctipEl(); t.innerHTML=html; t.style.display="block";
  t.style.left=Math.min(ev.clientX+14,innerWidth-300)+"px"; t.style.top=(ev.clientY+12)+"px"; }
function ctipHide(){ ctipEl().style.display="none"; }


/* =================================================== polygon explorer */
let sortKey = "hauled", sortAsc = false, selPoly = null;
function drawPTable(){
  const t = document.getElementById("ptable");
  const rows = [...D.pstat].sort((a, b) =>
    (a[sortKey] < b[sortKey] ? 1 : -1) * (sortAsc ? -1 : 1));
  const TH = [["p","Polygon"],["cls","Class"],["bench","Bench"],["init","Initial t"],
              ["mined","Mined t"],["hauled","Hauled t (cycles)"],["dep","Depleted"],
              ["au","Au g/t"],["ag","Ag g/t"]];
  let h = "<thead><tr>" + TH.map(([k, l]) => `<th data-k="${k}">${l}</th>`).join("") + "</tr></thead><tbody>";
  for (const r of rows){
    const dep = r.init ? Math.min(100, r.mined / r.init * 100) : 0;
    h += `<tr data-p="${esc(r.p)}"${r.p===selPoly?' class="sel"':''}><td>${esc(r.p)}</td><td style="text-align:center">${r.cls}</td>` +
         `<td style="text-align:center">${esc(r.bench)}</td><td>${fmt0(r.init)}</td><td>${fmt0(r.mined)}</td>` +
         `<td>${fmt0(r.hauled)}</td><td><div class="dbar"><i style="width:${dep.toFixed(0)}%"></i></div></td>` +
         `<td>${fmt2(r.au)}</td><td>${fmt2(r.ag)}</td></tr>`;
  }
  t.innerHTML = h + "</tbody>";
  t.querySelectorAll("th").forEach(th => th.addEventListener("click", () => {
    const k = th.dataset.k === "dep" ? "mined" : th.dataset.k;
    if (sortKey === k) sortAsc = !sortAsc; else { sortKey = k; sortAsc = false; }
    drawPTable();
  }));
  t.querySelectorAll("tbody tr").forEach(tr => tr.addEventListener("click", () => {
    selPoly = tr.dataset.p; drawPTable(); drawPDetail();
  }));
}
function drawPDetail(){
  const cWrap = document.getElementById("pdChart"), dWrap = document.getElementById("pdDest");
  cWrap.innerHTML = ""; dWrap.innerHTML = "";
  document.getElementById("pdTitle").textContent = selPoly ? `${selPoly} — daily extraction, t` : "Select a polygon";
  if (!selPoly) return;
  const days = Object.keys(D.pday[selPoly] || {}).sort();
  drawChart(cWrap, {title: "", cats: days.map(d => d.slice(5)),
    bars: [{name: "Hauled t", color: C_ACT, values: days.map(d => D.pday[selPoly][d])}]});
  cWrap.querySelector(".chart").style.border = "none";
  const dest = D.pdest[selPoly] || {};
  const entries = Object.entries(dest).sort((a, b) => b[1] - a[1]);
  const mx = Math.max(1, ...entries.map(e => e[1]));
  let h = "";
  for (const [k, v] of entries){
    h += `<div style="display:flex;align-items:center;gap:8px;font-size:11.5px;margin:3px 0">` +
         `<span style="width:150px;text-align:right;font-weight:700">${esc(k)}</span>` +
         `<div class="dbar" style="flex:1"><i style="width:${(v/mx*100).toFixed(0)}%;background:${flowColor(k, "")}"></i></div>` +
         `<span style="width:80px">${fmt0(v)} t</span></div>`;
  }
  dWrap.innerHTML = h || '<div class="note">no destination data</div>';
}

/* =============================================== stockpiles + mill sources */
/* The analytics charts follow the REPORT period (start..end) when the report
   half is present (Erdene 2026-10-17: "charts should show the selected dates,
   not everything since April"); the standalone atlas shows all snapshot days.
   When the snapshot does not reach the period, its last 30 days are shown with
   a note instead of empty charts. */
function atlWin(all){
  all = all || D.dates;
  const last = D.dates[D.dates.length - 1];
  const p = (window.RPT && window.RPT.period) ? window.RPT.period() : null;
  if (!p || !p.start || !p.end) return {dates: all, note: ""};
  const ds = all.filter(d => d >= p.start && d <= p.end);
  if (ds.length)
    return {dates: ds, note: p.end > last ? `Analytics snapshot ends ${last}: later days of the period are not in these charts until the page is rebuilt.` : ""};
  return {dates: all.slice(-30),
          note: `The analytics snapshot (${D.dates[0]} → ${last}) does not cover ${p.start} → ${p.end}: showing its last 30 days. Rebuild the page to cover the period.`};
}
function winNote(host, w){
  if (!w.note) return;
  const n = document.createElement("div");
  n.className = "note"; n.style.gridColumn = "1 / -1"; n.textContent = w.note;
  host.appendChild(n);
}
/* ============================================== equipment time model */
function hbars(host, title, rows, color, unit){
  const div = document.createElement("div");
  div.className = "chart";
  div.dataset.ck = "atl.hb." + String(title).toLowerCase()
                     .replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  const mx = Math.max(1, ...rows.map(r => r[1]));
  let h = `<h4>${esc(title)}</h4><div class="hbars">`;
  for (const [k, v] of rows){
    h += `<div class="row"><span class="lbl" title="${esc(k)}">${esc(k)}</span>` +
         `<div class="dbar" style="flex:1"><i style="width:${(v/mx*100).toFixed(0)}%;background:${color}"></i></div>` +
         `<span class="val">${fmt0(v)} ${unit}</span></div>`;
  }
  div.innerHTML = h + "</div>";
  host.appendChild(div);
  if (window.TC) window.TC.registerChart(div);
}
function drawEquip(){
  const groups = [["load", "chartsEquipLoad", "eqLoadHead", "LOADING UNITS", "Loading"],
                  ["haul", "chartsEquipHaul", "eqHaulHead", "HAULING UNITS", "Hauling"]];
  let any = false;
  for (const [gk, hostId, headId, label, word] of groups){
    const host = document.getElementById(hostId);
    const head = document.getElementById(headId);
    host.innerHTML = "";
    const models = (D.eqmodels || {})[gk] || [];
    head.innerHTML = esc(label) + (models.length
      ? ` <small>&mdash; ${esc(models.join(" · "))}</small>` : "");
    const eqd = (D.eqday || {})[gk] || {};
    const ew = atlWin(Object.keys(eqd).sort()), days = ew.dates, inWin = new Set(days);
    if (gk === "load") winNote(host, ew);
    if (!days.length){
      host.innerHTML = `<div class="note">No ${word.toLowerCase()}-unit status data in the cube.</div>`;
      continue;
    }
    any = true;
    const cats = days.map(d => d.slice(5));
    const get = k => days.map(d => eqd[d][k]);
    drawChart(host, {title: `${word} hours per day — scheduled vs operating`, cats,
      bars: [{name: "Scheduled h", color: C_TGT, values: get("sched")},
             {name: "Operating (Ready) h", color: C_ACT, values: get("ready")}]});
    drawChart(host, {title: `${word} availability & utilization, %`, cats, lMax: 100,
      lines: [{name: "Availability", color: C_ACT,
               values: days.map(d => { const e = eqd[d]; return e.sched ? (e.sched - e.maint) / e.sched * 100 : null; })},
              {name: "Utilization", color: C_CUM,
               values: days.map(d => { const e = eqd[d]; const av = e.sched - e.maint; return av > 0 ? e.ready / av * 100 : null; })}]});
    const smu = (D.smu || {})[gk] || {};
    const smuEq = Object.keys(smu);
    if (smuEq.length){
      /* average over the valid hourmeter days inside the period */
      const stats = smuEq.map(e => {
        const vals = Object.entries(smu[e]).filter(([d]) => inWin.has(d)).map(x => x[1]);
        const tot = vals.reduce((a, b) => a + b, 0);
        return {e, avg: vals.length ? tot / vals.length : 0, days: vals.length};
      }).filter(s => s.days).sort((a, b) => b.avg - a.avg);
      if (stats.length) drawChart(host, {key: `atl.eq.${gk}.smu`,
        title: `${word} engine hours — avg h/day per unit, all ${stats.length} units (hourmeter)`,
        cats: stats.map(s => s.e),
        bars: [{name: "Avg engine h/day", color: C_ACT,
                values: stats.map(s => Math.round(s.avg * 10) / 10)}]});
    }
    /* Erdene request 07 asks R4M to show motor hours beside the status
       histogram. That is a change to R4M's own Fleet Management module; the
       nearest thing this report can offer is the two side by side. */
    const est = (D.eqstat || {})[gk] || {};
    const units = Object.keys(est).sort();
    if (units.length){
      const smuAvg = e => {
        const v = smu[e] ? Object.entries(smu[e]).filter(([d]) => inWin.has(d)).map(x => x[1]) : null;
        return (v && v.length) ? Math.round(v.reduce((a, b) => a + b, 0) / v.length * 10) / 10 : null;
      };
      const col = i => units.map(e => est[e][i]);
      drawChart(host, {key: `atl.eq.${gk}.status`,
        title: `${word} hours by status vs engine hours — avg h/day per unit (status: all history)`,
        cats: units,
        bars: [{name: "Ready", color: C_ACT, stack: "a", values: col(0)},
               {name: "Delay", color: "#e08b00", stack: "a", values: col(1)},
               {name: "Standby", color: "#8a8f94", stack: "a", values: col(2)},
               {name: "Maintenance", color: "#c0392b", stack: "a", values: col(3)},
               {name: "Out of plan", color: "#cfd3d7", stack: "a", values: col(4)}],
        lines: [{name: "Engine hours (hourmeter)", color: C_AU, values: units.map(smuAvg)}]});
    }
  }
  document.getElementById("equipNote").style.display = any ? "" : "none";
}

/* ============================================= crew & operator performance */
function drawCrew(){
  const host = document.getElementById("chartsCrew");
  host.innerHTML = "";
  const crews = Object.keys(D.crewday || {}).sort();
  if (crews.length){
    const cw_ = atlWin([...new Set(crews.flatMap(c => Object.keys(D.crewday[c])))].sort()), days = cw_.dates;
    winNote(host, cw_);
    const cats = days.map(d => d.slice(5));
    const CCOL = ["#005aed", "#f06b32", "#55a630", "#7a4dd8"];
    drawChart(host, {title: "Hauled tonnes per day by crew — t", cats,
      bars: crews.map((c, i) => ({name: c, color: CCOL[i % CCOL.length],
        values: days.map(d => D.crewday[c][d] ?? 0)}))});
    drawChart(host, {title: "Cumulative hauled tonnes by crew — t", cats,
      lines: crews.map((c, i) => {
        let s = 0;
        return {name: "Cum " + c, color: CCOL[i % CCOL.length],
                values: days.map(d => (s += D.crewday[c][d] ?? 0))};
      })});
  } else {
    host.innerHTML = '<div class="note">No crew data in the cube.</div>';
  }
  const mkTable = (id, title, head, rows) => {
    const t = document.getElementById(id);
    let h = `<thead><tr><th colspan="${head.length}" style="text-align:left">${title}</th></tr>` +
            "<tr>" + head.map(x => `<th>${x}</th>`).join("") + "</tr></thead><tbody>";
    for (const r of rows){
      h += "<tr>" + r.map((v, i) => i === 0
        ? `<td>${esc(v)}</td>`
        : `<td style="text-align:right">${v == null ? "—" : (i <= 3 ? fmt0(v) : v.toFixed(1))}</td>`
      ).join("") + "</tr>";
    }
    t.innerHTML = h + "</tbody>";
  };
  mkTable("opsHaulTable", "Truck operators — top 30 by tonnage, all history",
          ["Operator", "Days", "Cycles", "Hauled t", "Cyc/day", "Queue min"],
          D.opshaul || []);
  mkTable("opsLoadTable", "Loading-unit operators — top 30 by tonnage, all history",
          ["Operator", "Days", "Cycles", "Loaded t", "Hang min", "Passes"],
          D.opsload || []);
}

/* ======================================= dig compliance: HPGPS vs dispatch */
function drawDigc(){
  const host = document.getElementById("chartsDigc");
  host.innerHTML = "";
  const dw = atlWin(Object.keys(D.digcday || {}).sort()), days = dw.dates;
  if (!days.length){
    host.innerHTML = '<div class="note">No HPGPS polygon data in the cube.</div>';
    return;
  }
  winNote(host, dw);
  const cats = days.map(d => d.slice(5));
  drawChart(host, {title: "Tonnage by GPS agreement — % of daily total", cats, pct: true,
    bars: [{name: "GPS agrees", color: "#1baf7a", stack: "d", values: days.map(d => D.digcday[d][0])},
           {name: "GPS disagrees", color: "#e03131", stack: "d", values: days.map(d => D.digcday[d][1])},
           {name: "No GPS fix", color: "#98a2a9", stack: "d", values: days.map(d => D.digcday[d][2])}]});
  drawChart(host, {title: "Off-polygon tonnage per day — t", cats,
    bars: [{name: "Mismatched t", color: "#e03131", values: days.map(d => D.digcday[d][1])}],
    lines: [{name: "Mismatch % of covered", color: "#8a4a00",
             values: days.map(d => { const [ok, bad] = D.digcday[d];
                                     return ok + bad > 0 ? bad / (ok + bad) * 100 : null; })}]});
  const t = document.getElementById("digcTable");
  let h = '<thead><tr><th colspan="5" style="text-align:left">Worst polygons by off-polygon tonnage (all history)</th></tr>' +
          "<tr><th>Assigned polygon</th><th>GPS mostly saw</th><th>Off t</th><th>Cycles</th><th>% of its t</th></tr></thead><tbody>";
  for (const [pn, gps, bt, n, share] of (D.digcpoly || [])){
    h += `<tr><td>${esc(pn)}</td><td>${esc(gps)}</td><td style="text-align:right">${fmt0(bt)}</td>` +
         `<td style="text-align:right">${fmt0(n)}</td><td style="text-align:right">${share.toFixed(1)}%</td></tr>`;
  }
  t.innerHTML = h + "</tbody>";
  const lh = document.getElementById("digcLoader");
  lh.innerHTML = (D.digcloader || []).map(([e, bt, sh]) =>
    `<div class="hbars" style="display:flex;align-items:center;gap:8px;margin:4px 0">` +
    `<span class="lbl" style="min-width:64px;font-weight:700">${esc(e)}</span>` +
    `<div style="flex:1;background:var(--color-bg-metrics,#eef0f2);border-radius:3px;height:14px">` +
    `<div style="width:${Math.min(100, sh * 4)}%;height:14px;border-radius:3px;background:#e03131"></div></div>` +
    `<span style="min-width:110px;text-align:right">${sh.toFixed(1)}% · ${fmt0(bt)} t</span></div>`).join("");
}

/* ==================================================== cycle anatomy + payload */
const SEG_COLORS = {"Travel empty": "#8a8f94", "Queue & spot": "#eb6834", "Loading": "#2a78d6",
                    "Haul loaded": "#1baf7a", "At dump": "#eda100", "Dumping": "#4a3aa7"};
function drawCycle(){
  const host = document.getElementById("chartsCycle");
  host.innerHTML = "";
  const cyw = atlWin(Object.keys(D.cyc).sort()), days = cyw.dates;
  if (!days.length){
    host.innerHTML = '<div class="note">No cycle-time data in the cube for this period.</div>';
    return;
  }
  winNote(host, cyw);
  const cats = days.map(d => d.slice(5));
  const segs = Object.keys(SEG_COLORS);
  drawChart(host, {title: "Average truck cycle composition, minutes", cats,
    bars: segs.map(sg => ({name: sg, color: SEG_COLORS[sg], stack: "c",
      values: days.map(d => D.cyc[d][sg] || 0)}))});
  drawChart(host, {title: "Waiting on each other — truck queue vs excavator hang, min/cycle", cats,
    lines: [{name: "Truck queue & spot", color: "#eb6834", values: days.map(d => D.cyc[d]["Queue & spot"] || null)},
            {name: "Excavator hang", color: "#2a78d6", values: days.map(d => D.cyc[d]["Excavator hang"] ?? null)}]});
}
/* ============================================================ haul metrics */
function drawHaul(){
  const host = document.getElementById("chartsHaul");
  host.innerHTML = "";
  const hw = atlWin(), dates = hw.dates, cats = dates.map(d => d.slice(5));
  winNote(host, hw);
  const get = k => dates.map(d => (D.haul[d] || {})[k] ?? null);
  drawChart(host, {title: "Haulage work — tonne-kilometres per day", cats,
    bars: [{name: "t·km", color: C_ACT, values: get("tkm")}]});
  drawChart(host, {title: "Average loaded haul distance, m", cats,
    lines: [{name: "avg distance loaded", color: C_ACT, values: get("dist")}]});
  drawChart(host, {title: "Average speeds, km/h", cats,
    lines: [{name: "loaded", color: C_ACT, values: get("vl")},
            {name: "empty", color: C_CUM, values: get("ve")}]});
  drawChart(host, {title: "Fleet — trucks active and tonnes per truck-day", cats,
    bars: [{name: "trucks active", color: C_TGT, values: get("trucks")}],
    lines: [{name: "t per truck-day", color: C_ACT, right: true,
             values: dates.map(d => { const h = D.haul[d]; return h && h.trucks ? h.t / h.trucks : null; })}]});
}

/* ================================================================== wiring */
function refreshPeriod(){
  drawSankey();
  refreshInv();
}
periodSel.addEventListener("change", refreshPeriod);

/* highlight the nav pill of the section in view */
const navLinks = [...document.querySelectorAll("nav.toc a[href^='#']")];
const secObs = new IntersectionObserver(es => {
  for (const e of es){
    if (!e.isIntersecting) continue;
    navLinks.forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#" + e.target.id));
  }
}, {rootMargin: "-10% 0px -70% 0px"});
document.querySelectorAll(".banner[id]").forEach(el => secObs.observe(el));

refreshPeriod();
drawPTable();
if (D.pstat.length){ selPoly = D.pstat[0].p; drawPTable(); drawPDetail(); }
/* stockpile window hooks (window.ATL.inv / setInvWindow; used by the checks) */
function invState(){
  return {state: INVL.state, year: INVL.year, live: INV.live, win: invWin(), label: INV.label, decoupled: !!INV_WIN,
          dots: INV.dots.length, mis: INV.dots.filter(c => c.dig.mis).length, npts: INV.npts, noHour: INVL.noHour, noGps: INV.noGps || 0,
          cov: INV.cov, rows: Object.fromEntries([...INV.rows].map(([k, r]) => [k, [r.per, r.out]]))};
}
function invSetWindow(sIso, eIso){         /* "YYYY-MM-DDTHH:00" wall clock; null = follow the report */
  INV_WIN = sIso ? {s: Date.parse(sIso + ":00Z"), e: Date.parse(eIso + ":00Z")} : null;
  refreshInv();
}
/* every period-following analytics chart; also called by the report's refresh() */
function redrawCharts(){
  drawEquip(); drawCrew(); drawDigc(); drawCycle(); drawHaul();
}
redrawCharts();
applyIVB();
</script>
</body>
</html>
"""
