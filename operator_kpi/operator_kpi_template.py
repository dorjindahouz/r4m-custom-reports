# -*- coding: utf-8 -*-
"""CSS / HTML / JS for the Operator KPI page (assembled by build_operator_kpi.py).

Same visual grammar as the over-speed page and daily_report_v3: white sheet on the grey dashboard,
Rubik uppercase title block, sticky section nav, numbered blue banners, KPI tiles with sparklines,
chart cards, table.x. Everything inline: the built HTML is one self-contained file that works offline.

Embedded data (see build_operator_kpi.py):
  ops      one row per shift date x shift x equipment x operator with sums/counts only, so any
           from/to range re-aggregates exactly on the page
  reasons  non-productive hours per shift x operator x status detail
  forms    one row per checklist form;  items.ids / items.nok = answered / NOT-OK item ids per form
  dimItems checklist items in template -> section -> ordinal order (the wide CSV's columns)
"""

CSS = r"""
:root {
  --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a; --series-4: #eda100; --series-5: #8a8f94;
  --seq-1: #9ec5f4; --seq-2: #6da7ec; --seq-3: #3987e5; --seq-4: #256abf; --seq-5: #184f95;
  --status-critical: #d03b3b; --status-warning: #fab219;
  --sheet-w: 1280px;
}
[data-theme="dark"] {
  --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500; --series-5: #a7adb3;
  --seq-1: #cde2fb; --seq-2: #9ec5f4; --seq-3: #6da7ec; --seq-4: #3987e5; --seq-5: #1c5cab;
}
* { box-sizing: border-box; }
html { color-scheme: light; scroll-behavior: smooth; }
[data-theme="dark"] { color-scheme: dark; }
body { background: var(--color-bg-dashboard); color: var(--color-text-primary); font-size: 13.5px; line-height: 1.45; counter-reset: sec; }
a { color: var(--color-primary); }
code { font-size: 11.5px; }
h1, h2, h3, h4 { font-family: "Rubik", -apple-system, BlinkMacSystemFont, sans-serif; }
.sheet { width: var(--sheet-w); max-width: 97vw; margin: 18px auto 30px; background: var(--color-bg-surface);
         border: 1px solid var(--color-border-subtle); border-radius: 6px; box-shadow: var(--shadow-md); padding: 0 28px 36px; }
html.embed .sheet { margin-top: 10px; }
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
#refreshBtn[hidden] { display: none; }
#refreshBtn.busy { opacity: .7; pointer-events: none; }
#refreshBtn.busy::before { content: ""; display: inline-block; width: 10px; height: 10px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; margin-right: 6px; vertical-align: -1px; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
#refreshMsg { font-size: 11px; color: var(--color-text-tertiary); margin-top: 4px; text-align: right; min-height: 14px; }
#refreshMsg.err { color: var(--status-critical); }
#refreshMsg.ok { color: #0f6b3a; }
.btn.sm { padding: 3px 9px; font-size: 11.5px; font-weight: 600; }
.btn.sm.on { background: var(--color-primary); border-color: var(--color-primary); color: var(--color-text-on-primary); }
.quick { display: flex; gap: 6px; justify-content: flex-end; margin-top: 7px; flex-wrap: wrap; }
html.embed .titleblock { padding-top: 14px; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 0; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 11px; border-radius: 12px; font-size: 11px; font-weight: 700; letter-spacing: .4px;
        background: var(--badge-bg); border: 1px solid var(--badge-border); color: var(--badge-text); }
.chip.warn { background: color-mix(in srgb, var(--status-warning) 16%, transparent); border-color: var(--status-warning); color: #6b4a00; }
[data-theme="dark"] .chip.warn { color: #ffd98a; }
.chip b { font-weight: 800; }
nav.toc { position: sticky; top: 0; z-index: 40; display: flex; flex-wrap: wrap; gap: 2px 4px; padding: 8px 10px; margin: 0 -28px 14px;
          background: var(--color-bg-surface); border-bottom: 2px solid var(--color-primary); }
nav.toc a { color: var(--color-text-secondary); text-decoration: none; font-size: 12.5px; font-weight: 700; padding: 5px 13px; border-radius: 14px; }
nav.toc a:hover { background: var(--state-hover-blue); color: var(--color-text-primary); }
nav.toc a.on { background: var(--color-primary); color: var(--color-text-on-primary); }
nav.toc .spring { flex: 1; }
nav.toc .hint { font-size: 11px; color: var(--color-text-tertiary); align-self: center; }
.banner { background: var(--color-primary); color: var(--color-text-on-primary); font-family: "Rubik", sans-serif; font-weight: 700; font-size: 14.5px;
          letter-spacing: 1.4px; text-transform: uppercase; padding: 8px 18px; margin: 26px 0 12px; border-left: 5px solid var(--color-primary-dark);
          border-radius: 3px; box-shadow: var(--shadow-sm); counter-increment: sec; }
.banner::before { content: counter(sec, decimal-leading-zero) "  \00b7  "; color: var(--color-primary-light); letter-spacing: 2px; }
.banner small { font-weight: 400; letter-spacing: .3px; text-transform: none; opacity: .85; margin-left: 10px; font-size: 12px; }
.lead { color: var(--color-text-secondary); font-size: 12.5px; font-style: italic; margin: -4px 0 12px 2px; }
.note { padding: 10px 14px; margin: 14px 0 0; border-left: 4px solid var(--status-warning); background: var(--color-bg-surface-secondary); border-radius: 0 4px 4px 0; font-size: 12.5px; }
.note b { font-weight: 700; }
.controls { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; padding: 10px 14px; margin: 10px 0 14px; border-radius: 5px;
            background: var(--color-bg-surface-secondary); border: 1px solid var(--color-border-subtle); font-size: 12.5px; }
.controls label { display: inline-flex; gap: 6px; align-items: center; color: var(--color-text-secondary); white-space: nowrap; }
.controls label b { color: var(--color-text-primary); font-weight: 700; }
.controls input, .controls select { font: inherit; font-size: 12.5px; padding: 4px 7px; border: 1px solid var(--color-border-strong); border-radius: 4px;
                                    background: var(--color-bg-surface); color: var(--color-text-primary); max-width: 190px; }
.controls input[type=number] { width: 62px; }
.controls input[type=search] { min-width: 180px; }
.controls .sep { color: var(--color-border-strong); }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(205px, 1fr)); gap: 10px; margin: 0 0 6px; }
.kpi { position: relative; padding: 11px 14px 10px; background: var(--color-bg-metrics); border: 1px solid var(--color-border-subtle);
       border-left: 4px solid var(--color-primary); border-radius: 6px; box-shadow: var(--shadow-sm); min-height: 88px; }
.kpi.alt { border-left-color: var(--series-2); }
.kpi.ok { border-left-color: var(--series-3); }
.kpi.crit { border-left-color: var(--status-critical); }
.kpi .k { font-size: 10.5px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: var(--color-text-secondary); }
.kpi .v { font-family: "Rubik", sans-serif; font-size: 26px; font-weight: 700; color: var(--color-text-kpi); line-height: 1.15; margin-top: 3px; }
.kpi .v small { font-size: 13px; font-weight: 400; color: var(--color-text-secondary); margin-left: 3px; }
.kpi .s { font-size: 11.5px; color: var(--color-text-secondary); margin-top: 3px; }
.kpi.hasspark .s { padding-right: 74px; }
.kpi svg.spark { position: absolute; right: 10px; bottom: 10px; width: 70px; height: 24px; }
.kpi svg.spark polyline { fill: none; stroke: var(--color-primary); stroke-width: 1.8; stroke-linejoin: round; }
.kpi.alt svg.spark polyline { stroke: var(--series-2); }
.kpi.ok svg.spark polyline { stroke: var(--series-3); }
.kpi svg.spark .area { fill: var(--color-primary); opacity: .10; }
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
svg.cv .dl { fill: var(--color-text-primary); font-size: 10.5px; }
.empty { padding: 28px 12px; text-align: center; color: var(--color-text-tertiary); font-size: 13px; }
#tip { position: fixed; pointer-events: none; z-index: 50; background: var(--color-bg-surface); color: var(--color-text-primary);
       border: 1px solid var(--color-border-medium); border-radius: 6px; box-shadow: var(--shadow-md); padding: 7px 10px; font-size: 12px;
       max-width: 340px; display: none; white-space: pre-line; line-height: 1.4; }
.tbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.tbar .n { color: var(--color-text-secondary); font-size: 12.5px; flex: 1; }
.tbar label { font-size: 12.5px; color: var(--color-text-secondary); display: inline-flex; gap: 6px; align-items: center; }
.tbar select { font: inherit; font-size: 12.5px; padding: 3px 6px; border: 1px solid var(--color-border-strong); border-radius: 4px; background: var(--color-bg-surface); color: var(--color-text-primary); }
.tbl { width: 100%; overflow: auto; border: 1px solid var(--color-border-subtle); border-radius: 5px; max-height: 640px; }
table.x { border-collapse: collapse; width: 100%; font-size: 12.5px; white-space: nowrap; }
table.x th, table.x td { padding: 6px 9px; border-bottom: 1px solid var(--color-border-subtle); text-align: left; }
table.x th { position: sticky; top: 0; background: var(--color-primary-light); color: #05498c; cursor: pointer; user-select: none; font-weight: 700; font-size: 11.5px; z-index: 1; }
[data-theme="dark"] table.x th { background: var(--color-bg-selected); color: var(--color-text-primary); }
table.x th.s::after { content: " ▲"; font-size: 9px; } table.x th.s.desc::after { content: " ▼"; }
table.x td.num, table.x th.num { text-align: right; font-variant-numeric: tabular-nums; }
table.x tbody tr:hover td { background: var(--state-hover-bg); }
table.x th.grp { background: var(--color-bg-surface-secondary); color: var(--color-text-secondary); text-align: center; font-size: 10.5px; letter-spacing: .8px; cursor: default; top: 0; }
table.x th.sub { top: 27px; }
.pill { display: inline-block; padding: 1px 7px; border-radius: 9px; font-size: 11px; font-weight: 600; border: 1px solid var(--color-border-medium); }
.pill.ok { background: #e6f6ee; color: #0f6b3a; border-color: #b7e3c9; }
.pill.rej { background: #fdecec; color: #8a1f1f; border-color: #f3b4b4; }
.pill.pend { background: var(--color-bg-surface-secondary); color: var(--color-text-secondary); }
.pill.haul { background: var(--color-primary-lighter); color: var(--color-primary-dark); border-color: var(--color-primary-light); }
.pill.load { background: #fdeee6; color: #8a3a12; border-color: #f5c3a8; }
[data-theme="dark"] .pill.ok { background: #143526; color: #9fe0bb; border-color: #245c3d; }
[data-theme="dark"] .pill.rej { background: #3a1d1d; color: #ffb3b3; border-color: #6b2b2b; }
[data-theme="dark"] .pill.haul { background: #1a2f4a; color: #cfe3ff; border-color: #2d4a6b; }
[data-theme="dark"] .pill.load { background: #3a2518; color: #ffc9ad; border-color: #6b3d22; }
.pager { display: flex; gap: 6px; align-items: center; justify-content: flex-end; margin-top: 8px; font-size: 12.5px; }
.foot { color: var(--color-text-tertiary); font-size: 11.5px; margin: 26px 2px 0; padding-top: 10px; border-top: 1px solid var(--color-border-subtle); line-height: 1.5; }
.nok { color: var(--status-critical); font-weight: 700; }
@media (max-width: 760px) { .sheet { padding: 0 14px 24px; } .titleblock, nav.toc { margin-left: -14px; margin-right: -14px; } .titleblock { padding-left: 14px; padding-right: 14px; flex-wrap: wrap; }
  .titleblock .right { text-align: left; width: 100%; } .titleblock .period, .titleblock .btns { justify-content: flex-start; } .titleblock h1 { font-size: 17px; } .kpi .v { font-size: 21px; } }
/* ---- 01 shift sheet ---- */
.controls.shiftctl { background: color-mix(in srgb, var(--color-primary) 7%, var(--color-bg-surface)); border-color: color-mix(in srgb, var(--color-primary) 30%, transparent); }
.controls.shiftctl .spring { flex: 1; }
#sRunning[hidden] { display: none; }
#shKpis { grid-template-columns: repeat(6, minmax(0, 1fr)); }
@media (max-width: 1100px) { #shKpis { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
.controls.shiftctl .btn { white-space: nowrap; }
.controls.shiftctl input[type=date] { max-width: none; font-weight: 700; border-color: var(--color-primary); }
.follow { display: flex; flex-wrap: wrap; gap: 6px 8px; margin: 10px 0 14px; align-items: center; }
.follow .ttl { font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--color-text-secondary); margin-right: 4px; }
.follow .none { font-size: 12.5px; color: #0f6b3a; font-weight: 600; }
.follow { align-items: flex-start; }
.follow .ttl { padding-top: 5px; }
.fgs { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 0; }
.fg { display: grid; grid-template-columns: 186px minmax(0, 1fr); gap: 6px; align-items: start; }
.fg .fc { display: flex; flex-wrap: wrap; gap: 5px 6px; }
.fg .fl { padding-top: 5px; font-size: 11.5px; font-weight: 700; color: var(--color-text-secondary); }
.fg .fl b { display: inline-block; min-width: 20px; padding: 0 6px; border-radius: 9px; text-align: center; color: #fff; background: var(--color-border-strong); font-size: 10.5px; }
.fg .fl.os b { background: var(--status-critical); } .fg .fl.chk b { background: #b07d00; } .fg .fl.nok b { background: var(--series-2); }
.fu { font: inherit; font-size: 12px; padding: 4px 10px 4px 8px; border-radius: 4px; cursor: pointer; text-align: left;
      background: var(--color-bg-surface); color: var(--color-text-primary); border: 1px solid var(--color-border-medium); border-left: 4px solid var(--color-border-strong); }
.fu:hover { background: var(--state-hover-bg); }
.fu b { font-weight: 700; }
.fu.os { border-left-color: var(--status-critical); }
.fu.chk { border-left-color: var(--status-warning); }
.fu.nok { border-left-color: var(--series-2); }
.fu.prod, .fu.rate { border-left-color: var(--series-5); }
.shtbl h4 { display: flex; align-items: baseline; gap: 10px; }
.shtbl h4 small { font-size: 11.5px; font-weight: 400; text-transform: none; letter-spacing: 0; color: var(--color-text-secondary); }
.shtbl .tbar { margin: 8px 0 6px; }
.shtbl .tbl { max-height: none; }
table.x.sk td { vertical-align: middle; }
table.x.sk td.rk { font-family: "Rubik", sans-serif; font-weight: 700; color: var(--color-text-secondary); width: 34px; }
table.x.sk tr.first td.rk { color: var(--color-primary); }
table.x td a.op, .fu a.op { color: var(--color-primary); font-weight: 600; cursor: pointer; text-decoration: none; }
table.x td a.op:hover { text-decoration: underline; }
table.x.sk td.tg { cursor: pointer; user-select: none; text-align: center; color: var(--color-primary); font-weight: 700; width: 26px; }
table.x.sk tr.ev > td { background: var(--color-bg-surface-secondary); padding: 4px 9px 10px 46px; white-space: normal; }
table.x.sk tr.ev[hidden] { display: none; }
table.x.sk tr.ev table.x { width: auto; min-width: 640px; }
table.x.sk tr.ev table.x th { position: static; cursor: default; }
table.x.sk tr.unat td { color: var(--color-text-secondary); font-style: italic; }
table.x tr.hl td { background: color-mix(in srgb, var(--status-warning) 22%, transparent) !important; transition: background .6s; }
.ib { display: inline-block; height: 8px; width: var(--w); max-width: 44px; background: var(--series-1); border-radius: 2px; margin-right: 6px; vertical-align: middle; opacity: .85; }
.ib.l { background: var(--series-2); }
.ibw { display: inline-block; width: 46px; text-align: left; }
table.x.sk { font-size: 12px; }
table.x.sk th, table.x.sk td { padding: 5px 7px; }
/* column dividers (user, 2026-10-30) */
table.x.sk > thead > tr > th + th, table.x.sk > tbody > tr > td + td { border-left: 1px solid var(--color-border-subtle); }
table.x.sk > thead > tr > th + th { border-left-color: color-mix(in srgb, var(--color-primary) 22%, transparent); }
.rb { display: inline-block; min-width: 26px; padding: 0 5px; margin-left: 5px; border-radius: 8px; font-size: 10px; font-weight: 700; line-height: 15px; text-align: center;
      font-variant-numeric: tabular-nums; background: var(--color-bg-surface-secondary); color: var(--color-text-secondary); border: 1px solid var(--color-border-subtle); }
.rb.top { background: #e6f6ee; color: #0f6b3a; border-color: #b7e3c9; }
.rb.low { background: #fdecec; color: #8a1f1f; border-color: #f3b4b4; }
[data-theme="dark"] .rb.top { background: #143526; color: #9fe0bb; border-color: #245c3d; }
[data-theme="dark"] .rb.low { background: #3a1d1d; color: #ffb3b3; border-color: #6b2b2b; }
.dlt { font-size: 10.5px; margin-left: 4px; color: var(--color-text-tertiary); white-space: nowrap; }
.dlt.up { color: #0f6b3a; } .dlt.dn { color: var(--status-critical); }
[data-theme="dark"] .dlt.up { color: #6fd39b; }
.okc { color: #0f6b3a; font-weight: 600; }
[data-theme="dark"] .okc { color: #6fd39b; }
.muted { color: var(--color-text-tertiary); }
.kpi .v .dlt { font-family: inherit; font-size: 11.5px; font-weight: 700; }
/* all-KPI view of the shift tables and the PDF (user, 2026-10-30: every KPI of the operator CSV) */
.shtbl .tbar label + label { margin-left: 10px; }
table.x.sk.all th.grp, table.x.sk.all th.sub { position: static; }
table.x.sk tr.med td { font-weight: 700; background: var(--color-bg-surface-secondary); border-top: 2px solid var(--color-border-subtle); }
table.skc.all { font-size: 6.5px; line-height: 1.2; table-layout: auto; }
table.skc.all th { font-size: 6px; padding: 2px 1.5px; letter-spacing: 0; text-transform: none; white-space: normal; vertical-align: bottom; line-height: 1.15; }
table.skc.all th.g { text-align: center; background: var(--skc-soft); color: var(--skc-head); border-left: 1px solid #fff; white-space: nowrap; }
table.skc.all td { padding: 1.3px 1.5px; white-space: nowrap; }
table.skc.all td.w { white-space: normal; max-width: 84px; }
table.skc.all td + td { border-left: 1px solid var(--skc-line); }
table.skc.all tr.med td { font-weight: 700; border-top: 1.5px solid var(--skc-head); background: var(--skc-soft); }
.skc-all { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0 14px; }
.skc-all table.skc { font-size: 8.4px; line-height: 1.2; }
.skc-all table.skc th { font-size: 7.4px; padding: 1.5px 4px; }
.skc-all table.skc td { padding: 1px 4px; vertical-align: middle; }
.skc-all table.skc td:first-child { color: var(--skc-muted); }
/* ---- operator card: one markup on screen (modal) and on paper (.sk-page) ---- */
.modal { position: fixed; inset: 0; z-index: 60; background: rgba(10, 16, 24, .5); display: flex; justify-content: center; align-items: flex-start; overflow: auto; padding: 22px 10px; }
.modal[hidden] { display: none; }
.mbox { background: var(--color-bg-surface); color: var(--color-text-primary); border-radius: 8px; box-shadow: var(--shadow-lg, var(--shadow-md)); width: min(860px, 96vw); padding: 12px 20px 20px;
        --skc-ink: var(--color-text-primary); --skc-muted: var(--color-text-secondary); --skc-line: var(--color-border-subtle); --skc-soft: var(--color-bg-surface-secondary);
        --skc-head: var(--color-primary-dark); --skc-bar: var(--series-1); --skc-bar2: var(--series-5); --skc-bar3: var(--series-4); --skc-bad: var(--status-critical); --skc-good: #0f6b3a; }
[data-theme="dark"] .mbox { --skc-head: var(--color-text-primary); --skc-th: var(--color-bg-selected); --skc-good: #6fd39b; }
.mbar { display: flex; gap: 8px; align-items: center; margin: 0 0 8px; padding-bottom: 8px; border-bottom: 1px solid var(--color-border-subtle); }
.mbar #mTitle { flex: 1; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--color-text-secondary); }
.sk-page { --skc-ink: #111; --skc-muted: #555; --skc-line: #dfe3e8; --skc-soft: #f1f4f7; --skc-head: #0b2d5b; --skc-bar: #2a78d6; --skc-bar2: #8a8f94; --skc-bar3: #eda100;
           --skc-bad: #b3261e; --skc-good: #0f6b3a;
           color: #111; font-size: 10px; line-height: 1.35; font-family: "Segoe UI", Roboto, Arial, sans-serif; break-after: page; page-break-after: always; }
.sk-page:last-child { break-after: auto; page-break-after: auto; }
.skc { color: var(--skc-ink); }
.skc-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; border-bottom: 2px solid var(--skc-head); padding-bottom: 6px; margin-bottom: 8px; }
.skc-head h2 { margin: 0; font-family: Rubik, "Segoe UI", Arial, sans-serif; font-size: 17px; letter-spacing: .4px; color: var(--skc-head); }
.skc-head .s { font-size: 10px; color: var(--skc-muted); letter-spacing: .4px; text-transform: uppercase; margin-top: 3px; }
.skc-head .s b { color: var(--skc-ink); }
.skc-head img { height: 34px; }
.skc-head .pill { font-size: 10px; vertical-align: 2px; margin-left: 6px; }
.skc-tiles { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; margin: 0 0 9px; }
.skc-tile { border: 1px solid var(--skc-line); border-left: 3px solid var(--skc-bar); border-radius: 4px; padding: 5px 7px; background: var(--skc-soft); min-width: 0; }
.skc-tile.bad { border-left-color: var(--skc-bad); }
.skc-tile.good { border-left-color: var(--skc-good); }
.skc-tile .k { font-size: 8.5px; font-weight: 700; letter-spacing: .6px; text-transform: uppercase; color: var(--skc-muted); }
.skc-tile .v { font-family: Rubik, "Segoe UI", Arial, sans-serif; font-size: 17px; font-weight: 700; line-height: 1.2; color: var(--skc-ink); white-space: nowrap; }
.skc-tile .v small { font-size: 10px; font-weight: 400; color: var(--skc-muted); margin-left: 2px; }
.skc-tile .s { font-size: 9px; color: var(--skc-muted); }
.skc-h { font-family: Rubik, "Segoe UI", Arial, sans-serif; font-size: 10.5px; font-weight: 700; letter-spacing: .8px; text-transform: uppercase; color: var(--skc-head);
         margin: 10px 0 5px; padding-bottom: 3px; border-bottom: 1px solid var(--skc-line); display: flex; justify-content: space-between; align-items: baseline; }
.skc-h small { font-weight: 400; letter-spacing: 0; text-transform: none; color: var(--skc-muted); font-size: 9.5px; }
.skc-bars { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 22px; }
.skc-bar .l { font-weight: 700; font-size: 10px; margin-bottom: 2px; }
.skc-bar .l small { font-weight: 400; color: var(--skc-muted); }
.skc-bar .r { display: grid; grid-template-columns: 74px 1fr 52px; gap: 6px; align-items: center; font-size: 9.5px; color: var(--skc-muted); height: 13px; }
.skc-bar .r .tr { height: 8px; background: var(--skc-soft); border-radius: 2px; overflow: hidden; }
.skc-bar .r .tr i { display: block; height: 100%; background: var(--skc-bar); border-radius: 2px; }
.skc-bar .r.f .tr i { background: var(--skc-bar2); }
.skc-bar .r.o .tr i { background: var(--skc-bar3); }
.skc-bar .r .v { text-align: right; font-variant-numeric: tabular-nums; color: var(--skc-ink); font-weight: 600; }
.skc-bar .r.me { color: var(--skc-ink); font-weight: 700; }
.skc-rank { display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 8px 0 0; padding: 5px 8px; background: var(--skc-soft); border-radius: 4px; font-size: 10px; }
.skc-rank .rb { margin-left: 3px; }
table.skc { width: 100%; border-collapse: collapse; font-size: 9.5px; }
table.skc th { text-align: left; background: var(--skc-th, var(--skc-head)); color: #fff; padding: 3px 5px; font-size: 8.5px; text-transform: uppercase; letter-spacing: .3px; font-weight: 700; }
table.skc td { padding: 2.5px 5px; border-bottom: 1px solid var(--skc-line); vertical-align: top; }
table.skc td.n, table.skc th.n { text-align: right; font-variant-numeric: tabular-nums; }
table.skc tr.steep td { background: color-mix(in srgb, var(--skc-bad) 9%, transparent); }
table.skc td.bad { color: var(--skc-bad); font-weight: 700; }
table.skc td.good { color: var(--skc-good); font-weight: 600; }
.skc-empty { color: var(--skc-muted); font-style: italic; padding: 3px 0; }
.skc-empty.good { color: var(--skc-good); font-style: normal; font-weight: 600; }
.skc-nok div { padding: 2px 0; border-bottom: 1px dotted var(--skc-line); font-size: 10px; }
.mbox .skc { font-size: 11px; }
.mbox .skc-nok div, .mbox .skc-follow div { font-size: 11px; }
.skc-nok .bad { color: var(--skc-bad); font-weight: 700; }
.skc-two { display: grid; grid-template-columns: 1fr 1fr; gap: 0 22px; }
.skc-reasons .r { display: grid; grid-template-columns: 1fr 90px 40px; gap: 6px; align-items: center; height: 14px; font-size: 9.5px; }
.skc-reasons .r span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.skc-reasons .tr { height: 7px; background: var(--skc-soft); border-radius: 2px; overflow: hidden; }
.skc-reasons .tr i { display: block; height: 100%; background: var(--skc-bar2); }
.skc-reasons .v { text-align: right; font-variant-numeric: tabular-nums; }
.skc-follow div { padding: 2px 0; border-bottom: 1px dotted var(--skc-line); }
.skc-sign { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin-top: 22px; }
.skc-sign div { border-top: 1px solid #333; padding-top: 3px; font-size: 9px; color: var(--skc-muted); }
.skc-foot { margin-top: 8px; font-size: 8.5px; color: var(--skc-muted); display: flex; justify-content: space-between; border-top: 1px solid var(--skc-line); padding-top: 4px; }
.mbox .skc-sign, .mbox .skc-foot { display: none; }
/* ---- bulk checklist PDF: one A4 portrait page per form (rendered only for printing) ---- */
#pdfForms { display: none; }
.pdfbar { border-top: 1px dashed var(--color-border-subtle); padding-top: 8px; margin-top: 2px; }
.pdfbar input[type=date] { font: inherit; font-size: 12.5px; padding: 3px 6px; border: 1px solid var(--color-border-strong); border-radius: 4px; background: var(--color-bg-surface); color: var(--color-text-primary); }
.cl-page { page-break-after: always; break-after: page; color: #111; font-size: 10.5px; line-height: 1.35; font-family: "Segoe UI", Roboto, Arial, sans-serif; }
.cl-page:last-child { page-break-after: auto; break-after: auto; }
.cl-head { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0b2d5b; padding-bottom: 6px; margin-bottom: 8px; }
.cl-head h2 { margin: 0; font-family: Rubik, "Segoe UI", Arial, sans-serif; font-size: 16px; letter-spacing: .6px; text-transform: uppercase; color: #0b2d5b; }
.cl-head .s { font-size: 9.5px; color: #555; letter-spacing: .4px; text-transform: uppercase; margin-top: 2px; }
.cl-head img { height: 34px; }
.cl-info { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 18px; margin-bottom: 6px; }
.cl-info div { display: flex; gap: 6px; border-bottom: 1px dotted #ccc; padding: 2px 0; min-height: 17px; }
.cl-info b { flex: 0 0 72px; color: #555; font-weight: 600; text-transform: uppercase; font-size: 9px; letter-spacing: .3px; padding-top: 2px; }
.cl-sum { display: flex; gap: 14px; margin: 6px 0; font-weight: 600; }
.cl-sum .bad { color: #b3261e; }
table.cl { width: 100%; border-collapse: collapse; font-size: 10px; }
table.cl th { text-align: left; background: #0b2d5b; color: #fff; padding: 3px 6px; font-size: 9.5px; text-transform: uppercase; letter-spacing: .3px; }
table.cl td { padding: 2.5px 6px; border-bottom: 1px solid #e3e6ea; vertical-align: top; }
table.cl td.n { width: 20px; color: #777; text-align: right; }
table.cl td.r { width: 56px; text-align: center; font-weight: 700; }
table.cl tr.sec td { background: #eef2f7; font-weight: 700; color: #0b2d5b; padding: 3px 6px; font-size: 9.5px; text-transform: uppercase; letter-spacing: .3px; }
table.cl tr.bad td { background: #fdecec; }
table.cl tr.bad td.r { color: #b3261e; }
table.cl tr.good td.r { color: #0f6b3a; }
.cl-sign { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin-top: 16px; }
.cl-sign div { border-top: 1px solid #333; padding-top: 3px; font-size: 9px; color: #555; }
.cl-foot { margin-top: 8px; font-size: 9px; color: #777; display: flex; justify-content: space-between; border-top: 1px solid #ccc; padding-top: 4px; }
@media print {
  @page { size: A4 landscape; margin: 10mm; }
  body.print-forms .sheet, body.print-forms #tip { display: none !important; }
  body.print-forms #pdfForms { display: block; }
  body.print-forms table.cl tr, body.print-forms .cl-info, body.print-forms .cl-sign { break-inside: avoid; }
  body.print-shift .sheet, body.print-shift #tip { display: none !important; }
  body.print-shift #pdfForms { display: block; }
  #opModal { display: none !important; }
  #pdfForms { width: 100%; }
  .sk-page { width: auto; max-width: 186mm; margin: 0 auto; }   /* centred whatever margins the print dialog uses */
  .sk-page.sk-wide { page: wide; max-width: none; padding-left: 9mm; padding-right: 9mm; }   /* all-KPI tables on A4 landscape pages, own side margins */
  /* own breathing room: the print dialog's "Minimum" margins remove the page's top/bottom space */
  .sk-page { padding: 7mm 0 5mm; box-sizing: border-box; }
  .sk-page .skc-head { padding-bottom: 9px; margin-bottom: 12px; }
  .sk-page .skc-head h2 { font-size: 19px; line-height: 1.25; }
  .sk-page .skc-head .s { margin-top: 5px; line-height: 1.4; }
  .sk-page .skc-head img { height: 38px; }
  .sk-page .skc-tiles { margin-bottom: 12px; gap: 8px; }
  .sk-page .skc-tile { padding: 7px 9px; }
  .sk-page .skc-h { margin: 14px 0 7px; padding-bottom: 4px; }
  .sk-page .skc-rank { margin-top: 10px; padding: 7px 10px; }
  .sk-page .skc-sign { margin-top: 30px; }
  .sk-page .skc-sign div { padding-top: 5px; font-size: 9.5px; }
  .sk-page .skc-foot { margin-top: 12px; padding-top: 6px; font-size: 9px; line-height: 1.4; gap: 14px; }
  /* checklist PDF: same page frame as the shift KPI pages (user, 2026-10-30: "checklist export has no padding") */
  .cl-page { width: auto; max-width: 186mm; margin: 0 auto; padding: 6mm 0 4mm; box-sizing: border-box; }
  .cl-page .cl-head { padding-bottom: 9px; margin-bottom: 12px; }
  .cl-page .cl-head img { height: 38px; }
  .cl-page .cl-sign { margin-top: 18px; }
  .cl-page .cl-foot { margin-top: 12px; padding-top: 6px; line-height: 1.4; gap: 14px; }
  .skc-head, .skc-tiles, .skc-bars, .skc-rank, .skc-nok, .skc-reasons, .skc-sign, .skc-two, .skc-follow, .skc-blk { break-inside: avoid; }
  .skc-h { break-after: avoid; }
  table.skc thead { display: table-header-group; }
  table.skc tr { break-inside: avoid; }
  .sk-op table.skc { break-inside: avoid; }
  body { background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; font-size: 11.5px; }
  nav.toc, .controls, .btns, .quick, .pager, #tip, .note, .tbar .btn, .tbar label { display: none !important; }
  .sheet { width: 100%; max-width: none; margin: 0; box-shadow: none; border: none; padding: 0 4mm; }
  .titleblock { padding-top: 4mm; }
  .kpis { grid-template-columns: repeat(4, 1fr); }
  .grid { grid-template-columns: repeat(2, 1fr); }
  .chart, .kpi { break-inside: avoid; }
  .banner { break-after: avoid; break-inside: avoid; }
  .tbl { max-height: none; overflow: visible; border: none; }
  table.x thead { display: table-header-group; }
  table.x tr { break-inside: avoid; }
  table.x th { position: static; }
  table.x { font-size: 10px; white-space: normal; }
}
"""

