# -*- coding: utf-8 -*-
"""CSS / HTML / JS for the C4M over-speed report page (assembled by build_overspeed.py).

Same visual grammar as daily_report_v3 / the mine atlas: a white "sheet" on the grey
dashboard background, a Rubik uppercase title block, a sticky section nav, numbered blue
section banners, KPI tiles with sparklines, chart cards with an accent underline, and an SVG
map with the same pan/zoom mechanics as the atlas (wheel = zoom at cursor, drag = pan).
Everything is inline so the built HTML is one self-contained file that works offline.

Chart colours follow the dataviz method: fixed categorical slots (blue = DS / flat road,
orange = NS / steep road), a one-hue sequential ramp for the threshold series, status red only
for the limit reference lines.
"""

CSS = r"""
/* ---- page tokens on top of the R4M design schema ---------------------- */
:root {
  --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a; --series-4: #eda100;
  --seq-1: #9ec5f4; --seq-2: #6da7ec; --seq-3: #3987e5; --seq-4: #256abf; --seq-5: #184f95;
  --status-critical: #d03b3b; --status-warning: #fab219;
  --sheet-w: 1280px;
}
[data-theme="dark"] {
  --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500;
  --seq-1: #cde2fb; --seq-2: #9ec5f4; --seq-3: #6da7ec; --seq-4: #3987e5; --seq-5: #1c5cab;
}
* { box-sizing: border-box; }
html { color-scheme: light; scroll-behavior: smooth; }
[data-theme="dark"] { color-scheme: dark; }
body { background: var(--color-bg-dashboard); color: var(--color-text-primary); font-size: 13.5px; line-height: 1.45; counter-reset: sec; }
a { color: var(--color-primary); }
code { font-size: 11.5px; }
h1, h2, h3, h4 { font-family: "Rubik", -apple-system, BlinkMacSystemFont, sans-serif; }

/* ---- sheet ------------------------------------------------------------ */
.sheet { width: var(--sheet-w); max-width: 97vw; margin: 18px auto 30px; background: var(--color-bg-surface);
         border: 1px solid var(--color-border-subtle); border-radius: 6px; box-shadow: var(--shadow-md); padding: 0 28px 36px; }
html.embed .sheet { margin-top: 10px; }

/* title block (as the daily report masthead) */
.titleblock { display: flex; gap: 26px; align-items: flex-start; padding: 24px 0 16px; border-bottom: 3px solid var(--color-primary); margin: 0 -28px 0; padding-left: 28px; padding-right: 28px; }
.titleblock img { height: 56px; margin-top: 6px; }
.titleblock .tb { flex: 1; min-width: 0; }
.titleblock h1 { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: .4px; text-transform: uppercase; line-height: 1.2; }
.titleblock .sub { color: var(--color-primary); letter-spacing: 2px; font-size: 11.5px; font-weight: 700; text-transform: uppercase; margin-top: 6px; }
.titleblock .meta { color: var(--color-text-secondary); font-size: 12px; margin-top: 6px; }
.titleblock .right { text-align: right; flex: none; }
.titleblock .period { font-size: 13px; color: var(--color-text-secondary); display: flex; gap: 8px; align-items: center; justify-content: flex-end; flex-wrap: wrap; }
.titleblock .period b { color: var(--color-text-primary); }
.titleblock .period input, .titleblock .period select { font: inherit; font-size: 13px; font-weight: 700; padding: 5px 8px; border: 1px solid var(--color-primary); border-radius: 4px; background: var(--color-bg-surface); color: var(--color-text-primary); }
.titleblock .btns { margin-top: 10px; display: flex; gap: 8px; justify-content: flex-end; }
.btn { background: var(--color-bg-surface); color: var(--color-text-primary); border: 1px solid var(--color-border-strong);
       border-radius: 5px; padding: 6px 12px; cursor: pointer; font: inherit; font-size: 12.5px; font-weight: 600; }
.btn:hover { background: var(--state-hover-bg); }
.btn.primary { background: var(--color-primary); border-color: var(--color-primary); color: var(--color-text-on-primary); }
.btn.primary:hover { background: var(--color-primary-hover); }
.btn[disabled] { opacity: .5; cursor: default; }
html.embed #themeBtn { display: none; }
@keyframes spin { to { transform: rotate(360deg); } }
#refreshBtn[hidden] { display: none; }
#refreshBtn.busy { opacity: .7; pointer-events: none; }
#refreshBtn.busy::before { content: ""; display: inline-block; width: 10px; height: 10px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; margin-right: 6px; vertical-align: -1px; animation: spin .8s linear infinite; }
#refreshMsg { font-size: 11px; color: var(--color-text-tertiary); margin-top: 4px; text-align: right; min-height: 14px; }
#refreshMsg.err { color: var(--status-critical); }
#refreshMsg.ok { color: #0f6b3a; }
.btn.sm { padding: 3px 9px; font-size: 11.5px; font-weight: 600; }
.btn.sm.on { background: var(--color-primary); border-color: var(--color-primary); color: var(--color-text-on-primary); }
.quick { display: flex; gap: 6px; justify-content: flex-end; margin-top: 7px; flex-wrap: wrap; }
html.embed .titleblock { padding-top: 14px; }

/* policy chip row */
.chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 0; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 11px; border-radius: 12px; font-size: 11px; font-weight: 700; letter-spacing: .4px;
        background: var(--badge-bg); border: 1px solid var(--badge-border); color: var(--badge-text); }
.chip.warn { background: color-mix(in srgb, var(--status-warning) 16%, transparent); border-color: var(--status-warning); color: #6b4a00; }
[data-theme="dark"] .chip.warn { color: #ffd98a; }
.chip b { font-weight: 800; }

/* sticky section nav */
nav.toc { position: sticky; top: 0; z-index: 40; display: flex; flex-wrap: wrap; gap: 2px 4px; padding: 8px 10px; margin: 0 -28px 14px;
          background: var(--color-bg-surface); border-bottom: 2px solid var(--color-primary); }
nav.toc a { color: var(--color-text-secondary); text-decoration: none; font-size: 12.5px; font-weight: 700; padding: 5px 13px; border-radius: 14px; }
nav.toc a:hover { background: var(--state-hover-blue); color: var(--color-text-primary); }
nav.toc a.on { background: var(--color-primary); color: var(--color-text-on-primary); }
nav.toc .spring { flex: 1; }
nav.toc .hint { font-size: 11px; color: var(--color-text-tertiary); align-self: center; }

/* banners */
.banner { background: var(--color-primary); color: var(--color-text-on-primary); font-family: "Rubik", sans-serif; font-weight: 700; font-size: 14.5px;
          letter-spacing: 1.4px; text-transform: uppercase; padding: 8px 18px; margin: 26px 0 12px; border-left: 5px solid var(--color-primary-dark);
          border-radius: 3px; box-shadow: var(--shadow-sm); counter-increment: sec; }
.banner::before { content: counter(sec, decimal-leading-zero) "  \00b7  "; color: var(--color-primary-light); letter-spacing: 2px; }
.banner small { font-weight: 400; letter-spacing: .3px; text-transform: none; opacity: .85; margin-left: 10px; font-size: 12px; }
.lead { color: var(--color-text-secondary); font-size: 12.5px; font-style: italic; margin: -4px 0 12px 2px; }

/* note / controls */
.note { padding: 10px 14px; margin: 14px 0 0; border-left: 4px solid var(--status-warning); background: var(--color-bg-surface-secondary); border-radius: 0 4px 4px 0; font-size: 12.5px; }
.note b { font-weight: 700; }
.controls { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; padding: 10px 14px; margin: 10px 0 14px; border-radius: 5px;
            background: var(--color-bg-surface-secondary); border: 1px solid var(--color-border-subtle); font-size: 12.5px; }
.controls label { display: inline-flex; gap: 6px; align-items: center; color: var(--color-text-secondary); white-space: nowrap; }
.controls label b { color: var(--color-text-primary); font-weight: 700; }
.controls input, .controls select { font: inherit; font-size: 12.5px; padding: 4px 7px; border: 1px solid var(--color-border-strong); border-radius: 4px;
                                    background: var(--color-bg-surface); color: var(--color-text-primary); max-width: 170px; }
.controls input[type=number] { width: 70px; }
.controls input[type=search] { min-width: 180px; }
.controls .sep { color: var(--color-border-strong); }
.controls .policy { padding: 2px 8px; border-left: 3px solid var(--series-2); }

.tabdesc { font-size: 12.5px; color: var(--color-text-secondary); margin: 0 0 12px 2px; }

/* KPI tiles (daily-report style) */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(205px, 1fr)); gap: 10px; margin: 0 0 6px; }
.kpi { position: relative; padding: 11px 14px 10px; background: var(--color-bg-metrics); border: 1px solid var(--color-border-subtle);
       border-left: 4px solid var(--color-primary); border-radius: 6px; box-shadow: var(--shadow-sm); min-height: 88px; }
.kpi.steep { border-left-color: var(--series-2); }
.kpi.crit { border-left-color: var(--status-critical); }
.kpi .k { font-size: 10.5px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: var(--color-text-secondary); }
.kpi .v { font-family: "Rubik", sans-serif; font-size: 26px; font-weight: 700; color: var(--color-text-kpi); line-height: 1.15; margin-top: 3px; }
.kpi .v small { font-size: 13px; font-weight: 400; color: var(--color-text-secondary); margin-left: 3px; }
.kpi .s { font-size: 11.5px; color: var(--color-text-secondary); margin-top: 3px; }
.kpi.hasspark .s { padding-right: 74px; }
.kpi svg.spark { position: absolute; right: 10px; bottom: 10px; width: 70px; height: 24px; }
.kpi svg.spark polyline { fill: none; stroke: var(--color-primary); stroke-width: 1.8; stroke-linejoin: round; }
.kpi.steep svg.spark polyline { stroke: var(--series-2); }
.kpi svg.spark .area { fill: var(--color-primary); opacity: .10; }

/* chart cards */
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 12px; margin-bottom: 6px; }
.chart { padding: 12px 14px 10px; background: var(--color-bg-surface); border: 1px solid var(--color-border-subtle); border-radius: 6px; box-shadow: var(--shadow-sm); }
.chart h4 { margin: 0 0 4px; font-size: 13px; font-weight: 700; letter-spacing: .3px; text-transform: uppercase; position: relative; padding-bottom: 7px; }
.chart h4::after { content: ""; position: absolute; left: 0; bottom: 0; width: 34px; height: 3px; background: var(--color-primary); border-radius: 2px; }
.chart .d { font-size: 11.5px; color: var(--color-text-secondary); margin: 6px 0 8px; }
.chart.wide { grid-column: 1 / -1; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11.5px; color: var(--color-text-secondary); margin: 2px 0 4px; }
.legend span::before { content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; background: var(--c); }
svg.cv { width: 100%; height: auto; display: block; font-size: 11px; }
svg.cv text { fill: var(--color-text-secondary); }
svg.cv .grid line { stroke: var(--chart-grid-line); }
svg.cv .bar { shape-rendering: crispEdges; transition: opacity .15s; }
svg.cv .hit { fill: transparent; }
svg.cv .hit:hover { fill: var(--state-hover-blue); }
svg.cv .ref { stroke: var(--status-critical); stroke-dasharray: 4 3; stroke-width: 1.5; }
svg.cv .reflbl { fill: var(--status-critical); font-size: 10.5px; font-weight: 700; }
svg.cv .dl { fill: var(--color-text-primary); font-size: 10.5px; }
.empty { padding: 28px 12px; text-align: center; color: var(--color-text-tertiary); font-size: 13px; }
#tip { position: fixed; pointer-events: none; z-index: 50; background: var(--color-bg-surface); color: var(--color-text-primary);
       border: 1px solid var(--color-border-medium); border-radius: 6px; box-shadow: var(--shadow-md); padding: 7px 10px; font-size: 12px;
       max-width: 320px; display: none; white-space: pre-line; line-height: 1.4; }

/* map (atlas mechanics) */
#mapwrap { position: relative; border: 1px solid var(--color-border-strong); border-radius: 5px; background: var(--color-bg-surface-tertiary); overflow: hidden; }
#map { display: block; width: 100%; height: 640px; cursor: grab; user-select: none; touch-action: none; }
#map.drag { cursor: grabbing; }
#map .pt { fill: var(--series-1); fill-opacity: .78; stroke: #fff; stroke-width: .5px; vector-effect: non-scaling-stroke; }
#map .pt.s { fill: var(--series-2); }
#map .pt:hover { fill-opacity: 1; stroke: var(--color-text-primary); }
#map .cell { fill: var(--color-primary); stroke: none; }
#map .cell.s { fill: var(--series-2); }
#map .cell:hover { stroke: var(--color-text-primary); stroke-width: 1px; vector-effect: non-scaling-stroke; }
[data-theme="dark"] #map image { opacity: .55; }
.mapbtns { position: absolute; top: 10px; right: 10px; display: flex; flex-direction: column; gap: 4px; }
.mapbtns button { width: 32px; height: 32px; font: inherit; font-size: 17px; font-weight: 700; border-radius: 5px; cursor: pointer;
                  border: 1px solid var(--color-border-strong); background: var(--color-bg-surface); color: var(--color-text-primary); box-shadow: var(--shadow-sm); }
.mapbtns button:hover { background: var(--state-hover-bg); }
.mapbtns button.txt { font-size: 10.5px; width: auto; padding: 0 8px; }
.maplegend { position: absolute; left: 10px; bottom: 10px; padding: 7px 10px; border-radius: 5px; font-size: 11.5px; background: color-mix(in srgb, var(--color-bg-surface) 88%, transparent);
             border: 1px solid var(--color-border-subtle); color: var(--color-text-secondary); display: flex; gap: 12px; align-items: center; }
.maplegend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; vertical-align: -1px; }
.mapscale { position: absolute; right: 10px; bottom: 10px; font-size: 11px; color: var(--color-text-secondary); background: color-mix(in srgb, var(--color-bg-surface) 88%, transparent); padding: 3px 8px; border-radius: 4px; }
.maphint { font-size: 11.5px; color: var(--color-text-tertiary); margin: 6px 2px 0; }

/* table */
.tbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.tbar .n { color: var(--color-text-secondary); font-size: 12.5px; flex: 1; }
.tbl { width: 100%; overflow: auto; border: 1px solid var(--color-border-subtle); border-radius: 5px; max-height: 640px; }
table.x { border-collapse: collapse; width: 100%; font-size: 12.5px; white-space: nowrap; }
table.x th, table.x td { padding: 6px 9px; border-bottom: 1px solid var(--color-border-subtle); text-align: left; }
table.x th { position: sticky; top: 0; background: var(--color-primary-light); color: #05498c; cursor: pointer; user-select: none; font-weight: 700; font-size: 11.5px; z-index: 1; }
[data-theme="dark"] table.x th { background: var(--color-bg-selected); color: var(--color-text-primary); }
table.x th.s::after { content: " ▲"; font-size: 9px; } table.x th.s.desc::after { content: " ▼"; }
table.x td.num, table.x th.num { text-align: right; font-variant-numeric: tabular-nums; }
table.x tbody tr:hover td { background: var(--state-hover-bg); }
.pill { display: inline-block; padding: 1px 7px; border-radius: 9px; font-size: 11px; font-weight: 600; border: 1px solid var(--color-border-medium); }
.pill.l { background: var(--color-primary-lighter); color: var(--color-primary-dark); border-color: var(--color-primary-light); }
.pill.steep { background: #fdeee6; color: #8a3a12; border-color: #f5c3a8; }
.pill.over { background: #fdecec; color: #8a1f1f; border-color: #f3b4b4; }
[data-theme="dark"] .pill.over { background: #3a1d1d; color: #ffb3b3; border-color: #6b2b2b; }
[data-theme="dark"] .pill.steep { background: #3a2518; color: #ffc9ad; border-color: #6b3d22; }
[data-theme="dark"] .pill.l { background: #1a2f4a; color: #cfe3ff; border-color: #2d4a6b; }
.pager { display: flex; gap: 6px; align-items: center; justify-content: flex-end; margin-top: 8px; font-size: 12.5px; }
.foot { color: var(--color-text-tertiary); font-size: 11.5px; margin: 26px 2px 0; padding-top: 10px; border-top: 1px solid var(--color-border-subtle); line-height: 1.5; }

@media (max-width: 760px) { .sheet { padding: 0 14px 24px; } .titleblock, nav.toc { margin-left: -14px; margin-right: -14px; } .titleblock { padding-left: 14px; padding-right: 14px; flex-wrap: wrap; }
  .titleblock .right { text-align: left; width: 100%; } .titleblock .period, .titleblock .btns { justify-content: flex-start; } .titleblock h1 { font-size: 17px; } .kpi .v { font-size: 21px; } #map { height: 420px; } }
@media print {
  @page { size: A4 landscape; margin: 10mm; }
  body { background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; font-size: 11.5px; }
  nav.toc, .controls, .btns, #refreshMsg, .quick, .mapbtns, .pager, .maphint, #tip, .note { display: none !important; }
  .sheet { width: 100%; max-width: none; margin: 0; box-shadow: none; border: none; padding: 0 4mm; }
  .titleblock { padding-top: 4mm; }
  .kpis { grid-template-columns: repeat(4, 1fr); }
  .grid { grid-template-columns: repeat(2, 1fr); }
  .chart, .kpi, #mapwrap { break-inside: avoid; }
  .banner { break-after: avoid; break-inside: avoid; }
  .tbl { max-height: none; overflow: visible; border: none; }
  table.x thead { display: table-header-group; }
  table.x tr { break-inside: avoid; }
  table.x th { position: static; }
  table.x { font-size: 10.5px; }
  #map { height: 170mm; }
}
"""

