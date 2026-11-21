"""Manual data: figures that exist in the mine but not in R4M.

Answers three of Erdene's 2026-08-13 requests with one engine:

  04  auxiliary equipment (dozers, graders, mobile crusher, blast drills).
      R4M's fleet master holds 27 machines - 18 haul trucks, 8 loading units
      and one crusher - and no dozer/grader/drill/water truck exists anywhere in
      the data, so these can only be typed in until IT registers them upstream.
  05  surveyor (marksheider) measurements, taken weekly and on the 1st, and the
      survey-vs-dispatch reconciliation they are actually for.
  09  anything else the system does not record, e.g. mill tailings.

All three are the same shape - a named series with a unit and a value per date -
so they share one store, one editor grid, one Excel round-trip and one renderer.

Store (inside the existing `inputs` object, so it exports/imports with the rest):

    inputs.manual.defs  [{key, name, unit, group, kind, cmp}]
    inputs.manual.vals  {key: {"YYYY-MM-DD": number}}
    inputs.aux.machines [{id, name, type, wname, wunit}]

Auxiliary machines need no defs: their four series are derived from the machine
id (aux:<id>:oph | dth | work | fuel), so adding a machine cannot desynchronise
the two lists.

`kind` drives the reconciliation: "flow" values are what moved since the previous
survey date, "stock" values are a standing balance measured on that date.
"""

# --------------------------------------------------------------- build side
from master_template import master_defs  # noqa: E402

AUX_TYPES = ["Dozer", "Grader", "Mobile Crusher", "Blast drill", "Water truck",
             "Excavator", "Loader", "Truck", "Other"]

# survey rows seeded per R4M material code, plus the two plant-side totals
SURVEY_EXTRA = [("sv_millfeed", "Survey mill feed", "t", "flow", "MILLFEED"),
                ("sv_romstock", "Survey ROM stock balance", "t", "stock", "ROMSTOCK"),
                # per-class ROM balances, for the Master Report's section 5 "MTD (SURVEY)"
                ("sv_rom_hg", "Survey ROM balance HG", "t", "stock", "ROMCLS:HG"),
                ("sv_rom_mg", "Survey ROM balance MG", "t", "stock", "ROMCLS:MG"),
                ("sv_rom_lg2", "Survey ROM balance LG2", "t", "stock", "ROMCLS:LG2"),
                ("sv_rom_lg1", "Survey ROM balance LG1", "t", "stock", "ROMCLS:LG1"),
                # the plant's month-end reconciled feed per class, for section 7 "MTD (SURVEY)"
                ("sv_ff_hg", "Survey mill feed HG", "t", "flow", "MILLFEED:HG"),
                ("sv_ff_mg", "Survey mill feed MG", "t", "flow", "MILLFEED:MG"),
                ("sv_ff_lg2", "Survey mill feed LG2", "t", "flow", "MILLFEED:LG2"),
                ("sv_ff_lg1", "Survey mill feed LG1", "t", "flow", "MILLFEED:LG1")]
OTHER_SEED = [("ot_tailings", "Mill tailings", "t", "flow", "")]


def seed_manual(lcm):
    """Default manual-series definitions, derived from the LCM material list."""
    defs = []
    for code, row in (lcm or {}).items():
        defs.append({"key": "sv_" + code.lower(), "name": "Survey %s" % (row.get("name") or code),
                     "unit": "t", "group": "survey", "kind": "flow", "cmp": code})
    for key, name, unit, kind, cmp_ in SURVEY_EXTRA:
        defs.append({"key": key, "name": name, "unit": unit, "group": "survey",
                     "kind": kind, "cmp": cmp_})
    for key, name, unit, kind, cmp_ in OTHER_SEED:
        defs.append({"key": key, "name": name, "unit": unit, "group": "other",
                     "kind": kind, "cmp": cmp_})
    defs += master_defs()
    return {"defs": defs, "vals": {}}


# groups whose seeded series are re-added when a saved / published list lacks them
# ("other" stays user-managed: a series someone deleted must not come back)
SEEDED_GROUPS = ("survey", "master")


def merge_defs(incoming, seeded):
    """a saved series list (published plan, browser) + the seeded series it predates"""
    keys = {d.get("key") for d in incoming}
    return list(incoming) + [d for d in seeded if d.get("group") in SEEDED_GROUPS and d.get("key") not in keys]


# ------------------------------------------------------------------ page CSS