HTML = r"""
<div class="sheet">
  <div class="titleblock">
    <img src="data:image/png;base64,__LOGO__" alt="Erdene">
    <div class="tb">
      <h1>Operator KPI &mdash; haul &amp; loading operators</h1>
      <div class="sub">Bayankhundii gold mine &middot; C4M fleet management &middot; pre-start checklists &middot; production &middot; time use</div>
      <div class="chips" id="chips"></div>
    </div>
    <div class="right">
      <div class="period"><b>Shift dates:</b> <input type="date" id="fFrom"> &rarr; <input type="date" id="fTo">
        <b>Shift:</b> <select id="fShift"><option value="">Both</option><option>DS</option><option>NS</option></select></div>
      <div class="meta" style="margin-top:4px">shift day = 07:00 &rarr; 07:00 &middot; DS 07&ndash;19 &middot; NS 19&ndash;07 &middot; checklists dated from 06:20</div>
      <div class="quick" id="quick"><button class="btn sm" data-range="7">Last 7 days</button><button class="btn sm" data-range="30">Last 30 days</button><button class="btn sm" data-range="all">All since 1 Jul</button></div>
      <div class="btns"><button class="btn" id="refreshBtn" hidden title="Pull the newest shift days from C4M now (the same job the nightly cron runs; one run at a time)">&#8635; Refresh data</button><button class="btn" id="themeBtn">&#9681; Theme</button><button class="btn primary" id="pdfBtn" title="Print the report to PDF (use 'Save as PDF' as the printer)">&#10515; Export PDF</button></div>
      <div id="refreshMsg"></div>
    </div>
  </div>

  <nav class="toc" id="toc">
    <a href="#secShift">Shift sheet</a><a href="#secOverview">Overview</a><a href="#secTrend">Trends</a>
    <span class="spring"></span><span class="hint">daily PDFs: shift KPIs &middot; checklists</span>
  </nav>

  <div class="banner" id="secShift">Shift sheet <small id="shSub"></small></div>
  <div class="controls shiftctl" id="shiftCtl">
    <button class="btn sm" id="sPrev" title="Previous shift day">&lsaquo;</button>
    <label><b>Shift date</b> <input type="date" id="pdfDate"></label>
    <button class="btn sm" id="sNext" title="Next shift day">&rsaquo;</button>
    <label><b>Shift</b> <select id="pdfShift"><option value="">Both</option><option>DS</option><option>NS</option></select></label>
    <label><b>Crew</b> <select id="pdfCrew"><option value="">All</option></select></label>
    <button class="btn sm" id="sLast" title="The last shift day that has finished (07:00 to 07:00)">Last complete shift day</button>
    <span class="chip warn" id="sRunning" hidden>shift day still running &middot; partial</span>
    <span class="spring"></span>
    <button class="btn primary" id="shiftPdfBtn" title="One summary page per shift, then one A4 page per operator, merged into a single PDF (choose &ldquo;Save as PDF&rdquo; as the printer)">&#8681; Export shift KPIs (PDF)</button>
    <button class="btn" id="pdfFormsBtn" title="One A4 page per checklist of the selected shift date, merged into a single PDF">&#8681; Export checklists (PDF)</button>
  </div>
  <div class="kpis" id="shKpis"></div>
  <div class="chart wide shtbl"><h4>Truck operators <small id="shTruckN"></small></h4>
    <div class="tbar"><div class="n">ranked within the shift &middot; badges = rank in cycles per productive hour (from 2 productive h), productive time, checklist and over-speed &middot; &Delta; = against the operator&rsquo;s own previous 30 shift days &middot; click a name for the operator card</div>
      <label>Rank by <select id="sRankBy"></select></label>
      <label>Columns <select id="sView"><option value="">Headline KPIs</option><option value="all">All KPIs (as in the CSV)</option></select></label></div>
    <div class="tbl"><table class="x sk" id="tblTrucks"><thead></thead><tbody></tbody></table></div></div>
  <div class="chart wide shtbl" style="margin-top:12px"><h4>Loader operators <small id="shLoadN"></small></h4>
    <div class="tbl"><table class="x sk" id="tblLoaders"><thead></thead><tbody></tbody></table></div></div>
  <div class="lead" style="margin-top:22px">Period analysis &mdash; the shift dates at the top and the filters below apply to sections 02&ndash;04.</div>


  <div class="controls">
    <label><b>Role</b> <select id="fRole"><option value="">All operators</option><option value="haul">Truck operators</option><option value="load">Excavator / loader operators</option></select></label>
    <label><b>Fleet</b> <select id="fModel"><option value="">All</option></select></label>
    <label><b>Crew</b> <select id="fCrew"><option value="">All</option></select></label>
    <label><b>Operator</b> <select id="fOp"><option value="">All</option></select></label>
    <span class="sep">|</span>
    <label><b>Min shifts</b> <input type="number" id="fMin" min="1" step="1" value="2"></label>
    <label><input type="search" id="fQ" placeholder="search operator, crew, equipment&hellip;"></label>
    <button class="btn" id="resetBtn">Reset</button>
  </div>

  <div class="banner" id="secOverview">Overview <small id="ovsub"></small></div>
  <div class="kpis" id="kpis"></div>

  <div class="banner" id="secTrend">Trends <small>per shift day</small></div>
  <div class="grid">
    <div class="chart wide"><h4>Cycles per productive hour &middot; truck operators</h4><div class="legend"><span style="--c:var(--series-1)">cycles / productive h</span></div><div id="cTrendRate"></div></div>
    <div class="chart"><h4>Productive time share</h4><div class="legend"><span style="--c:var(--series-1)">Truck operators</span><span style="--c:var(--series-2)">Loader operators</span></div><div id="cTrendProd"></div></div>
    <div class="chart" id="cTrendOsBox"><h4>Over-speed events</h4><div class="legend"><span style="--c:var(--status-critical)">events per shift day (trucks)</span></div><div id="cTrendOs"></div></div>
    <div class="chart"><h4>Checklist compliance</h4><div class="legend"><span style="--c:var(--series-3)">forms filed / equipment-shifts worked</span></div><div id="cTrendChk"></div></div>
  </div>

  <div class="foot" id="foot"></div>
</div>
<div id="tip"></div>
<div id="opModal" class="modal" hidden><div class="mbox" role="dialog" aria-modal="true"><div class="mbar"><span id="mTitle"></span>
  <button class="btn sm" id="mPrint" title="This card as one A4 page (choose &ldquo;Save as PDF&rdquo; as the printer)">&#8681; Print this card (PDF)</button><button class="btn sm" id="mClose">Close &times;</button></div><div id="mCard"></div></div></div>
<div id="pdfForms"></div>
"""

