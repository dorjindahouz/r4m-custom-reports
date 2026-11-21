"""In-browser Excel round-trip for the Inputs panel (requests 03 and 08).

Erdene asked to download a template, fill it in Excel and import it back, and
said the current in-page grids make it unclear how to enter plan numbers.

No library is vendored for this.  An .xlsx is a zip of XML, and Chrome ships
CompressionStream / DecompressionStream("deflate-raw"), so ~300 lines of plain
JS read and write real workbooks - checked against the openpyxl-written
"Report Inputs.xlsx", whose parts are all deflated.

Deliberate simplifications, all safe because we generate the template we read:
  * strings are written inline (t="inlineStr"), so no sharedStrings table is
    produced; the reader still handles sharedStrings because Excel writes one
    when the user re-saves.
  * dates are written as TEXT ("2026-08-01"), which Excel leaves alone, so the
    serial-number minefield never appears.  A numeric cell in a date position is
    still converted from the 1900 serial as a safety net.

The metric vocabulary is never hard-coded here: sheets are generated from the
live `inputs` object, so the strings stay identical to the ones build_report and
"Report Inputs.xlsx" already agree on.
"""

XLSX_CSS = r"""
  /* ------------------------------------------- Excel round-trip (03 and 08) */
  .xlprev{position:fixed;inset:0;background:rgba(14,18,22,.72);z-index:420;
          display:flex;align-items:center;justify-content:center;padding:20px}
  .xlbox{background:#fff;border-radius:8px;padding:18px 22px 16px;max-width:720px;
         width:100%;max-height:88vh;overflow:auto;box-shadow:0 12px 44px rgba(0,0,0,.45)}
  .xlbox h3{margin:0 0 8px;font-size:15px}
  .xlbox table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0}
  .xlbox th,.xlbox td{border:1px solid #e2e7ea;padding:4px 8px;text-align:left}
  .xlbox th{background:#f2f5f7}
  .xlbox td.n{text-align:right;font-variant-numeric:tabular-nums}
  .xlwarn{color:#a33}
  .xlbtns{display:flex;gap:8px;justify-content:flex-end;margin-top:12px}
  @media print{.xlprev{display:none !important}}
"""

# --------------------------------------------------------------------------- #
# generic xlsx reader / writer  ->  window.XLSXIO
# --------------------------------------------------------------------------- #