HTML = r"""
<div class="sheet">
  <div class="titleblock">
    <img src="data:image/png;base64,__LOGO__" alt="Erdene">
    <div class="tb">
      <h1>Over-speed report &mdash; haul fleet speed compliance</h1>
      <div class="sub">Bayankhundii gold mine &middot; C4M fleet management &middot; GPS telemetry</div>
      <div class="chips" id="chips"></div>
    </div>
    <div class="right">
      <div class="period"><b>Shift dates:</b> <input type="date" id="fFrom"> &rarr; <input type="date" id="fTo">
        <b>Shift:</b> <select id="fShift"><option value="">Both</option><option>DS</option><option>NS</option></select></div>
      <div class="meta" style="margin-top:4px">shift day = 07:00 &rarr; 07:00 &middot; DS 07&ndash;19 &middot; NS 19&ndash;07</div>
      <div class="quick" id="quick"><button class="btn sm" data-range="7">Last 7 days</button><button class="btn sm" data-range="30">Last 30 days</button><button class="btn sm" data-range="all">All since 1 Jul</button></div>
      <div class="btns"><button class="btn" id="refreshBtn" hidden title="Pull the newest shift days from C4M now (the same job the nightly cron runs; one run at a time)">&#8635; Refresh data</button><button class="btn" id="themeBtn">&#9681; Theme</button><button class="btn primary" id="pdfBtn" title="Print the report to PDF (use 'Save as PDF' as the printer)">&#10515; Export PDF</button></div>
      <div id="refreshMsg"></div>
    </div>
  </div>

  <nav class="toc" id="toc">
    <a href="#secOverview">Overview</a><a href="#secWhen">When</a><a href="#secWho">Who</a><a href="#secList">Event list</a>
    <a href="#secProfile">Speed profile</a><a href="#secMap">Map</a>
    <span class="spring"></span><span class="hint">scroll = zoom on the map &middot; drag = pan</span>
  </nav>

  <div class="note" id="note"></div>

  <div class="controls">
    <label><b>Truck</b> <select id="fEq"><option value="">All</option></select></label>
    <label><b>Operator</b> <select id="fOp"><option value="">All</option></select></label>
    <label><b>Crew</b> <select id="fCrew"><option value="">All</option></select></label>
    <span class="sep">|</span>
    <label><b>Road</b> <select id="fRoad"><option value="">Flat + steep</option><option value="flat">Flat only</option><option value="steep">Steep only</option></select></label>
    <label class="policy"><b>Steep = grade &ge;</b> <select id="fSteep"></select></label>
    <label><b>Load</b> <select id="fLoad"><option value="">Both</option><option value="1">Loaded</option><option value="0">Empty</option></select></label>
    <span class="sep">|</span>
    <label title="average speed during the event minus the limit"><b>Avg over by &ge;</b> <input type="number" id="fOver" min="0" step="0.5" value="0"> km/h</label>
    <label><b>Duration &ge;</b> <input type="number" id="fDur" min="0" step="1" value="0"> s</label>
    <label><input type="search" id="fQ" placeholder="search truck, operator, segment&hellip;"></label>
    <button class="btn" id="resetBtn">Reset</button>
  </div>

  <div class="tabdesc" id="tabdesc"></div>

  <div class="banner" id="secOverview">Overview <small id="ovsub"></small></div>
  <div class="kpis" id="kpis"></div>

  <div class="banner" id="secWhen">When &mdash; by shift day, road and hour</div>
  <div class="grid">
    <div class="chart"><h4>Events per shift day</h4><div class="d">Day shift vs night shift.</div><div class="legend"><span style="--c:var(--series-1)">DS 07:00&ndash;19:00</span><span style="--c:var(--series-2)">NS 19:00&ndash;07:00</span></div><div id="cDay"></div></div>
    <div class="chart"><h4>Flat vs steep roads</h4><div class="d">Limit 40 km/h on flat roads, 30 km/h on steep roads.</div><div class="legend"><span style="--c:var(--series-1)">Flat road</span><span style="--c:var(--series-2)">Steep road</span></div><div id="cRoad"></div></div>
    <div class="chart"><h4>Hour of day</h4><div class="d">When events start (local time).</div><div id="cHour"></div></div>
    <div class="chart"><h4>How far over the limit</h4><div class="d">Average speed during the event minus the limit that applied (km/h).</div><div id="cHist"></div></div>
  </div>

  <div class="banner" id="secWho">Who &mdash; trucks and operators</div>
  <div class="grid">
    <div class="chart wide"><h4>Trucks</h4><div class="d">Events per truck, most first. Hover for the worst excess.</div><div id="cEq"></div></div>
    <div class="chart wide"><h4>Operators</h4><div class="d">Events per operator (name from the C4M worker list), top 25. Hover for the worst excess.</div><div id="cOp"></div></div>
    <div class="chart wide"><h4>Highest sustained speed per truck</h4>
      <div class="d">Each truck's highest event-average speed in the period — an average over the whole event, never a single 2-second GPS sample — on flat and on steep roads. Dashed lines: the 40 and 30 km/h limits. Sorted by the worst excess.</div>
      <div class="legend"><span style="--c:var(--series-1)">Flat road</span><span style="--c:var(--series-2)">Steep road</span></div>
      <div id="cSustained"></div></div>
  </div>

  <div class="banner" id="secList">Event list <small>one row per over-speed event</small></div>
  <div class="tbar"><div class="n" id="tblN"></div><button class="btn" id="csvBtn">&#8681; Export CSV</button></div>
  <div class="tbl"><table class="x" id="tbl"><thead></thead><tbody></tbody></table></div>
  <div class="pager" id="pager"></div>

  <div class="banner" id="secProfile">Speed profile <small>whole fleet, from the 2-second GPS stream</small></div>
  <p class="lead">Independent of the event tabs above: how fast the fleet actually drives. Date, shift, truck, road and load filters apply.</p>
  <div class="grid">
    <div class="chart wide"><h4>Minutes above each speed, per shift day</h4>
      <div class="legend"><span style="--c:var(--seq-1)">&gt; 30 km/h</span><span style="--c:var(--seq-2)">&gt; 35 km/h</span><span style="--c:var(--seq-3)">&gt; 40 km/h</span><span style="--c:var(--seq-4)">&gt; 45 km/h</span><span style="--c:var(--seq-5)">&gt; 50 km/h</span></div>
      <div id="cProf"></div></div>
  </div>

  <div class="banner" id="secMap">Map &mdash; where the events happen</div>
  <p class="lead">Each dot is one event on the pit contour map (mine grid, metres). Dot size grows with the average excess over the limit. Hover a dot for details.</p>
  <div id="mapwrap">
    <svg id="map" preserveAspectRatio="xMidYMid meet"></svg>
    <div class="mapbtns"><button id="mzIn" title="Zoom in">+</button><button id="mzOut" title="Zoom out">&minus;</button><button id="mzFit" class="txt" title="Zoom to the events">fit</button><button id="mzReset" class="txt" title="Whole map">all</button><button id="mzMode" class="txt" title="Dots: one per event. Heat: 40 m grid, darker = more events">heat</button></div>
    <div class="maplegend"><span><i style="background:var(--series-1)"></i>flat road &middot; limit 40</span><span><i style="background:var(--series-2)"></i>steep road &middot; limit 30</span><span id="mapN"></span></div>
    <div class="mapscale" id="mapScale"></div>
  </div>
  <div class="maphint">Scroll to zoom at the cursor &middot; drag to pan &middot; <b>fit</b> frames the filtered events &middot; <b>all</b> shows the whole map &middot; <b>heat</b> switches between one dot per event and a 40 m density grid (the grid is used automatically above 20,000 events).</div>

  <div class="foot" id="foot"></div>
</div>
<div id="tip"></div>
"""

