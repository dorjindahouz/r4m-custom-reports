"""Report customisation layer (window.TC) - CSS + JS injected into the page.

Answers Erdene's 2026-08-13 requests 10 (hide/show charts), 12 (blow a chart up
to a full page) and 11 (show/hide, reorder, rename and resize table columns and
rows).  One mechanism for both halves of the page:

  * a CSS layer  - a single generated <style id="tcStyle"> carrying every hide /
    order / width rule.  Tables and charts are re-rendered from scratch on every
    refresh, so anything expressed in CSS survives for free.
  * a DOM pass   - TC.apply(), run after each render, for the two things CSS
    cannot do: reordering rows/columns and renaming a header.

Renames are DISPLAY ALIASES only.  Row labels and input metric strings are exact
match lookup keys elsewhere in the page (rowByLabel, renderKPIs, buildCharts) and
a contract with "Report Inputs.xlsx", so TC never touches the source strings.

Preferences live under their own localStorage key: the inputs bundle
(erd_daily_report_inputs_v1) is exported and shared between people, and one
engineer's column widths must not travel with another's plan numbers.
"""

CUSTOM_CSS = r"""
  /* ---------------------------------------------- customisation layer (TC) */
  .chart{position:relative}
  .tcbar{position:absolute;top:6px;right:6px;display:flex;gap:3px;z-index:2;
         opacity:0;transition:opacity .12s}
  .chart:hover .tcbar,.tcbar:focus-within{opacity:1}
  .tcbar button,.tcgear{font:inherit;font-size:11px;line-height:1;cursor:pointer;
         border:1px solid #cdd4d9;background:#fff;color:#4a5257;border-radius:4px;
         padding:3px 6px}
  .tcbar button:hover,.tcgear:hover{background:#eef2f5;border-color:#9aa4ac}
  .tcgear{margin-left:8px}
  .tcoverlay{position:fixed;inset:0;background:rgba(14,18,22,.74);z-index:400;
         display:flex;align-items:center;justify-content:center;padding:18px}
  .tcbox{background:#fff;border-radius:8px;padding:14px 20px 12px;width:100%;
         max-width:2000px;max-height:97vh;overflow:auto;
         box-shadow:0 12px 44px rgba(0,0,0,.45);position:relative}
  .tcbox .chart{border:none;box-shadow:none;padding:0}
  .tcbox .chart h4{font-size:17px}
  .tcbox .clegend{font-size:13px}
  .tchead{display:flex;align-items:center;justify-content:space-between;gap:14px;
          margin-bottom:2px}
  .tchint{font-size:11.5px;color:#6b747b}
  .tcx{font-size:15px;line-height:1;border:1px solid #cdd4d9;background:#fff;
       border-radius:4px;padding:4px 9px;cursor:pointer}
  #customPanel .tcgrp{margin:10px 0 2px;font-weight:700;font-size:11px;
       letter-spacing:1px;text-transform:uppercase;color:#6b747b}
  #customPanel .tclist{display:grid;grid-template-columns:repeat(auto-fill,minmax(265px,1fr));
       gap:2px 18px;font-size:12px}
  #customPanel .tclist label{display:flex;align-items:center;gap:6px;cursor:pointer;
       padding:1px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  #customPanel .tcoff{color:#9aa1a7}
  .tcpop{position:absolute;z-index:410;background:#fff;border:1px solid #cdd4d9;
       border-radius:7px;box-shadow:0 8px 28px rgba(16,24,32,.28);padding:10px 12px 12px;
       width:392px;max-height:70vh;overflow:auto;font-size:12px}
  .tcpoph{display:flex;align-items:center;justify-content:space-between;gap:10px;
       margin-bottom:4px;font-size:12.5px}
  .tcsec{margin:9px 0 3px;font-weight:700;font-size:10.5px;letter-spacing:1px;
       text-transform:uppercase;color:#6b747b}
  .tcrow{display:flex;align-items:center;gap:5px;padding:1px 0}
  .tcrow.tcsub{padding-left:4px;opacity:.9}
  .tcdrag{cursor:grab;color:#9aa4ac;user-select:none;font-size:13px;line-height:1}
  .tcname{flex:1 1 auto;min-width:0;font:inherit;font-size:11.5px;padding:2px 5px;
       border:1px solid #dde3e7;border-radius:3px}
  .tcw{width:52px;font:inherit;font-size:11.5px;padding:2px 4px;border:1px solid #dde3e7;
       border-radius:3px}
  .tcbtns{display:flex;justify-content:flex-end;margin-top:9px}
  .tcbtns button{font:inherit;font-size:11.5px;padding:3px 9px;cursor:pointer;
       border:1px solid #cdd4d9;background:#fff;border-radius:4px}
  @media print{
    .tcbar,.tcgear,.tcoverlay,.tcpop,#customPanel{display:none !important}
  }
"""