XLSX_JS = r"""
"use strict";
/* window.XLSXIO - minimal .xlsx read/write with no library.
   See xlsx_template.py for the contract and the deliberate simplifications. */
(function(){
  var CRC = (function(){
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++){
      var c = n;
      for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      t[n] = c >>> 0;
    }
    return t;
  })();
  function crc32(buf){
    var c = 0xFFFFFFFF;
    for (var i = 0; i < buf.length; i++) c = CRC[(c ^ buf[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }
  var enc = new TextEncoder(), dec = new TextDecoder();

  async function deflateRaw(bytes){
    if (typeof CompressionStream === "undefined") return null;
    try{
      var cs = new CompressionStream("deflate-raw");
      var b = await new Response(new Blob([bytes]).stream().pipeThrough(cs)).arrayBuffer();
      return new Uint8Array(b);
    }catch(e){ return null; }
  }
  async function inflateRaw(bytes){
    var ds = new DecompressionStream("deflate-raw");
    var b = await new Response(new Blob([bytes]).stream().pipeThrough(ds)).arrayBuffer();
    return new Uint8Array(b);
  }

  /* ------------------------------------------------------------- zip write */
  async function zip(files){        /* files: [{name, text}] */
    var parts = [], central = [], offset = 0;
    for (var i = 0; i < files.length; i++){
      var raw = enc.encode(files[i].text);
      var nameB = enc.encode(files[i].name);
      var crc = crc32(raw);
      var comp = await deflateRaw(raw);
      var method = comp ? 8 : 0;
      var body = comp || raw;
      var lh = new DataView(new ArrayBuffer(30));
      lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0, true);
      lh.setUint16(8, method, true); lh.setUint16(10, 0, true); lh.setUint16(12, 0x2821, true);
      lh.setUint32(14, crc, true); lh.setUint32(18, body.length, true);
      lh.setUint32(22, raw.length, true); lh.setUint16(26, nameB.length, true);
      lh.setUint16(28, 0, true);
      parts.push(new Uint8Array(lh.buffer), nameB, body);
      var cd = new DataView(new ArrayBuffer(46));
      cd.setUint32(0, 0x02014b50, true); cd.setUint16(4, 20, true); cd.setUint16(6, 20, true);
      cd.setUint16(8, 0, true); cd.setUint16(10, method, true); cd.setUint16(12, 0, true);
      cd.setUint16(14, 0x2821, true); cd.setUint32(16, crc, true);
      cd.setUint32(20, body.length, true); cd.setUint32(24, raw.length, true);
      cd.setUint16(28, nameB.length, true); cd.setUint16(30, 0, true); cd.setUint16(32, 0, true);
      cd.setUint16(34, 0, true); cd.setUint16(36, 0, true); cd.setUint32(38, 0, true);
      cd.setUint32(42, offset, true);
      central.push(new Uint8Array(cd.buffer), nameB);
      offset += 30 + nameB.length + body.length;
    }
    var cdSize = central.reduce(function(a, b){ return a + b.length; }, 0);
    var eo = new DataView(new ArrayBuffer(22));
    eo.setUint32(0, 0x06054b50, true); eo.setUint16(8, files.length, true);
    eo.setUint16(10, files.length, true); eo.setUint32(12, cdSize, true);
    eo.setUint32(16, offset, true); eo.setUint16(20, 0, true);
    return new Blob(parts.concat(central, [new Uint8Array(eo.buffer)]),
                    {type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"});
  }

  /* -------------------------------------------------------------- zip read */
  async function unzip(buf){
    var u8 = new Uint8Array(buf), dv = new DataView(buf), out = {};
    var eocd = -1;
    for (var i = u8.length - 22; i >= 0 && i > u8.length - 66000; i--)
      if (dv.getUint32(i, true) === 0x06054b50){ eocd = i; break; }
    if (eocd < 0) throw new Error("not a zip file");
    var n = dv.getUint16(eocd + 10, true), p = dv.getUint32(eocd + 16, true);
    for (var k = 0; k < n; k++){
      var method = dv.getUint16(p + 10, true);
      var csize = dv.getUint32(p + 20, true);
      var nlen = dv.getUint16(p + 28, true), elen = dv.getUint16(p + 30, true),
          clen = dv.getUint16(p + 32, true), lho = dv.getUint32(p + 42, true);
      var name = dec.decode(u8.subarray(p + 46, p + 46 + nlen));
      var lnlen = dv.getUint16(lho + 26, true), lelen = dv.getUint16(lho + 28, true);
      var start = lho + 30 + lnlen + lelen;
      /* parts stay compressed until asked for: an .xlsm export can carry 50 MB sheets nobody needs */
      out[name] = {method: method, body: u8.subarray(start, start + csize), size: dv.getUint32(p + 24, true)};
      p += 46 + nlen + elen + clen;
    }
    return out;
  }
  async function partText(ent){
    if (!ent) return null;
    return dec.decode(ent.method === 8 ? await inflateRaw(ent.body) : ent.body.slice());
  }

  /* ------------------------------------------------------------ xlsx write */
  function colName(i){
    var s = "";
    do { s = String.fromCharCode(65 + (i % 26)) + s; i = Math.floor(i / 26) - 1; } while (i >= 0);
    return s;
  }
  function xesc(s){
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;");
  }
  function sheetXml(rows){
    var x = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>';
    for (var r = 0; r < rows.length; r++){
      x += '<row r="' + (r + 1) + '">';
      var row = rows[r] || [];
      for (var c = 0; c < row.length; c++){
        var v = row[c];
        if (v === null || v === undefined || v === "") continue;
        var ref = colName(c) + (r + 1), st = (r === 0 ? ' s="1"' : "");
        if (typeof v === "number" && isFinite(v))
          x += '<c r="' + ref + '"' + st + "><v>" + v + "</v></c>";
        else
          x += '<c r="' + ref + '"' + st + ' t="inlineStr"><is><t xml:space="preserve">' +
               xesc(v) + "</t></is></c>";
      }
      x += "</row>";
    }
    return x + "</sheetData></worksheet>";
  }
  var STYLES = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>' +
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>' +
    '<fills count="2"><fill><patternFill patternType="none"/></fill>' +
    '<fill><patternFill patternType="gray125"/></fill></fills>' +
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>' +
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
    '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>' +
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>' +
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>';

  async function write(sheets){          /* sheets: [{name, rows}] */
    var files = [], types = "", wbs = "", rels = "";
    for (var i = 0; i < sheets.length; i++){
      var id = i + 1;
      files.push({name: "xl/worksheets/sheet" + id + ".xml", text: sheetXml(sheets[i].rows)});
      types += '<Override PartName="/xl/worksheets/sheet' + id + '.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>';
      wbs += '<sheet name="' + xesc(sheets[i].name) + '" sheetId="' + id + '" r:id="rId' + id + '"/>';
      rels += '<Relationship Id="rId' + id + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet' + id + '.xml"/>';
    }
    var sid = sheets.length + 1;
    files.unshift({name: "[Content_Types].xml", text:
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
      '<Default Extension="xml" ContentType="application/xml"/>' +
      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
      '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
      types + "</Types>"});
    files.push({name: "_rels/.rels", text:
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rIdWb" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'});
    files.push({name: "xl/workbook.xml", text:
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' +
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
      "<sheets>" + wbs + "</sheets></workbook>"});
    files.push({name: "xl/_rels/workbook.xml.rels", text:
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      rels + '<Relationship Id="rId' + sid + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'});
    files.push({name: "xl/styles.xml", text: STYLES});
    return zip(files);
  }

  /* ------------------------------------------------------------- xlsx read */
  function refCol(ref){
    var m = /^([A-Z]+)/.exec(ref); if (!m) return 0;
    var n = 0;
    for (var i = 0; i < m[1].length; i++) n = n * 26 + (m[1].charCodeAt(i) - 64);
    return n - 1;
  }
  var SERIAL_MIN = 20000, SERIAL_MAX = 80000;    /* 1954-10-03 .. 2119-01-29 */
  function serialToDate(n){
    var ms = Math.round((n - 25569) * 86400000);   /* 1900 epoch, leap-bug offset */
    return new Date(ms).toISOString().slice(0, 10);
  }
  /* opts.maxSheetBytes: sheets larger than this (uncompressed) are skipped unless
     opts.want(name) - they are listed in out.__skipped [{name, mb}] */
  async function read(buf, opts){
    opts = opts || {};
    var maxB = opts.maxSheetBytes || Infinity, want = opts.want || null, skipped = [];
    var z = await unzip(buf), P = new DOMParser();
    var shared = [];
    if (z["xl/sharedStrings.xml"]){
      var sx = P.parseFromString(await partText(z["xl/sharedStrings.xml"]), "application/xml");
      var sis = sx.getElementsByTagName("si");
      for (var i = 0; i < sis.length; i++){
        var ts = sis[i].getElementsByTagName("t"), s = "";
        for (var j = 0; j < ts.length; j++) s += ts[j].textContent;
        shared.push(s);
      }
    }
    var wb = P.parseFromString(await partText(z["xl/workbook.xml"]), "application/xml");
    var relXml = P.parseFromString(await partText(z["xl/_rels/workbook.xml.rels"]), "application/xml");
    var target = {};
    var rl = relXml.getElementsByTagName("Relationship");
    for (var r = 0; r < rl.length; r++)
      target[rl[r].getAttribute("Id")] = rl[r].getAttribute("Target").replace(/^\/?xl\//, "");
    var out = {}, order = [];
    var shs = wb.getElementsByTagName("sheet");
    for (var k = 0; k < shs.length; k++){
      var name = shs[k].getAttribute("name");
      var rid = shs[k].getAttribute("r:id") ||
                shs[k].getAttributeNS("http://schemas.openxmlformats.org/officeDocument/2006/relationships", "id");
      var path = "xl/" + (target[rid] || ("worksheets/sheet" + (k + 1) + ".xml"));
      if (!z[path]) continue;
      if (z[path].size > maxB && !(want && want(String(name).trim()))){
        skipped.push({name: String(name).trim(), mb: z[path].size / 1048576});
        continue;
      }
      var doc = P.parseFromString(await partText(z[path]), "application/xml");
      var rows = [], rws = doc.getElementsByTagName("row");
      for (var ri = 0; ri < rws.length; ri++){
        var cells = rws[ri].getElementsByTagName("c"), arr = [];
        for (var ci = 0; ci < cells.length; ci++){
          var c = cells[ci], t = c.getAttribute("t"), col = refCol(c.getAttribute("r") || "");
          var vEl = c.getElementsByTagName("v")[0], val = null;
          if (t === "inlineStr"){
            var its = c.getElementsByTagName("t"); val = "";
            for (var q = 0; q < its.length; q++) val += its[q].textContent;
          } else if (t === "s"){
            val = shared[+(vEl ? vEl.textContent : -1)] || "";
          } else if (t === "str" || t === "e"){
            val = vEl ? vEl.textContent : "";
          } else if (vEl){
            var num = parseFloat(vEl.textContent);
            val = isFinite(num) ? num : vEl.textContent;
          }
          while (arr.length < col) arr.push(null);
          arr[col] = val;
        }
        rows.push(arr);
      }
      out[name] = rows;
      order.push(name);
    }
    out.__order = order;
    out.__skipped = skipped;
    return out;
  }

  /* a header cell that should be a date: text passes through, a serial converts */
  function asDate(v){
    if (typeof v === "number" && v >= SERIAL_MIN && v <= SERIAL_MAX) return serialToDate(v);
    var s = String(v == null ? "" : v).trim();
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
    return m ? m[0] : null;
  }
  function asMonth(v){
    var d = asDate(v);
    if (d) return d.slice(0, 7);
    var s = String(v == null ? "" : v).trim();
    return /^\d{4}-\d{2}$/.test(s) ? s : null;
  }

  window.XLSXIO = {read: read, write: write, asDate: asDate, asMonth: asMonth,
                   colName: colName, crc32: crc32};
})();
"""

# --------------------------------------------------------------------------- #
# the app-level glue: inputs  <->  workbook   (lives inside the report IIFE)
# --------------------------------------------------------------------------- #