JS = r"""
const D = __DATA__;
const M = D.meta;
/* the build embeds compact column tables (dictionary-encoded text); expand them to row objects */
function decode(t) {
  if (!t) return [];
  const n = t.data[t.cols[0]].length, out = new Array(n);
  for (let i = 0; i < n; i++) { const o = {}; for (const c of t.cols) { const v = t.data[c][i]; o[c] = (t.dict[c] && v != null) ? t.dict[c][v] : v; } out[i] = o; }
  return out;
}
D.policy = Object.fromEntries(Object.entries(D.policy).map(([g, t]) => [g, decode(t)]));
D.profile = decode(D.profile);
const DEFAULT_DAYS = 7;
const $ = s => document.querySelector(s);
const fmt = (n, d=0) => n == null || isNaN(n) ? '–' : Number(n).toLocaleString('en-US', {maximumFractionDigits: d, minimumFractionDigits: d});
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const uniq = a => [...new Set(a.filter(v => v != null && v !== ''))].sort((x, y) => String(x).localeCompare(String(y)));
const sum = a => a.reduce((s, v) => s + (+v || 0), 0);
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const LF = M.limit_flat, LS = M.limit_steep;
const BAND = {6: 1, 8: 2, 10: 3, 12: 4};              // steep threshold % -> first profile grade band that counts as steep
const QP = new URLSearchParams(location.search);
if (QP.get('embed')) document.documentElement.classList.add('embed');   // inside daily_report_v3 sheet 3

/* ---- theme ------------------------------------------------------------ */
(function () {
  let t = QP.get('theme');                                               // ?theme=light|dark wins (embedding page)
  if (!t) { try { t = localStorage.getItem('os_theme'); } catch (e) {} }
  if (!t && matchMedia('(prefers-color-scheme: dark)').matches) t = 'dark';
  if (t === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  $('#themeBtn').onclick = () => {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (dark) document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', 'dark');
    try { localStorage.setItem('os_theme', dark ? 'light' : 'dark'); } catch (e) {}
    render();
  };
})();

/* ---- sources ----------------------------------------------------------- */
const GRADES = M.steep_grades || [];
let steep = GRADES.includes(10) ? 10 : GRADES[0];
const SRC = {rows: () => D.policy[String(steep)] || [],
  desc: () => `An event = a truck driving faster than the mine limit — ${fmt(LF)} km/h on normal roads, ${fmt(LS)} km/h on steep roads (grade ≥ ${steep} %) — derived from the 2-second GPS speed stream in C4M. Consecutive over-limit samples form one event; it is reported when it lasts ≥ ${M.min_duration_s} s and its average speed is ≥ ${fmt(M.tolerance_kmh, 0)} km/h over the limit (shorter or more marginal runs are trucks cruising at the limit, not speeding). "Over by" = average speed during the event minus the limit.`};

/* ---- filters ----------------------------------------------------------- */
const F = {};
const ALL = [].concat(...Object.values(D.policy));
function fillSel(id, vals) { const el = $(id); const cur = el.value; el.innerHTML = '<option value="">All</option>' + vals.map(v => `<option>${esc(v)}</option>`).join(''); el.value = vals.includes(cur) ? cur : ''; }
function rangeFrom(r) {
  if (r === 'all') return M.date_from;
  const d = new Date(M.date_to + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() - (+r - 1));
  const from = d.toISOString().slice(0, 10);
  return from < M.date_from ? M.date_from : from;
}
function setRange(r) { $('#fFrom').value = rangeFrom(r); $('#fTo').value = M.date_to; }
function markQuick() {
  const from = $('#fFrom').value, to = $('#fTo').value;
  let hit = null;                                   // the shortest quick range that matches wins
  for (const b of document.querySelectorAll('#quick button')) if (!hit && to === M.date_to && from === rangeFrom(b.dataset.range)) hit = b;
  document.querySelectorAll('#quick button').forEach(b => b.classList.toggle('on', b === hit));
}
function initFilters() {
  setRange(DEFAULT_DAYS);
  $('#fFrom').min = $('#fTo').min = M.date_from; $('#fFrom').max = $('#fTo').max = M.date_to;
  document.querySelectorAll('#quick button').forEach(b => b.onclick = () => { setRange(b.dataset.range); page = 1; render(); });
  $('#fSteep').innerHTML = GRADES.map(g => `<option value="${g}" ${g === steep ? 'selected' : ''}>${g} %</option>`).join('');
  if (GRADES.length < 2) $('#fSteep').closest('label').style.display = 'none';
  fillSel('#fEq', uniq(ALL.map(r => r.equipment).concat(D.profile.map(r => r.equipment))));
  fillSel('#fOp', uniq(ALL.map(r => r.operator)));
  fillSel('#fCrew', uniq(ALL.map(r => r.crew)));
  document.querySelectorAll('.controls input, .controls select, .period input, .period select').forEach(el => el.addEventListener('input', () => { page = 1; render(); }));
  $('#resetBtn').onclick = () => { document.querySelectorAll('.controls select, .period select').forEach(s => s.value = ''); $('#fSteep').value = GRADES.includes(12) ? 12 : GRADES[0];
    $('#fOver').value = 0; $('#fDur').value = 0; $('#fQ').value = ''; setRange(DEFAULT_DAYS); page = 1; render(); };
  $('#pdfBtn').onclick = () => window.print();
  addEventListener('beforeprint', () => { printMode = true; if (window._rows) renderTable(window._rows); });
  addEventListener('afterprint', () => { printMode = false; if (window._rows) renderTable(window._rows); });
}
function readFilters() {
  F.from = $('#fFrom').value || M.date_from; F.to = $('#fTo').value || M.date_to;
  if (F.from > F.to) { F.from = F.to; $('#fFrom').value = F.to; }
  markQuick();
  F.shift = $('#fShift').value; F.eq = $('#fEq').value; F.op = $('#fOp').value; F.crew = $('#fCrew').value; F.road = $('#fRoad').value;
  F.load = $('#fLoad').value; F.over = +$('#fOver').value || 0; F.dur = +$('#fDur').value || 0; F.q = $('#fQ').value.trim().toLowerCase();
  steep = +$('#fSteep').value || steep;
}
function passBase(r) {
  if (r.shift_date < F.from || r.shift_date > F.to) return false;
  if (F.shift && r.shift !== F.shift) return false;
  if (F.eq && r.equipment !== F.eq) return false;
  if (F.load !== '' && (r.is_loaded ? '1' : '0') !== F.load) return false;
  return true;
}
function passEvent(r) {
  if (!passBase(r)) return false;
  if (F.op && r.operator !== F.op) return false;
  if (F.crew && r.crew !== F.crew) return false;
  if (F.road && r.road && r.road !== F.road) return false;
  if ((r.over_kmh ?? 0) < F.over) return false;
  if ((r.duration_s ?? 0) < F.dur) return false;
  if (F.q) { const h = [r.equipment, r.operator, r.crew, r.segment, r.event_ts].join(' ').toLowerCase(); if (!h.includes(F.q)) return false; }
  return true;
}
const isSteepBand = b => b >= (BAND[steep] ?? 2);
function passProfile(r) {
  if (!passBase(r)) return false;
  if (F.road === 'steep' && !isSteepBand(r.grade_band)) return false;
  if (F.road === 'flat' && isSteepBand(r.grade_band)) return false;
  return true;
}


/* ---- tooltip ----------------------------------------------------------- */
const tip = $('#tip');
function hover(el, text) {
  el.addEventListener('mousemove', e => { tip.style.display = 'block'; tip.textContent = typeof text === 'function' ? text() : text; const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(e.clientX + 14, innerWidth - w - 8) + 'px'; tip.style.top = Math.min(e.clientY + 14, innerHeight - h - 8) + 'px'; });
  el.addEventListener('mouseleave', () => tip.style.display = 'none');
}

/* ---- SVG helpers ------------------------------------------------------- */
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function text(parent, x, y, s, attrs={}) { const t = el('text', Object.assign({x, y}, attrs), parent); t.textContent = s; return t; }
function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); const n = v / p; const m = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10; return m * p; }
function empty(box, msg='No events match the current filters.') { box.innerHTML = `<div class="empty">${msg}</div>`; }

/* vertical bars, optionally stacked. cats: labels; series: [{name,color,values}] */
function barChart(box, cats, series, opts={}) {
  box.innerHTML = '';
  if (!cats.length || !series.some(s => sum(s.values) > 0)) return empty(box, opts.emptyMsg);
  const W = 640, H = opts.h || 230, ml = 44, mr = 10, mt = 12, mb = 42;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, class: 'cv'}, box);
  const tot = cats.map((_, i) => opts.stacked ? sum(series.map(s => s.values[i])) : Math.max(...series.map(s => s.values[i])));
  const ymax = niceMax(Math.max(...tot) * 1.08);
  const pw = W - ml - mr, ph = H - mt - mb;
  const y = v => mt + ph - v / ymax * ph;
  const g = el('g', {class: 'grid'}, svg);
  for (let i = 0; i <= 4; i++) { const v = ymax * i / 4; el('line', {x1: ml, x2: W - mr, y1: y(v), y2: y(v)}, g); text(svg, ml - 6, y(v) + 3.5, fmt(v, opts.dec || 0), {'text-anchor': 'end'}); }
  el('line', {x1: ml, x2: W - mr, y1: y(0), y2: y(0), stroke: css('--color-border-strong')}, svg);
  const bw = pw / cats.length, inner = Math.min(bw * 0.68, 46), gap = 2;
  const step = Math.ceil(cats.length / 14);
  cats.forEach((c, i) => {
    const x0 = ml + bw * i + (bw - inner) / 2;
    let base = 0;
    const n = opts.stacked ? 1 : series.length, sw = (inner - gap * (n - 1)) / n;
    series.forEach((s, j) => {
      const v = s.values[i] || 0; if (!v) return;
      const bx = opts.stacked ? x0 : x0 + j * (sw + gap), w = opts.stacked ? inner : sw;
      const top = opts.stacked ? base + v : v, yb = y(opts.stacked ? base : 0), yt = y(top);
      el('rect', {x: bx, y: yt, width: w, height: Math.max(0, yb - yt - (opts.stacked && base ? 2 : 0)), fill: s.color, rx: base ? 0 : 3, class: 'bar'}, svg);
      base = top;
    });
    const hit = el('rect', {x: ml + bw * i, y: mt, width: bw, height: ph, class: 'hit'}, svg);
    hover(hit, `${opts.catLabel ? opts.catLabel(c) : c}\n` + series.map(s => `${s.name}: ${fmt(s.values[i], opts.dec || 0)}${opts.unit || ''}`).join('\n') + (opts.stacked && series.length > 1 ? `\nTotal: ${fmt(tot[i], opts.dec || 0)}${opts.unit || ''}` : ''));
    if (tot[i] && cats.length <= 16) text(svg, x0 + inner / 2, y(tot[i]) - 4, fmt(tot[i], opts.dec || 0), {'text-anchor': 'middle', class: 'dl'});
    if (i % step === 0) text(svg, x0 + inner / 2, H - mb + 16, opts.short ? opts.short(c) : c, {'text-anchor': 'middle'});
  });
  if (opts.xLabel) text(svg, ml + pw / 2, H - 6, opts.xLabel, {'text-anchor': 'middle'});
}

/* horizontal ranked bars. items: [{label, value, tip}] */
function hbarChart(box, items, color, opts={}) {
  box.innerHTML = '';
  if (!items.length) return empty(box);
  const top = items.slice(0, opts.top || 12);
  const W = opts.W || 640, rh = opts.rh || 24, fs = opts.fs || 11, cw = fs * 0.6;   // cw ≈ label char width
  const ml = Math.min(W * 0.32, Math.max(60, Math.max(...top.map(i => i.label.length)) * cw + 16)), mr = fs * 4.5, mt = 6, mb = 6;
  const H = mt + mb + rh * top.length;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, class: 'cv', style: `font-size:${fs}px`}, box);
  const vmax = Math.max(...top.map(i => i.value)) || 1, pw = W - ml - mr;
  top.forEach((it, i) => {
    const yy = mt + i * rh, w = Math.max(2, it.value / vmax * pw), ty = yy + rh / 2 + fs * 0.36;
    text(svg, ml - 8, ty, it.label.length > 32 ? it.label.slice(0, 31) + '…' : it.label, {'text-anchor': 'end'});
    el('rect', {x: ml, y: yy + rh * 0.18, width: w, height: rh * 0.64, fill: color, rx: 3, class: 'bar'}, svg);
    text(svg, ml + w + 6, ty, fmt(it.value, opts.dec || 0), {class: 'dl', style: `font-size:${fs}px`});
    const hit = el('rect', {x: 0, y: yy, width: W, height: rh, class: 'hit'}, svg);
    hover(hit, it.tip || `${it.label}: ${fmt(it.value, opts.dec || 0)}`);
  });
}

/* multi-series lines */
function lineChart(box, cats, series, opts={}) {
  box.innerHTML = '';
  if (!cats.length || !series.some(s => s.values.some(v => v > 0))) return empty(box, 'No telemetry for the current filters.');
  const W = 900, H = 240, ml = 48, mr = 14, mt = 12, mb = 40;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, class: 'cv'}, box);
  const ymax = niceMax(Math.max(...series.flatMap(s => s.values)) * 1.08);
  const pw = W - ml - mr, ph = H - mt - mb;
  const x = i => ml + (cats.length === 1 ? pw / 2 : i / (cats.length - 1) * pw), y = v => mt + ph - v / ymax * ph;
  const g = el('g', {class: 'grid'}, svg);
  for (let i = 0; i <= 4; i++) { const v = ymax * i / 4; el('line', {x1: ml, x2: W - mr, y1: y(v), y2: y(v)}, g); text(svg, ml - 6, y(v) + 3.5, fmt(v), {'text-anchor': 'end'}); }
  series.forEach(s => {
    const d = s.values.map((v, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1)).join(' ');
    el('path', {d, fill: 'none', stroke: s.color, 'stroke-width': 2, 'stroke-linejoin': 'round'}, svg);
    s.values.forEach((v, i) => el('circle', {cx: x(i), cy: y(v), r: 3.5, fill: s.color, stroke: css('--color-bg-surface'), 'stroke-width': 1.5}, svg));
  });
  const step = Math.ceil(cats.length / 14);
  cats.forEach((c, i) => {
    if (i % step === 0) text(svg, x(i), H - mb + 16, c.slice(5), {'text-anchor': 'middle'});
    const w = pw / Math.max(1, cats.length - 1);
    const hit = el('rect', {x: x(i) - w / 2, y: mt, width: w, height: ph, class: 'hit'}, svg);
    hover(hit, `${c}\n` + series.map(s => `${s.name}: ${fmt(s.values[i], 1)} ${opts.unit || ''}`).join('\n'));
  });
  text(svg, ml + pw / 2, H - 6, opts.xLabel || '', {'text-anchor': 'middle'});
  text(svg, 12, mt + 4, opts.yLabel || '', {'text-anchor': 'start', transform: `rotate(-90 12 ${mt + 4})`, 'font-size': 10});
}

/* highest sustained speed per truck = the highest EVENT AVERAGE (never a single 2 s sample), flat vs steep, with the two limits as reference lines */
function sustainedChart(box, rows) {
  box.innerHTML = '';
  const eqs = uniq(rows.map(r => r.equipment));
  if (!eqs.length) return empty(box);
  const by = {}; rows.forEach(r => { const k = r.equipment + (r.road === 'steep' ? 'S' : 'F'); if (!by[k] || r.avg_speed_kmh > by[k].avg_speed_kmh) by[k] = r; });
  const v = r => r ? r.avg_speed_kmh : 0, excess = it => Math.max(it.F ? v(it.F) - LF : -99, it.S ? v(it.S) - LS : -99);
  const items = eqs.map(e => ({e, F: by[e + 'F'], S: by[e + 'S']})).sort((a, b) => excess(b) - excess(a));
  const W = 900, rh = 26, ml = 60, mr = 20, mt = 16, mb = 24, H = mt + mb + rh * items.length;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, class: 'cv'}, box);
  const vmax = Math.max(60, niceMax(Math.max(...items.map(i => Math.max(v(i.F), v(i.S)))) * 1.05)), pw = W - ml - mr;
  const x = s => ml + s / vmax * pw;
  const g = el('g', {class: 'grid'}, svg);
  for (let s = 0; s <= vmax; s += 10) { el('line', {x1: x(s), x2: x(s), y1: mt, y2: H - mb}, g); text(svg, x(s), H - mb + 14, s, {'text-anchor': 'middle'}); }
  const c1 = css('--series-1'), c2 = css('--series-2');
  const say = (r, lim) => r ? `${fmt(r.avg_speed_kmh, 1)} km/h averaged over ${fmt(r.duration_s)} s on ${r.event_ts.slice(0, 10)} (limit ${fmt(lim)})` : 'no event';
  items.forEach((it, i) => {
    const yy = mt + i * rh;
    text(svg, ml - 8, yy + rh / 2 + 4, it.e, {'text-anchor': 'end'});
    el('rect', {x: ml, y: yy + 4, width: Math.max(0, x(v(it.F)) - ml), height: 8, fill: c1, rx: 2, class: 'bar'}, svg);
    el('rect', {x: ml, y: yy + 14, width: Math.max(0, x(v(it.S)) - ml), height: 8, fill: c2, rx: 2, class: 'bar'}, svg);
    const hit = el('rect', {x: 0, y: yy, width: W, height: rh, class: 'hit'}, svg);
    hover(hit, `${it.e}\nFlat roads: ${say(it.F, LF)}\nSteep roads (≥ ${steep} %): ${say(it.S, LS)}`);
  });
  [[LS, `steep ${fmt(LS)}`], [LF, `flat ${fmt(LF)}`]].forEach(([s, l]) => { el('line', {x1: x(s), x2: x(s), y1: mt - 4, y2: H - mb, class: 'ref'}, svg); text(svg, x(s) + 3, mt + 4, l, {class: 'reflbl'}); });
  text(svg, ml + pw / 2, H - 2, 'km/h (event average)', {'text-anchor': 'middle', 'font-size': 10});
}

/* sparkline for a KPI tile */
function spark(vals) {
  if (!vals.length || !vals.some(v => v > 0)) return '';
  const W = 84, H = 28, mx = Math.max(...vals) || 1;
  const pts = vals.map((v, i) => [(vals.length === 1 ? W / 2 : i / (vals.length - 1) * (W - 2) + 1), H - 2 - v / mx * (H - 6)]);
  const line = pts.map(p => p.map(n => n.toFixed(1)).join(',')).join(' ');
  return `<svg class="spark" viewBox="0 0 ${W} ${H}"><polygon class="area" points="${pts[0][0]},${H} ${line} ${pts[pts.length - 1][0]},${H}"/><polyline points="${line}"/></svg>`;
}

/* ---- map: SVG with atlas-style pan/zoom -------------------------------- */
const CM = D.contour;
const map = $('#map');
let vb = null, mapPts = [], fitBox = null, mapMode = 'auto';
const HEAT_AT = 20000, CELL = 40;
const MW_ = CM ? CM.x1 - CM.x0 : 1, MH_ = CM ? CM.y1 - CM.y0 : 1;
const wx = x => x - CM.x0, wy = y => CM.y1 - y;
function mapK() { const r = map.getBoundingClientRect(); return Math.max(vb[2] / r.width, vb[3] / r.height); }   // world m per CSS px
function applyVB() {
  map.setAttribute('viewBox', vb.join(' '));
  const k = mapK();
  for (const c of mapPts) c.setAttribute('r', (+c.dataset.px * k).toFixed(2));
  const m = 100 * Math.pow(2, Math.round(Math.log2(Math.max(1, 120 * k) / 100)));   // nice scale-bar length in m
  $('#mapScale').textContent = `${fmt(m)} m ≈ ${fmt(m / k)} px  ·  ${fmt(MW_ / vb[2], 1)}×`;
}
function initMap() {
  if (!CM) { $('#mapwrap').style.display = 'none'; $('.maphint').style.display = 'none'; return; }
  vb = [0, 0, MW_, MH_];
  el('image', {href: `data:image/png;base64,${CM.png}`, x: 0, y: 0, width: MW_, height: MH_, preserveAspectRatio: 'none'}, map);
  el('g', {id: 'gPts'}, map);
  const zoomAt = (px, py, k) => { vb = [px - (px - vb[0]) * k, py - (py - vb[1]) * k, vb[2] * k, vb[3] * k]; applyVB(); };
  const centre = () => [vb[0] + vb[2] / 2, vb[1] + vb[3] / 2];
  $('#mzIn').onclick = () => zoomAt(...centre(), 0.7);
  $('#mzOut').onclick = () => zoomAt(...centre(), 1 / 0.7);
  $('#mzReset').onclick = () => { vb = [0, 0, MW_, MH_]; applyVB(); };
  $('#mzFit').onclick = fitEvents;
  $('#mzMode').onclick = () => { mapMode = (mapMode === 'heat' || (mapMode === 'auto' && mapPts.length === 0)) ? 'dots' : 'heat'; renderMap(window._rows || []); };
  let drag = null;
  map.addEventListener('pointerdown', ev => { drag = [ev.clientX, ev.clientY, ...vb]; map.classList.add('drag'); map.setPointerCapture(ev.pointerId); });
  map.addEventListener('pointerup', () => { drag = null; map.classList.remove('drag'); });
  map.addEventListener('pointercancel', () => { drag = null; map.classList.remove('drag'); });
  map.addEventListener('pointermove', ev => {
    if (!drag) return;
    const r = map.getBoundingClientRect(), k = mapK();
    vb[0] = drag[2] - (ev.clientX - drag[0]) * k; vb[1] = drag[3] - (ev.clientY - drag[1]) * k; applyVB();
  });
  map.addEventListener('wheel', ev => {
    ev.preventDefault();
    const r = map.getBoundingClientRect(), k = mapK();
    const px = vb[0] + (vb[2] - r.width * k) / 2 + (ev.clientX - r.left) * k;   // meet: centred letterbox
    const py = vb[1] + (vb[3] - r.height * k) / 2 + (ev.clientY - r.top) * k;
    zoomAt(px, py, ev.deltaY > 0 ? 1.25 : 0.8);
  }, {passive: false});
  map.addEventListener('dblclick', ev => { const r = map.getBoundingClientRect(), k = mapK(); zoomAt(vb[0] + (vb[2] - r.width * k) / 2 + (ev.clientX - r.left) * k, vb[1] + (vb[3] - r.height * k) / 2 + (ev.clientY - r.top) * k, 0.5); });
  window.addEventListener('resize', () => vb && applyVB());
  applyVB();
}
function fitEvents() {
  if (!fitBox) { vb = [0, 0, MW_, MH_]; applyVB(); return; }
  const [x0, y0, x1, y1] = fitBox;
  const pad = Math.max(60, (x1 - x0) * 0.08, (y1 - y0) * 0.08);
  vb = [x0 - pad, y0 - pad, Math.max(120, x1 - x0 + 2 * pad), Math.max(120, y1 - y0 + 2 * pad)]; applyVB();
}
function renderMap(rows) {
  if (!CM) return;
  const g = $('#gPts'); g.innerHTML = ''; mapPts = []; fitBox = null;
  const inside = rows.filter(r => r.x != null && r.y != null && r.x >= CM.x0 && r.x <= CM.x1 && r.y >= CM.y0 && r.y <= CM.y1);
  const n = inside.length;
  if (n) fitBox = [wx(Math.min(...inside.map(r => r.x))), wy(Math.max(...inside.map(r => r.y))), wx(Math.max(...inside.map(r => r.x))), wy(Math.min(...inside.map(r => r.y)))];
  const heat = mapMode === 'heat' || (mapMode === 'auto' && n > HEAT_AT);
  $('#mzMode').textContent = heat ? 'dots' : 'heat';
  if (heat) {
    const cells = new Map();
    for (const r of inside) { const k = Math.floor(wx(r.x) / CELL) + ',' + Math.floor(wy(r.y) / CELL); const c = cells.get(k) || {n: 0, s: 0, mx: 0}; c.n++; if (r.road === 'steep') c.s++; c.mx = Math.max(c.mx, r.over_kmh || 0); cells.set(k, c); }
    const mx = Math.max(...[...cells.values()].map(c => c.n));
    for (const [k, c] of cells) {
      const [ix, iy] = k.split(',').map(Number);
      const rc = el('rect', {x: ix * CELL, y: iy * CELL, width: CELL, height: CELL, class: 'cell' + (c.s > c.n / 2 ? ' s' : ''), 'fill-opacity': (0.18 + 0.82 * Math.sqrt(c.n / mx)).toFixed(2)}, g);
      hover(rc, `${fmt(c.n)} events in this 40 m cell\n${fmt(c.s)} on steep roads · worst excess +${fmt(c.mx, 1)} km/h`);
    }
    $('#mapN').textContent = `${fmt(n)} events · ${fmt(cells.size)} cells (darker = more)`;
  } else {
    const sorted = inside.slice().sort((a, b) => (a.over_kmh || 0) - (b.over_kmh || 0));   // worst on top
    for (const r of sorted) {
      const px = 3 + Math.min(6, Math.max(0, r.over_kmh || 0) * 0.45);                 // screen radius in px, by excess
      const c = el('circle', {cx: wx(r.x).toFixed(1), cy: wy(r.y).toFixed(1), class: 'pt' + (r.road === 'steep' ? ' s' : '')}, g);
      c.dataset.px = px; mapPts.push(c);
      hover(c, () => `${r.event_ts}  ${r.equipment}\n${r.operator || ''}${r.crew ? ' · ' + r.crew : ''}\n${r.road ? r.road + ' road' + (r.grade_pct != null ? `, grade ${fmt(r.grade_pct, 1)} %` : '') : r.segment}\navg ${fmt(r.avg_speed_kmh, 1)} km/h (limit ${fmt(r.limit_kmh)}) · +${fmt(r.over_kmh, 1)} km/h · ${fmt(r.duration_s)} s · ${r.is_loaded ? 'loaded' : 'empty'}`);
    }
    $('#mapN').textContent = n ? `${fmt(n)} events shown` : (rows.length ? 'events are outside the map extent' : 'no events to plot');
  }
  if (!renderMap.fitted && n) { renderMap.fitted = true; fitEvents(); } else applyVB();   // first view frames the events; "all" shows the whole pit
}

/* ---- render ------------------------------------------------------------ */
let page = 1, sortKey = 'event_ts', sortDesc = false, printMode = false;
const COLS = [
  ['event_ts', 'Start', 'txt'], ['shift_date', 'Shift date', 'txt'], ['shift', 'Shift', 'txt'], ['equipment', 'Truck', 'txt'],
  ['operator', 'Operator', 'txt'], ['crew', 'Crew', 'txt'], ['road', 'Road', 'road'], ['grade_pct', 'Grade %', 'num1'], ['segment', 'Segment', 'txt'],
  ['limit_kmh', 'Limit', 'num'], ['avg_speed_kmh', 'Avg km/h', 'num1'], ['over_kmh', 'Over by (avg)', 'num1'],
  ['duration_s', 'Duration s', 'num'], ['is_loaded', 'Load', 'load'], ['x', 'X', 'num'], ['y', 'Y', 'num'], ['z', 'Z', 'num1']];

function render() {
  readFilters(); $('#tabdesc').textContent = SRC.desc();
  const rows = SRC.rows().filter(passEvent);
  const prof = D.profile.filter(passProfile);
  const days = []; for (let t = Date.parse(F.from + 'T00:00:00Z'); t <= Date.parse(F.to + 'T00:00:00Z'); t += 864e5) days.push(new Date(t).toISOString().slice(0, 10));
  const cnt = (arr, key) => { const m = {}; arr.forEach(r => { const v = key(r); m[v] = (m[v] || 0) + 1; }); return m; };

  // KPIs
  const trucks = uniq(rows.map(r => r.equipment)), ops = uniq(rows.map(r => r.operator));
  const movingH = sum(prof.map(r => r.sec_moving)) / 3600;
  const overPolicy = sum(prof.map(r => isSteepBand(r.grade_band) ? r['sec_gt' + LS] : r['sec_gt' + LF])) || 0;
  const perDay = cnt(rows, r => r.shift_date), steepDay = cnt(rows.filter(r => r.road === 'steep'), r => r.shift_date);
  const byDayProf = {}; prof.forEach(r => { byDayProf[r.shift_date] = (byDayProf[r.shift_date] || 0) + (isSteepBand(r.grade_band) ? r['sec_gt' + LS] : r['sec_gt' + LF]); });
  const longDay = {}; rows.forEach(r => { longDay[r.shift_date] = Math.max(longDay[r.shift_date] || 0, r.duration_s || 0); });
  const worst = rows.length ? rows.reduce((a, b) => (b.over_kmh > a.over_kmh ? b : a)) : null;
  const longest = rows.length ? rows.reduce((a, b) => (b.duration_s > a.duration_s ? b : a)) : null;
  const perDayAvg = days.length ? rows.length / days.length : 0;
  const k = [
    ['Over-speed events', fmt(rows.length), '', `${fmt(perDayAvg, 0)} per shift day`, days.map(d => perDay[d] || 0), ''],
    ['On steep roads', fmt(rows.filter(r => r.road === 'steep').length), '', `limit ${fmt(LS)} km/h · grade ≥ ${steep} %`, days.map(d => steepDay[d] || 0), 'steep'],
    ['Trucks / operators', `${fmt(trucks.length)}<small>/ ${fmt(ops.length)}</small>`, '', 'involved in the period', null, ''],
    ['Worst excess', worst ? fmt(worst.over_kmh, 1) : '–', 'km/h', worst ? `${worst.equipment} · averaged ${fmt(worst.avg_speed_kmh, 1)} km/h for ${fmt(worst.duration_s)} s on a ${worst.road ? worst.road + ' road' : 'segment'} (limit ${fmt(worst.limit_kmh)})` : '', null, 'crit'],
    ['Time in events', rows.length ? fmt(sum(rows.map(r => r.duration_s)) / 60, 1) : '–', 'min', rows.length ? `avg ${fmt(sum(rows.map(r => r.duration_s)) / rows.length, 0)} s per event` : '', null, ''],
    ['GPS time over limit', fmt(overPolicy / 60, 1), 'min', `of ${fmt(movingH, 0)} h moving (${fmt(movingH ? overPolicy / 36 / movingH : 0, 2)} %) · raw stream, no rule`, days.map(d => (byDayProf[d] || 0) / 60), ''],
    ['Longest event', longest ? fmt(longest.duration_s) : '–', 's', longest ? `${longest.equipment} · averaged ${fmt(longest.avg_speed_kmh, 1)} km/h on a ${longest.road ? longest.road + ' road' : 'segment'} (limit ${fmt(longest.limit_kmh)})` : '', days.map(d => longDay[d] || 0), ''],
  ];
  $('#kpis').innerHTML = k.map(([l, v, u, s, sp, cls]) => { const sv = sp ? spark(sp) : ''; return `<div class="kpi ${cls}${sv ? ' hasspark' : ''}"><div class="k">${l}</div><div class="v">${v}${u ? `<small>${u}</small>` : ''}</div><div class="s">${s}</div>${sv}</div>`; }).join('');
  $('#ovsub').textContent = `${F.from} → ${F.to}${F.shift ? ' · ' + F.shift : ''}${F.eq ? ' · ' + F.eq : ''}${F.road ? ' · ' + F.road + ' roads' : ''}`;

  // charts
  const c1 = css('--series-1'), c2 = css('--series-2');
  const byDayDS = cnt(rows.filter(r => r.shift === 'DS'), r => r.shift_date), byDayNS = cnt(rows.filter(r => r.shift === 'NS'), r => r.shift_date);
  barChart($('#cDay'), days, [{name: 'DS', color: c1, values: days.map(d => byDayDS[d] || 0)}, {name: 'NS', color: c2, values: days.map(d => byDayNS[d] || 0)}], {stacked: true, short: d => d.slice(5)});
  const byDayF = cnt(rows.filter(r => r.road !== 'steep'), r => r.shift_date);
  barChart($('#cRoad'), days, [{name: 'Flat road', color: c1, values: days.map(d => byDayF[d] || 0)}, {name: 'Steep road', color: c2, values: days.map(d => steepDay[d] || 0)}], {stacked: true, short: d => d.slice(5)});
  const hrs = [...Array(24).keys()], byHr = cnt(rows, r => +r.event_ts.slice(11, 13));
  barChart($('#cHour'), hrs, [{name: 'events', color: c1, values: hrs.map(h => byHr[h] || 0)}], {catLabel: h => `${String(h).padStart(2, '0')}:00–${String(h).padStart(2, '0')}:59`, xLabel: 'hour of day'});
  const rank = (key, extra) => Object.entries(cnt(rows, key)).map(([label, value]) => ({label, value, tip: extra ? extra(label, value) : undefined})).sort((a, b) => b.value - a.value);
  const worstOf = (key, lab) => fmt(Math.max(...rows.filter(r => String(key(r)) === lab).map(r => r.over_kmh)), 1);
  hbarChart($('#cEq'), rank(r => r.equipment, (l, v) => `${l}: ${v} events, worst +${worstOf(r => r.equipment, l)} km/h over the limit (avg)`), c1, {top: 20, W: 1000, rh: 30, fs: 13});
  hbarChart($('#cOp'), rank(r => r.operator || '(unknown)', (l, v) => `${l}: ${v} events, worst +${worstOf(r => r.operator || '(unknown)', l)} km/h over the limit (avg)`), c1, {top: 25, W: 1000, rh: 30, fs: 13});
  sustainedChart($('#cSustained'), rows);
  const bins = [[0, 3, '2–3'], [3, 5, '3–5'], [5, 8, '5–8'], [8, 12, '8–12'], [12, 1e9, '12+']];
  barChart($('#cHist'), bins.map(b => b[2]), [{name: 'events', color: c1, values: bins.map(b => rows.filter(r => r.over_kmh >= b[0] && r.over_kmh < b[1]).length)}], {xLabel: 'km/h over the limit'});

  // profile
  const T = [30, 35, 40, 45, 50];
  const pd = {}; prof.forEach(r => { const o = pd[r.shift_date] = pd[r.shift_date] || {}; T.forEach(t => o[t] = (o[t] || 0) + (r['sec_gt' + t] || 0)); });
  lineChart($('#cProf'), days, T.map((t, i) => ({name: `> ${t} km/h`, color: css(`--seq-${i + 1}`), values: days.map(d => (pd[d] ? pd[d][t] || 0 : 0) / 60)})), {unit: 'min', yLabel: 'minutes', xLabel: 'shift date'});

  renderMap(rows);
  renderTable(rows);
}

function renderTable(rows) {
  const cols = COLS;
  const r2 = rows.slice().sort((a, b) => { const x = a[sortKey], y = b[sortKey]; const c = x == null ? 1 : y == null ? -1 : typeof x === 'number' ? x - y : String(x).localeCompare(String(y)); return sortDesc ? -c : c; });
  const per = printMode ? 200 : 50, pages = Math.max(1, Math.ceil(r2.length / per)); if (printMode) page = 1; page = Math.min(page, pages);
  const slice = r2.slice((page - 1) * per, page * per);
  $('#tbl thead').innerHTML = '<tr>' + cols.map(c => `<th class="${c[2].startsWith('num') ? 'num' : ''} ${sortKey === c[0] ? 's' + (sortDesc ? ' desc' : '') : ''}" data-k="${c[0]}">${c[1]}</th>`).join('') + '</tr>';
  $('#tbl tbody').innerHTML = slice.map(r => '<tr>' + cols.map(c => {
    const v = r[c[0]];
    if (c[2] === 'num') return `<td class="num">${fmt(v, 0)}</td>`;
    if (c[2] === 'num1') return `<td class="num">${c[0] === 'over_kmh' && v > 0 ? `<span class="pill over">+${fmt(v, 1)}</span>` : fmt(v, 1)}</td>`;
    if (c[2] === 'road') return `<td>${v === 'steep' ? '<span class="pill steep">Steep</span>' : v ? '<span class="pill">Flat</span>' : '–'}</td>`;
    if (c[2] === 'load') return `<td>${v ? '<span class="pill l">Loaded</span>' : '<span class="pill">Empty</span>'}</td>`;
    if (c[2] === 'bool') return `<td>${v ? '✓' : ''}</td>`;
    return `<td>${esc(v)}</td>`;
  }).join('') + '</tr>').join('') || `<tr><td colspan="${cols.length}" class="empty">No events match the current filters.</td></tr>`;
  document.querySelectorAll('#tbl th').forEach(th => th.onclick = () => { if (sortKey === th.dataset.k) sortDesc = !sortDesc; else { sortKey = th.dataset.k; sortDesc = false; } renderTable(rows); });
  $('#tblN').textContent = `${fmt(r2.length)} rows${r2.length > per ? ` · showing ${(page - 1) * per + 1}–${Math.min(page * per, r2.length)}` : ''}${printMode ? ' (PDF shows the first 200 — export the CSV for all)' : ' · click a header to sort'}`;
  $('#pager').innerHTML = pages > 1 ? `<button class="btn" ${page <= 1 ? 'disabled' : ''} onclick="page--;renderTable(window._rows)">‹ Prev</button><span>Page ${page} / ${pages}</span><button class="btn" ${page >= pages ? 'disabled' : ''} onclick="page++;renderTable(window._rows)">Next ›</button>` : '';
  window._rows = rows;
  $('#csvBtn').onclick = () => {
    const keys = cols.map(c => c[0]);
    const csv = [keys.join(',')].concat(r2.map(r => keys.map(k => { let v = r[k]; if (v == null) v = ''; if (typeof v === 'boolean') v = v ? 1 : 0; v = String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(','))).join('\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['﻿' + csv], {type: 'text/csv;charset=utf-8'})); a.download = `overspeed_events_${F.from}_${F.to}.csv`; a.click();
  };
}

/* ---- section nav scroll-spy ------------------------------------------- */
(function () {
  const links = [...document.querySelectorAll('nav.toc a')];
  const ids = links.map(a => a.getAttribute('href').slice(1));
  const spy = () => { let on = ids[0]; for (const id of ids) { const e = document.getElementById(id); if (e && e.getBoundingClientRect().top <= 90) on = id; } links.forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + on)); };
  addEventListener('scroll', spy, {passive: true}); spy();
})();

/* ---- on-demand refresh (runs the nightly C4M job on the R4M server; hidden when the service is absent) ---- */
(function () {
  const btn = $('#refreshBtn'), msg = $('#refreshMsg'), JOB = 'overspeed';
  if (location.protocol === 'file:') return;
  // the service answers under /r4m_custom_report/ only; the R4M menu embeds the report under /fronts/r4m_custom_report/
  const BASE = location.pathname.replace(/^\/fronts(?=\/)/, '').replace(/[^/]*$/, '');
  const api = q => fetch(BASE + 'refresh' + q, { cache: 'no-store' }).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)));
  const say = (t, cls) => { msg.textContent = t; msg.className = cls || ''; };
  const idle = st => {
    btn.hidden = false; btn.classList.remove('busy');
    if (st.rc != null && st.rc !== 0) say(`last on-demand refresh failed (exit ${st.rc}, ${st.finished}) — see the server log`, 'err');
    else if (st.cooldownLeft > 0) say(`refreshed ${st.finished} · next refresh possible in ${Math.ceil(st.cooldownLeft / 60)} min`);
    else say(`data to ${M.date_to} · nightly at 10:30 · click to pull the newest shifts now`);
  };
  const poll = () => api('/status?job=' + JOB).then(st => {
    if (st.running) { btn.classList.add('busy'); say(`refreshing from C4M… ${st.elapsed || 0} s (pull + build ≈ 1 min)`); setTimeout(poll, 4000); return; }
    if (st.rc === 0 && window.__refreshWait) {
      say('done — reloading the page with the new data', 'ok');
      const q = new URLSearchParams(location.search); q.set('v', Date.now());
      setTimeout(() => location.replace(location.pathname + '?' + q + location.hash), 800);
      return;
    }
    window.__refreshWait = false; idle(st);
  }).catch(() => { btn.hidden = true; say(''); });
  btn.onclick = () => {
    btn.classList.add('busy'); say('starting…');
    fetch(BASE + 'refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ job: JOB }) })
      .then(r => r.json().then(j => ({ code: r.status, j })))
      .then(({ code, j }) => {
        if (code === 202 || code === 409) { window.__refreshWait = true; poll(); }
        else if (code === 429) { say(`a refresh just ran (${j.finished}) · try again in ${Math.ceil((j.cooldownLeft || 0) / 60)} min`, 'err'); btn.classList.remove('busy'); }
        else { say(`refresh not available: ${j.error || code}`, 'err'); btn.classList.remove('busy'); }
      }).catch(e => { say('refresh service unreachable: ' + e.message, 'err'); btn.classList.remove('busy'); });
  };
  api('/status?job=' + JOB).then(st => { if (!st.available) return; if (st.running) { window.__refreshWait = true; } poll(); }).catch(() => {});
})();

/* ---- boot --------------------------------------------------------------- */
$('#chips').innerHTML = `<span class="chip">limit <b>${fmt(LF)} km/h</b></span><span class="chip">steep roads <b>${fmt(LS)} km/h</b></span><span class="chip">${fmt((D.policy[String(steep)] || []).length)} events at grade ≥ ${steep} %</span><span class="chip warn">C4M in-cab alerts still configured 50/60</span>`;
$('#note').innerHTML = `<b>Mine speed limit: ${fmt(LF)} km/h, ${fmt(LS)} km/h on steep roads.</b> Events are derived from the 2-second GPS speed stream C4M records for every truck; road steepness is measured from the GPS track (grade over ±${M.grade_window_s} s of travel, cut-off selectable in the filter bar). C4M's own segment limits are still 50 km/h loaded / 60 km/h empty, so operators get no in-cab warning at the real policy — ask the C4M administrator to set them to ${fmt(LF)}/${fmt(LS)}.`;
$('#foot').innerHTML = `Data: C4M ControlSenseDB — <code>ta_datacamion_historic</code> (2 s GPS: speed, position, elevation, load state, operator), <code>ts_equipos</code>, <code>tp_trabajador</code>, <code>ta_guardias</code>. Telemetry rows arrive with a 1–3 h delay, so the last hours of the final shift may be incomplete. Coordinates are mine-grid metres. Grade = elevation change ÷ horizontal distance over a ±${M.grade_window_s} s window; samples with less than 15 m of travel in the window have no grade and count as flat. An event merges consecutive over-limit samples with gaps ≤ 4 s under the same limit; it is reported when it lasts ≥ ${M.min_duration_s} s and its average speed is ≥ ${fmt(M.tolerance_kmh, 0)} km/h over the limit — shorter or more marginal runs are trucks cruising at the limit (rule set 2026-10-16; peak 2-second samples are not reported). Built by overspeed/build_overspeed.py.`;
initFilters(); initMap(); render();
"""