CUSTOM_JS = r"""
"use strict";
/* window.TC - see customize_template.py for the contract. Loaded BEFORE the
   report/atlas IIFEs in the combined build, and after them in the standalone
   report build, so every entry point is idempotent and self-healing. */
(function(){
  var KEY = "erd_report_custom_v1";
  var TC = window.TC = {charts: new Map(), tables: new Map(), prefs: null};

  function blank(){ return {v: 1, charts: {}, tables: {}}; }
  TC.load = function(){
    try{
      var p = JSON.parse(localStorage.getItem(KEY) || "null");
      TC.prefs = (p && p.v === 1) ? p : blank();
    }catch(e){ TC.prefs = blank(); }
    if (!TC.prefs.charts) TC.prefs.charts = {};
    if (!TC.prefs.tables) TC.prefs.tables = {};
    return TC.prefs;
  };
  TC.save = function(){
    try{ localStorage.setItem(KEY, JSON.stringify(TC.prefs)); }
    catch(e){ console.warn("layout prefs not saved", e); }
    TC.applyCss(); TC.renderPanel();
  };
  TC.load();

  var cp = function(ck){ return TC.prefs.charts[ck] || (TC.prefs.charts[ck] = {}); };
  var tp = function(id){
    var t = TC.prefs.tables[id] || (TC.prefs.tables[id] = {cols: {}, rows: {}});
    if (!t.cols) t.cols = {};
    if (!t.rows) t.rows = {};
    return t;
  };

  /* ------------------------------------------------------------ CSS layer */
  TC.applyCss = function(){
    var css = [];
    for (var ck in TC.prefs.charts){
      var c = TC.prefs.charts[ck];
      var sel = '.chart[data-ck="' + ck + '"]';
      if (c.hidden) css.push(sel + '{display:none !important}');
      if (c.order !== undefined && c.order !== null) css.push(sel + '{order:' + (+c.order) + '}');
    }
    for (var id in TC.prefs.tables){
      var t = TC.prefs.tables[id], k;
      for (k in (t.cols || {})){
        var col = t.cols[k], cs = '#' + id + ' [data-c="' + k + '"]';
        if (col.hidden) css.push(cs + '{display:none !important}');
        else if (col.w) css.push(cs + '{width:' + (+col.w) + 'px;max-width:' + (+col.w) + 'px}');
      }
      for (k in (t.rows || {})){
        if (t.rows[k].hidden) css.push('#' + id + ' tr[data-rk="' + k + '"]{display:none !important}');
      }
      /* row height: the request asks for width AND height, and for a table the
         useful axis is row density rather than a pixel height per row */
      if (t.rh) css.push('#' + id + ' td, #' + id + ' th{padding-top:' + (+t.rh) +
                         'px;padding-bottom:' + (+t.rh) + 'px}');
    }
    var el = document.getElementById("tcStyle");
    if (!el){
      el = document.createElement("style"); el.id = "tcStyle";
      document.head.appendChild(el);
    }
    el.textContent = css.join("\n");
  };
  TC.applyCss();          /* hide rules must exist before the first chart paints */

  /* ------------------------------------------------------- chart registry */
  TC.registerChart = function(div){
    var ck = div.dataset.ck;
    if (!ck) return;
    var h4 = div.querySelector("h4");
    var host = div.parentNode;
    TC.charts.set(ck, {title: h4 ? h4.textContent : ck,
                       group: (host && host.id) || "charts"});
    /* :scope > - the polygon-detail panel is a .chart that CONTAINS a .chart, so
       a plain descendant query would find the inner one and skip the outer */
    if (!div.querySelector(":scope > .tcbar")){
      var bar = document.createElement("div");
      bar.className = "tcbar noprint";
      /* only charts drawn by drawChart can be re-drawn at another size */
      bar.innerHTML = (div.__draw ? '<button type="button" title="Show this chart full page">&#10530;</button>' : "") +
                      '<button type="button" title="Hide this chart">&#10005;</button>';
      var btns = bar.querySelectorAll("button");
      if (div.__draw) btns[0].addEventListener("click", function(){ TC.zoom(div); });
      btns[btns.length - 1].addEventListener("click", function(){ cp(ck).hidden = true; TC.save(); });
      div.appendChild(bar);
    }
    if (!TC._panelQueued){
      TC._panelQueued = true;
      setTimeout(function(){ TC._panelQueued = false; TC.renderPanel(); }, 0);
    }
  };

  /* ---------------------------------------------------- full-page overlay */
  TC.zoom = function(div){
    if (!div || !div.__cfg || !div.__draw) return;
    TC.closeZoom();
    var ov = document.createElement("div");
    ov.className = "tcoverlay noprint";
    ov.innerHTML = '<div class="tcbox"><div class="tchead">' +
      '<span class="tchint">Full-page view &mdash; press Esc or click outside to close</span>' +
      '<button type="button" class="tcx" title="Close">&#10005;</button></div>' +
      '<div class="tcbody"></div></div>';
    document.body.appendChild(ov);
    var body = ov.querySelector(".tcbody");
    var render = function(){
      body.innerHTML = "";
      var cfg = Object.assign({}, div.__cfg, {
        W: Math.round(Math.min(Math.max(window.innerWidth * 0.9, 900), 2000)),
        H: Math.round(Math.min(Math.max(window.innerHeight * 0.72, 380), 1020)),
        fs: 13});
      div.__draw(body, cfg);
      var b = body.querySelector(".tcbar"); if (b) b.remove();
    };
    render();
    var onKey = function(e){ if (e.key === "Escape") TC.closeZoom(); };
    var onResize = function(){ clearTimeout(TC._rz); TC._rz = setTimeout(render, 180); };
    ov.addEventListener("click", function(e){ if (e.target === ov) TC.closeZoom(); });
    ov.querySelector(".tcx").addEventListener("click", TC.closeZoom);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    TC._ov = ov;
    TC._ovOff = function(){
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  };
  TC.closeZoom = function(){
    if (!TC._ov) return;
    TC._ovOff(); TC._ov.remove(); TC._ov = null; TC._ovOff = null;
  };

  /* ------------------------------------------------------- table registry */
  /* A "unit" is one column of the FIRST header row. #tblMP / #tblMF have a split
     header, so the "Today" unit spans the DS and NS cells: it moves as one block
     and its members can be hidden individually but not moved out of the group. */
  /* Some atlas tables put a full-width caption in the first header row
     ("Worst polygons…"), so the real headers are the first row with more than
     one cell; the row after that, if any, holds a grouped header's members. */
  function headRows(tbl){
    if (!tbl.tHead || !tbl.tHead.rows.length) return null;
    var rows = tbl.tHead.rows, i = 0;
    while (i < rows.length - 1 && rows[i].cells.length <= 1) i++;
    return {head: rows[i], sub: rows[i + 1] || null, caption: i ? rows[0].textContent.trim() : ""};
  }
  function tableUnits(tbl){
    var hr = headRows(tbl);
    var head = hr && hr.head;
    if (!head || head.cells.length < 2) return [];
    var row2 = hr.sub, units = [], sub = 0;
    for (var i = 0; i < head.cells.length; i++){
      /* the ORIGINAL span, remembered once: TC itself shrinks a group's colspan
         when a member is hidden, so reading the live value would be self-locking */
      var th = head.cells[i];
      if (th.dataset.span0 === undefined) th.dataset.span0 = th.colSpan || 1;
      if (th.dataset.ord0 === undefined) th.dataset.ord0 = i;   /* the source order */
      var span = +th.dataset.span0, grouped = span > 1 && !!row2, members = [];
      if (grouped){
        for (var j = 0; j < span; j++){
          var st = row2.cells[sub + j];
          if (st) members.push({key: st.dataset.c || ("c" + (sub + j)), th: st});
        }
        sub += span;
      } else {
        members.push({key: th.dataset.c || ("c" + i), th: th});
      }
      units.push({key: th.dataset.c || ("u" + i), th: th, label: th.textContent.trim(),
                  members: members, grouped: grouped, ord0: +th.dataset.ord0});
    }
    return units;
  }
  TC.registerTable = function(tbl){
    if (!tbl || !tbl.id) return;
    var units = tableUnits(tbl);
    if (!units.length) return;
    var prev = tbl.previousElementSibling;
    while (prev && /tablectl/.test(prev.className || "")) prev = prev.previousElementSibling;
    var cap = (headRows(tbl) || {}).caption;
    TC.tables.set(tbl.id, {
      /* the atlas tables have flat headers and no data-c on their cells, so they
         are addressed by position: hide/width/rename work, reordering does not */
      positional: !tbl.querySelector("tbody [data-c]"),
      caption: cap || ((prev && /banner|mdhead|subhead/.test(prev.className || ""))
                       ? prev.textContent.trim() : tbl.id),
      units: units.map(function(u){
        return {key: u.key, label: u.label, grouped: u.grouped,
                members: u.members.map(function(x){
                  return {key: x.key, label: x.th.textContent.trim()};
                })};
      }),
      rows: [].slice.call(tbl.querySelectorAll("tbody tr[data-rk]")).map(function(tr){
        return {rk: tr.dataset.rk,
                label: (tr.cells[0] ? tr.cells[0].textContent.trim() : tr.dataset.rk)};
      })
    });
    if (!tbl.__tcGear) TC.addGear(tbl);
  };
  TC.addGear = function(tbl){
    tbl.__tcGear = 1;
    var bar = tbl.previousElementSibling;
    if (!bar || !/tablectl/.test(bar.className || "")){
      bar = document.createElement("div");
      bar.className = "tablectl noprint";
      tbl.parentNode.insertBefore(bar, tbl);
    }
    var b = document.createElement("button");
    b.type = "button"; b.className = "tcgear"; b.textContent = "⚙ Columns";
    b.title = "Show, hide, rename, resize or reorder this table's columns and rows";
    b.addEventListener("click", function(){ TC.tablePopover(tbl.id, b); });
    bar.appendChild(b);
  };

  /* -------------------------------------------------- DOM pass: order + names */
  TC.apply = function(){
    TC._busy = 1;
    try{
      TC.tables.forEach(function(info, id){ applyTable(id); });
      for (var id in TC.prefs.tables) if (!TC.tables.has(id)) applyTable(id);
    } finally { TC._busy = 0; }
  };
  function applyTable(id){
    var tbl = document.getElementById(id), pr = TC.prefs.tables[id] || {cols: {}, rows: {}};
    if (!tbl) return;
    var units = tableUnits(tbl), cols = pr.cols || {}, i;
    /* renames */
    for (i = 0; i < units.length; i++){
      var u = units[i], c = cols[u.key];
      if (u.th.dataset.lbl0 === undefined) u.th.dataset.lbl0 = u.th.textContent;
      var want = (c && c.label) || u.th.dataset.lbl0;
      if (u.th.textContent !== want) u.th.textContent = want;
      for (var k = 0; k < u.members.length; k++){
        var mth = u.members[k].th, mc = cols[u.members[k].key];
        if (mth.dataset.lbl0 === undefined) mth.dataset.lbl0 = mth.textContent;
        var mw = (mc && mc.label) || mth.dataset.lbl0;
        if (mth.textContent !== mw) mth.textContent = mw;
      }
      /* a grouped header shrinks to the number of visible members */
      if (u.grouped){
        var vis = u.members.filter(function(x){ return !(cols[x.key] || {}).hidden; }).length;
        u.th.colSpan = Math.max(vis, 1);
        u.th.style.display = vis ? "" : "none";
      }
    }
    if (!tbl.querySelector("tbody [data-c]")){
      /* positional table: apply hide + width straight to the cells at that index */
      var tb = tbl.tBodies[0];
      units.forEach(function(u, ci){
        var c = cols[u.key] || {};
        u.th.style.display = c.hidden ? "none" : "";
        u.th.style.width = c.w ? (+c.w) + "px" : "";
        if (!tb) return;
        for (var r = 0; r < tb.rows.length; r++){
          var cell = tb.rows[r].cells[ci];
          if (cell) cell.style.display = c.hidden ? "none" : "";
        }
      });
      return;
    }
    /* order: permute the first header row and every body row in step */
    var ord = units.map(function(u, idx){
      var c = cols[u.key] || {};
      return {u: u, idx: idx, o: (c.order === undefined || c.order === null) ? u.ord0 : +c.order};
    });
    var sorted = ord.slice().sort(function(a, b){ return a.o - b.o || a.idx - b.idx; });
    var changed = sorted.some(function(x, n){ return x.idx !== n; });
    if (changed){
      var head = (headRows(tbl) || {}).head;
      sorted.forEach(function(x){ head.appendChild(x.u.th); });
      var bodyRows = tbl.tBodies[0] ? tbl.tBodies[0].rows : [];
      for (var r = 0; r < bodyRows.length; r++){
        var tr = bodyRows[r], byKey = {};
        for (var cN = 0; cN < tr.cells.length; cN++){
          var kk = tr.cells[cN].dataset.c || ("c" + cN);
          byKey[kk] = tr.cells[cN];
        }
        sorted.forEach(function(x){
          x.u.members.forEach(function(mm){ if (byKey[mm.key]) tr.appendChild(byKey[mm.key]); });
        });
      }
    }
    /* row order */
    var rp = pr.rows || {}, body = tbl.tBodies[0];
    if (body){
      var trs = [].slice.call(body.querySelectorAll("tr[data-rk]"));
      var ro = trs.map(function(tr, idx){
        var c = rp[tr.dataset.rk] || {};
        return {tr: tr, idx: idx, o: (c.order === undefined || c.order === null) ? idx : +c.order, lbl: c.label};
      });
      ro.forEach(function(x){ if (x.lbl && x.tr.cells[0]) x.tr.cells[0].textContent = x.lbl; });
      var rs = ro.slice().sort(function(a, b){ return a.o - b.o || a.idx - b.idx; });
      if (rs.some(function(x, n){ return x.idx !== n; }))
        rs.forEach(function(x){ body.appendChild(x.tr); });
    }
  }

  /* the atlas half re-renders its tables from its own handlers, so watch them */
  TC.observe = function(el){
    if (!el || el.__tcObs || typeof MutationObserver === "undefined") return;
    el.__tcObs = 1;
    var mo = new MutationObserver(function(){
      if (TC._busy) return;
      clearTimeout(el.__tcT);
      el.__tcT = setTimeout(TC.sweep, 80);
    });
    mo.observe(el, {childList: true, subtree: true});
  };

  /* ------------------------------------------------------- table popover */
  TC.tablePopover = function(id, anchor){
    var open = document.querySelector(".tcpop");
    if (open) open.remove();
    var info = TC.tables.get(id);
    if (!info) return;
    var pr = tp(id);
    var pop = document.createElement("div");
    pop.className = "tcpop noprint";
    var drag = !info.positional;
    var h = '<div class="tcpoph"><b>' + esc(info.caption) + "</b>" +
            '<button type="button" class="tcx tcpopx">&#10005;</button></div>' +
            '<div class="tchint">' + (drag ? "Drag &#8942; to reorder. " : "") +
            'Renaming only changes what is displayed.</div>' +
            '<div class="tcsec">Columns</div><div class="tccols">';
    info.units.forEach(function(u){
      var c = pr.cols[u.key] || {};
      h += '<div class="tcrow"' + (drag ? ' draggable="true"' : "") + ' data-u="' + esc(u.key) + '">' +
           (drag ? '<span class="tcdrag">&#8942;</span>' : "") +
           '<input type="checkbox" data-col="' + esc(u.key) + '"' + (c.hidden ? "" : " checked") + ">" +
           '<input type="text" class="tcname" data-col="' + esc(u.key) + '" value="' + esc(c.label || u.label) + '">' +
           '<input type="number" class="tcw" data-col="' + esc(u.key) + '" placeholder="auto" min="30" max="400" value="' + (c.w || "") + '">px</div>';
      if (u.grouped) u.members.forEach(function(m){
        var mc = pr.cols[m.key] || {};
        h += '<div class="tcrow tcsub"><span class="tcdrag" style="visibility:hidden">&#8942;</span>' +
             '<input type="checkbox" data-col="' + esc(m.key) + '"' + (mc.hidden ? "" : " checked") + ">" +
             '<input type="text" class="tcname" data-col="' + esc(m.key) + '" value="' + esc(mc.label || m.label) + '">' +
             '<span class="tchint">in ' + esc(u.label) + "</span></div>";
      });
    });
    h += "</div>";
    if (info.rows.length){
      h += '<div class="tcsec">Rows</div><div class="tcrows">';
      info.rows.forEach(function(r){
        var c = pr.rows[r.rk] || {};
        h += '<div class="tcrow" draggable="true" data-r="' + esc(r.rk) + '"><span class="tcdrag">&#8942;</span>' +
             '<input type="checkbox" data-row="' + esc(r.rk) + '"' + (c.hidden ? "" : " checked") + ">" +
             '<input type="text" class="tcname" data-row="' + esc(r.rk) + '" value="' + esc(c.label || r.label) + '"></div>';
      });
      h += "</div>";
    }
    var RH = [["", "Normal"], ["1", "Compact"], ["6", "Tall"]];
    h += '<div class="tcsec">Row height</div><div class="tcrow"><select class="tcrh">' +
         RH.map(function(o){
           return '<option value="' + o[0] + '"' +
                  (String(pr.rh || "") === o[0] ? " selected" : "") + ">" + o[1] + "</option>";
         }).join("") + "</select></div>";
    h += '<div class="tcbtns"><button type="button" class="tcreset">Reset this table</button></div>';
    pop.innerHTML = h;
    document.body.appendChild(pop);
    var b = anchor.getBoundingClientRect();
    pop.style.top = (window.scrollY + b.bottom + 6) + "px";
    pop.style.left = Math.max(8, Math.min(window.scrollX + b.left, window.scrollX + window.innerWidth - 400)) + "px";

    pop.querySelector(".tcpopx").addEventListener("click", function(){ pop.remove(); });
    pop.querySelectorAll("input[data-col]").forEach(function(inp){
      inp.addEventListener("change", function(){
        var k = inp.dataset.col, c = pr.cols[k] = pr.cols[k] || {};
        if (inp.type === "checkbox"){
          c.hidden = !inp.checked;
          var unit = info.units.filter(function(u){ return u.key === k; })[0];
          if (unit && unit.grouped)          /* body cells carry the member keys */
            unit.members.forEach(function(m){ (pr.cols[m.key] = pr.cols[m.key] || {}).hidden = c.hidden; });
        }
        else if (inp.classList.contains("tcw")) c.w = inp.value ? +inp.value : null;
        else c.label = inp.value;
        TC.save(); TC.apply();
      });
    });
    pop.querySelectorAll("input[data-row]").forEach(function(inp){
      inp.addEventListener("change", function(){
        var k = inp.dataset.row, c = pr.rows[k] = pr.rows[k] || {};
        if (inp.type === "checkbox") c.hidden = !inp.checked; else c.label = inp.value;
        TC.save(); TC.apply();
      });
    });
    pop.querySelector(".tcrh").addEventListener("change", function(){
      pr.rh = this.value ? +this.value : null;
      TC.save();
    });
    pop.querySelector(".tcreset").addEventListener("click", function(){
      delete TC.prefs.tables[id];
      TC.save();
      if (window.RPT && RPT.refresh) RPT.refresh(false); else TC.apply();
      pop.remove();
    });
    wireDrag(pop, ".tccols", "u", function(order){
      order.forEach(function(k, i){ (pr.cols[k] = pr.cols[k] || {}).order = i; });
      TC.save(); TC.apply();
    });
    wireDrag(pop, ".tcrows", "r", function(order){
      order.forEach(function(k, i){ (pr.rows[k] = pr.rows[k] || {}).order = i; });
      TC.save(); TC.apply();
    });
  };

  /* drag reordering happens on the popover list, never on real <th> elements -
     dragging a header would fight the atlas tables' sort-on-click handlers */
  function wireDrag(pop, sel, attr, done){
    var list = pop.querySelector(sel);
    if (!list) return;
    var dragging = null;
    list.querySelectorAll("[draggable]").forEach(function(row){
      row.addEventListener("dragstart", function(){ dragging = row; row.style.opacity = ".4"; });
      row.addEventListener("dragend", function(){
        row.style.opacity = "";
        done([].slice.call(list.querySelectorAll("[draggable]")).map(function(r){ return r.dataset[attr]; }));
      });
      row.addEventListener("dragover", function(e){
        e.preventDefault();
        if (!dragging || dragging === row) return;
        var r = row.getBoundingClientRect();
        list.insertBefore(dragging, (e.clientY - r.top) / r.height > 0.5 ? row.nextSibling : row);
      });
    });
  }

  TC.renderTablePanel = function(){
    var host = document.getElementById("tcTableList");
    if (!host) return;
    var h = "";
    TC.tables.forEach(function(info, id){
      var pr = TC.prefs.tables[id] || {cols: {}, rows: {}};
      var hid = Object.keys(pr.cols || {}).filter(function(k){ return pr.cols[k].hidden; }).length +
                Object.keys(pr.rows || {}).filter(function(k){ return pr.rows[k].hidden; }).length;
      h += '<label><button type="button" class="tcgear" data-tbl="' + esc(id) + '">&#9881;</button> ' +
           esc(info.caption) + (hid ? ' <span class="tcoff">(' + hid + " hidden)</span>" : "") + "</label>";
    });
    host.innerHTML = h ? '<div class="tcgrp">Tables</div><div class="tclist">' + h + "</div>" : "";
    host.querySelectorAll("button[data-tbl]").forEach(function(b){
      b.addEventListener("click", function(){ TC.tablePopover(b.dataset.tbl, b); });
    });
  };

  /* ------------------------------------------------------- control panel */
  var GROUP_NAME = {
    chartsMP: "Mine production", chartsMF: "Mill feeding", chartsEXC: "Excavators",
    chartsDigc: "Dig compliance",
    chartsEquipLoad: "Equipment - loading", chartsEquipHaul: "Equipment - hauling",
    chartsCrew: "Crew & operators", chartsCycle: "Cycle anatomy", chartsHaul: "Haul efficiency",
    chartsAux: "Auxiliary equipment", chartsManual: "Manual data"
  };
  TC.renderPanel = function(){
    var host = document.getElementById("tcChartList");
    if (!host) return;
    var groups = {};
    TC.charts.forEach(function(info, ck){
      (groups[info.group] = groups[info.group] || []).push([ck, info.title]);
    });
    var keys = Object.keys(groups).sort();
    var html = "", nOff = 0;
    for (var i = 0; i < keys.length; i++){
      var g = keys[i], items = groups[g];
      items.sort(function(a, b){ return a[1] < b[1] ? -1 : 1; });
      html += '<div class="tcgrp">' + esc(GROUP_NAME[g] || g) + "</div><div class=\"tclist\">";
      for (var j = 0; j < items.length; j++){
        var ck = items[j][0], on = !(TC.prefs.charts[ck] || {}).hidden;
        if (!on) nOff++;
        html += '<label' + (on ? "" : ' class="tcoff"') + ' title="' + esc(items[j][1]) + '">' +
                '<input type="checkbox" data-ck="' + esc(ck) + '"' + (on ? " checked" : "") + ">" +
                esc(items[j][1]) + "</label>";
      }
      html += "</div>";
    }
    host.innerHTML = html || '<div class="tchint">No charts rendered yet.</div>';
    host.querySelectorAll("input[data-ck]").forEach(function(inp){
      inp.addEventListener("change", function(){
        cp(inp.dataset.ck).hidden = !inp.checked;
        TC.save();
      });
    });
    var cnt = document.getElementById("tcHiddenCount");
    if (cnt) cnt.textContent = nOff ? nOff + " chart(s) hidden" : "";
    TC.renderTablePanel();
  };

  function esc(s){ return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); }

  /* ------------------------------------------------------------- resets */
  TC.showAllCharts = function(){
    for (var ck in TC.prefs.charts) delete TC.prefs.charts[ck].hidden;
    TC.save();
  };
  TC.reset = function(){
    TC.prefs = blank();
    try{ localStorage.removeItem(KEY); }catch(e){}
    TC.applyCss(); TC.renderPanel();
    if (window.RPT && RPT.refresh) RPT.refresh(false);
    if (window.ATL && ATL.refreshPeriod) try{ ATL.refreshPeriod(); }catch(e){}
  };

  /* ------------------------------------------------------------- sweep */
  /* Charts and tables appear at very different times: the report renders after
     its live fetch, the atlas after its own, and both re-render on demand. One
     idempotent sweep picks up whatever is on the page now. */
  TC.sweep = function(){
    if (TC._sweeping) return;
    TC._sweeping = 1;
    try{
      document.querySelectorAll(".chart[data-ck]").forEach(TC.registerChart);
      document.querySelectorAll("table.rep[id], table.x[id]").forEach(TC.registerTable);
      TC.apply();
    } finally { TC._sweeping = 0; }
  };

  /* -------------------------------------------------------------- boot */
  TC.boot = function(){
    TC.applyCss();
    TC.sweep();
    document.querySelectorAll(".atlaspart").forEach(TC.observe);
    var a = document.getElementById("tcShowAll"), b = document.getElementById("tcResetAll");
    if (a && !a.__w){ a.__w = 1; a.addEventListener("click", TC.showAllCharts); }
    if (b && !b.__w){ b.__w = 1; b.addEventListener("click", function(){
      if (confirm("Reset every layout change (hidden charts, columns, widths, names)?")) TC.reset();
    }); }
    TC.renderPanel();
  };
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", TC.boot);
  else TC.boot();
})();
"""