JS = r"""
const D = __DATA__;
const M = D.meta;
function decode(t) {
  if (!t) return [];
  const n = t.data[t.cols[0]].length, out = new Array(n);
  for (let i = 0; i < n; i++) { const o = {}; for (const c of t.cols) { const v = t.data[c][i]; o[c] = (t.dict[c] && v != null) ? t.dict[c][v] : v; } out[i] = o; }
  return out;
}
const OPS = decode(D.ops), REASONS = decode(D.reasons), FORMS = decode(D.forms), DIM = decode(D.dimItems);
FORMS.forEach((f, i) => { f.ids = D.items.ids[i] || []; f.nok = D.items.nok[i] || []; });
const ITEM = Object.fromEntries(DIM.map(d => [d.item_id, d]));
const DEFAULT_DAYS = 30;
const $ = s => document.querySelector(s);
const fmt = (n, d=0) => n == null || isNaN(n) ? '–' : Number(n).toLocaleString('en-US', {maximumFractionDigits: d, minimumFractionDigits: d});
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const uniq = a => [...new Set(a.filter(v => v != null && v !== ''))].sort((x, y) => String(x).localeCompare(String(y)));
const sum = a => a.reduce((s, v) => s + (+v || 0), 0);
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const pct = (a, b) => b > 0 ? a / b * 100 : null;
const QP = new URLSearchParams(location.search);
if (QP.get('embed')) document.documentElement.classList.add('embed');

/* ---- theme ------------------------------------------------------------ */
(function () {
  let t = QP.get('theme');
  if (!t) { try { t = localStorage.getItem('ok_theme'); } catch (e) {} }
  if (!t && matchMedia('(prefers-color-scheme: dark)').matches) t = 'dark';
  if (t === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  $('#themeBtn').onclick = () => {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (dark) document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', 'dark');
    try { localStorage.setItem('ok_theme', dark ? 'light' : 'dark'); } catch (e) {}
    render(); renderShift();
  };
})();

/* ---- filters ----------------------------------------------------------- */
const F = {};
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
  let hit = null;
  for (const b of document.querySelectorAll('#quick button')) if (!hit && to === M.date_to && from === rangeFrom(b.dataset.range)) hit = b;
  document.querySelectorAll('#quick button').forEach(b => b.classList.toggle('on', b === hit));
}
function initFilters() {
  setRange(DEFAULT_DAYS);
  $('#fFrom').min = $('#fTo').min = M.date_from; $('#fFrom').max = $('#fTo').max = M.date_to;
  document.querySelectorAll('#quick button').forEach(b => b.onclick = () => { setRange(b.dataset.range); page = 1; fpage = 1; render(); });
  fillSel('#fModel', uniq(OPS.map(r => r.model)));
  fillSel('#fCrew', uniq(OPS.map(r => r.crew).concat(FORMS.map(f => f.crew))));
  fillSel('#fOp', uniq(OPS.map(r => r.operator).concat(FORMS.map(f => f.operator))));
  document.querySelectorAll('.controls:not(.shiftctl) input, .controls:not(.shiftctl) select, .period input, .period select').forEach(el => el.addEventListener('input', () => { page = 1; fpage = 1; render(); }));
  $('#resetBtn').onclick = () => { document.querySelectorAll('.controls:not(.shiftctl) select, .period select').forEach(s => s.value = ''); $('#fMin').value = 2; $('#fQ').value = ''; setRange(DEFAULT_DAYS); page = 1; fpage = 1; render(); };
  $('#pdfBtn').onclick = () => window.print();
  addEventListener('beforeprint', () => { if (pdfMode) return; printMode = true; render(); });
  addEventListener('afterprint', () => { if (pdfMode === 'forms') { endFormsPrint(); return; } if (pdfMode === 'shift') { endShiftPrint(); return; } printMode = false; render(); });
}
function readFilters() {
  F.from = $('#fFrom').value || M.date_from; F.to = $('#fTo').value || M.date_to;
  if (F.from > F.to) { F.from = F.to; $('#fFrom').value = F.to; }
  markQuick();
  F.shift = $('#fShift').value; F.role = $('#fRole').value; F.model = $('#fModel').value; F.crew = $('#fCrew').value; F.op = $('#fOp').value;
  F.min = Math.max(1, +$('#fMin').value || 1); F.q = $('#fQ').value.trim().toLowerCase();
}
function passRow(r) {
  if (r.shift_date < F.from || r.shift_date > F.to) return false;
  if (F.shift && r.shift !== F.shift) return false;
  if (F.role && r.role !== F.role) return false;
  if (F.model && r.model !== F.model) return false;
  if (F.crew && r.crew !== F.crew) return false;
  if (F.op && r.operator !== F.op) return false;
  return true;
}
function passForm(f) {
  if (f.shift_date < F.from || f.shift_date > F.to) return false;
  if (F.shift && f.shift !== F.shift) return false;
  return passFormCtl(f);
}
function passFormCtl(f, skipCrew) {  // the control-bar filters only (no period / shift)
  if (F.role && f.role !== F.role) return false;
  if (F.model && f.model !== F.model) return false;
  if (F.crew && !skipCrew && f.crew !== F.crew) return false;
  if (F.op && f.operator !== F.op) return false;
  if (F.q) { const h = [f.equipment, f.operator, f.crew, f.form_status, f.review_comment].join(' ').toLowerCase(); if (!h.includes(F.q)) return false; }
  return true;
}

/* ---- aggregation: ops rows -> one object per operator ------------------- */
const SUMS = ['loads','tonnes','n_queue','s_queue','n_spot','s_spot','n_load','s_load','n_haul','s_haul','n_atdump','s_atdump','n_dump','s_dump','n_empty','s_empty',
  'loads_ld','tonnes_ld','n_ldg','s_ldg','n_hang','s_hang','h_prod','h_ready_other','h_delay','h_standby','h_maint','h_oop','h_unknown','min_shiftchange',
  'forms','forms_rej','forms_pend','items','items_nok','os_n','os_s','os_steep'];
const worked = r => (r.h_prod + r.h_ready_other + r.h_delay + r.h_standby + r.h_maint) >= 0.5 || (r.loads || 0) >= 1 || (r.loads_ld || 0) >= 1;
function newAgg(key) { const o = {key, shifts: new Set(), eqShifts: new Set(), eqs: new Set(), hHaul: 0, hLoad: 0, hAux: 0, trucks: 0, os_max: 0}; SUMS.forEach(k => o[k] = 0); return o; }
function addRow(o, r) {
  SUMS.forEach(k => { if (r[k] != null) o[k] += +r[k]; });
  if (worked(r)) { o.shifts.add(r.shift_date + '|' + r.shift); o.eqShifts.add(r.shift_date + '|' + r.shift + '|' + r.id_equipo); o.eqs.add(r.equipment); }
  const h = r.h_prod + r.h_ready_other + r.h_delay + r.h_standby + r.h_maint;
  if (r.role === 'haul') o.hHaul += h; else if (r.role === 'load') o.hLoad += h; else o.hAux += h;
  if (r.trucks_served) o.trucks = Math.max(o.trucks, r.trucks_served);
  if (r.os_max != null) o.os_max = Math.max(o.os_max, r.os_max);
}
function finish(o) {
  o.shifts_worked = o.shifts.size; o.eq_shifts = o.eqShifts.size; o.equipment_used = [...o.eqs].sort().join(' ');
  o.hours_logged = o.h_prod + o.h_ready_other + o.h_delay + o.h_standby + o.h_maint;
  o.productive_pct = pct(o.h_prod, o.hours_logged);
  o.role = o.hHaul >= o.hLoad && o.hHaul >= o.hAux ? 'haul' : o.hLoad >= o.hAux ? 'load' : 'aux';
  if (!o.hours_logged) o.role = o.loads ? 'haul' : o.loads_ld ? 'load' : o.os_n ? 'haul' : 'aux';
  o.loads_per_prod_h = o.h_prod ? o.loads / o.h_prod : null;
  o.tonnes_per_prod_h = o.h_prod ? o.tonnes / o.h_prod : null;
  o.loads_ld_per_prod_h = o.h_prod ? o.loads_ld / o.h_prod : null;
  const avg = (s, n) => o[n] ? o[s] / o[n] : null;
  o.avg_queue_s = avg('s_queue', 'n_queue'); o.avg_spot_s = avg('s_spot', 'n_spot'); o.avg_load_s = avg('s_load', 'n_load'); o.avg_haul_s = avg('s_haul', 'n_haul');
  o.avg_at_dump_s = avg('s_atdump', 'n_atdump'); o.avg_dump_s = avg('s_dump', 'n_dump'); o.avg_travel_empty_s = avg('s_empty', 'n_empty');
  o.avg_cycle_s = ['avg_queue_s','avg_spot_s','avg_load_s','avg_haul_s','avg_at_dump_s','avg_dump_s','avg_travel_empty_s'].every(k => o[k] != null) ? sum(['avg_queue_s','avg_spot_s','avg_load_s','avg_haul_s','avg_at_dump_s','avg_dump_s','avg_travel_empty_s'].map(k => o[k])) : null;
  o.avg_loading_s = avg('s_ldg', 'n_ldg'); o.avg_hang_s = avg('s_hang', 'n_hang');
  o.checklist_compliance_pct = o.eq_shifts ? Math.min(100, o.forms / o.eq_shifts * 100) : null;
  o.items_not_ok_pct = pct(o.items_nok, o.items);
  o.shift_change_min_per_shift = o.shifts_worked ? o.min_shiftchange / o.shifts_worked : null;
  o.os_per100h = D.hasOverspeed && o.role === 'haul' && o.hours_logged ? o.os_n / o.hours_logged * 100 : null;
  o.os_rank_v = D.hasOverspeed && o.role === 'haul' ? o.os_n * 1000 + o.os_max : null;   // fewest events first, then the mildest worst
  o.missing = o.role === 'aux' ? 0 : Math.max(0, o.eq_shifts - o.forms);
  o.rate_r = o.h_prod >= RATE_MIN_PROD_H ? (o.role === 'load' ? o.loads_ld_per_prod_h : o.loads_per_prod_h) : null;   // ranked only with enough productive time
  return o;
}
const RATE_MIN_PROD_H = 2;      // cycles per productive hour is ranked only from 2 productive hours (a 1 h shift gives noise)
function aggregate(rows, keyOf) {
  const m = new Map();
  rows.forEach(r => { const k = keyOf(r); if (!m.has(k)) m.set(k, newAgg(k)); addRow(m.get(k), r); });
  return [...m.values()].map(finish);
}

/* ---- tooltip / SVG helpers --------------------------------------------- */
const tip = $('#tip');
function hover(el, text) {
  el.addEventListener('mousemove', e => { tip.style.display = 'block'; tip.textContent = typeof text === 'function' ? text() : text; const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(e.clientX + 14, innerWidth - w - 8) + 'px'; tip.style.top = Math.min(e.clientY + 14, innerHeight - h - 8) + 'px'; });
  el.addEventListener('mouseleave', () => tip.style.display = 'none');
}
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function text(parent, x, y, s, attrs={}) { const t = el('text', Object.assign({x, y}, attrs), parent); t.textContent = s; return t; }
function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); const n = v / p; const m = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10; return m * p; }
function empty(box, msg='Nothing in the selected period.') { box.innerHTML = `<div class="empty">${msg}</div>`; }
function barChart(box, cats, series, opts={}) {
  box.innerHTML = '';
  if (!cats.length || !series.some(s => sum(s.values) > 0)) return empty(box, opts.emptyMsg);
  const W = 640, H = opts.h || 230, ml = 44, mr = 10, mt = 12, mb = 42;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, class: 'cv'}, box);
  const tot = cats.map((_, i) => opts.stacked ? sum(series.map(s => s.values[i])) : Math.max(...series.map(s => s.values[i])));
  const ymax = opts.ymax || niceMax(Math.max(...tot) * 1.08);
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
    hover(hit, `${opts.catLabel ? opts.catLabel(c) : c}\n` + series.map(s => `${s.name}: ${fmt(s.values[i], opts.dec || 0)}${opts.unit || ''}`).join('\n'));
    if (tot[i] && cats.length <= 16) text(svg, x0 + inner / 2, y(tot[i]) - 4, fmt(tot[i], opts.dec || 0), {'text-anchor': 'middle', class: 'dl'});
    if (i % step === 0) text(svg, x0 + inner / 2, H - mb + 16, opts.short ? opts.short(c) : c, {'text-anchor': 'middle'});
  });
  if (opts.xLabel) text(svg, ml + pw / 2, H - 6, opts.xLabel, {'text-anchor': 'middle'});
}
function hbarChart(box, items, color, opts={}) {
  box.innerHTML = '';
  if (!items.length) return empty(box, opts.emptyMsg);
  const top = items.slice(0, opts.top || 12);
  const W = 640, rh = 24, ml = Math.min(260, Math.max(60, Math.max(...top.map(i => i.label.length)) * 6.4 + 14)), mr = 52, mt = 6, mb = 6;
  const H = mt + mb + rh * top.length;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, class: 'cv'}, box);
  const vmax = Math.max(...top.map(i => i.value)) || 1, pw = W - ml - mr;
  top.forEach((it, i) => {
    const yy = mt + i * rh, w = Math.max(2, it.value / vmax * pw);
    text(svg, ml - 8, yy + rh / 2 + 4, it.label.length > 38 ? it.label.slice(0, 37) + '…' : it.label, {'text-anchor': 'end'});
    el('rect', {x: ml, y: yy + 5, width: w, height: rh - 10, fill: it.color || color, rx: 3, class: 'bar'}, svg);
    text(svg, ml + w + 5, yy + rh / 2 + 4, fmt(it.value, opts.dec || 0) + (opts.unit || ''), {class: 'dl'});
    const hit = el('rect', {x: 0, y: yy, width: W, height: rh, class: 'hit'}, svg);
    hover(hit, it.tip || `${it.label}: ${fmt(it.value, opts.dec || 0)}${opts.unit || ''}`);
  });
}
function lineChart(box, cats, series, opts={}) {
  box.innerHTML = '';
  if (!cats.length || !series.some(s => s.values.some(v => v > 0))) return empty(box);
  const W = opts.w || 640, H = 230, ml = 48, mr = 14, mt = 12, mb = 40;
  const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, class: 'cv'}, box);
  const ymax = opts.ymax || niceMax(Math.max(...series.flatMap(s => s.values.filter(v => v != null))) * 1.08);
  const pw = W - ml - mr, ph = H - mt - mb;
  const x = i => ml + (cats.length === 1 ? pw / 2 : i / (cats.length - 1) * pw), y = v => mt + ph - v / ymax * ph;
  const g = el('g', {class: 'grid'}, svg);
  for (let i = 0; i <= 4; i++) { const v = ymax * i / 4; el('line', {x1: ml, x2: W - mr, y1: y(v), y2: y(v)}, g); text(svg, ml - 6, y(v) + 3.5, fmt(v, opts.dec || 0), {'text-anchor': 'end'}); }
  series.forEach(s => {
    let d = '', pen = false;
    s.values.forEach((v, i) => { if (v == null) { pen = false; return; } d += (pen ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1) + ' '; pen = true; });
    el('path', {d, fill: 'none', stroke: s.color, 'stroke-width': 2, 'stroke-linejoin': 'round'}, svg);
    s.values.forEach((v, i) => { if (v != null) el('circle', {cx: x(i), cy: y(v), r: 3, fill: s.color, stroke: css('--color-bg-surface'), 'stroke-width': 1.5}, svg); });
  });
  if (opts.ref != null) { el('line', {x1: ml, x2: W - mr, y1: y(opts.ref), y2: y(opts.ref), class: 'ref'}, svg); }
  const step = Math.ceil(cats.length / 14);
  cats.forEach((c, i) => {
    if (i % step === 0) text(svg, x(i), H - mb + 16, c.slice(5), {'text-anchor': 'middle'});
    const w = pw / Math.max(1, cats.length - 1);
    const hit = el('rect', {x: x(i) - w / 2, y: mt, width: w, height: ph, class: 'hit'}, svg);
    hover(hit, `${c}\n` + series.map(s => `${s.name}: ${fmt(s.values[i], opts.dec == null ? 1 : opts.dec)}${opts.unit || ''}`).join('\n'));
  });
  text(svg, ml + pw / 2, H - 6, opts.xLabel || 'shift date', {'text-anchor': 'middle'});
}
function spark(vals) {
  if (!vals.length || !vals.some(v => v > 0)) return '';
  const W = 84, H = 28, mx = Math.max(...vals) || 1;
  const pts = vals.map((v, i) => [(vals.length === 1 ? W / 2 : i / (vals.length - 1) * (W - 2) + 1), H - 2 - (v || 0) / mx * (H - 6)]);
  const line = pts.map(p => p.map(n => n.toFixed(1)).join(',')).join(' ');
  return `<svg class="spark" viewBox="0 0 ${W} ${H}"><polygon class="area" points="${pts[0][0]},${H} ${line} ${pts[pts.length - 1][0]},${H}"/><polyline points="${line}"/></svg>`;
}

/* ---- CSV ------------------------------------------------------------------ */
function csvDownload(name, header, rows) {
  const cell = v => { if (v == null) v = ''; if (typeof v === 'boolean') v = v ? 1 : 0; if (typeof v === 'number') v = Number.isInteger(v) ? String(v) : v.toFixed(2); v = String(v); return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  const lines = [header.map(cell).join(',')];
  for (const r of rows) lines.push(r.map(cell).join(','));
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['﻿' + lines.join('\r\n')], {type: 'text/csv;charset=utf-8'}));
  a.download = `${name}_${F.from}_${F.to}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

/* ---- ranking table ---------------------------------------------------------- */
const RANKS = [['tonnes', 'Nominal tonnes hauled'], ['loads', 'Cycles hauled'], ['loads_per_prod_h', 'Cycles per productive hour'], ['loads_ld', 'Cycles loaded (loaders)'],
  ['productive_pct', 'Productive %'], ['hours_logged', 'Hours logged'], ['shifts_worked', 'Shifts worked'], ['checklist_compliance_pct', 'Checklist compliance %'],
  ['items_not_ok_pct', 'Items NOT OK %'], ['avg_cycle_s', 'Avg cycle time'], ['os_n', 'Over-speed events'], ['os_per100h', 'Over-speed per 100 h'], ['os_max', 'Worst over-speed']];
const LOWER_BETTER = new Set(['items_not_ok_pct', 'avg_cycle_s', 'avg_queue_s', 'avg_spot_s', 'avg_load_s', 'avg_haul_s', 'avg_at_dump_s', 'avg_dump_s', 'avg_travel_empty_s', 'avg_hang_s', 'avg_loading_s',
  'os_n', 'os_s', 'os_max', 'os_steep', 'os_per100h', 'h_delay', 'h_standby', 'shift_change_min_per_shift', 'items_nok', 'forms_rej', 'forms_pend']);
const BADGE = {loads_per_prod_h: ['rate', 'haul'], loads_ld_per_prod_h: ['rate', 'load'], productive_pct: ['prod'], checklist_compliance_pct: ['chk'], os_n: ['os', 'haul']};
const COLS = [
  ['rank', '#', 'rank', 'id'], ['operator', 'Operator', 'op', 'id'], ['crew', 'Crew', 'txt', 'id'], ['role', 'Role', 'role', 'id'], ['equipment_used', 'Equipment', 'txt', 'id'],
  ['shifts_worked', 'Shifts', 'num', 'time'], ['hours_logged', 'Hours', 'num1', 'time'], ['h_prod', 'Productive h', 'num1', 'time'], ['productive_pct', 'Prod %', 'pct', 'time'],
  ['h_delay', 'Delay h', 'num1', 'time'], ['h_standby', 'Standby h', 'num1', 'time'], ['h_ready_other', 'Breaks h', 'num1', 'time'], ['h_maint', 'Maint h', 'num1', 'time'], ['shift_change_min_per_shift', 'Shift-change min', 'num', 'time'],
  ['loads', 'Cycles', 'num', 'haul'], ['tonnes', 'Nominal t', 'num', 'haul'], ['loads_per_prod_h', 'Cycles/prod h', 'num1', 'haul'], ['tonnes_per_prod_h', 't/prod h', 'num', 'haul'],
  ['avg_queue_s', 'Queue s', 'num', 'haul'], ['avg_spot_s', 'Spot s', 'num', 'haul'], ['avg_load_s', 'Loading s', 'num', 'haul'], ['avg_haul_s', 'Haul s', 'num', 'haul'], ['avg_at_dump_s', 'At dump s', 'num', 'haul'], ['avg_dump_s', 'Dump s', 'num', 'haul'], ['avg_travel_empty_s', 'Empty s', 'num', 'haul'], ['avg_cycle_s', 'Cycle s', 'num', 'haul'],
  ['loads_ld', 'Cycles loaded', 'num', 'load'], ['tonnes_ld', 'Nominal t', 'num', 'load'], ['loads_ld_per_prod_h', 'Cycles/prod h', 'num1', 'load'], ['avg_loading_s', 'Loading s', 'num', 'load'], ['avg_hang_s', 'Hang s', 'num', 'load'], ['trucks', 'Trucks served', 'num', 'load'],
  ['forms', 'Forms', 'num', 'chk'], ['checklist_compliance_pct', 'Compliance %', 'pct', 'chk'], ['items', 'Items', 'num', 'chk'], ['items_nok', 'NOT OK', 'num', 'chk'], ['items_not_ok_pct', 'NOT OK %', 'pct', 'chk'], ['forms_rej', 'Rejected', 'num', 'chk'], ['forms_pend', 'Not reviewed', 'num', 'chk'],
  ['os_n', 'Over-speed', 'num', 'safe'], ['os_max', 'Worst +km/h', 'num1', 'safe'], ['os_steep', 'Steep', 'num', 'safe'], ['os_per100h', 'Per 100 h', 'num1', 'safe'], ['os_s', 'Over-speed s', 'num', 'safe']];
const GROUPS = {id: 'Operator', time: 'Time use', haul: 'Truck operator', load: 'Loader operator', chk: 'Pre-start checklists', safe: 'Safety'};
let page = 1, fpage = 1, sortKey = 'tonnes', sortDesc = true, fsortKey = 'created_ts', fsortDesc = true, printMode = false;
function visibleCols() {
  return COLS.filter(c => {
    if (c[3] === 'safe' && !D.hasOverspeed) return false;
    if (c[3] === 'haul' && F.role === 'load') return false;
    if (c[3] === 'load' && F.role === 'haul') return false;
    return true;
  });
}
function cellHtml(c, v, r) {
  const b = BADGE[c[0]], badge = b && r && r.rk && (!b[1] || b[1] === r.role) ? rb(r.rk[b[0]]) : '';
  if (c[2] === 'rank') return `<td class="num rk">${v == null ? '–' : v}</td>`;
  if (c[2] === 'op') return `<td><a class="op" data-id="${r.key}" data-scope="period">${esc(v)}</a></td>`;
  if (c[2] === 'num') return `<td class="num">${fmt(v, 0)}${badge}</td>`;
  if (c[2] === 'num1') return `<td class="num">${fmt(v, 1)}${badge}</td>`;
  if (c[2] === 'pct') return `<td class="num">${v == null ? '–' : fmt(v, 0) + ' %'}${badge}</td>`;
  if (c[2] === 'role') return `<td><span class="pill ${v}">${v === 'haul' ? 'Truck' : v === 'load' ? 'Loader' : 'Aux'}</span></td>`;
  return `<td>${esc(v)}</td>`;
}
/* the period ranking table and its operator CSV were removed with section 03 (user, 2026-10-30) */

const itemName = id => (ITEM[id] ? ITEM[id].item : `#${id}`);

/* ---- bulk checklist PDF: one A4 portrait page per form, merged by the browser's print-to-PDF ---- */
const ORD = Object.fromEntries(DIM.map((d, i) => [d.item_id, i]));
const TITLE0 = document.title, LOGO_SRC = ($('.titleblock img') || {}).src || '';
let pdfMode = null;      // null | 'forms' (checklist PDF) | 'shift' (shift KPI PDF); both use #pdfForms
function pdfSel() {
  const date = $('#pdfDate').value, sh = $('#pdfShift').value, crew = $('#pdfCrew').value;
  return FORMS.filter(f => f.shift_date === date && (!sh || f.shift === sh) && (!crew || f.crew === crew))   // the shift-sheet selection only
    .sort((a, b) => (a.shift + '|' + a.equipment + '|' + a.created_ts).localeCompare(b.shift + '|' + b.equipment + '|' + b.created_ts));
}
function updatePdfBtn() {
  const n = pdfSel().length, b = $('#pdfFormsBtn');
  b.disabled = !n; b.innerHTML = `&#8681; Export ${fmt(n)} checklist${n === 1 ? '' : 's'} (PDF)`;
}
function clPage(f, i, n) {
  const ids = f.ids.slice().sort((a, b) => ((ORD[a] ?? 1e9) - (ORD[b] ?? 1e9)) || a - b), nok = new Set(f.nok);
  let sec = null, k = 0; const rows = [];
  ids.forEach(id => {
    const d = ITEM[id] || {}, s = d.section || '';
    if (s !== sec) { sec = s; if (s) rows.push(`<tr class="sec"><td colspan="3">${esc(s)}</td></tr>`); }
    const bad = nok.has(id);
    rows.push(`<tr class="${bad ? 'bad' : 'good'}"><td class="n">${++k}</td><td>${esc(d.item || '#' + id)}</td><td class="r">${bad ? 'NOT OK' : 'OK'}</td></tr>`);
  });
  const tpl = f.description || (ITEM[ids[0]] || {}).template || '';
  const shiftTxt = f.shift === 'DS' ? 'day shift (07–19)' : f.shift === 'NS' ? 'night shift (19–07)' : f.shift;
  return `<div class="cl-page">
  <div class="cl-head"><div><h2>Pre-start checklist</h2><div class="s">Bayankhundii gold mine · C4M fleet management · form #${f.id_checklist}</div></div><img src="${LOGO_SRC}" alt="Erdene"></div>
  <div class="cl-info">
    <div><b>Equipment</b><span>${esc(f.equipment)}${f.model ? ' · ' + esc(f.model) : ''}</span></div>
    <div><b>Shift</b><span>${esc(f.shift_date)} · ${esc(shiftTxt)}</span></div>
    <div><b>Operator</b><span>${esc(f.operator || '–')}${f.operator_login ? ' (' + esc(f.operator_login) + ')' : ''}</span></div>
    <div><b>Crew</b><span>${esc(f.crew || '–')}</span></div>
    <div><b>Filed</b><span>${esc(f.created_ts)}</span></div>
    <div><b>Template</b><span>${esc(tpl || '–')}</span></div>
    <div><b>Review</b><span>${esc(f.form_status || 'Not reviewed')}${f.status_ts ? ' · ' + esc(f.status_ts) : ''}</span></div>
    <div><b>Comment</b><span>${esc(f.review_comment || '–')}</span></div>
  </div>
  <div class="cl-sum"><span>${fmt(ids.length)} items checked</span><span class="${nok.size ? 'bad' : ''}">${fmt(nok.size)} NOT OK</span></div>
  <table class="cl"><thead><tr><th>#</th><th>Item</th><th>Result</th></tr></thead><tbody>${rows.join('')}</tbody></table>
  <div class="cl-sign"><div>Operator signature</div><div>Supervisor signature</div></div>
  <div class="cl-foot"><span>Source: C4M ControlSenseDB · ta_checklist #${f.id_checklist} · exported ${new Date().toISOString().slice(0, 16).replace('T', ' ')} UTC</span><span>Checklist ${i + 1} of ${n}</span></div>
</div>`;
}
function prepareFormsPrint() {
  const fs = pdfSel(); if (!fs.length) return 0;
  $('#pdfForms').innerHTML = fs.map((f, i) => clPage(f, i, fs.length)).join('');
  pdfMode = 'forms'; document.body.classList.add('print-forms');
  injectPageStyle();
  document.title = `checklists_${$('#pdfDate').value}${$('#pdfShift').value ? '_' + $('#pdfShift').value : ''}${$('#pdfCrew').value ? '_' + $('#pdfCrew').value.replace(/\s+/g, '') : ''}`;   // the suggested PDF file name
  return fs.length;
}
function endFormsPrint() {
  pdfMode = null; document.body.classList.remove('print-forms');
  const st = $('#pdfPageStyle'); if (st) st.remove();
  document.title = TITLE0; $('#pdfForms').innerHTML = '';
}
window.__formsPdf = { prepare: prepareFormsPrint, end: endFormsPrint, count: () => pdfSel().length };

/* ---- on-demand refresh (runs the nightly C4M job on the R4M server; hidden when the service is absent) ---- */
(function () {
  const btn = $('#refreshBtn'), msg = $('#refreshMsg'), JOB = 'opkpi';
  if (location.protocol === 'file:') return;
  // the service answers under /r4m_custom_report/ only; the R4M menu embeds the report under /fronts/r4m_custom_report/
  const BASE = location.pathname.replace(/^\/fronts(?=\/)/, '').replace(/[^/]*$/, '');
  const api = q => fetch(BASE + 'refresh' + q, { cache: 'no-store' }).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)));
  const say = (t, cls) => { msg.textContent = t; msg.className = cls || ''; };
  const idle = st => {
    btn.hidden = false; btn.classList.remove('busy');
    if (st.rc != null && st.rc !== 0) say(`last on-demand refresh failed (exit ${st.rc}, ${st.finished}) — see the server log`, 'err');
    else if (st.cooldownLeft > 0) say(`refreshed ${st.finished} · next refresh possible in ${Math.ceil(st.cooldownLeft / 60)} min`);
    else say(`page built ${st.pageAt || '?'} · nightly at 10:45 · click to pull the newest shifts now`);
  };
  const poll = () => api('/status?job=' + JOB).then(st => {
    if (st.running) { btn.classList.add('busy'); say(`refreshing from C4M… ${st.elapsed || 0} s (pull + build ≈ 1–2 min)`); setTimeout(poll, 4000); return; }
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
        if (code === 202) { window.__refreshWait = true; poll(); }
        else if (code === 409) { window.__refreshWait = true; poll(); }
        else if (code === 429) { say(`a refresh just ran (${j.finished}) · try again in ${Math.ceil((j.cooldownLeft || 0) / 60)} min`, 'err'); btn.classList.remove('busy'); }
        else { say(`refresh not available: ${j.error || code}`, 'err'); btn.classList.remove('busy'); }
      }).catch(e => { say('refresh service unreachable: ' + e.message, 'err'); btn.classList.remove('busy'); });
  };
  api('/status?job=' + JOB).then(st => { if (!st.available) return; if (st.running) { window.__refreshWait = true; } poll(); }).catch(() => {});
})();

/* ---- render ------------------------------------------------------------ */
/* ---- shift sheet (section 01): one shift day, ranked operators, follow-ups, operator cards, the daily PDF ---- */
const OSEV = D.osev ? decode(D.osev) : [];
const HAS_OS = !!D.hasOverspeed, OS_TO = M.os_to || null, OS_RULE = M.os_rule || [8, 2];
const addDays = (iso, n) => { const d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const LAST_COMPLETE = addDays(M.date_to, -1) < M.date_from ? M.date_from : addDays(M.date_to, -1);
const ord = n => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };
const median = a => { const b = a.filter(v => v != null && isFinite(v)).sort((x, y) => x - y); if (!b.length) return null; const m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
const shiftTxt = s => s === 'DS' ? 'day shift (07–19)' : s === 'NS' ? 'night shift (19–07)' : 'both shifts';
const evKey = e => (e.t < '07:00' ? '1' : '0') + e.t;
const noTelemetry = date => !HAS_OS || (OS_TO && date > OS_TO);
const WK_CREW = new Map(); OPS.forEach(r => { if (r.id_worker > 0 && r.crew) WK_CREW.set(r.id_worker, r.crew); });
const WK_NAME = new Map(); OPS.forEach(r => { if (r.id_worker > 0 && r.operator) WK_NAME.set(r.id_worker, r.operator); });
FORMS.forEach(f => { if (f.id_worker > 0 && f.operator && !WK_NAME.has(f.id_worker)) WK_NAME.set(f.id_worker, f.operator); });

/* the four headline KPIs, ranked within role; [badge key, field, lower is better, label] */
const HEAD = {
  haul: [['rate', 'rate_r', false, 'Cycles / productive h'], ['prod', 'productive_pct', false, 'Productive time'],
         ['chk', 'checklist_compliance_pct', false, 'Checklist'], ['os', 'os_rank_v', true, 'Over-speed']],
  load: [['rate', 'rate_r', false, 'Cycles loaded / productive h'], ['prod', 'productive_pct', false, 'Productive time'],
         ['chk', 'checklist_compliance_pct', false, 'Checklist']]};
function rankBy(list, key, lower) {      // competition ranking (1, 1, 3); operators without a value are not ranked
  const vals = list.filter(o => o[key] != null && isFinite(o[key])).sort((a, b) => lower ? a[key] - b[key] : b[key] - a[key]);
  const at = new Map(), cnt = {}; let prev = null, r = 0;
  vals.forEach((o, i) => { if (prev === null || Math.abs(o[key] - prev) > 1e-9) r = i + 1; prev = o[key]; at.set(o.key, r); cnt[r] = (cnt[r] || 0) + 1; });
  return id => at.has(id) ? {r: at.get(id), n: vals.length, tie: cnt[at.get(id)] > 1} : null;
}
function applyRanks(list, role) {
  const R = HEAD[role].map(([k, key, lower]) => [k, rankBy(list, key, lower)]);
  list.forEach(o => { o.rk = {}; R.forEach(([k, f]) => o.rk[k] = f(o.key)); });
  return list;
}
function rb(x) {                         // rank badge: top 3 green, bottom quarter red
  if (!x) return '';
  const cls = x.r <= 3 ? 'top' : (x.n >= 4 && x.r > x.n * 0.75) ? 'low' : '';
  return `<span class="rb ${cls}" title="${ord(x.r)} of ${x.n}${x.tie ? ' (shared)' : ''}">${ord(x.r)}</span>`;
}
function opsOf(rows) {                   // one aggregate per named operator (the period code's aggregate/finish)
  const named = rows.filter(r => r.id_worker > 0 && r.operator);
  const first = new Map(); named.forEach(r => { if (!first.has(r.id_worker)) first.set(r.id_worker, r); });
  const ops = aggregate(named, r => r.id_worker);
  ops.forEach(o => { const r = first.get(o.key); o.operator = r.operator; o.operator_login = r.operator_login; o.crew = r.crew; });
  return ops;
}
const MEDKEYS = COLS.filter(c => /^(num|num1|pct)$/.test(c[2])).map(c => c[0]).concat(['eq_shifts', 'loads_per_prod_h', 'loads_ld_per_prod_h', 'productive_pct', 'avg_cycle_s', 'avg_hang_s', 'checklist_compliance_pct', 'os_per100h', 'loads', 'loads_ld', 'hours_logged']).filter((k, i, a) => a.indexOf(k) === i);
function medOf(list) { const o = {}; MEDKEYS.forEach(k => o[k] = median(list.map(x => x[k]))); return o; }
function fleetOf(rows, role) { return finish(rows.filter(r => r.role === role).reduce((o, r) => (addRow(o, r), o), newAgg(role))); }

/* previous 30 shift days before a date (complete days only): per operator + per role fleet; memoised per date */
const BASE_CACHE = new Map();
function baseline(date) {
  if (BASE_CACHE.has(date)) return BASE_CACHE.get(date);
  const from = addDays(date, -30), rows = OPS.filter(r => r.shift_date >= from && r.shift_date < date);
  const ops = opsOf(rows);
  const b = {from, to: addDays(date, -1), byOp: new Map(ops.map(o => [o.key, o])), fleet: {haul: fleetOf(rows, 'haul'), load: fleetOf(rows, 'load')}};
  BASE_CACHE.set(date, b);
  return b;
}

/* everything the shift sheet, the cards and the PDF show for one date / shift / crew */
function shiftModel(date, sh, crew) {
  const rows = OPS.filter(r => r.shift_date === date && (!sh || r.shift === sh) && (!crew || r.crew === crew));
  const forms = FORMS.filter(f => f.shift_date === date && (!sh || f.shift === sh) && (!crew || f.crew === crew));
  const noTel = noTelemetry(date);
  const events = noTel ? [] : OSEV.filter(e => e.shift_date === date && (!sh || e.shift === sh) && (!crew || (e.id_worker > 0 && WK_CREW.get(e.id_worker) === crew)))
    .sort((a, b) => (a.shift + evKey(a)).localeCompare(b.shift + evKey(b)));
  const evBy = new Map(); events.forEach(e => { if (e.id_worker > 0) { if (!evBy.has(e.id_worker)) evBy.set(e.id_worker, []); evBy.get(e.id_worker).push(e); } });
  const fBy = new Map(); forms.forEach(f => { if (!fBy.has(f.id_worker)) fBy.set(f.id_worker, []); fBy.get(f.id_worker).push(f); });
  const base = baseline(date);
  const all = opsOf(rows).filter(o => o.shifts_worked > 0 || o.os_n > 0);
  all.forEach(o => {
    o.events = evBy.get(o.key) || []; o.formsList = fBy.get(o.key) || [];
    o.shiftsTxt = [...new Set([...o.shifts].map(s => s.split('|')[1]))].sort().join('+') || (o.events[0] || {}).shift || '';
    o.missing = o.role === 'aux' ? 0 : Math.max(0, o.eq_shifts - o.forms);
    if (noTel) { o.os_n = null; o.os_max = null; o.os_steep = null; o.os_per100h = null; o.os_rank_v = null; }
    o.own = base.byOp.get(o.key) || null;
  });
  const trucks = applyRanks(all.filter(o => o.role === 'haul'), 'haul'), loaders = applyRanks(all.filter(o => o.role === 'load'), 'load');
  const aux = all.filter(o => o.role === 'aux');
  const med = {haul: medOf(trucks), load: medOf(loaders)};
  // fleet tiles: every row of the shift, including machine time nobody was logged in for
  const haulRows = rows.filter(r => r.role === 'haul'), loadRows = rows.filter(r => r.role === 'load');
  const fh = fleetOf(rows, 'haul'), fl = fleetOf(rows, 'load');
  const eqs = new Set(); rows.forEach(r => { if (worked(r) && r.role !== 'aux') eqs.add(r.shift + '|' + r.id_equipo); });
  const follow = [];
  const flag = (o, cls, html) => follow.push({id: o.key, cls, html});
  [...trucks, ...loaders].forEach(o => {
    const m = med[o.role], rateKey = o.role === 'haul' ? 'loads_per_prod_h' : 'loads_ld_per_prod_h';
    if (o.os_n >= FLAG_RULES.os) flag(o, 'os', `<b>${esc(o.operator)}</b> · ${o.os_n} over-speed · worst +${fmt(o.os_max, 1)} km/h${o.os_steep ? ` · ${o.os_steep} steep` : ''}`);
    if (o.missing > 0) flag(o, 'chk', `<b>${esc(o.operator)}</b> · no checklist for ${o.missing === 1 ? esc(o.equipment_used) : o.missing + ' machine-shifts'}`);
    const blank = o.formsList.filter(f => f.n_items > 0 && f.n_not_ok === f.n_items).length;
    if (blank) flag(o, 'nok', `<b>${esc(o.operator)}</b> · checklist saved blank (all items NOT OK)${blank > 1 ? ' ×' + blank : ''}`);
    else if (o.items_nok >= FLAG_RULES.nok) flag(o, 'nok', `<b>${esc(o.operator)}</b> · ${o.items_nok} checklist items NOT OK`);
    if (o.hours_logged >= FLAG_RULES.prodMinH && m.productive_pct != null && o.productive_pct != null && o.productive_pct < m.productive_pct - FLAG_RULES.prodGap)
      flag(o, 'prod', `<b>${esc(o.operator)}</b> · productive ${fmt(o.productive_pct, 0)} % (shift median ${fmt(m.productive_pct, 0)} %)`);
    if (o.h_prod >= FLAG_RULES.rateMinH && m[rateKey] && o[rateKey] != null && o[rateKey] < m[rateKey] * FLAG_RULES.rateShare)
      flag(o, 'rate', `<b>${esc(o.operator)}</b> · ${fmt(o[rateKey], 2)} cycles / productive h (median ${fmt(m[rateKey], 2)})`);
  });
  const order = {os: 0, chk: 1, nok: 2, prod: 3, rate: 4};
  follow.sort((a, b) => order[a.cls] - order[b.cls]);
  return {date, sh, crew, rows, forms, events, noTel, trucks, loaders, aux, med, base, fh, fl, haulRows, loadRows, eqShifts: eqs.size, follow,
          unattributed: events.filter(e => !(e.id_worker > 0)), ops: [...trucks, ...loaders]};
}
const FLAG_RULES = {os: 1, nok: 3, prodGap: 15, prodMinH: 4, rateShare: 0.6, rateMinH: 2};

/* ---- rendering ---- */
const SRANK = [['rate', 'Cycles per productive hour'], ['prod', 'Productive time %'], ['loads', 'Cycles'], ['chk', 'Checklist compliance'], ['os', 'Over-speed (fewest first)']];
const SH = {date: null, sh: '', crew: ''};
let CUR = null;
function readShift() {
  let d = $('#pdfDate').value || LAST_COMPLETE;
  if (d < M.date_from) d = M.date_from; if (d > M.date_to) d = M.date_to;
  $('#pdfDate').value = d;
  SH.date = d; SH.sh = $('#pdfShift').value; SH.crew = $('#pdfCrew').value;
}
const pctDelta = (v, b) => (v == null || !b) ? null : (v - b) / b * 100;
function dlt(d, unit, lowerBetter) {     // ▲ / ▼ against a baseline
  if (d == null || !isFinite(d) || Math.abs(d) < 0.5) return d == null || !isFinite(d) ? '' : `<span class="dlt">±0${unit}</span>`;
  const good = lowerBetter ? d < 0 : d > 0;
  return `<span class="dlt ${good ? 'up' : 'dn'}">${d > 0 ? '▲' : '▼'} ${fmt(Math.abs(d), 0)}${unit}</span>`;
}
function osCell(o, noTel) {
  if (noTel) return '<span class="muted">no telemetry yet</span>';
  if (!o.os_n) return '<span class="okc">none</span>';
  return `<span class="nok">${o.os_n}</span> · worst +${fmt(o.os_max, 1)}${o.os_steep ? ` · ${o.os_steep} steep` : ''}`;
}
function chkCell(o) {
  if (o.role === 'aux' || !o.eq_shifts) return '<span class="muted">–</span>';
  const p = o.missing ? `<span class="pill rej">${o.forms}/${o.eq_shifts} missing</span>` : `<span class="pill ok">${o.forms}/${o.eq_shifts}</span>`;
  return p + (o.items_nok ? ` <span class="nok">${o.items_nok} NOT OK</span>` : '');
}
function evTable(evs, withOp) {
  return `<table class="x"><thead><tr><th>Time</th>${withOp ? '<th>Operator</th>' : ''}<th>Truck</th><th>Segment</th><th class="num">Avg km/h</th><th class="num">Limit</th><th class="num">Over</th><th class="num">Seconds</th><th>Road</th><th>Load</th></tr></thead><tbody>` +
    evs.map(e => `<tr><td>${e.shift} ${esc(e.t)}</td>${withOp ? `<td>${e.id_worker > 0 ? esc(WK_NAME.get(e.id_worker) || '#' + e.id_worker) : '<span class="muted">no operator logged in</span>'}</td>` : ''}<td>${esc(e.equipment)}</td><td>${esc(e.segment)}</td><td class="num">${fmt(e.avg, 1)}</td><td class="num">${e.lim}</td><td class="num nok">+${fmt(e.over, 1)}</td><td class="num">${e.dur}</td><td>${e.road === 'steep' ? '<b>steep</b>' : 'flat'}</td><td>${e.loaded ? 'loaded' : 'empty'}</td></tr>`).join('') + '</tbody></table>';
}
function sortShift(list, role) {
  const k = $('#sRankBy').value || 'rate';
  const key = k === 'loads' ? (role === 'haul' ? 'loads' : 'loads_ld') : k === 'os' && role === 'haul' ? 'os_rank_v' : (HEAD[role].find(h => h[0] === k) || HEAD[role][0])[1];
  const lower = key === 'os_rank_v', rk = rankBy(list, key, lower);
  list.forEach(o => o.srank = rk(o.key));
  return list.slice().sort((a, b) => (a.srank ? a.srank.r : 1e9) - (b.srank ? b.srank.r : 1e9) || String(a.operator).localeCompare(String(b.operator)));
}
const OWN_TOTALS = new Set(['hours_logged', 'h_prod', 'h_delay', 'h_standby', 'h_ready_other', 'h_maint', 'loads', 'tonnes', 'loads_ld', 'tonnes_ld', 'trucks', 'forms', 'eq_shifts', 'items', 'items_nok', 'forms_rej', 'forms_pend', 'os_n', 'os_s', 'os_steep']);
const ALLGRP = {time: 'Time use', haul: 'Cycles · average phase seconds', load: 'Loading', chk: 'Pre-start checklists', safe: 'Over-speed'};
function allCols(role) {                 // every KPI of the operator CSV for one role (user, 2026-10-30)
  const cols = COLS.filter(c => c[3] !== 'id' && c[0] !== 'shifts_worked' && (c[3] !== 'haul' || role === 'haul') && (c[3] !== 'load' || role === 'load') && (c[3] !== 'safe' || (role === 'haul' && HAS_OS)));
  cols.splice(cols.findIndex(c => c[0] === 'forms') + 1, 0, ['eq_shifts', 'Expected', 'num', 'chk']);
  return cols;
}
const fmtCol = (c, v) => v == null || !isFinite(v) ? '–' : c[2] === 'pct' ? fmt(v, 0) + ' %' : fmt(v, c[2] === 'num1' ? 1 : 0);
function bindToggles(sel) {
  document.querySelectorAll(sel + ' td.tg').forEach(td => { if (td.dataset.ev !== '') td.onclick = () => { const ev = td.parentElement.nextElementSibling; if (ev && ev.classList.contains('ev')) { ev.hidden = !ev.hidden; td.textContent = ev.hidden ? '▸' : '▾'; } }; });
}
function renderShiftTableAll(sel, list, role, m) {
  const haul = role === 'haul', cols = allCols(role), showShift = !m.sh;
  const idc = ['#', 'Operator', 'Crew', haul ? 'Truck' : 'Unit'].concat(showShift ? ['Shift'] : []);
  const groups = []; cols.forEach(c => { const g = groups[groups.length - 1]; if (g && g.k === c[3]) g.n++; else groups.push({k: c[3], n: 1}); });
  const ncol = idc.length + cols.length + (haul ? 1 : 0);
  $(sel).classList.add('all');
  $(sel + ' thead').innerHTML = `<tr><th class="grp" colspan="${idc.length}">Operator</th>${groups.map(g => `<th class="grp" colspan="${g.n}">${ALLGRP[g.k]}</th>`).join('')}${haul ? '<th class="grp"></th>' : ''}</tr><tr>` +
    idc.map(h => `<th class="sub" style="cursor:default">${h}</th>`).join('') + cols.map(c => `<th class="sub num" style="cursor:default">${c[1]}</th>`).join('') + (haul ? '<th class="sub"></th>' : '') + '</tr>';
  const sorted = sortShift(list, role);
  const rows = sorted.map((o, i) => `<tr data-id="${o.key}" class="${o.srank && o.srank.r === 1 ? 'first' : ''}"><td class="rk">${o.srank ? o.srank.r : '–'}</td><td><a class="op" data-id="${o.key}" data-scope="shift">${esc(o.operator)}</a></td><td>${esc(o.crew || '')}</td><td>${esc(o.equipment_used)}</td>${showShift ? `<td>${esc(o.shiftsTxt)}</td>` : ''}` +
    cols.map(c => cellHtml(c, o[c[0]], o)).join('') + (haul ? `<td class="tg" data-ev="${o.events.length ? i : ''}">${o.events.length ? '▸' : ''}</td>` : '') + '</tr>' +
    (haul && o.events.length ? `<tr class="ev" hidden><td colspan="${ncol}">${evTable(o.events)}</td></tr>` : ''));
  if (sorted.length) rows.push(`<tr class="med"><td></td><td colspan="${idc.length - 1}">Median of the ${sorted.length} ${haul ? 'truck' : 'loader'} operators</td>${cols.map(c => `<td class="num">${fmtCol(c, median(sorted.map(o => o[c[0]])))}</td>`).join('')}${haul ? '<td></td>' : ''}</tr>`);
  if (haul && m.unattributed.length) rows.push(`<tr class="unat"><td class="rk"></td><td colspan="${ncol - 2}">(no operator logged in on the truck) · ${m.unattributed.length} over-speed event${m.unattributed.length === 1 ? '' : 's'}</td><td class="tg" data-ev="u">▸</td></tr>` +
    `<tr class="ev" hidden><td colspan="${ncol}">${evTable(m.unattributed)}</td></tr>`);
  $(sel + ' tbody').innerHTML = rows.join('') || `<tr><td colspan="${ncol}" class="empty">No ${haul ? 'truck' : 'loader'} operators worked in this selection.</td></tr>`;
  bindToggles(sel);
}
function renderShiftTable(sel, list, role, m) {
  if ($('#sView').value === 'all') return renderShiftTableAll(sel, list, role, m);
  $(sel).classList.remove('all');
  const haul = role === 'haul', rateKey = haul ? 'loads_per_prod_h' : 'loads_ld_per_prod_h';
  const vmax = Math.max(0, ...list.map(o => o[rateKey] || 0)) || 1;
  const head = haul
    ? ['#', 'Operator', 'Crew', 'Truck', 'Shift', 'Hours', 'Cycles', 'Cycles / prod h', 'Prod %', 'Cycle min', 'Checklist', 'Over-speed', '']
    : ['#', 'Operator', 'Crew', 'Unit', 'Shift', 'Hours', 'Cycles loaded', 'Cycles / prod h', 'Prod %', 'Hang s', 'Trucks served', 'Checklist'];
  const showShift = !m.sh;
  if (!showShift) head.splice(4, 1);
  const num = new Set(['Hours', 'Cycles', 'Cycles / prod h', 'Prod %', 'Cycle min', 'Cycles loaded', 'Hang s', 'Trucks served']);
  const tipH = { 'Cycles / prod h': 'Bar = this operator against the highest cycles per productive hour in this table (full bar = the best). Badge = rank in the shift. Δ = change against the operator’s own previous 30 shift days.' };
  $(sel + ' thead').innerHTML = '<tr>' + head.map(h => `<th class="${num.has(h) ? 'num' : ''}" style="cursor:default"${tipH[h] ? ` title="${tipH[h]}"` : ''}>${h}</th>`).join('') + '</tr>';
  const rows = sortShift(list, role).map((o, i) => {
    const own = o.own && o.own.shifts_worked >= 3 ? o.own : null;
    const rate = o[rateKey];
    const rateCell = `<td class="num"><span class="ibw"><i class="ib ${haul ? '' : 'l'}" style="--w:${rate ? Math.max(2, rate / vmax * 44) : 0}px"></i></span>${fmt(rate, 2)}${rb(o.rk.rate)}${own ? dlt(pctDelta(rate, own[rateKey]), ' %') : ''}</td>`;
    const prodCell = `<td class="num">${o.productive_pct == null ? '–' : fmt(o.productive_pct, 0) + ' %'}${rb(o.rk.prod)}${own && o.productive_pct != null && own.productive_pct != null ? dlt(o.productive_pct - own.productive_pct, ' pts') : ''}</td>`;
    const cells = haul
      ? [`<td class="num">${fmt(o.hours_logged, 1)}</td>`, `<td class="num">${fmt(o.loads)}</td>`, rateCell, prodCell,
         `<td class="num">${o.avg_cycle_s == null ? '–' : fmt(o.avg_cycle_s / 60, 1)}</td>`, `<td>${chkCell(o)}${rb(o.rk.chk)}</td>`,
         `<td>${osCell(o, m.noTel)}${rb(o.rk.os)}</td>`, `<td class="tg" data-ev="${o.events.length ? i : ''}">${o.events.length ? '▸' : ''}</td>`]
      : [`<td class="num">${fmt(o.hours_logged, 1)}</td>`, `<td class="num">${fmt(o.loads_ld)}</td>`, rateCell, prodCell,
         `<td class="num">${fmt(o.avg_hang_s, 0)}</td>`, `<td class="num">${fmt(o.trucks)}</td>`, `<td>${chkCell(o)}${rb(o.rk.chk)}</td>`];
    const main = `<tr data-id="${o.key}" class="${o.srank && o.srank.r === 1 ? 'first' : ''}"><td class="rk">${o.srank ? o.srank.r : '–'}</td><td><a class="op" data-id="${o.key}" data-scope="shift">${esc(o.operator)}</a></td><td>${esc(o.crew || '')}</td><td>${esc(o.equipment_used)}</td>${showShift ? `<td>${esc(o.shiftsTxt)}</td>` : ''}${cells.join('')}</tr>`;
    return main + (haul && o.events.length ? `<tr class="ev" hidden><td colspan="${head.length}">${evTable(o.events)}</td></tr>` : '');
  });
  if (haul && m.unattributed.length) rows.push(`<tr class="unat"><td class="rk"></td><td colspan="${head.length - 3}">(no operator logged in on the truck) · ${m.unattributed.length} over-speed event${m.unattributed.length === 1 ? '' : 's'}</td><td><span class="nok">${m.unattributed.length}</span></td><td class="tg" data-ev="u">▸</td></tr>` +
    `<tr class="ev" hidden><td colspan="${head.length}">${evTable(m.unattributed)}</td></tr>`);
  $(sel + ' tbody').innerHTML = rows.join('') || `<tr><td colspan="${head.length}" class="empty">No ${haul ? 'truck' : 'loader'} operators worked in this selection.</td></tr>`;
  bindToggles(sel);
}
function shiftTiles(m) {
  const haulLoads = sum(m.haulRows.map(r => r.loads)), allLoads = sum(m.rows.map(r => r.loads)), t = sum(m.rows.map(r => r.tonnes));
  const bh = m.base.fleet.haul, bl = m.base.fleet.load;
  const rate = m.fh.loads_per_prod_h, prodH = m.fh.productive_pct, prodL = m.fl.productive_pct;
  const nok = sum(m.forms.map(f => f.n_not_ok)), missing = Math.max(0, m.eqShifts - m.forms.length);
  const ev = m.events, kOps = new Set(ev.filter(e => e.id_worker > 0).map(e => e.id_worker)).size, worst = ev.length ? Math.max(...ev.map(e => e.over)) : 0, steep = ev.filter(e => e.road === 'steep').length;
  const osTile = m.noTel ? ['Over-speed events', '<span class="muted">–</span>', '', `no truck telemetry for this shift yet (over-speed data to ${OS_TO || '–'})`, null, '']
    : ev.length ? ['Over-speed events', fmt(ev.length), '', `${kOps} operator${kOps === 1 ? '' : 's'} · worst +${fmt(worst, 1)} km/h · ${steep} on steep roads${m.unattributed.length ? ` · ${m.unattributed.length} without a login` : ''}`, null, 'crit']
    : ['Over-speed events', '<span class="okc">none</span>', '', `no event ≥ ${OS_RULE[0]} s at ≥ limit + ${OS_RULE[1]} km/h average`, null, 'ok'];
  return [
    ['Operators on shift', `${fmt(m.trucks.length)}<small>trucks</small> ${fmt(m.loaders.length)}<small>loaders</small>`, '', `${m.aux.length ? m.aux.length + ' auxiliary not ranked · ' : ''}${fmt(m.eqShifts)} machine-shifts worked`, null, ''],
    ['Cycles', fmt(allLoads), '', `${fmt(haulLoads)} by trucks · ${fmt(allLoads - haulLoads)} load-and-carry · ${fmt(t)} nominal t`, null, ''],
    ['Cycles per productive hour', `${fmt(rate, 2)}${dlt(pctDelta(rate, bh.loads_per_prod_h), ' %')}`, '', `trucks · previous 30 days ${fmt(bh.loads_per_prod_h, 2)}`, null, ''],
    ['Productive time', `${fmt(prodH, 0)}<small>%</small>${prodH != null && bh.productive_pct != null ? dlt(prodH - bh.productive_pct, ' pts') : ''}`, '', `trucks · loaders ${fmt(prodL, 0)} % · previous 30 days ${fmt(bh.productive_pct, 0)} / ${fmt(bl.productive_pct, 0)} %`, null, 'alt'],
    ['Checklists filed', `${fmt(m.forms.length)}<small>/ ${fmt(m.eqShifts)}</small>`, '', `${missing ? missing + ' machine-shift' + (missing === 1 ? '' : 's') + ' without a form · ' : 'every machine-shift has a form · '}${fmt(nok)} items NOT OK`, null, missing ? 'crit' : 'ok'],
    osTile];
}
function renderShift() {
  readShift();
  const m = CUR = shiftModel(SH.date, SH.sh, SH.crew);
  $('#shSub').textContent = `${SH.date} · ${shiftTxt(SH.sh)}${SH.crew ? ' · ' + SH.crew : ''}`;
  $('#sRunning').hidden = SH.date !== M.date_to;
  $('#sPrev').disabled = SH.date <= M.date_from; $('#sNext').disabled = SH.date >= M.date_to;
  $('#sLast').classList.toggle('on', SH.date === LAST_COMPLETE);
  $('#shKpis').innerHTML = shiftTiles(m).map(([l, v, u, s, sp, cls]) => `<div class="kpi ${cls}"><div class="k">${l}</div><div class="v">${v}${u ? `<small>${u}</small>` : ''}</div><div class="s">${s}</div></div>`).join('');
  /* the follow-up list is on the PDF summary page only (user, 2026-10-30: not on the screen) */
  $('#shTruckN').textContent = `${m.trucks.length} operators`;
  $('#shLoadN').textContent = `${m.loaders.length} operators`;
  renderShiftTable('#tblTrucks', m.trucks, 'haul', m);
  renderShiftTable('#tblLoaders', m.loaders, 'load', m);
  const n = shiftPrintModels().reduce((s, x) => s + x.ops.length, 0);
  $('#shiftPdfBtn').disabled = !n;
  $('#shiftPdfBtn').innerHTML = `&#8681; Export shift KPIs (${fmt(n)} operator${n === 1 ? '' : 's'}, PDF)`;
  updatePdfBtn();
}

/* ---- operator card ---- */
function cmpBar(label, unit, dec, me, fleet, own, lower, ownLbl) {
  const vals = [me, fleet, own].filter(v => v != null && isFinite(v)), mx = Math.max(...vals, 0) || 1;
  const row = (cls, who, v) => `<div class="r ${cls}"><span>${who}</span><span class="tr"><i style="width:${v == null || !isFinite(v) ? 0 : Math.max(1.5, v / mx * 100).toFixed(1)}%"></i></span><span class="v">${v == null || !isFinite(v) ? '–' : fmt(v, dec) + unit}</span></div>`;
  return `<div class="skc-bar"><div class="l">${label}${lower ? ' <small>· lower is better</small>' : ''}</div>${row('me', 'Operator', me)}${row('f', 'Fleet median', fleet)}${row('o', ownLbl, own)}</div>`;
}
function opCard(o, ctx, pr) {
  const haul = o.role === 'haul', rateKey = haul ? 'loads_per_prod_h' : 'loads_ld_per_prod_h', med = ctx.med[o.role] || {}, own = o.own;
  const ownLbl = ctx.scope === 'shift' ? 'Own 30 days' : 'Own prior 30 d';
  const pill = `<span class="pill ${o.role}">${haul ? 'Truck' : o.role === 'load' ? 'Loader' : 'Aux'}</span>`;
  const head = `<div class="skc-head"><div><h2>${esc(o.operator)}${pill}</h2>
    <div class="s">${esc(o.crew || 'no crew')} · login ${esc(o.operator_login || '–')} · ${esc(o.equipment_used || '–')}</div>
    <div class="s"><b>${esc(ctx.title)}</b> · ${ctx.scope === 'shift' ? 'operator shift card' : 'operator card · selected period'}</div></div><img src="${LOGO_SRC}" alt="Erdene"></div>`;
  const evs = ctx.events(o), noTel = ctx.noTel;
  const tile = (k, v, s, cls) => `<div class="skc-tile ${cls || ''}"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
  const tiles = `<div class="skc-tiles">${[
    haul ? tile('Cycles', fmt(o.loads), `${fmt(o.tonnes)} nominal t`) : tile('Cycles loaded', fmt(o.loads_ld), `${fmt(o.tonnes_ld)} nominal t`),
    tile('Cycles / prod h', fmt(o[rateKey], 2), `fleet median ${fmt(med[rateKey], 2)}`),
    tile('Productive', `${fmt(o.productive_pct, 0)}<small>%</small>`, `${fmt(o.h_prod, 1)} of ${fmt(o.hours_logged, 1)} h`),
    haul ? tile('Avg cycle', `${o.avg_cycle_s == null ? '–' : fmt(o.avg_cycle_s / 60, 1)}<small>min</small>`, `queue ${fmt(o.avg_queue_s, 0)} s · haul ${o.avg_haul_s == null ? '–' : fmt(o.avg_haul_s / 60, 1)} min`)
         : tile('Avg hang', `${fmt(o.avg_hang_s, 0)}<small>s</small>`, `${fmt(o.trucks)} trucks served`),
    tile('Checklists', o.eq_shifts ? `${fmt(o.forms)}<small>/ ${fmt(o.eq_shifts)}</small>` : fmt(o.forms), `${fmt(o.items_nok)} items NOT OK`, o.missing ? 'bad' : 'good'),
    haul ? (noTel ? tile('Over-speed', '–', 'no telemetry yet') : tile('Over-speed', fmt(o.os_n), o.os_n ? `worst +${fmt(o.os_max, 1)} km/h · ${fmt(o.os_steep)} steep` : 'no events', o.os_n ? 'bad' : 'good'))
         : tile('Over-speed', 'n/a', 'trucks only')].join('')}</div>`;
  const bars = [cmpBar(haul ? 'Cycles per productive hour' : 'Cycles loaded per productive hour', '', 2, o[rateKey], med[rateKey], own && own[rateKey], false, ownLbl),
    cmpBar('Productive time', ' %', 0, o.productive_pct, med.productive_pct, own && own.productive_pct, false, ownLbl),
    haul ? cmpBar('Average cycle', ' min', 1, o.avg_cycle_s == null ? null : o.avg_cycle_s / 60, med.avg_cycle_s == null ? null : med.avg_cycle_s / 60, own && own.avg_cycle_s != null ? own.avg_cycle_s / 60 : null, true, ownLbl)
         : cmpBar('Average hang (truck waiting at the loader)', ' s', 0, o.avg_hang_s, med.avg_hang_s, own && own.avg_hang_s, true, ownLbl),
    cmpBar('Checklist compliance', ' %', 0, o.checklist_compliance_pct, med.checklist_compliance_pct, own && own.checklist_compliance_pct, false, ownLbl)];
  if (haul && !noTel) bars.push(cmpBar('Over-speed events per 100 operated hours', '', 1, o.os_per100h, med.os_per100h, own && own.os_per100h, true, ownLbl));
  const grp = haul ? 'trucks' : 'loaders';
  const ranks = (HEAD[o.role] || []).map(([k, , , lbl]) => { const x = o.rk && o.rk[k]; return `<span>${lbl}: ${x ? `<b>${ord(x.r)} of ${x.n} ${grp}</b>${x.tie ? ' (shared)' : ''}${rb(x)}` : '–'}</span>`; }).join('');
  const evShow = evs.slice(0, 8);
  const evHtml = !haul ? '' : `<div class="skc-blk"><div class="skc-h">Over-speed events <small>≥ ${OS_RULE[0]} s with an average ≥ limit + ${OS_RULE[1]} km/h · 40 km/h, 30 km/h on steep roads</small></div>${
    noTel ? '<div class="skc-empty">No truck telemetry for this shift yet.</div>'
    : evs.length ? `<table class="skc"><thead><tr><th>Time</th><th>Truck</th><th>Segment</th><th class="n">Avg km/h</th><th class="n">Limit</th><th class="n">Over</th><th class="n">s</th><th>Road</th><th>Load</th></tr></thead><tbody>${
        evShow.map(e => `<tr class="${e.road === 'steep' ? 'steep' : ''}"><td>${ctx.scope === 'period' ? esc(e.shift_date.slice(5)) + ' ' : ''}${e.shift} ${esc(e.t)}</td><td>${esc(e.equipment)}</td><td>${esc(e.segment)}</td><td class="n">${fmt(e.avg, 1)}</td><td class="n">${e.lim}</td><td class="n bad">+${fmt(e.over, 1)}</td><td class="n">${e.dur}</td><td>${e.road}</td><td>${e.loaded ? 'loaded' : 'empty'}</td></tr>`).join('')
      }</tbody></table>${evs.length > evShow.length ? `<div class="skc-empty">+ ${evs.length - evShow.length} more (worst shown first)</div>` : ''}`
    : '<div class="skc-empty good">No over-speed events.</div>'}</div>`;
  const allTbl = (title, keys) => { const cs = keys.map(k => k === 'eq_shifts' ? ['eq_shifts', 'Checklists expected', 'num'] : COLS.find(c => c[0] === k)).filter(Boolean);
    return `<table class="skc"><thead><tr><th>${title}</th><th class="n">Operator</th><th class="n">Median</th><th class="n" title="the operator's own ${ctx.scope === 'shift' ? 'previous 30 shift days' : '30 days before the period'}; totals scaled to the same number of shifts">${ctx.scope === 'shift' ? 'Own 30 d' : 'Prior 30 d'}</th></tr></thead><tbody>${
      cs.map(c => `<tr><td>${c[1]}</td><td class="n"><b>${fmtCol(c, o[c[0]])}</b></td><td class="n">${fmtCol(c, med[c[0]])}</td><td class="n">${own && own.shifts_worked ? fmtCol(c, ownVal(c[0])) : '–'}</td></tr>`).join('')}</tbody></table>`; };
  // totals (hours, tonnes, forms, events ...) of the own 30 days are scaled to the operator's number of shifts here; rates and averages as they are
  const ownVal = k => OWN_TOTALS.has(k) && own[k] != null ? own[k] / own.shifts_worked * (o.shifts_worked || 1) : own[k];
  const allKpi = `<div class="skc-blk"><div class="skc-h">All KPIs <small>as in the operator CSV · median of the ${grp} ${ctx.scope === 'shift' ? 'in this shift' : 'in this period'} · own 30 d totals scaled to ${o.shifts_worked > 1 ? fmt(o.shifts_worked) + ' shifts' : 'one shift'}</small></div><div class="skc-all">${[
    allTbl(haul ? 'Time use · output' : 'Time use', ['hours_logged', 'h_prod', 'h_delay', 'h_standby', 'h_ready_other', 'h_maint', 'shift_change_min_per_shift'].concat(haul ? ['tonnes', 'tonnes_per_prod_h'] : [])),
    haul ? allTbl('Cycle · avg s', ['avg_queue_s', 'avg_spot_s', 'avg_load_s', 'avg_haul_s', 'avg_at_dump_s', 'avg_dump_s', 'avg_travel_empty_s', 'avg_cycle_s'])
         : allTbl('Loading', ['tonnes_ld', 'loads_ld_per_prod_h', 'avg_loading_s', 'avg_hang_s', 'trucks']),
    allTbl(haul ? 'Checklist · safety' : 'Checklist', [].concat(['eq_shifts', 'forms', 'items_nok', 'items_not_ok_pct', 'forms_rej', 'forms_pend'],
      haul && !noTel ? ['os_s', 'os_steep', 'os_per100h'] : []))].join('')}</div></div>`;
  const forms = ctx.forms(o), clip = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;
  const fl = forms.slice(0, 4).map(f => `<div>${esc(f.equipment)} · ${esc(String(f.created_ts).slice(ctx.scope === 'shift' ? 11 : 5, 16))} · ${esc(f.form_status || 'Not reviewed')} · ${f.n_not_ok ? `<span class="bad">${f.n_not_ok} NOT OK</span>: ${esc(clip(f.nok.map(itemName).join('; '), 150))}` : 'all items OK'}</div>`);
  if (forms.length > 4) fl.push(`<div>+ ${forms.length - 4} more forms · ${fmt(sum(forms.slice(4).map(f => f.n_not_ok)))} NOT-OK items</div>`);
  if (o.missing) fl.unshift(`<div class="bad">No checklist filed for ${o.missing} machine-shift${o.missing === 1 ? '' : 's'} worked</div>`);
  const rs = ctx.reasons(o), rmax = Math.max(...rs.map(r => r[1]), 0) || 1;
  const reasons = rs.length ? rs.map(([l, h]) => `<div class="r"><span title="${esc(l)}">${esc(l)}</span><span class="tr"><i style="width:${(h / rmax * 100).toFixed(1)}%"></i></span><span class="v">${fmt(h, 1)} h</span></div>`).join('') : '<div class="skc-empty">No non-productive time recorded.</div>';
  return `<div class="skc">${head}${tiles}
  <div class="skc-blk"><div class="skc-h">Against the fleet <small>operator · fleet median (${grp}, ${ctx.scope === 'shift' ? 'this shift' : 'this period'}) · own ${ctx.scope === 'shift' ? 'previous 30 shift days' : '30 days before the period'}</small></div>
  <div class="skc-bars">${bars.join('')}</div><div class="skc-rank">${ranks}</div></div>
  ${allKpi}
  ${evHtml}
  <div class="skc-two"><div class="skc-blk"><div class="skc-h">Pre-start checklists</div><div class="skc-nok">${fl.join('') || '<div class="skc-empty">No checklists.</div>'}</div></div>
  <div class="skc-blk"><div class="skc-h">Non-productive time <small>top reasons</small></div><div class="skc-reasons">${reasons}</div></div></div>
  ${ctx.scope === 'shift' ? '<div class="skc-sign"><div>Operator signature</div><div>Shift supervisor signature</div></div>' : ''}
  <div class="skc-foot"><span>Source: C4M ControlSenseDB (cycles, status, checklists, truck telemetry) · exported ${new Date().toISOString().slice(0, 16).replace('T', ' ')} UTC</span><span>${pr ? `Operator ${pr.i + 1} of ${pr.n}` : ''}</span></div></div>`;
}
function topReasons(filter) {
  const acc = {}; REASONS.forEach(r => { if (filter(r)) acc[r.status_name] = (acc[r.status_name] || 0) + r.hours; });
  return Object.entries(acc).filter(([, h]) => h >= 0.05).sort((a, b) => b[1] - a[1]).slice(0, 6);
}
function shiftCtx(m) {
  return {scope: 'shift', title: `${m.date} · ${shiftTxt(m.sh)}${m.crew ? ' · ' + m.crew : ''}`, med: m.med, noTel: m.noTel,
    events: o => o.events.slice().sort((a, b) => b.over - a.over), forms: o => o.formsList,
    reasons: o => topReasons(r => r.shift_date === m.date && (!m.sh || r.shift === m.sh) && r.id_worker === o.key)};
}
let PERIOD = null;                       // set by render(): the period ranking's operators, for the period card
function periodCtx() {
  const P = PERIOD;
  return {scope: 'period', title: `${P.from} → ${P.to} · ${shiftTxt(P.shift)}`, med: P.med, noTel: !HAS_OS,
    events: o => OSEV.filter(e => e.id_worker === o.key && e.shift_date >= P.from && e.shift_date <= P.to && (!P.shift || e.shift === P.shift)).sort((a, b) => b.over - a.over),
    forms: o => FORMS.filter(f => f.id_worker === o.key && f.shift_date >= P.from && f.shift_date <= P.to && (!P.shift || f.shift === P.shift)).sort((a, b) => b.n_not_ok - a.n_not_ok || String(b.created_ts).localeCompare(String(a.created_ts))),
    reasons: o => topReasons(r => r.shift_date >= P.from && r.shift_date <= P.to && (!P.shift || r.shift === P.shift) && r.id_worker === o.key)};
}
let CARD = null;
function openCard(id, scope) {
  const o = scope === 'period' ? (PERIOD && PERIOD.ops.find(x => x.key === id)) : CUR && CUR.ops.find(x => x.key === id);
  if (!o) return;
  CARD = {id, scope};
  $('#mTitle').textContent = scope === 'period' ? 'Operator card · selected period' : 'Operator shift card';
  $('#mPrint').hidden = scope !== 'shift';
  $('#mCard').innerHTML = opCard(o, scope === 'period' ? periodCtx() : shiftCtx(CUR));
  $('#opModal').hidden = false;
  $('#mClose').focus();
}
function closeCard() { $('#opModal').hidden = true; CARD = null; }

/* ---- the daily PDF: per shift of the selection one summary page, then one A4 page per operator-shift ---- */
function shiftPrintModels() {
  const shifts = SH.sh ? [SH.sh] : ['DS', 'NS'];
  return shifts.map(s => shiftModel(SH.date, s, SH.crew)).filter(m => m.ops.length || m.events.length || m.forms.length);
}
function summaryPage(m) {
  const tiles = shiftTiles(m).map(([l, v, , s, , cls]) => `<div class="skc-tile ${cls === 'crit' ? 'bad' : cls === 'ok' ? 'good' : ''}"><div class="k">${l}</div><div class="v">${v.replace(/<span class="dlt[^"]*">[^<]*<\/span>/g, '')}</div><div class="s">${s}</div></div>`).join('');
  const trucks = sortShift(m.trucks, 'haul'), loaders = sortShift(m.loaders, 'load');
  const rankLbl = (SRANK.find(r => r[0] === ($('#sRankBy').value || 'rate')) || SRANK[0])[1];
  const tr = trucks.map(o => `<tr><td class="n">${o.srank ? o.srank.r : '–'}</td><td>${esc(o.operator)}</td><td>${esc(o.crew || '')}</td><td>${esc(o.equipment_used)}</td><td class="n">${fmt(o.hours_logged, 1)}</td><td class="n">${fmt(o.loads)}</td><td class="n">${fmt(o.loads_per_prod_h, 2)}</td><td class="n">${fmt(o.productive_pct, 0)}</td><td class="n">${o.avg_cycle_s == null ? '–' : fmt(o.avg_cycle_s / 60, 1)}</td><td class="${o.missing ? 'bad' : ''}">${o.eq_shifts ? o.forms + '/' + o.eq_shifts : '–'}${o.items_nok ? ' · ' + o.items_nok + ' NOT OK' : ''}</td><td class="${o.os_n ? 'bad' : m.noTel ? '' : 'good'}">${m.noTel ? '–' : o.os_n ? `${o.os_n} · +${fmt(o.os_max, 1)}` : 'none'}</td></tr>`).join('');
  const lr = loaders.map(o => `<tr><td class="n">${o.srank ? o.srank.r : '–'}</td><td>${esc(o.operator)}</td><td>${esc(o.crew || '')}</td><td>${esc(o.equipment_used)}</td><td class="n">${fmt(o.hours_logged, 1)}</td><td class="n">${fmt(o.loads_ld)}</td><td class="n">${fmt(o.loads_ld_per_prod_h, 2)}</td><td class="n">${fmt(o.productive_pct, 0)}</td><td class="n">${fmt(o.avg_hang_s, 0)}</td><td class="${o.missing ? 'bad' : ''}">${o.eq_shifts ? o.forms + '/' + o.eq_shifts : '–'}${o.items_nok ? ' · ' + o.items_nok + ' NOT OK' : ''}</td><td>${fmt(o.trucks)}</td></tr>`).join('');
  const fu = m.follow.length ? m.follow.map(f => `<div>${{os: '⚠ Over-speed', chk: '✗ Checklist', nok: '✗ NOT OK items', prod: '▼ Productive time', rate: '▼ Loading rate'}[f.cls]} — ${f.html}</div>`).join('') : '<div class="skc-empty good">Nothing to follow up.</div>';
  const ev = m.noTel ? '<div class="skc-empty">No truck telemetry for this shift yet.</div>' : m.events.length ? `<table class="skc"><thead><tr><th>Time</th><th>Operator</th><th>Truck</th><th>Segment</th><th class="n">Avg km/h</th><th class="n">Limit</th><th class="n">Over</th><th class="n">s</th><th>Road</th></tr></thead><tbody>${
    m.events.map(e => `<tr class="${e.road === 'steep' ? 'steep' : ''}"><td>${esc(e.t)}</td><td>${e.id_worker > 0 ? esc(WK_NAME.get(e.id_worker) || '#' + e.id_worker) : 'no operator logged in'}</td><td>${esc(e.equipment)}</td><td>${esc(e.segment)}</td><td class="n">${fmt(e.avg, 1)}</td><td class="n">${e.lim}</td><td class="n bad">+${fmt(e.over, 1)}</td><td class="n">${e.dur}</td><td>${e.road}</td></tr>`).join('')}</tbody></table>` : '<div class="skc-empty good">No over-speed events.</div>';
  return `<div class="sk-page sk-summary"><div class="skc">
  <div class="skc-head"><div><h2>Operator shift sheet</h2><div class="s"><b>${m.date} · ${shiftTxt(m.sh)}${m.crew ? ' · ' + esc(m.crew) : ''}</b>${m.date === M.date_to ? ' · shift day still running, partial data' : ''}</div>
    <div class="s">Bayankhundii gold mine · C4M fleet management · ranked within the shift</div></div><img src="${LOGO_SRC}" alt="Erdene"></div>
  <div class="skc-tiles">${tiles}</div>
  <div class="skc-blk"><div class="skc-h">Needs follow-up</div><div class="skc-follow">${fu}</div></div>
  <div class="skc-h">Truck operators <small>ranked by ${esc(rankLbl.toLowerCase())} · checklists filed / machine-shifts</small></div>
  <table class="skc"><thead><tr><th class="n">#</th><th>Operator</th><th>Crew</th><th>Truck</th><th class="n">Hours</th><th class="n">Cycles</th><th class="n">Cycles/prod h</th><th class="n">Prod %</th><th class="n">Cycle min</th><th>Checklist</th><th>Over-speed</th></tr></thead><tbody>${tr || '<tr><td colspan="11">No truck operators.</td></tr>'}</tbody></table>
  <div class="skc-h">Loader operators <small>ranked by ${esc(rankLbl.toLowerCase())}</small></div>
  <table class="skc"><thead><tr><th class="n">#</th><th>Operator</th><th>Crew</th><th>Unit</th><th class="n">Hours</th><th class="n">Cycles</th><th class="n">Cycles/prod h</th><th class="n">Prod %</th><th class="n">Hang s</th><th>Checklist</th><th class="n">Trucks</th></tr></thead><tbody>${lr || '<tr><td colspan="11">No loader operators.</td></tr>'}</tbody></table>
  <div class="skc-h">Over-speed events <small>≥ ${OS_RULE[0]} s with an average ≥ limit + ${OS_RULE[1]} km/h</small></div>${ev}
  <div class="skc-sign"><div>Shift supervisor signature</div><div>Mine superintendent signature</div></div>
  <div class="skc-foot"><span>Source: C4M ControlSenseDB · exported ${new Date().toISOString().slice(0, 16).replace('T', ' ')} UTC</span><span>Shift summary</span></div></div></div>`;
}
function allKpiPage(m) {
  const part = (role, list) => {
    const haul = role === 'haul', cols = allCols(role), sorted = sortShift(list, role);
    const groups = []; cols.forEach(c => { const g = groups[groups.length - 1]; if (g && g.k === c[3]) g.n++; else groups.push({k: c[3], n: 1}); });
    const body = sorted.map(o => `<tr><td class="n">${o.srank ? o.srank.r : '–'}</td><td class="w">${esc(o.operator)}</td><td>${esc(String(o.crew || '').replace(/^Crew\s*/i, ''))}</td><td class="w">${esc(o.equipment_used)}</td>${cols.map(c => `<td class="n">${fmtCol(c, o[c[0]])}</td>`).join('')}</tr>`).join('');
    const med = sorted.length ? `<tr class="med"><td></td><td colspan="3">Median (${sorted.length} operators)</td>${cols.map(c => `<td class="n">${fmtCol(c, median(sorted.map(o => o[c[0]])))}</td>`).join('')}</tr>` : '';
    return `<div class="skc-h">${haul ? 'Truck' : 'Loader'} operators <small>all KPIs of the operator CSV · same order as the ranked table</small></div>
    <table class="skc all"><thead><tr><th class="g" colspan="4">Operator</th>${groups.map(g => `<th class="g" colspan="${g.n}">${ALLGRP[g.k]}</th>`).join('')}</tr>
    <tr><th class="n">#</th><th>Operator</th><th>Crew</th><th>${haul ? 'Truck' : 'Unit'}</th>${cols.map(c => `<th class="n">${c[1]}</th>`).join('')}</tr></thead><tbody>${body || `<tr><td colspan="${cols.length + 4}">No ${haul ? 'truck' : 'loader'} operators.</td></tr>`}${med}</tbody></table>`;
  };
  return `<div class="sk-page sk-wide"><div class="skc">
  <div class="skc-head"><div><h2>Operator shift sheet · all KPIs</h2><div class="s"><b>${m.date} · ${shiftTxt(m.sh)}${m.crew ? ' · ' + esc(m.crew) : ''}</b>${m.date === M.date_to ? ' · shift day still running, partial data' : ''}</div></div><img src="${LOGO_SRC}" alt="Erdene"></div>
  ${part('haul', m.trucks)}${part('load', m.loaders)}
  <div class="skc-foot"><span>Source: C4M ControlSenseDB · hours from status time, seconds = average per cycle · exported ${new Date().toISOString().slice(0, 16).replace('T', ' ')} UTC</span><span>All KPIs</span></div></div></div>`;
}
function prepareShiftPrint(opts = {}) {
  readShift();
  let pages = [], n = 0, only = null;
  if (opts.only) {
    const o = CUR && CUR.ops.find(x => x.key === opts.only);
    if (!o) return 0;
    only = o; pages.push(`<div class="sk-page sk-op">${opCard(o, shiftCtx(CUR), {i: 0, n: 1})}</div>`); n = 1;
  } else {
    const ms = shiftPrintModels(), total = ms.reduce((s, m) => s + m.ops.length, 0);
    let i = 0;
    ms.forEach(m => {
      pages.push(summaryPage(m), allKpiPage(m));
      const ctx = shiftCtx(m);
      sortShift(m.trucks, 'haul').concat(sortShift(m.loaders, 'load')).forEach(o => pages.push(`<div class="sk-page sk-op">${opCard(o, ctx, {i: i++, n: total})}</div>`));
    });
    n = total + ms.length;
    if (!ms.length) return 0;
  }
  $('#pdfForms').innerHTML = pages.join('');
  pdfMode = 'shift'; document.body.classList.add('print-shift');
  injectPageStyle();
  document.title = `operator_kpis_${SH.date}${SH.sh ? '_' + SH.sh : ''}${SH.crew ? '_' + SH.crew.replace(/\s+/g, '') : ''}${only ? '_' + (only.operator_login || only.key) : ''}${SH.date === M.date_to ? '_partial' : ''}`;
  return n;
}
function endShiftPrint() {
  pdfMode = null; document.body.classList.remove('print-shift');
  const st = $('#pdfPageStyle'); if (st) st.remove();
  document.title = TITLE0; $('#pdfForms').innerHTML = '';
}
function injectPageStyle() {
  const old = $('#pdfPageStyle'); if (old) old.remove();
  const st = document.createElement('style'); st.id = 'pdfPageStyle'; st.textContent = '@page { size: A4 portrait; margin: 10mm 12mm; } @page wide { size: A4 landscape; margin: 9mm 10mm; }'; document.head.appendChild(st);
}
window.__shiftPdf = {prepare: prepareShiftPrint, end: endShiftPrint, count: () => { readShift(); return shiftPrintModels().reduce((s, m) => s + m.ops.length, 0); }};
window.__shiftSheet = {
  set: (d, s, c) => { $('#pdfDate').value = d; $('#pdfShift').value = s || ''; $('#pdfCrew').value = c || ''; renderShift(); },
  summary: (d, s, c) => { const m = shiftModel(d, s || '', c || ''); const p = o => ({id: o.key, operator: o.operator, role: o.role, loads: o.loads, loads_ld: o.loads_ld, h_prod: o.h_prod, hours_logged: o.hours_logged,
      rate: o.role === 'haul' ? o.loads_per_prod_h : o.loads_ld_per_prod_h, productive_pct: o.productive_pct, forms: o.forms, eq_shifts: o.eq_shifts, items_nok: o.items_nok,
      os_n: o.os_n, os_max: o.os_max, rk: o.rk, own_rate: o.own ? (o.role === 'haul' ? o.own.loads_per_prod_h : o.own.loads_ld_per_prod_h) : null});
    return {date: d, shift: s || '', noTel: m.noTel, trucks: m.trucks.map(p), loaders: m.loaders.map(p), aux: m.aux.length, loads: sum(m.rows.map(r => r.loads)),
      haulLoads: sum(m.haulRows.map(r => r.loads)), rate: m.fh.loads_per_prod_h, forms: m.forms.length, eqShifts: m.eqShifts, events: m.events.length,
      unattributed: m.unattributed.length, follow: m.follow.map(f => [f.cls, f.id]), base_rate: m.base.fleet.haul.loads_per_prod_h}; }};
function initShift() {
  $('#pdfDate').min = M.date_from; $('#pdfDate').max = M.date_to; $('#pdfDate').value = LAST_COMPLETE;
  fillSel('#pdfCrew', uniq(OPS.map(r => r.crew).concat(FORMS.map(f => f.crew))));
  $('#sRankBy').innerHTML = SRANK.map(([k, l]) => `<option value="${k}">${l}</option>`).join('');
  ['#pdfDate', '#pdfShift', '#pdfCrew', '#sRankBy', '#sView'].forEach(q => $(q).addEventListener('input', renderShift));
  $('#sPrev').onclick = () => { $('#pdfDate').value = addDays(SH.date, -1); renderShift(); };
  $('#sNext').onclick = () => { $('#pdfDate').value = addDays(SH.date, 1); renderShift(); };
  $('#sLast').onclick = () => { $('#pdfDate').value = LAST_COMPLETE; renderShift(); };
  $('#pdfFormsBtn').onclick = () => { if (prepareFormsPrint()) window.print(); };
  $('#shiftPdfBtn').onclick = () => { if (prepareShiftPrint()) window.print(); };
  $('#mClose').onclick = closeCard;
  $('#mPrint').onclick = () => { if (CARD && prepareShiftPrint({only: CARD.id})) window.print(); };
  $('#opModal').addEventListener('click', e => { if (e.target.id === 'opModal') closeCard(); });
  addEventListener('keydown', e => { if (e.key === 'Escape' && !$('#opModal').hidden) closeCard(); });
  document.addEventListener('click', e => { const a = e.target.closest && e.target.closest('a.op'); if (a) { e.preventDefault(); openCard(+a.dataset.id, a.dataset.scope || 'shift'); } });
}

function render() {
  readFilters();
  const rows = OPS.filter(passRow);
  const forms = FORMS.filter(passForm);
  updatePdfBtn();
  const days = []; for (let t = Date.parse(F.from + 'T00:00:00Z'); t <= Date.parse(F.to + 'T00:00:00Z'); t += 864e5) days.push(new Date(t).toISOString().slice(0, 10));
  const c1 = css('--series-1'), c2 = css('--series-2'), c3 = css('--series-3'), c5 = css('--series-5');

  // per-operator aggregates (named operators only), then the min-shifts and search filters
  let ops = aggregate(rows.filter(r => r.id_worker > 0 && r.operator), r => r.id_worker);
  ops.forEach(o => { const r = rows.find(x => x.id_worker === o.key); o.operator = r.operator; o.operator_login = r.operator_login; o.crew = r.crew; });
  ops = ops.filter(o => o.shifts_worked >= F.min && (!F.q || [o.operator, o.crew, o.equipment_used].join(' ').toLowerCase().includes(F.q)));
  applyRanks(ops.filter(o => o.role === 'haul'), 'haul'); applyRanks(ops.filter(o => o.role === 'load'), 'load');
  const pbase = baseline(F.from); ops.forEach(o => o.own = pbase.byOp.get(o.key) || null);
  PERIOD = {ops, from: F.from, to: F.to, shift: F.shift, med: {haul: medOf(ops.filter(o => o.role === 'haul')), load: medOf(ops.filter(o => o.role === 'load'))}};
  // over-speed events of the period (incl. events without a login), narrowed by the control-bar filters
  const eqSet = F.model ? new Set(rows.map(r => r.equipment)) : null, opSet0 = (F.op || F.crew) ? new Set(rows.map(r => r.id_worker)) : null;
  const osEv = !HAS_OS || F.role === 'load' ? [] : OSEV.filter(e => e.shift_date >= F.from && e.shift_date <= F.to && (!F.shift || e.shift === F.shift) && (!eqSet || eqSet.has(e.equipment)) && (!opSet0 || opSet0.has(e.id_worker)));

  // fleet-level numbers for the tiles (all rows of the period, including unattributed machine time)
  const fleet = finish(rows.reduce((o, r) => (addRow(o, r), o), newAgg('fleet')));
  const haulRows = rows.filter(r => r.role === 'haul'), loadRows = rows.filter(r => r.role === 'load');
  const byDay = (arr, f) => { const m = {}; arr.forEach(r => { m[r.shift_date] = (m[r.shift_date] || 0) + (f(r) || 0); }); return m; };
  const dLoads = byDay(haulRows, r => r.loads), dLoadsAll = byDay(rows, r => r.loads), dProdH = byDay(haulRows, r => r.h_prod), dProdL = byDay(loadRows, r => r.h_prod);
  const dAll = byDay(haulRows, r => r.h_prod + r.h_ready_other + r.h_delay + r.h_standby + r.h_maint), dAllL = byDay(loadRows, r => r.h_prod + r.h_ready_other + r.h_delay + r.h_standby + r.h_maint);
  const dForms = byDay(forms, () => 1), dItems = byDay(forms, f => f.n_items), dNok = byDay(forms, f => f.n_not_ok);
  const eqShiftsByDay = {}; rows.forEach(r => { if (worked(r) && r.role !== 'aux') { const s = eqShiftsByDay[r.shift_date] = eqShiftsByDay[r.shift_date] || new Set(); s.add(r.shift + '|' + r.id_equipo); } });
  const dEqS = Object.fromEntries(Object.entries(eqShiftsByDay).map(([d, s]) => [d, s.size]));
  const eqShiftsTot = sum(Object.values(dEqS));
  const opsHaul = uniq(haulRows.filter(r => r.id_worker > 0).map(r => r.id_worker)).length, opsLoad = uniq(loadRows.filter(r => r.id_worker > 0).map(r => r.id_worker)).length;
  const k = [
    ['Operators active', `${fmt(opsHaul)}<small>trucks</small> ${fmt(opsLoad)}<small>loaders</small>`, '', `${fmt(fleet.shifts_worked)} operator-shifts in the period`, null, ''],
    ['Cycles', fmt(fleet.loads), '', `${fmt(sum(haulRows.map(r => r.loads)))} by trucks · ${fmt(fleet.loads - sum(haulRows.map(r => r.loads)))} load-and-carry · ${fmt(fleet.tonnes)} nominal t`, days.map(d => dLoadsAll[d] || 0), ''],
    ['Cycles per productive hour', fmt(fleet.loads_per_prod_h, 2), '', `trucks · ${fmt(sum(haulRows.map(r => r.h_prod)), 0)} productive h`, days.map(d => dProdH[d] ? (dLoads[d] || 0) / dProdH[d] : 0), ''],
    ['Productive time', fmt(pct(sum(haulRows.map(r => r.h_prod)), sum(Object.values(dAll))), 0), '%', `trucks · loaders ${fmt(pct(sum(loadRows.map(r => r.h_prod)), sum(Object.values(dAllL))), 0)} %`, days.map(d => dAll[d] ? (dProdH[d] || 0) / dAll[d] * 100 : 0), ''],
    ['Checklist compliance', fmt(eqShiftsTot ? Math.min(100, forms.length / eqShiftsTot * 100) : null, 0), '%', `${fmt(forms.length)} forms · ${fmt(eqShiftsTot)} equipment-shifts worked`, days.map(d => dEqS[d] ? Math.min(100, (dForms[d] || 0) / dEqS[d] * 100) : 0), 'ok'],
    ['Items NOT OK', fmt(pct(sum(forms.map(f => f.n_not_ok)), sum(forms.map(f => f.n_items))), 1), '%', `${fmt(sum(forms.map(f => f.n_not_ok)))} of ${fmt(sum(forms.map(f => f.n_items)))} items`, days.map(d => dItems[d] ? (dNok[d] || 0) / dItems[d] * 100 : 0), 'alt'],
    ['Forms rejected / not reviewed', `${fmt(forms.filter(f => f.form_status === 'Rejected').length)}<small>/ ${fmt(forms.filter(f => f.form_status === 'Not reviewed').length)}</small>`, '', `${fmt(forms.filter(f => f.form_status === 'Approved').length)} approved`, null, 'crit'],
  ];
  const dOs = {}; osEv.forEach(e => dOs[e.shift_date] = (dOs[e.shift_date] || 0) + 1);
  if (HAS_OS) k.push(['Over-speed events', fmt(osEv.length), '', `${new Set(osEv.filter(e => e.id_worker > 0).map(e => e.id_worker)).size} operators · worst +${fmt(osEv.length ? Math.max(...osEv.map(e => e.over)) : 0, 1)} km/h · ≥ ${OS_RULE[0]} s at ≥ limit + ${OS_RULE[1]} km/h · telemetry to ${OS_TO}`, days.map(d => dOs[d] || 0), 'crit']);
  $('#kpis').innerHTML = k.map(([l, v, u, s, sp, cls]) => { const sv = sp ? spark(sp) : ''; return `<div class="kpi ${cls}${sv ? ' hasspark' : ''}"><div class="k">${l}</div><div class="v">${v}${u ? `<small>${u}</small>` : ''}</div><div class="s">${s}</div>${sv}</div>`; }).join('');
  $('#ovsub').textContent = `${F.from} → ${F.to}${F.shift ? ' · ' + F.shift : ''}${F.role ? ' · ' + (F.role === 'haul' ? 'truck operators' : 'loader operators') : ''}${F.crew ? ' · ' + F.crew : ''}`;

  $('#cTrendOsBox').hidden = !HAS_OS;

  // trends
  lineChart($('#cTrendRate'), days, [{name: 'cycles / productive h', color: c1, values: days.map(d => dProdH[d] ? (dLoads[d] || 0) / dProdH[d] : null)}], {w: 900, dec: 2});
  lineChart($('#cTrendProd'), days, [{name: 'trucks', color: c1, values: days.map(d => dAll[d] ? (dProdH[d] || 0) / dAll[d] * 100 : null)}, {name: 'loaders', color: c2, values: days.map(d => dAllL[d] ? (dProdL[d] || 0) / dAllL[d] * 100 : null)}], {unit: ' %', ymax: 100, dec: 0});
  if (HAS_OS) barChart($('#cTrendOs'), days, [{name: 'over-speed events', color: css('--status-critical'), values: days.map(d => OS_TO && d > OS_TO ? 0 : (dOs[d] || 0))}], {short: d => d.slice(5), emptyMsg: 'No over-speed events in the period.'});
  lineChart($('#cTrendChk'), days, [{name: 'compliance', color: c3, values: days.map(d => dEqS[d] ? Math.min(100, (dForms[d] || 0) / dEqS[d] * 100) : null)}], {unit: ' %', ymax: 100, dec: 0});
}

/* ---- section nav scroll-spy ------------------------------------------- */
(function () {
  const links = [...document.querySelectorAll('nav.toc a')];
  const ids = links.map(a => a.getAttribute('href').slice(1));
  const spy = () => { let on = ids[0]; for (const id of ids) { const e = document.getElementById(id); if (e && e.getBoundingClientRect().top <= 90) on = id; } links.forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + on)); };
  addEventListener('scroll', spy, {passive: true}); spy();
})();

/* ---- boot --------------------------------------------------------------- */
$('#chips').innerHTML = `<span class="chip">${fmt(FORMS.length)} checklists</span><span class="chip">${fmt(uniq(OPS.map(r => r.operator)).length)} operators</span><span class="chip">${fmt(sum(OPS.filter(r => r.role === 'haul').map(r => r.loads)))} cycles</span><span class="chip warn">tonnes are nominal (no payload scale)</span>`;
$('#foot').innerHTML = `Data: C4M ControlSenseDB — <code>ta_checklist</code> / <code>ta_checklistdetalle</code> / <code>ts_checkliststruc</code> (pre-start checklists), <code>tp_cargadescarga</code> (haul cycles; phases verified against the R4M cube), <code>tp_estados</code> + the R4M status dimension (READY / DELAY / STANDBY / MAINT.), <code>at_worker_login</code> (who was on which machine), <code>tp_trabajador</code>, <code>ta_guardias</code>${D.hasOverspeed ? `, over-speed events from the Over-speed page (truck telemetry ${M.os_from} → ${M.os_to}; events ≥ ${OS_RULE[0]} s with an average ≥ limit + ${OS_RULE[1]} km/h; the operator is the one logged in on the truck according to its own telemetry, with the login sessions as a fallback; events without a login are counted but not ranked)` : ''}. Shift sheet: ranks are within the role and the shift (ties share a rank; no combined score), &Delta; compares with the operator's own previous 30 shift days, the fleet median is the median of the operators ranked. Status rows without an end time are closed by the next status on the same machine (max 24 h); the newest shift may still be incomplete. Operators with fewer shifts than the minimum are hidden from the ranking but included in the fleet tiles. A wheel loader working load-and-carry (e.g. LO215 feeding the crusher) is both the loading and the hauling unit of its cycles, so they appear under "Cycles" and under "Cycles loaded". The bulk checklist PDF is produced by the browser's print-to-PDF (one A4 page per form, item order as in the C4M template). Built by operator_kpi/build_operator_kpi.py.`;
initFilters(); initShift(); render(); renderShift();
"""