INPUTS_XLSX_JS = r"""
/* ======================================== Excel round-trip for the Inputs panel
   Sheets are generated FROM `inputs`, so the metric strings stay byte-identical
   to the ones "Report Inputs.xlsx" and build_report already agree on. */
const XL_README = [
  ["OPERATIONAL MINING REPORT - input workbook (one file for everything)"],
  [],
  ["How to use this file"],
  ["1.", "Sheet 1 is the mine's Site Operation Plan for the month. Edit it, or replace it with the planners' own SOP sheet (same layout)."],
  ["2.", "Rows are matched by section and name, not position; rows the report does not use are kept and handed back on the next export."],
  ["3.", "The other sheets hold what the SOP does not: other targets, plant actuals, ROM adjustments, manual data, densities."],
  ["4.", "Save, then 'Import workbook' in the report's Inputs panel. You get a summary before anything changes; then Publish."],
  [],
  ["Sheet", "What it holds"],
  ["SOP Template", "The month's plan: one column per day + TOTAL. Importing it replaces that month's plan for every row it carries."],
  ["Other Targets", "Targets with no SOP row (excavator bcm/h, engineering work), per day + monthly target."],
  ["PP Actuals", "Process-plant daybook: weightometer tonnes and head grade per day."],
  ["Mill Monthly", "Monthly mill history used by the year-to-date charts."],
  ["LCM", "Density and swell factor per R4M material code (t/bcm, bcm->lcm); also converts the SOP's m3 rows to tonnes."],
  ["ROM Adjustments", "Manual ROM-pile balance resets: pile, date, balance (t), note. The sheet replaces the list."],
  ["Aux Equipment", "Machines R4M does not track: hours, work done and fuel per day."],
  ["Survey", "Surveyor measurements per measurement date. The planners' own Master Report workbook also imports as-is: its SURVEY sheet (closed months from the monthly rows, the running month from the weekly rows), 5.1 ROM_Survey (pile measurements summed by class) and 7.1 MILLFEED_PP (plant daily throughput and Au head grade, plus the month-end reconciled feed per class)."],
  ["Other Data", "Anything else the system does not record."],
  ["Budget", "The approved budget behind the Master Report's MONTHLY / ANNUAL PLAN columns (sections 4 Mining, 5 ROM inventories, 7 Mill feeding): one column per month + the year total (the planners' own Work_Order sheet imports as-is). A budget import replaces that year for the lines it carries."],
];

function xlDailyDates(){
  const s = new Set();
  for (const m in inputs.daily) for (const d in inputs.daily[m]) s.add(d);
  for (const d of monthDays(inMon())) s.add(d);   /* always fillable */
  return [...s].sort();
}
function xlPPDates(){
  const s = new Set();
  for (const k in inputs.pp) for (const d in inputs.pp[k]) s.add(d);
  for (const d of monthDays(inMon())) s.add(d);
  return [...s].sort();
}

function xlSheets(){
  const M = inMon(), pd = xlPPDates(), md = monthDays(M);
  const sheets = [{name: "SOP Template", rows: sopExportRows(M)}];

  /* targets the SOP sheet has no row for */
  const other = Object.keys(inputs.daily).filter(m => !SOP_METRICS.has(m) && m !== "IWF Spreading (lcm)");
  const ov = (m, d) => { const v = (inputs.daily[m] || {})[d]; return (v === undefined || v === null) ? null : +v; };
  sheets.push({name: "Other Targets", rows: [["Metric"].concat(md, ["Monthly target"])]
    .concat(other.map(m => [m].concat(md.map(d => ov(m, d)),
      [((inputs.monthly[m] || {})[M] ?? null)])))});

  sheets.push({name: "PP Actuals", rows: [["Metric"].concat(pd),
    ["PP throughput (t)"].concat(pd.map(d => inputs.pp.t[d] ?? null)),
    ["PP head grade Au (g/t)"].concat(pd.map(d => inputs.pp.au[d] ?? null))]});

  sheets.push({name: "ROM Adjustments", rows: [["Pile", "Date", "Balance (t)", "Note"]]
    .concat((inputs.romadj || []).map(a => [a.pile, a.date, +a.bal || 0, a.note || ""]))});

  const arows = [["Machine", "Type", "Work label", "Work unit", "Metric"].concat(md)];
  for (const m of (inputs.aux.machines || []))
    for (const [met, label, unit] of AUX_METRICS)
      arows.push([m.name, m.type, m.wname || "Work done", m.wunit || "unit",
                  met === "work" ? "work" : met]
        .concat(md.map(d => mdGet(auxKey(m.id, met), d))));
  sheets.push({name: "Aux Equipment", rows: arows});

  for (const [grp, sheet] of [["survey", "Survey"], ["other", "Other Data"]]){
    const defs = mdDefs(grp);
    const dates = mdDates(defs.map(d => d.key));
    /* an empty group still gets a few day columns so the sheet is fillable */
    const cols = dates.length ? dates : md.slice(0, 5);
    const rows = [["Measurement", "Unit", "Kind"].concat(cols)];
    for (const def of defs)
      rows.push([def.name, def.unit, def.kind || "flow"].concat(cols.map(d => mdGet(def.key, d))));
    sheets.push({name: sheet, rows});
  }
  sheets.push(...mrSheets());

  const MK = ["bt", "mt", "pt", "bg", "fg", "pg"];
  sheets.push({name: "Mill Monthly", rows: [["Month", "Monthly Plan throughput (t)", "Mine throughput (t)",
      "PP throughput (t)", "Monthly Plan grade Au (g/t)", "Feed grade Au (g/t)", "PP grade Au (g/t)"]]
    .concat(Object.keys(inputs.millmon).sort().map(m =>
      [m].concat(MK.map(k => inputs.millmon[m][k] ?? null))))});

  sheets.push({name: "LCM", rows: [["Material Code", "Material Name", "Density t/bcm", "Swell Factor"]]
    .concat(Object.keys(inputs.lcm).map(c => [c, inputs.lcm[c].name || c,
                                              inputs.lcm[c].density, inputs.lcm[c].swell]))});
  sheets.push({name: "ReadMe", rows: XL_README});
  return sheets;
}

async function xlDownloadTemplate(){
  try{
    const blob = await XLSXIO.write(xlSheets());
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "Site Operation Plan_" + inMon().replace("-", "") + " (report inputs).xlsx";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }catch(e){ alert("Could not build the Excel template: " + e); }
}

/* Parse a workbook into a patch for `inputs`, plus a human summary of what it
   will change and what it could not match. Nothing is applied until Apply. */
function xlParseWorkbook(wb){
  const patch = {lcm: {}, daily: {}, monthly: {}, pp: {t: {}, au: {}}, millmon: {},
                 manual: {vals: {}, clear: []}, aux: null, romadj: null, clearMonths: [], sopraw: {},
                 budget: {}, budgetYears: {}};
  const notes = [], unknown = [];
  const num = v => (typeof v === "number" && isFinite(v)) ? v : null;

  const lcm = wb["LCM"];
  if (lcm){
    let n = 0;
    for (const row of lcm.slice(1)){
      if (!row || !row[0]) continue;
      const code = String(row[0]).trim();
      if (!inputs.lcm[code]){ unknown.push("LCM material " + code); continue; }
      patch.lcm[code] = {density: num(row[2]) ?? inputs.lcm[code].density,
                         swell: num(row[3]) ?? inputs.lcm[code].swell};
      n++;
    }
    notes.push(["LCM", n + " material code(s)"]);
  }

  /* "Other Targets" = targets the SOP sheet does not carry (excavator bcm/h,
     engineering work ...), with a "Monthly target" column; "Daily Targets" is the
     older all-metrics sheet, still accepted */
  for (const sname of ["Other Targets", "Daily Targets"]){
    const dt = wb[sname];
    if (!dt || dt.length < 2) continue;
    const head = dt[0].map(XLSXIO.asDate);
    const monCol = dt[0].findIndex(v => /monthly/i.test(String(v || "")));
    const firstD = head.find(Boolean);
    let n = 0, cells = 0;
    for (const row of dt.slice(1)){
      if (!row || !row[0]) continue;
      const metric = String(row[0]).trim();
      if (!(metric in inputs.daily)){ unknown.push(sname + " metric “" + metric + "”"); continue; }
      const m = patch.daily[metric] = Object.assign(patch.daily[metric] || {}, {});
      for (let c = 1; c < row.length; c++){
        if (!head[c]) continue;
        const v = num(row[c]);
        if (v !== null){ m[head[c]] = v; cells++; }
      }
      if (monCol > 0 && firstD && num(row[monCol]) !== null)
        (patch.monthly[metric] = patch.monthly[metric] || {})[firstD.slice(0, 7)] = num(row[monCol]);
      n++;
    }
    notes.push([sname, n + " metric(s), " + cells + " value(s)"]);
  }

  const mt = wb["Monthly Targets"];
  if (mt && mt.length > 1){
    let n = 0;
    for (const row of mt.slice(1)){
      if (!row || !row[0]) continue;
      const metric = String(row[0]).trim(), mo = XLSXIO.asMonth(row[1]), v = num(row[2]);
      if (!(metric in inputs.monthly)){ unknown.push("Monthly metric “" + metric + "”"); continue; }
      if (!mo || v === null) continue;
      (patch.monthly[metric] = patch.monthly[metric] || {})[mo] = v;
      n++;
    }
    notes.push(["Monthly Targets", n + " value(s)"]);
  }

  const pp = wb["PP Actuals"];
  if (pp && pp.length > 1){
    const head = pp[0].map(XLSXIO.asDate);
    const KEY = {"PP throughput (t)": "t", "PP head grade Au (g/t)": "au"};
    let cells = 0;
    for (const row of pp.slice(1)){
      const k = KEY[String(row && row[0] || "").trim()];
      if (!k) continue;
      for (let c = 1; c < row.length; c++){
        if (!head[c]) continue;
        const v = num(row[c]);
        if (v !== null){ patch.pp[k][head[c]] = v; cells++; }
      }
    }
    notes.push(["PP Actuals", cells + " value(s)"]);
  }

  const mm = wb["Mill Monthly"];
  if (mm && mm.length > 1){
    const MK = ["bt", "mt", "pt", "bg", "fg", "pg"];
    let n = 0;
    for (const row of mm.slice(1)){
      const mo = XLSXIO.asMonth(row && row[0]);
      if (!mo) continue;
      const o = patch.millmon[mo] = {};
      MK.forEach((k, i) => { const v = num(row[i + 1]); if (v !== null) o[k] = v; });
      n++;
    }
    notes.push(["Mill Monthly", n + " month(s)"]);
  }

  const ra = wb["ROM Adjustments"];
  if (ra){
    const list = [];
    for (const row of ra.slice(1)){
      if (!row || !row[0]) continue;
      const date = XLSXIO.asDate(row[1]), bal = num(row[2]);
      if (!date || bal === null){ unknown.push("ROM Adjustments row “" + String(row[0]).trim() + "” (needs a date and a balance)"); continue; }
      list.push({pile: String(row[0]).trim(), date, bal, note: String(row[3] || "").trim()});
    }
    patch.romadj = list;
    notes.push(["ROM Adjustments", list.length + " adjustment(s) (replaces the list)"]);
  }

  const ax = wb["Aux Equipment"];
  if (ax && ax.length > 1){
    const head = ax[0].map(XLSXIO.asDate);
    const byName = new Map((inputs.aux.machines || []).map(m => [m.name, m]));
    const machines = [], seen = new Map();
    let cells = 0;
    for (const row of ax.slice(1)){
      if (!row || !row[0] || !row[4]) continue;
      const name = String(row[0]).trim(), met = String(row[4]).trim();
      let m = seen.get(name);
      if (!m){
        const ex = byName.get(name);
        m = {id: ex ? ex.id : "m" + Math.random().toString(36).slice(2, 9),
             name, type: String(row[1] || "Other").trim(),
             wname: String(row[2] || "Work done").trim(), wunit: String(row[3] || "unit").trim()};
        seen.set(name, m); machines.push(m);
      }
      if (!AUX_METRICS.some(a => a[0] === met)){ unknown.push("Aux metric “" + met + "”"); continue; }
      const key = auxKey(m.id, met), tgt = patch.manual.vals[key] = patch.manual.vals[key] || {};
      for (let c = 5; c < row.length; c++){
        if (!head[c]) continue;
        const v = num(row[c]);
        if (v !== null){ tgt[head[c]] = v; cells++; }
      }
    }
    if (machines.length){ patch.aux = machines; notes.push(["Aux Equipment", machines.length + " machine(s), " + cells + " value(s)"]); }
  }

  for (const [grp, sheet] of [["survey", "Survey"], ["other", "Other Data"]]){
    const sh = wb[sheet];
    if (!sh || sh.length < 2) continue;
    const head = sh[0].map(XLSXIO.asDate);
    const byName = new Map(mdDefs(grp).map(d => [d.name, d]));
    let cells = 0, miss = 0;
    for (const row of sh.slice(1)){
      if (!row || !row[0]) continue;
      const def = byName.get(String(row[0]).trim());
      if (!def){ miss++; unknown.push(sheet + " row “" + String(row[0]).trim() + "”"); continue; }
      const tgt = patch.manual.vals[def.key] = patch.manual.vals[def.key] || {};
      for (let c = 3; c < row.length; c++){
        if (!head[c]) continue;
        const v = num(row[c]);
        if (v !== null){ tgt[head[c]] = v; cells++; }
      }
    }
    notes.push([sheet, cells + " value(s)" + (miss ? ", " + miss + " unknown row(s)" : "")]);
  }
  xlParseClientSheets(wb, patch, notes, unknown);
  mrParseMaster(wb, patch, notes, unknown);
  for (const sh of mrBudgetSheets(wb)) mrParseBudget(sh, patch, notes, unknown);
  return {patch, notes, unknown};
}

/* ---- the planners' own Master Report workbook (Master Report Example.xlsm): its SURVEY,
   5.1 ROM_Survey and 7.1 MILLFEED_PP sheets import as they are, recognised by their
   headers (never by sheet name or row number).
   SURVEY: a closed month takes its monthly row, dated the month's last day; the month still
   running takes its weekly rows, dated at each week's end, so MTD (SURVEY) fills during the
   month. A month imported this way replaces that month's surveyed movement.
   ROM_Survey: every measurement date is a full re-measure; pile tonnes are summed by class
   (Test and other material types are left out). MILLFEED_PP: the plant's daily throughput
   and Au head grade -> Process Plant actuals. */
const XL_SV_COLS = [[/^waste/, "sv_w"], [/^topsoil/, "sv_ts"], [/^high-grade/, "sv_hg"], [/^mid-grade/, "sv_mg"],
  [/^low-grade ?2/, "sv_lg2"], [/^low-grade ?1/, "sv_lg1"], [/^subgrade/, "sv_sg"], [/^min ?waste/, "sv_mw"]];
const XL_ROM_CLS = [[/^high-grade/i, "HG"], [/^mid-grade/i, "MG"], [/^low-grade ?2/i, "LG2"], [/^low-grade ?1/i, "LG1"]];
const xlCell = v => String(v == null ? "" : v).replace(/\u00a0/g, " ").trim();
const xlNum = v => (typeof v === "number" && isFinite(v)) ? v : null;
const xlMonthEnd = m => { const [y, mo] = m.split("-").map(Number); return new Date(Date.UTC(y, mo, 0)).toISOString().slice(0, 10); };
const xlR2 = v => Math.round(v * 100) / 100;

function xlParseClientSurvey(sh, name, patch, notes){
  const hi = sh.findIndex(r => r && /^month$/i.test(xlCell(r[0])) && /^weekly$/i.test(xlCell(r[3])));
  if (hi < 0) return false;
  /* the unit row (BCM | Tonnes | BCM | Tonnes ...) under the class labels; the Excel table's own
     header row ("BCM | Tonnes | BCM2 | Tonnes3 ...") has a single exact "Tonnes" and must lose */
  let ui = -1, best = 0;
  for (let i = hi + 1; i < Math.min(sh.length, hi + 8); i++){
    const n = (sh[i] || []).filter(v => xlCell(v) === "Tonnes").length;
    if (n > best){ best = n; ui = i; }
  }
  if (ui < 1) return false;
  const labels = sh[ui - 1] || [], cols = [];
  const known = new Set(mdDefs("survey").map(d => d.key));
  sh[ui].forEach((v, c) => {
    if (xlCell(v) !== "Tonnes") return;
    const hit = XL_SV_COLS.find(([re]) => re.test(xlCell(labels[c]).toLowerCase()));
    if (hit && known.has(hit[1]) && !cols.some(x => x[1] === hit[1])) cols.push([c, hit[1]]);
  });
  if (!cols.length) return false;
  const months = {};             /* "YYYY-MM" -> {monthly: row, weeks: [[date, row]]} */
  for (let i = ui + 1; i < sh.length; i++){
    const r = sh[i]; if (!r) continue;
    if (/^total$/i.test(xlCell(r[0]))) break;  /* the rehandle / engineering blocks follow */
    const md = XLSXIO.asDate(r[0]);
    if (md){ const m = md.slice(0, 7); (months[m] = months[m] || {weeks: []}).monthly = r; continue; }
    const ws = XLSXIO.asDate(r[3]), we = XLSXIO.asDate(r[4]);
    if (ws && we){            /* a week's end date is the next week's start: clamp to its own month */
      const m = ws.slice(0, 7), end = xlMonthEnd(m);
      (months[m] = months[m] || {weeks: []}).weeks.push([we < end ? we : end, r]);
    }
  }
  const today = mrShiftDate();
  let closed = 0, running = 0, cells = 0;
  const put = (d, r) => { for (const [c, k] of cols){ const v = xlNum(r[c]); if (v === null) continue;
    const t = patch.manual.vals[k] = patch.manual.vals[k] || {}; t[d] = xlR2((t[d] || 0) + v); cells++; } };
  for (const m of Object.keys(months).sort()){
    const M = months[m], end = xlMonthEnd(m);
    if (end < today && M.monthly){ put(end, M.monthly); closed++; }
    else if (M.weeks.some(([, r]) => cols.some(([c]) => xlNum(r[c]) !== null))){ for (const [d, r] of M.weeks) put(d, r); running++; }
    else if (M.monthly){ put(end, M.monthly); closed++; }
    else continue;
    for (const [, k] of cols) patch.manual.clear.push({key: k, from: m + "-01", to: end});
  }
  notes.push([name + " (survey)", closed + " closed month(s) from the monthly rows, " + running +
    " running month(s) from the weekly rows, " + cells + " value(s) - replaces those months' surveyed tonnes"]);
  return true;
}
function xlParseClientRomSurvey(sh, name, patch, notes, unknown){
  const hi = sh.findIndex(r => r && r.some(v => /^updated date$/i.test(xlCell(v))) && r.some(v => /^tonnage$/i.test(xlCell(v))));
  if (hi < 0) return false;
  const H = sh[hi].map(v => xlCell(v).toLowerCase());
  const cD = H.indexOf("updated date"), cM = H.indexOf("material type"), cT = H.indexOf("tonnage");
  if (cD < 0 || cM < 0 || cT < 0) return false;
  const by = {};
  let rows = 0, other = 0;
  for (const r of sh.slice(hi + 1)){
    if (!r) continue;
    const d = XLSXIO.asDate(r[cD]), t = xlNum(r[cT]);
    if (!d || t === null) continue;
    const hit = XL_ROM_CLS.find(([re]) => re.test(xlCell(r[cM])));
    if (!hit){ other++; continue; }
    (by[d] = by[d] || {HG: 0, MG: 0, LG2: 0, LG1: 0})[hit[1]] += t;
    rows++;
  }
  const dates = Object.keys(by).sort();
  if (!dates.length) return false;
  for (const d of dates){
    let tot = 0;
    for (const c of ["HG", "MG", "LG2", "LG1"]){
      const k = "sv_rom_" + c.toLowerCase();
      (patch.manual.vals[k] = patch.manual.vals[k] || {})[d] = xlR2(by[d][c]);
      tot += by[d][c];
    }
    (patch.manual.vals.sv_romstock = patch.manual.vals.sv_romstock || {})[d] = xlR2(tot);
  }
  notes.push([name + " (ROM survey)", dates.length + " measurement date(s), " + dates[0] + " → " + dates[dates.length - 1] +
    ", " + rows + " pile row(s) summed by class"]);
  if (other) unknown.push(name + ": " + other + " pile row(s) of another material type (e.g. Test) not counted");
  return true;
}
function xlParseClientPP(sh, name, patch, notes){
  const hi = sh.findIndex(r => r && r.some(v => /^mill throughput, ?t$/i.test(xlCell(v))));
  if (hi < 0) return false;
  const H = sh[hi].map(v => xlCell(v).toLowerCase());
  const cT = H.findIndex(v => /^mill throughput/.test(v)), cA = H.findIndex(v => /^head grade, ?au/.test(v));
  let cD = -1;
  for (let c = cT - 1; c >= 0; c--) if (H[c] === "date"){ cD = c; break; }
  if (cD < 0) return false;   /* e.g. the REPORT V1 row label, not a daybook */
  const ds = [];
  for (const r of sh.slice(hi + 1)){
    if (!r) continue;
    const d = XLSXIO.asDate(r[cD]), t = xlNum(r[cT]);
    if (!d || t === null) continue;
    patch.pp.t[d] = t;
    const a = cA >= 0 ? xlNum(r[cA]) : null;
    if (a !== null) patch.pp.au[d] = a;
    ds.push(d);
  }
  if (!ds.length) return false;
  ds.sort();
  notes.push([name + " (plant daybook)", ds.length + " day(s), " + ds[0] + " → " + ds[ds.length - 1] + ": PP throughput + head grade Au"]);
  return true;
}
/* 7.1 MILLFEED_PP, right-hand block: the plant's month-end reconciled feed per class (Date, Subclass
   HG/MG/LG2/LG1, Process Plant t). A month counts only when some class has tonnes (the sheet keeps
   formula rows at 0 for months not reconciled); such a month replaces that month's sv_ff_* values. */
function xlParseClientFeedSurvey(sh, name, patch, notes){
  const hi = sh.findIndex(r => r && r.some(v => /^subclass$/i.test(xlCell(v))) && r.some(v => /^process plant$/i.test(xlCell(v))));
  if (hi < 0) return false;
  const H = sh[hi].map(v => xlCell(v).toLowerCase());
  const cS = H.indexOf("subclass"), cT = H.indexOf("process plant");
  let cD = -1;
  for (let c = cS - 1; c >= 0; c--) if (H[c] === "date"){ cD = c; break; }
  if (cD < 0 || cT < 0) return false;
  const by = {};                  /* "YYYY-MM" -> {date, cls: {HG: t}} */
  for (const r of sh.slice(hi + 1)){
    if (!r) continue;
    const d = XLSXIO.asDate(r[cD]), c = xlCell(r[cS]).toUpperCase(), t = xlNum(r[cT]);
    if (!d || t === null || !["HG", "MG", "LG2", "LG1"].includes(c)) continue;
    const m = d.slice(0, 7), o = by[m] = by[m] || {date: d, cls: {}};
    if (d > o.date) o.date = d;
    o.cls[c] = (o.cls[c] || 0) + t;
  }
  const months = Object.keys(by).sort().filter(m => Object.values(by[m].cls).some(t => t > 0));
  if (!months.length) return false;
  for (const m of months){
    for (const c of ["HG", "MG", "LG2", "LG1"]){
      const k = "sv_ff_" + c.toLowerCase();
      (patch.manual.vals[k] = patch.manual.vals[k] || {})[by[m].date] = xlR2(by[m].cls[c] || 0);
      patch.manual.clear.push({key: k, from: m + "-01", to: xlMonthEnd(m)});
    }
  }
  notes.push([name + " (plant month-end feed)", months.length + " reconciled month(s) " + months.join(", ") +
    ": feed tonnes per class for the Master Report's mill feeding MTD (SURVEY)"]);
  return true;
}
function xlParseClientSheets(wb, patch, notes, unknown){
  for (const nm of (wb.__order || [])){
    const sh = wb[nm], name = String(nm).trim();
    if (!sh || !sh.length) continue;
    if (xlParseClientSurvey(sh, name, patch, notes) || xlParseClientRomSurvey(sh, name, patch, notes, unknown)) continue;
    xlParseClientPP(sh, name, patch, notes);
    xlParseClientFeedSurvey(sh, name, patch, notes);
  }
}

function xlApply(patch){
  for (const {month, metrics} of (patch.clearMonths || [])){   /* an SOP month replaces what was there */
    for (const m of metrics){
      const dm = inputs.daily[m]; if (dm) for (const d in dm) if (d.slice(0, 7) === month) delete dm[d];
      if (inputs.monthly[m]) delete inputs.monthly[m][month];
    }
  }
  if (patch.sopraw && Object.keys(patch.sopraw).length)
    inputs.sopraw = Object.assign(inputs.sopraw || {}, patch.sopraw);
  for (const code in patch.lcm) Object.assign(inputs.lcm[code], patch.lcm[code]);
  for (const m in patch.daily) inputs.daily[m] = Object.assign(inputs.daily[m] || {}, patch.daily[m]);
  for (const m in patch.monthly) inputs.monthly[m] = Object.assign(inputs.monthly[m] || {}, patch.monthly[m]);
  for (const k of ["t", "au"]) Object.assign(inputs.pp[k], patch.pp[k]);
  for (const mo in patch.millmon) inputs.millmon[mo] = Object.assign(inputs.millmon[mo] || {}, patch.millmon[mo]);
  if (patch.aux) inputs.aux.machines = patch.aux;
  if (patch.romadj) inputs.romadj = patch.romadj;
  for (const c of (patch.manual.clear || [])){   /* an imported survey month replaces that month */
    const sv = inputs.manual.vals[c.key];
    if (sv) for (const d in sv) if (d >= c.from && d <= c.to) delete sv[d];
  }
  for (const key in patch.manual.vals)
    inputs.manual.vals[key] = Object.assign(inputs.manual.vals[key] || {}, patch.manual.vals[key]);
  mrApplyBudget(patch);
  saveInputs();
  refresh(true);
}

function xlPreview(res, fileName){
  const ov = document.createElement("div");
  ov.className = "xlprev noprint";
  const rows = res.notes.map(([a, b]) => "<tr><td>" + a + '</td><td class="n">' + b + "</td></tr>").join("");
  const unk = res.unknown.length
    ? '<p class="xlwarn"><b>' + res.unknown.length + " item(s) not used by the report</b> (left as they are in the file):<br>" +
      res.unknown.slice(0, 12).map(u => "&bull; " + u).join("<br>") +
      (res.unknown.length > 12 ? "<br>&bull; …" : "") + "</p>"
    : "<p>Every row matched a known metric.</p>";
  ov.innerHTML = '<div class="xlbox"><h3>Import &ldquo;' + fileName + '&rdquo;</h3>' +
    "<p>This will update the parameters below. Nothing has changed yet.</p>" +
    "<table><thead><tr><th>Sheet</th><th>Will update</th></tr></thead><tbody>" +
    (rows || '<tr><td colspan="2">No recognised sheets found.</td></tr>') + "</tbody></table>" +
    unk + '<div class="xlbtns"><button type="button" class="xlcancel">Cancel</button>' +
    '<button type="button" class="xlok">Apply</button></div></div>';
  document.body.appendChild(ov);
  const close = () => ov.remove();
  ov.querySelector(".xlcancel").addEventListener("click", close);
  ov.querySelector(".xlok").addEventListener("click", () => { close(); xlApply(res.patch); });
  ov.addEventListener("click", e => { if (e.target === ov) close(); });
}

/* ---------------- Site Operation Plan (SOP) sheet: import + export ----------------
   ONE workbook carries every input: sheet 1 = the mine's own "SOP Template" (the
   monthly plan, one column per day + "<yyyy/mm> TOTAL"), then the report's
   non-plan sheets (PP Actuals, ROM Adjustments, Aux Equipment, Survey, ...).
   SOP rows are matched by (section number, label) - never by row number - and
   "Au grade, g/t" / "Ag grade, g/t" rows belong to the tonnage row above them;
   m3 rows convert to tonnes with the LCM density. Importing a month REPLACES
   that month's values of every metric the sheet carries, and keeps the whole
   sheet (inputs.sopraw[month]) so the export gives the planners their full
   sheet back - rows the report does not use included. */
const SOP_NORM = s => String(s == null ? "" : s).replace(/ /g, " ")
  .replace(/^\s*\d+(\.\d+)*\.?\s+/, "").replace(/\s+/g, " ").trim().toLowerCase();
const SOP_SEC = s => { const m = /^\s*(\d+)\.\s+\S/.exec(String(s == null ? "" : s).replace(/ /g, " ")); return m ? m[1] : null; };
const SOP_ALLORE = ["Subgrade (t)", "MinWaste (t)", "HG (t)", "MG (t)", "LG (t)", "LG1 (t)"];
/* the SOP layout the report knows, in the planners' own wording: the skeleton
   for a month that was never imported, and the source of the import mapping */
const SOP_LAYOUT = [
  ["4. MINING", null],
  ["4.1 Total Movement Materials, t", {m: "Total Movement (t)"}],
  ["Total Movement Materials, m3", {m: "Total Movement (m3)"}],
  ["4.1.1 Topsoil, t", {m: "Topsoil (t)"}],
  ["4.1.2 Waste, t", {m: "Waste (t)"}],
  ["Blasted Waste, m3", {m: "Blasted Waste (t)", dens: "W"}],
  ["Common Mineral, m3", {m: "Common Mineral (t)", dens: "BAS"}],
  ["Freedig Waste, m3", {m: "Freedig (t)", dens: "FD"}],
  ["4.2 Total Ore movement, t", {sum: SOP_ALLORE}],
  ["4.2.1 Non-Rom Ore, (0.1-0.45 g/t), t", {sum: ["Subgrade (t)", "MinWaste (t)"]}],
  ["Subgrade  (0.35-0.45 g/t), t", {m: "Subgrade (t)", au: "Subgrade Au (g/t)", ag: "Subgrade Ag (g/t)"}],
  ["Au grade, g/t", "au"], ["Ag grade, g/t", "ag"],
  ["MinWaste  (0.1-0.35 g/t), t", {m: "MinWaste (t)", au: "MinWaste Au (g/t)", ag: "MinWaste Ag (g/t)"}],
  ["Au grade, g/t", "au"], ["Ag grade, g/t", "ag"],
  ["4.2.2 Rom Ore, (>0.45 g/t), t", {sum: ["HG (t)", "MG (t)", "LG (t)", "LG1 (t)"], au: "Ore Au (g/t)", ag: "Ore Ag (g/t)"}],
  ["Au grade, g/t", "au"], ["Ag grade, g/t", "ag"],
  ["High-Grade ore (>6.0 g/t), t", {m: "HG (t)", au: "HG Au (g/t)", ag: "HG Ag (g/t)"}],
  ["Au grade, g/t", "au"], ["Ag grade, g/t", "ag"],
  ["Mid-Grade ore (2.0-6.0 g/t), t", {m: "MG (t)", au: "MG Au (g/t)", ag: "MG Ag (g/t)"}],
  ["Au grade, g/t", "au"], ["Ag grade, g/t", "ag"],
  ["Low-Grade2 ore (0.7-2.0 g/t), t", {m: "LG (t)", au: "LG Au (g/t)", ag: "LG Ag (g/t)"}],
  ["Au grade, g/t", "au"], ["Ag grade, g/t", "ag"],
  ["Low-Grade1 ore (0.45-0.7 g/t), t", {m: "LG1 (t)", au: "LG1 Au (g/t)", ag: "LG1 Ag (g/t)"}],
  ["Au grade, g/t", "au"], ["Ag grade, g/t", "ag"],
  ["6. ORE CRUSH", null],
  ["6.1 Crushed Total Ore, (>0.45 g/t), t", {sum: ["Crushed HG (t)", "Crushed MG (t)", "Crushed LG (t)"]}],
  ["High-Grade ore (>6.0 g/t), t", {m: "Crushed HG (t)"}],
  ["Mid-Grade ore (2.0-6.0 g/t), t", {m: "Crushed MG (t)"}],
  ["Low-Grade2 ore (0.7-2.0 g/t), t", {m: "Crushed LG (t)"}],
  ["7. MILL FEEDING", null],
  ["7.1 Total Ore Feed, t", {sum: ["Mill Feed HG (t)", "Mill Feed MG (t)", "Mill Feed LG (t)"]}],
  ["High-Grade ore (>6.0 g/t), t", {m: "Mill Feed HG (t)"}],
  ["High-Grade ore Au grade, g/t", {m: "Mill Feed HG Au (g/t)", g: 1}],
  ["High-Grade ore Ag grade, g/t", {m: "Mill Feed HG Ag (g/t)", g: 1}],
  ["Mid-Grade ore (2.0-6.0 g/t), t", {m: "Mill Feed MG (t)"}],
  ["Mid-Grade ore Au grade, g/t", {m: "Mill Feed MG Au (g/t)", g: 1}],
  ["Mid-Grade ore Ag grade, g/t", {m: "Mill Feed MG Ag (g/t)", g: 1}],
  ["Low-Grade2 ore (0.7-2.0 g/t), t", {m: "Mill Feed LG (t)"}],
  ["Low-Grade2 Au grade, g/t", {m: "Mill Feed LG Au (g/t)", g: 1}],
  ["Low-Grade2 Ag grade, g/t", {m: "Mill Feed LG Ag (g/t)", g: 1}],
  ["9. PROCESSING WASTE (Dry Cake Tailings)", null],
  ["Dry Cake Tailings, t", {m: "Tailings (t)"}],
];
const SOP_MAP = {};            /* section -> normalised label -> spec */
const SOP_METRICS = new Set(); /* every input metric the SOP sheet carries */
(() => { let sec = "";
  for (const [lab, spec] of SOP_LAYOUT){
    const s = SOP_SEC(lab); if (s){ sec = s; continue; }
    if (!spec || typeof spec !== "object") continue;
    (SOP_MAP[sec] = SOP_MAP[sec] || {})[SOP_NORM(lab)] = spec;
    for (const k of ["m", "au", "ag"]) if (spec[k]) SOP_METRICS.add(spec[k]);
  } })();
/* walk SOP rows, calling fn(row, kind, spec, metric): kind = "head" | "ton" |
   "sum" | "grade" | "other" (metric = the input metric of a ton / grade row) */
function sopWalk(rows, fn){
  let sec = "", last = null;
  for (const row of rows){
    const lab = row && row[0];
    if (lab == null || String(lab).trim() === ""){ fn(row, "other", null, null); continue; }
    const s = SOP_SEC(lab);
    if (s){ sec = s; last = null; fn(row, "head", null, null); continue; }
    const key = SOP_NORM(lab), spec = (SOP_MAP[sec] || {})[key];
    if (/^(au|ag) grade, g\/t$/.test(key)){
      const met = last && (key.startsWith("au") ? last.au : last.ag);
      fn(row, met ? "grade" : "other", last, met || null);
      continue;
    }
    if (spec){
      last = spec;
      if (spec.m) fn(row, spec.g ? "grade" : "ton", spec, spec.m);
      else fn(row, "sum", spec, null);
      continue;
    }
    last = null;
    fn(row, "other", null, null);
  }
}
/* sheets that are never an SOP plan, whatever their first column holds */
const XL_NOT_SOP = new Set(["master report", "budget", "work_order", "report v1"]);
function sopSheets(wb){            /* every sheet whose column A has a "Date" row with day columns */
  const out = [];
  for (const nm of (wb.__order || [])){
    if (XL_NOT_SOP.has(String(nm).trim().toLowerCase())) continue;
    const rows = wb[nm] || [];
    const hi = rows.findIndex(r => r && String(r[0] == null ? "" : r[0]).trim().toLowerCase() === "date"
                                  && r.some((v, c) => c > 0 && XLSXIO.asDate(v)));
    if (hi >= 0) out.push({name: nm, rows, hi});
  }
  return out;
}
function sopParse(sh){
  const head = sh.rows[sh.hi], dayCols = [];
  let totalCol = -1;
  head.forEach((v, c) => {
    if (c === 0) return;
    const d = XLSXIO.asDate(v);
    if (d) dayCols.push([c, d]);
    else if (totalCol < 0 && dayCols.length && /total/i.test(String(v || ""))) totalCol = c;
  });
  if (!dayCols.length) return null;
  const month = dayCols[0][1].slice(0, 7);
  const days = dayCols.filter(([, d]) => d.slice(0, 7) === month);
  const daily = {}, monthly = {}, metrics = [];
  const num = v => (typeof v === "number" && isFinite(v)) ? v : null;
  const r4 = v => Math.round(v * 10000) / 10000;
  const skipped = {};
  let secTitle = "", cells = 0;
  const body = sh.rows.slice(sh.hi + 1);
  sopWalk(body, (row, kind, spec, metric) => {
    if (kind === "head"){ secTitle = String(row[0]).trim(); return; }
    if (kind === "ton" || kind === "grade"){
      const isG = kind === "grade", f = (!isG && spec.dens) ? dens(spec.dens) : 1;
      const dm = daily[metric] = daily[metric] || {};
      for (const [c, d] of days){
        let v = num(row[c]);
        if (v === null){ if (isG) continue; v = 0; }
        if (isG && v <= 0) continue;              /* no grade on a day with no tonnes */
        dm[d] = r4(v * f); cells++;
      }
      const tv = totalCol >= 0 ? num(row[totalCol]) : null;
      if (tv !== null && !(isG && tv <= 0)) (monthly[metric] = monthly[metric] || {})[month] = r4(tv * f);
      if (!metrics.includes(metric)) metrics.push(metric);
      return;
    }
    if (kind === "other" && row && row[0] != null && String(row[0]).trim() !== ""){
      const has = days.some(([c]) => num(row[c]) !== null) || (totalCol >= 0 && num(row[totalCol]) !== null);
      if (has) skipped[secTitle || "(top)"] = (skipped[secTitle || "(top)"] || 0) + 1;
    }
  });
  /* the whole sheet, so the export can hand it back: label, column B, the days, TOTAL */
  const cols = [0, 1].concat(days.map(x => x[0]), totalCol >= 0 ? [totalCol] : []);
  const cellv = v => typeof v === "number" ? Math.round(v * 1e6) / 1e6 : (v == null || v === "" ? null : String(v));
  const raw = {sheet: sh.name.trim(), days: days.map(x => x[1]), total: totalCol >= 0,
               head: cols.map((c, i) => i >= 2 && i < 2 + days.length ? days[i - 2][1] : cellv(head[c])),
               rows: body.map(r => r ? cols.map(c => cellv(r[c])) : []).filter(r => r.some(v => v !== null))};
  while (raw.rows.length && raw.rows[raw.rows.length - 1].every(v => v === null)) raw.rows.pop();
  const notes = [[sh.name.trim() + " · " + month,
                  metrics.length + " metric(s), " + cells + " daily value(s), " + Object.keys(monthly).length +
                  " monthly total(s) - replaces " + month]];
  /* the plan's own identity: Total Movement = Topsoil + Waste + Total Ore */
  const tot = lab => { const r = body.find(x => x && SOP_NORM(x[0]) === lab); return r && totalCol >= 0 ? (num(r[totalCol]) || 0) : null; };
  const tm = tot("total movement materials, t"), parts = (tot("topsoil, t") || 0) + (tot("waste, t") || 0) + (tot("total ore movement, t") || 0);
  if (tm && Math.abs(tm - parts) / tm > 0.005)
    notes.push(["⚠ check", "Total Movement " + Math.round(tm).toLocaleString("en-US") + " t ≠ Topsoil + Waste + Total Ore " + Math.round(parts).toLocaleString("en-US") + " t in the sheet"]);
  const unknown = Object.entries(skipped).map(([t, n]) => sh.name.trim() + ": " + t + " — " + n + " row(s)");
  return {month, daily, monthly, metrics, raw, notes, unknown};
}

/* the SOP sheet for month M, filled from the current inputs: the planners' own
   sheet as last imported (every row kept, report rows overwritten with the
   current plan), or the report's skeleton when that month was never imported */
function sopExportRows(M){
  const raw = (inputs.sopraw || {})[M];
  const days = raw ? raw.days : monthDays(M);
  const r6 = v => (v === null || v === undefined || !isFinite(v)) ? null : Math.round(v * 1e6) / 1e6;
  const dv = (m, d) => { const x = (inputs.daily[m] || {})[d]; return (x === undefined || x === null) ? null : +x; };
  const mv = m => { const x = (inputs.monthly[m] || {})[M]; return (x === undefined || x === null) ? null : +x; };
  const has = m => days.some(d => dv(m, d) !== null) || mv(m) !== null;
  const series = (kind, spec, metric) => {
    if (kind === "sum"){
      const v = days.map(d => { let s = null; for (const m of spec.sum){ const x = dv(m, d); if (x !== null) s = (s || 0) + x; } return s; });
      let t = 0, any = false; for (const m of spec.sum){ const x = mv(m); if (x !== null){ t += x; any = true; } }
      return {v, t: any ? t : v.reduce((a, b) => a + (b || 0), 0)};
    }
    const f = (kind === "ton" && spec && spec.dens) ? 1 / dens(spec.dens) : 1;
    const v = days.map(d => { const x = dv(metric, d); return x === null ? (kind === "ton" ? 0 : null) : x * f; });
    const t = mv(metric);
    return {v, t: t !== null ? t * f : (kind === "ton" ? v.reduce((a, b) => a + (b || 0), 0) : null)};
  };
  const nD = days.length;
  if (raw){
    const rows = raw.rows.map(r => r.slice());
    sopWalk(rows, (row, kind, spec, metric) => {
      if ((kind === "ton" || kind === "grade") && has(metric)){
        const s = series(kind, spec, metric);
        for (let i = 0; i < nD; i++) row[2 + i] = r6(s.v[i]);
        if (raw.total) row[2 + nD] = r6(s.t);
      }
    });
    return [raw.head.slice()].concat(rows);
  }
  const [y, m] = M.split("-").map(Number);
  const prev = new Date(Date.UTC(y, m - 2, 1)).toLocaleString("en-US", {month: "long", timeZone: "UTC"});
  const out = [["Date", "End of " + prev].concat(days, [M.replace("-", "/") + " TOTAL"])];
  sopWalk(SOP_LAYOUT.map(([lab]) => [lab]), (row, kind, spec, metric) => {
    if (kind === "head" || kind === "other"){ out.push([row[0]]); return; }
    const s = series(kind, spec, metric);
    out.push([row[0], null].concat(s.v.map(r6), [r6(s.t)]));
  });
  return out;
}

const XL_KNOWN = new Set(["sop template", "sop  template", "other targets", "daily targets", "monthly targets",
  "pp actuals", "mill monthly", "lcm", "rom adjustments", "aux equipment", "survey", "other data",
  "master report", "budget", "work_order"]);
async function xlImportFile(f){
  try{
    /* an .xlsm Master Report workbook carries 50 MB of department records: read only the
       sheets that can be inputs, plus anything small */
    const wb = await XLSXIO.read(await f.arrayBuffer(), {maxSheetBytes: 6e6, want: n => XL_KNOWN.has(n.toLowerCase())});
    const res = xlParseWorkbook(wb);
    for (const sh of sopSheets(wb)){
      const s = sopParse(sh);
      if (!s) continue;
      for (const m in s.daily) res.patch.daily[m] = Object.assign(res.patch.daily[m] || {}, s.daily[m]);
      for (const m in s.monthly) res.patch.monthly[m] = Object.assign(res.patch.monthly[m] || {}, s.monthly[m]);
      res.patch.clearMonths.push({month: s.month, metrics: s.metrics});
      res.patch.sopraw[s.month] = s.raw;
      res.notes.unshift(...s.notes);
      res.unknown.push(...s.unknown);
    }
    if (!res.notes.length){ alert("Nothing to import: the workbook has no SOP sheet (a \u201cDate\u201d row of day columns) and none of the report's input sheets."); return; }
    if ((wb.__skipped || []).length)
      res.notes.push(["Not read (large, not an input sheet)", wb.__skipped.map(x => x.name + " (" + x.mb.toFixed(1) + " MB)").join(", ")]);
    xlPreview(res, f.name);
  }catch(e){ alert("Could not read that workbook: " + e); }
}

/* -------- paste a block copied from Excel straight into any editor grid ---- */
function wirePasteGrids(){
  document.querySelectorAll("table.edit").forEach(t => {
    if (t.__paste) return;
    t.__paste = 1;
    t.addEventListener("paste", ev => {
      const txt = (ev.clipboardData || window.clipboardData).getData("text");
      if (!txt || txt.indexOf("\t") < 0 && txt.indexOf("\n") < 0) return;
      const cell = ev.target;
      if (!cell || cell.tagName !== "INPUT") return;
      ev.preventDefault();
      window.__pasting = 1;
      const td = cell.closest("td"), tr = td.closest("tr");
      const c0 = [...tr.children].indexOf(td), r0 = [...t.rows].indexOf(tr);
      const grid = txt.replace(/\r/g, "").replace(/\n$/, "").split("\n").map(l => l.split("\t"));
      let n = 0;
      grid.forEach((line, ri) => {
        const row = t.rows[r0 + ri];
        if (!row) return;
        line.forEach((val, ci) => {
          const target = row.children[c0 + ci];
          const inp = target && target.querySelector("input");
          if (!inp) return;
          const v = parseFloat(String(val).replace(/[, ]/g, ""));
          inp.value = isFinite(v) ? v : "";
          inp.dispatchEvent(new Event("change", {bubbles: true}));
          n++;
        });
      });
      window.__pasting = 0;
      if (n){ saveInputs(); refresh(false); console.log("[inputs] pasted " + n + " cell(s)"); }
    });
  });
}
"""