MANUAL_CSS = r"""
  /* ------------------------------------------------- manual data (04/05/09) */
  .mdhead{font-size:13px;font-weight:700;letter-spacing:1.6px;margin:20px 0 0;
          text-transform:uppercase;color:#5c6166}
  .mdempty{border:1px dashed #c3cbd1;border-radius:6px;padding:14px 16px;
           background:#fbfcfd;color:#5c6166;font-size:12.5px;margin-top:10px}
  .mdempty b{color:var(--ink)}
  .mdcard{border:1px solid #e2e7ea;border-radius:6px;background:#fff;padding:10px 14px 4px;
          box-shadow:0 1px 3px rgba(16,24,32,.08);break-inside:avoid;margin-top:14px}
  .mdcard>h4{margin:0 0 2px;font-size:13.5px}
  .mdcard .mdsub{font-size:11.5px;color:#6b747b;margin-bottom:6px}
  .mdkpis{display:flex;flex-wrap:wrap;gap:6px 22px;font-size:12px;margin:2px 0 8px}
  .mdkpis span b{font-variant-numeric:tabular-nums}
  .mdadd{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0 2px;font-size:12px}
  .mdadd input,.mdadd select{font:inherit;font-size:12px;padding:3px 6px;border:1px solid #c3cbd1;
          border-radius:4px}
  .mdadd input[type=text]{width:130px}
  table.edit td.mdname{text-align:left;white-space:nowrap}
  table.edit .mddel{cursor:pointer;color:#a33;border:none;background:none;font-size:13px;padding:0 4px}
  table.rep td.mdvpos{color:#0a7a33}
  @media print{
    /* an empty section would print as a banner with nothing under it */
    body.md-empty #secManual,body.md-empty #mdIntro,body.md-empty #mdAux,
    body.md-empty #mdSurvey,body.md-empty #mdOther,
    body.nd-empty #secNotes,body.nd-empty #ndList{display:none !important}
    .mdempty{display:none !important}
  }
  table.rep td.mdvneg{color:#b00000}
"""

# ------------------------------------------------- editor grids (inputs panel)

MANUAL_INPUTS_HTML = r"""
    <h3>Auxiliary equipment &mdash; machines R4M does not track</h3>
    <div class="mdadd">
      <input type="text" id="auxName" placeholder="Machine name" maxlength="24">
      <select id="auxType"></select>
      <input type="text" id="auxWork" placeholder="Work done (label)" maxlength="22">
      <input type="text" id="auxUnit" placeholder="unit" maxlength="10">
      <button type="button" id="auxAdd">Add machine</button>
    </div>
    <div class="scrollx"><table class="edit" id="tblAux"></table></div>

    <h3>Surveyor measurements &mdash; <span id="svMonthLbl"></span></h3>
    <div class="mdadd">
      <input type="date" id="svNewDate">
      <button type="button" id="svAddDate">Add survey date</button>
    </div>
    <div class="scrollx"><table class="edit" id="tblSurvey"></table></div>

    <h3>Other figures not registered in the system</h3>
    <div class="mdadd">
      <input type="text" id="otName" placeholder="Series name" maxlength="36">
      <input type="text" id="otUnit" placeholder="unit" maxlength="10">
      <input type="date" id="otNewDate">
      <button type="button" id="otAdd">Add series</button>
      <button type="button" id="otAddDate">Add date</button>
    </div>
    <div class="scrollx"><table class="edit" id="tblOther"></table></div>
"""

# ---------------------------------------------------------- report section

MANUAL_SECTION_HTML = r"""
  <div class="banner" id="secManual">MANUAL DATA &mdash; AUXILIARY EQUIPMENT, SURVEY &amp; OFF-SYSTEM FIGURES</div>
  <div class="note" id="mdIntro">Everything in this section is typed into the <b>Inputs</b> panel at the foot of the page, not measured by R4M. It follows the selected reporting period; it is never split by shift.</div>
  <div id="mdAux"></div>
  <div id="mdSurvey"></div>
  <div id="mdOther"></div>
"""

# ------------------------------------------------------------------ page JS

MANUAL_JS = r"""
/* ============================================ manual data (requests 04/05/09)
   One store, one editor, one renderer for auxiliary equipment, survey
   measurements and off-system series. See manual_template.py for the contract. */
const AUX_TYPES = __AUX_TYPES__;
const AUX_METRICS = [["oph", "Operating hours", "h"], ["dth", "Downtime", "h"],
                     ["work", "Work done", ""], ["fuel", "Fuel", "L"]];
const MD_CMP_NAME = {MILLFEED: "mill feed (crusher)", ROMSTOCK: "ROM pad balance"};

/* a saved / published series list + the seeded survey and Master Report series it
   predates (same rule as manual_template.merge_defs) */
function mergeDefs(incoming, seeded){
  const keys = new Set(incoming.map(d => d.key));
  return incoming.concat((seeded || []).filter(d => (d.group === "survey" || d.group === "master") && !keys.has(d.key)));
}
function mdDefs(group){ return (inputs.manual.defs || []).filter(d => d.group === group); }
function mdVals(key){ return (inputs.manual.vals[key] = inputs.manual.vals[key] || {}); }
function mdGet(key, d){ const v = mdVals(key)[d]; return (v === undefined || v === null) ? null : +v; }
function mdSet(key, d, v){
  const m = mdVals(key);
  if (v === null || v === "" || !isFinite(v)) delete m[d]; else m[d] = v;
}
/* every date any series in `keys` carries a value for, sorted */
function mdDates(keys){
  const s = new Set();
  for (const k of keys) for (const d in (inputs.manual.vals[k] || {})) s.add(d);
  return [...s].sort();
}
function mdSum(key, from, to){
  const m = inputs.manual.vals[key] || {};
  let x = 0, any = false;
  for (const d in m){ if (d >= from && d <= to){ x += +m[d]; any = true; } }
  return any ? x : null;
}
function auxKey(id, met){ return "aux:" + id + ":" + met; }
function auxMachines(){ return inputs.aux.machines || (inputs.aux.machines = []); }

/* --------------------------------------------------------- editor grids */
function renderAuxGrid(mon){
  const t = document.getElementById("tblAux");
  const days = monthDays(mon);
  const ms = auxMachines();
  t.innerHTML = "";
  if (!ms.length){
    t.innerHTML = '<tr><td class="mdname">No machines yet &mdash; add one above.</td></tr>';
    return;
  }
  const head = document.createElement("tr");
  head.innerHTML = "<th>Machine</th><th>Metric</th>" +
    days.map(d => "<th>" + d.slice(8) + "</th>").join("") + "<th></th>";
  t.appendChild(head);
  for (const m of ms){
    AUX_METRICS.forEach(([met, label, unit], i) => {
      const tr = document.createElement("tr");
      const c0 = document.createElement("td");
      c0.className = "mdname";
      if (i === 0){ c0.rowSpan = AUX_METRICS.length; c0.innerHTML = "<b>" + esc(m.name) + "</b><br><span style='color:#6b747b'>" + esc(m.type) + "</span>"; tr.appendChild(c0); }
      const c1 = document.createElement("td");
      c1.className = "mdname";
      c1.textContent = met === "work" ? (m.wname || "Work done") + " (" + (m.wunit || "unit") + ")"
                                      : label + " (" + unit + ")";
      tr.appendChild(c1);
      const key = auxKey(m.id, met);
      for (const d of days){
        const td = document.createElement("td");
        td.appendChild(numInput(mdGet(key, d), v => mdSet(key, d, v)));
        tr.appendChild(td);
      }
      if (i === 0){
        const del = document.createElement("td");
        del.rowSpan = AUX_METRICS.length;
        const b = document.createElement("button");
        b.type = "button"; b.className = "mddel"; b.title = "Remove this machine";
        b.textContent = "✕";
        b.addEventListener("click", () => {
          if (!confirm("Remove " + m.name + " and everything entered for it?")) return;
          inputs.aux.machines = auxMachines().filter(x => x.id !== m.id);
          for (const [mk] of AUX_METRICS) delete inputs.manual.vals[auxKey(m.id, mk)];
          saveInputs(); refresh(true);
        });
        del.appendChild(b);
        tr.appendChild(del);
      }
      t.appendChild(tr);
    });
  }
}

/* sparse-date grid: only the dates that carry a value, so a weekly survey is
   four columns and not a wall of 31 */
function renderSparseGrid(tblId, group, emptyMsg){
  const t = document.getElementById(tblId);
  const defs = mdDefs(group);
  t.innerHTML = "";
  if (!defs.length){ t.innerHTML = '<tr><td class="mdname">' + emptyMsg + "</td></tr>"; return; }
  const dates = mdDates(defs.map(d => d.key));
  const head = document.createElement("tr");
  head.innerHTML = "<th>Measurement</th><th>Unit</th>" +
    dates.map(d => '<th>' + d.slice(5) + '<br><span style="font-weight:400;color:#6b747b">' + d.slice(0, 4) + "</span></th>").join("") +
    (dates.length ? "" : "<th>&mdash; add a date above &mdash;</th>") +
    (group === "other" ? "<th></th>" : "");
  t.appendChild(head);
  for (const def of defs){
    const tr = document.createElement("tr");
    const c0 = document.createElement("td");
    c0.className = "mdname";
    c0.textContent = def.name;
    if (def.cmp) c0.title = "reconciled against R4M " + (MD_CMP_NAME[def.cmp] || def.cmp);
    tr.appendChild(c0);
    const c1 = document.createElement("td");
    c1.className = "mdname";
    c1.style.color = "#6b747b";
    c1.textContent = def.unit;
    tr.appendChild(c1);
    for (const d of dates){
      const td = document.createElement("td");
      td.appendChild(numInput(mdGet(def.key, d), v => mdSet(def.key, d, v)));
      tr.appendChild(td);
    }
    if (group === "other"){
      const del = document.createElement("td");
      const b = document.createElement("button");
      b.type = "button"; b.className = "mddel"; b.title = "Remove this series";
      b.textContent = "✕";
      b.addEventListener("click", () => {
        if (!confirm("Remove " + def.name + " and its values?")) return;
        inputs.manual.defs = inputs.manual.defs.filter(x => x.key !== def.key);
        delete inputs.manual.vals[def.key];
        saveInputs(); refresh(true);
      });
      del.appendChild(b);
      tr.appendChild(del);
    }
    t.appendChild(tr);
  }
}

function renderManualGrids(mon){
  const sel = document.getElementById("auxType");
  if (sel && !sel.options.length)
    sel.innerHTML = AUX_TYPES.map(x => '<option value="' + x + '">' + x + "</option>").join("");
  const lbl = document.getElementById("svMonthLbl");
  if (lbl) lbl.textContent = "measured dates";
  renderAuxGrid(mon);
  renderSparseGrid("tblSurvey", "survey", "No survey rows defined.");
  renderSparseGrid("tblOther", "other", "No series yet &mdash; add one above.");
  if (typeof renderMasterGrid === "function") renderMasterGrid(mon);
}

/* ------------------------------------------------------- report rendering */
/* R4M's own number for a survey row, over (from, to] or as a balance at `to` */
function mdActual(def, from, to){
  if (def.cmp === "MILLFEED")
    return slot(agg(DATES.filter(d => d > from && d <= to), null, null), TC);
  if (def.cmp === "ROMSTOCK"){
    let x = 0;
    for (const p in ROM) for (const d in ROM[p]) if (d <= to) x += ROM[p][d][0];
    return x;
  }
  if (!def.cmp) return null;
  if (String(def.cmp).startsWith("MILLFEED:")){     /* crusher feed of one class (LG = LG1 + LG2 in R4M) */
    const r = rowById({HG: "feed.hg", MG: "feed.mg", LG2: "feed.lg"}[def.cmp.slice(9)]);
    return r ? r.v(DATES.filter(d => d > from && d <= to), null) : null;
  }
  if (String(def.cmp).startsWith("ROMCLS:"))        /* R4M pad balance of one class (Master Report rule) */
    return typeof mrRomClassBal === "function" ? mrRomClassBal(def.cmp.slice(7), to) : null;
  return expitT(agg(DATES.filter(d => d > from && d <= to), null, [def.cmp]));
}

function renderManualAux(){
  const host = document.getElementById("mdAux");
  if (!host) return;
  host.innerHTML = "";
  const ms = auxMachines();
  const h = document.createElement("div");
  h.innerHTML = '<div class="mdhead">Auxiliary equipment</div>';
  host.appendChild(h);
  if (!ms.length){
    host.insertAdjacentHTML("beforeend",
      '<div class="mdempty"><b>No auxiliary machines defined.</b> Dozers, graders, mobile crushers, ' +
      'blast drills and water trucks are <b>not present in R4M at all</b> &mdash; its fleet master holds ' +
      'only the 18 haul trucks, 8 loading units and the crusher &mdash; so their hours have to be entered ' +
      'by hand. Open <b>Inputs &rarr; Auxiliary equipment</b> at the foot of the page to add one.</div>');
    return;
  }
  const days = rangeDays(), cats = days.map(d => d.slice(5));
  for (const m of ms){
    const oph = days.map(d => mdGet(auxKey(m.id, "oph"), d) || 0);
    const dth = days.map(d => mdGet(auxKey(m.id, "dth"), d) || 0);
    const wrk = days.map(d => mdGet(auxKey(m.id, "work"), d) || 0);
    const fue = days.map(d => mdGet(auxKey(m.id, "fuel"), d) || 0);
    const sum = a => a.reduce((x, y) => x + y, 0);
    const O = sum(oph), D = sum(dth), W = sum(wrk), F = sum(fue);
    const card = document.createElement("div");
    card.className = "mdcard";
    const wunit = m.wunit || "unit", wname = m.wname || "Work done";
    card.innerHTML = '<h4>' + esc(m.name) + ' <span style="font-weight:400;color:#6b747b">&mdash; ' + esc(m.type) + "</span></h4>" +
      '<div class="mdkpis">' +
      "<span>Operating <b>" + FMT.d1(O) + "</b> h</span>" +
      "<span>Downtime <b>" + FMT.d1(D) + "</b> h</span>" +
      "<span>Availability <b>" + ((O + D) > 0 ? FMT.d1(O / (O + D) * 100) : "–") + "</b> %</span>" +
      "<span>" + esc(wname) + " <b>" + FMT.d1(W) + "</b> " + esc(wunit) + "</span>" +
      "<span>Fuel <b>" + FMT.d1(F) + "</b> L</span>" +
      "<span>Fuel per " + esc(wunit) + " <b>" + (W > 0 ? FMT.d2(F / W) : "–") + "</b></span>" +
      "</div>" + '<div class="charts"></div>';
    host.appendChild(card);
    const cg = card.querySelector(".charts");
    drawChart(cg, {key: "aux." + m.id + ".hours", title: esc(m.name) + " — operating vs downtime, h", cats,
      bars: [{name: "Operating", color: C_CUM, values: oph, stack: "a"},
             {name: "Downtime", color: "#c0392b", values: dth, stack: "a"}],
      lines: [{name: "STD operating h", color: C_ACT, right: true, values: cumOf(oph)}]});
    drawChart(cg, {key: "aux." + m.id + ".work", title: esc(m.name) + " — " + esc(wname) + ", " + esc(wunit), cats,
      bars: [{name: wname, color: C_ACT, values: wrk}],
      lines: [{name: "STD " + wname, color: C_CUM, right: true, values: cumOf(wrk)}]});
  }
}

function renderManualSurvey(){
  const host = document.getElementById("mdSurvey");
  if (!host) return;
  host.innerHTML = '<div class="mdhead">Survey vs dispatch reconciliation</div>';
  const defs = mdDefs("survey");
  const dates = mdDates(defs.map(d => d.key)).filter(d => d >= PERIOD.start && d <= PERIOD.end);
  if (!dates.length){
    host.insertAdjacentHTML("beforeend",
      '<div class="mdempty"><b>No surveyor measurements inside this period.</b> ' +
      'Enter them under <b>Inputs &rarr; Surveyor measurements</b>; the weekly and month-start ' +
      'figures are then compared here against what R4M dispatched over the same window.</div>');
    return;
  }
  const all = mdDates(defs.map(d => d.key));
  const rows = [];
  for (const def of defs){
    for (const d of dates){
      const sv = mdGet(def.key, d);
      if (sv === null) continue;
      const idx = all.indexOf(d);
      const prev = idx > 0 ? all[idx - 1] : "0000-00-00";
      const act = mdActual(def, prev, d);
      rows.push({name: def.name, unit: def.unit, kind: def.kind, date: d, prev: idx > 0 ? prev : "",
                 sv, act, dv: (act === null) ? null : sv - act});
    }
  }
  const t = document.createElement("table");
  t.className = "rep";
  t.id = "tblSurveyRec";
  t.innerHTML = "<thead><tr><th>Measurement</th><th>Survey date</th><th>Since</th>" +
    "<th>Surveyed</th><th>R4M dispatch</th><th>Variance</th><th>Variance %</th></tr></thead><tbody></tbody>";
  const tb = t.querySelector("tbody");
  for (const r of rows){
    const pct = (r.act && r.dv !== null) ? r.dv / r.act * 100 : null;
    const tr = document.createElement("tr");
    tr.innerHTML =
      '<td class="lbl">' + esc(r.name) + " <span style='color:#6b747b'>(" + esc(r.unit) + (r.kind === "stock" ? ", balance" : "") + ")</span></td>" +
      '<td class="num">' + r.date + "</td>" +
      '<td class="num">' + (r.kind === "stock" ? "–" : (r.prev || "start")) + "</td>" +
      '<td class="num">' + FMT.d1(r.sv) + "</td>" +
      '<td class="num">' + (r.act === null ? "–" : FMT.d1(r.act)) + "</td>" +
      '<td class="num ' + (r.dv === null ? "" : (r.dv >= 0 ? "mdvpos" : "mdvneg")) + '">' + (r.dv === null ? "–" : FMT.d1(r.dv)) + "</td>" +
      '<td class="num ' + (pct === null ? "" : (Math.abs(pct) <= 5 ? "mdvpos" : "mdvneg")) + '">' + (pct === null ? "–" : FMT.d1(pct)) + "</td>";
    tb.appendChild(tr);
  }
  host.appendChild(t);
  host.insertAdjacentHTML("beforeend",
    '<div class="note">Tonnage rows compare the surveyed movement since the previous survey date with ' +
    'the R4M dispatch tonnage over the same window; the ROM balance row compares the surveyed standing ' +
    'stock with the cumulative R4M receipts up to that date (reclaim is logged at the feed points and ' +
    'cannot be netted per pile, so that row will drift high). Green marks a variance within 5%.</div>');
}

function renderManualOther(){
  const host = document.getElementById("mdOther");
  if (!host) return;
  host.innerHTML = "";
  const defs = mdDefs("other");
  const withVals = defs.filter(d => Object.keys(inputs.manual.vals[d.key] || {}).length);
  if (!withVals.length) return;
  host.innerHTML = '<div class="mdhead">Other figures not registered in R4M</div><div class="charts"></div>';
  const cg = host.querySelector(".charts");
  const days = rangeDays(), cats = days.map(d => d.slice(5));
  for (const def of withVals){
    const vals = days.map(d => mdGet(def.key, d) || 0);
    drawChart(cg, {key: "manual." + def.key, title: def.name + ", " + def.unit, cats,
      bars: [{name: def.name, color: C_ACT, values: vals}],
      lines: [{name: "STD " + def.name, color: C_CUM, right: true, values: cumOf(vals)}]});
  }
}

function renderManual(){
  renderManualAux(); renderManualSurvey(); renderManualOther();
  const empty = !auxMachines().length &&
                !document.getElementById("mdSurvey").querySelector("table") &&
                !document.getElementById("mdOther").querySelector(".chart");
  document.body.classList.toggle("md-empty", empty);
}

/* ------------------------------------------------------------- wiring */
function wireManual(){
  const on = (id, ev, fn) => { const el = document.getElementById(id); if (el) el.addEventListener(ev, fn); };
  on("auxAdd", "click", () => {
    const name = (document.getElementById("auxName").value || "").trim();
    if (!name) return alert("Give the machine a name first.");
    const wname = (document.getElementById("auxWork").value || "").trim();
    const wunit = (document.getElementById("auxUnit").value || "").trim();
    auxMachines().push({id: "m" + Date.now().toString(36),
                        name, type: document.getElementById("auxType").value,
                        wname: wname || "Work done", wunit: wunit || "unit"});
    document.getElementById("auxName").value = "";
    document.getElementById("auxWork").value = "";
    document.getElementById("auxUnit").value = "";
    saveInputs(); refresh(true);
  });
  on("svAddDate", "click", () => {
    const d = document.getElementById("svNewDate").value;
    if (!d) return alert("Pick the date the survey was taken.");
    const defs = mdDefs("survey");
    if (defs.length) mdVals(defs[0].key)[d] = mdGet(defs[0].key, d) ?? 0;
    saveInputs(); refresh(true);
  });
  on("otAdd", "click", () => {
    const name = (document.getElementById("otName").value || "").trim();
    if (!name) return alert("Give the series a name first.");
    const unit = (document.getElementById("otUnit").value || "").trim() || "t";
    inputs.manual.defs.push({key: "ot_" + Date.now().toString(36), name, unit,
                             group: "other", kind: "flow", cmp: ""});
    document.getElementById("otName").value = "";
    document.getElementById("otUnit").value = "";
    saveInputs(); refresh(true);
  });
  on("otAddDate", "click", () => {
    const d = document.getElementById("otNewDate").value;
    if (!d) return alert("Pick a date first.");
    const defs = mdDefs("other");
    if (!defs.length) return alert("Add a series first.");
    mdVals(defs[0].key)[d] = mdGet(defs[0].key, d) ?? 0;
    saveInputs(); refresh(true);
  });
}
"""
