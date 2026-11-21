"""Engineering notes with photographs (request 06).

Erdene asked to attach the mine engineers' picture reports to the daily report.
The page is a single self-contained HTML file that people mail around, so:

  * notes and photographs live in IndexedDB, not localStorage - localStorage caps
    out near 5 MB and one phone photo would fill it;
  * photographs are downscaled to 1600 px on the long edge and re-encoded as
    JPEG before storing, so a twenty-photo shift report stays a few megabytes;
  * they travel in the existing "Export inputs (JSON)" bundle as data URIs, so
    one engineer can prepare a set and send it to the rest;
  * they PRINT (the add/delete controls do not), and render_pdf.py waits on
    window.__notesReady before printing.

Notes are filtered by the report's selected period, so the PDF for a period
carries exactly the notes written for it.
"""

NOTES_CSS = r"""
  /* ------------------------------------------------- engineering notes (06) */
  .ndadd{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:10px 0 4px;font-size:12px}
  .ndadd input,.ndadd select,.ndadd textarea{font:inherit;font-size:12px;padding:4px 7px;
        border:1px solid #c3cbd1;border-radius:4px}
  .ndadd input[type=text]{width:230px}
  .ndadd textarea{width:100%;min-height:52px;resize:vertical}
  .nddrop{border:1px dashed #b9c2c9;border-radius:6px;padding:10px 14px;color:#6b747b;
        font-size:12px;background:#fbfcfd;flex:1 1 260px;cursor:pointer}
  .nddrop.on{border-color:var(--gold);background:#fffdf3;color:var(--ink)}
  .ndqueue{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
  .ndqueue img{height:52px;border-radius:4px;border:1px solid #dde3e7}
  .ndnote{border:1px solid #e2e7ea;border-left:4px solid var(--gold);border-radius:6px;
        background:#fff;padding:10px 14px 12px;margin-top:12px;break-inside:avoid;
        box-shadow:0 1px 3px rgba(16,24,32,.08)}
  .ndnote h4{margin:0 0 3px;font-size:13.5px}
  .ndmeta{font-size:11.5px;color:#6b747b;margin-bottom:6px}
  .ndtext{font-size:12.5px;white-space:pre-wrap;line-height:1.5}
  .ndimgs{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
  .ndimgs img{max-height:180px;max-width:100%;border-radius:4px;border:1px solid #dde3e7;
        cursor:zoom-in}
  .ndlight{position:fixed;inset:0;background:rgba(12,15,18,.86);z-index:430;display:flex;
        align-items:center;justify-content:center;padding:20px;cursor:zoom-out}
  .ndlight img{max-width:96vw;max-height:94vh;border-radius:5px}
  @media print{
    .ndadd,.nddrop,.ndqueue,.nddel,.ndlight{display:none !important}
    .ndimgs img{max-height:120px}
  }
"""

NOTES_SECTION_HTML = r"""
  <div class="banner" id="secNotes">ENGINEERING NOTES &amp; SITE PHOTOGRAPHS</div>
  <div class="note noprint">Written and stored in <b>this browser</b> (not in R4M). Notes dated inside the selected reporting period appear below and are included when the page is printed to PDF. To share them, print the period to PDF.</div>
  <div class="ndadd noprint">
    <input type="date" id="ndDate">
    <select id="ndShift"><option value="">Both shifts</option><option value="DS">Day (DS)</option><option value="NS">Night (NS)</option></select>
    <input type="text" id="ndTitle" placeholder="Title, e.g. 1217 bench face" maxlength="90">
    <label class="nddrop" id="ndDrop">Drop or paste photographs here, or click to choose files
      <input type="file" id="ndFiles" accept="image/*" multiple style="display:none"></label>
  </div>
  <div class="ndadd noprint"><textarea id="ndText" placeholder="What the engineers observed..."></textarea></div>
  <div class="ndadd noprint">
    <button type="button" id="ndAdd">Add note</button>
    <span class="hint" id="ndStatus"></span>
  </div>
  <div class="ndqueue noprint" id="ndQueue"></div>
  <div id="ndList"></div>
"""

NOTES_JS = r"""
/* ==================================== engineering notes with photographs (06)
   IndexedDB-backed; see notes_template.py for why localStorage is not used. */
const ND_DB = "erd_report_notes", ND_V = 1;
let ndPending = [];              /* images queued for the note being written */
let ndReadyResolve;
window.__notesReady = new Promise(r => { ndReadyResolve = r; });

function ndOpen(){
  return new Promise((res, rej) => {
    const rq = indexedDB.open(ND_DB, ND_V);
    rq.onupgradeneeded = () => {
      const db = rq.result;
      if (!db.objectStoreNames.contains("notes")) db.createObjectStore("notes", {keyPath: "id"});
      if (!db.objectStoreNames.contains("images")) db.createObjectStore("images");
    };
    rq.onsuccess = () => res(rq.result);
    rq.onerror = () => rej(rq.error);
  });
}
function ndTx(store, mode, fn){
  return ndOpen().then(db => new Promise((res, rej) => {
    const tx = db.transaction(store, mode), st = tx.objectStore(store);
    const out = fn(st);
    tx.oncomplete = () => res(out && out.result !== undefined ? out.result : out);
    tx.onerror = () => rej(tx.error);
  }));
}
function ndAll(){
  return ndTx("notes", "readonly", st => st.getAll()).catch(e => {
    console.warn("notes unavailable", e); return [];
  });
}

/* photographs are re-encoded before they are stored: a 12 MP phone picture
   becomes ~200 KB, so a whole shift report still fits in a mailed JSON bundle */
async function ndShrink(file, max){
  max = max || 1600;
  try{
    const bmp = await createImageBitmap(file);
    const s = Math.min(1, max / Math.max(bmp.width, bmp.height));
    const w = Math.round(bmp.width * s), h = Math.round(bmp.height * s);
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    cv.getContext("2d").drawImage(bmp, 0, 0, w, h);
    bmp.close && bmp.close();
    return await new Promise(r => cv.toBlob(r, "image/jpeg", 0.82));
  }catch(e){ return file; }          /* unreadable image: store it as-is */
}

function ndQueueRender(){
  const q = document.getElementById("ndQueue");
  if (!q) return;
  q.innerHTML = "";
  for (const p of ndPending){
    const img = document.createElement("img");
    img.src = p.url;
    img.title = p.name + " — click to remove";
    img.style.cursor = "pointer";
    img.addEventListener("click", () => {
      URL.revokeObjectURL(p.url);
      ndPending = ndPending.filter(x => x !== p);
      ndQueueRender();
    });
    q.appendChild(img);
  }
  const st = document.getElementById("ndStatus");
  if (st) st.textContent = ndPending.length ? ndPending.length + " photograph(s) attached" : "";
}

async function ndAcceptFiles(files){
  for (const f of files){
    if (!/^image\//.test(f.type)) continue;
    const blob = await ndShrink(f);
    ndPending.push({id: "i" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
                    name: f.name, blob, url: URL.createObjectURL(blob)});
  }
  ndQueueRender();
}

async function ndAddNote(){
  const date = document.getElementById("ndDate").value || PERIOD.end;
  const title = (document.getElementById("ndTitle").value || "").trim();
  const text = (document.getElementById("ndText").value || "").trim();
  if (!title && !text && !ndPending.length){ alert("Write something or attach a photograph first."); return; }
  const note = {id: "n" + Date.now().toString(36), date,
                shift: document.getElementById("ndShift").value || "",
                title: title || "Site note", text, images: ndPending.map(p => p.id)};
  const imgs = ndPending.slice();
  await ndTx("images", "readwrite", st => { for (const p of imgs) st.put(p.blob, p.id); });
  await ndTx("notes", "readwrite", st => st.put(note));
  for (const p of imgs) URL.revokeObjectURL(p.url);
  ndPending = [];
  document.getElementById("ndTitle").value = "";
  document.getElementById("ndText").value = "";
  ndQueueRender();
  await ndRender();
}

async function ndDelete(id){
  const notes = await ndAll();
  const n = notes.find(x => x.id === id);
  if (!n) return;
  await ndTx("images", "readwrite", st => { for (const i of (n.images || [])) st.delete(i); });
  await ndTx("notes", "readwrite", st => st.delete(id));
  await ndRender();
}

let ndUrls = [];
async function ndRender(){
  const host = document.getElementById("ndList");
  if (!host) return;
  for (const u of ndUrls) URL.revokeObjectURL(u);
  ndUrls = [];
  const all = (await ndAll()).filter(n => n.date >= PERIOD.start && n.date <= PERIOD.end)
                             .sort((a, b) => a.date < b.date ? 1 : -1);
  document.body.classList.toggle("nd-empty", !all.length);
  host.innerHTML = "";
  if (!all.length){
    host.innerHTML = '<div class="mdempty noprint"><b>No notes for this period.</b> Add the engineers&rsquo; ' +
      'observations and photographs above; they are stored in this browser and printed with the report.</div>';
    ndReadyResolve();
    return;
  }
  const store = await ndTx("images", "readonly", st => st.getAll()).catch(() => []);
  const keys = await ndTx("images", "readonly", st => st.getAllKeys()).catch(() => []);
  const byId = new Map(keys.map((k, i) => [k, store[i]]));
  const pend = [];
  for (const n of all){
    const el = document.createElement("div");
    el.className = "ndnote";
    el.innerHTML = "<h4>" + esc(n.title) + "</h4>" +
      '<div class="ndmeta">' + n.date + (n.shift ? " &middot; " + n.shift : "") +
      ' <button type="button" class="mddel nddel noprint" title="Delete this note">&#10005;</button></div>' +
      (n.text ? '<div class="ndtext">' + esc(n.text) + "</div>" : "") +
      '<div class="ndimgs"></div>';
    el.querySelector(".nddel").addEventListener("click", () => {
      if (confirm("Delete this note and its photographs?")) ndDelete(n.id);
    });
    const box = el.querySelector(".ndimgs");
    for (const iid of (n.images || [])){
      const blob = byId.get(iid);
      if (!blob) continue;
      const url = URL.createObjectURL(blob);
      ndUrls.push(url);
      const img = document.createElement("img");
      img.src = url;
      img.alt = n.title;
      img.addEventListener("click", () => ndLightbox(url));
      pend.push(new Promise(r => { img.onload = img.onerror = r; }));
      box.appendChild(img);
    }
    host.appendChild(el);
  }
  await Promise.all(pend);        /* the PDF must not print half-loaded images */
  ndReadyResolve();
}

function ndLightbox(url){
  const ov = document.createElement("div");
  ov.className = "ndlight noprint";
  ov.innerHTML = '<img src="' + url + '">';
  ov.addEventListener("click", () => ov.remove());
  document.addEventListener("keydown", function esc_(e){
    if (e.key === "Escape"){ ov.remove(); document.removeEventListener("keydown", esc_); }
  });
  document.body.appendChild(ov);
}

/* ---- the export bundle carries notes so a set can be mailed to a colleague */
async function ndExportBlock(){
  const notes = await ndAll();
  if (!notes.length) return null;
  const store = await ndTx("images", "readonly", st => st.getAll()).catch(() => []);
  const keys = await ndTx("images", "readonly", st => st.getAllKeys()).catch(() => []);
  const byId = new Map(keys.map((k, i) => [k, store[i]]));
  const toDataUrl = b => new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(b); });
  const images = {};
  for (const [k, v] of byId) if (v) images[k] = await toDataUrl(v);
  return {notes, images};
}
async function ndImportBlock(block){
  if (!block || !Array.isArray(block.notes)) return 0;
  const imgs = block.images || {};
  await ndTx("images", "readwrite", st => {
    for (const k in imgs){
      const [meta, b64] = String(imgs[k]).split(",");
      const bin = atob(b64 || ""), buf = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
      st.put(new Blob([buf], {type: (/data:([^;]+)/.exec(meta) || [, "image/jpeg"])[1]}), k);
    }
  });
  await ndTx("notes", "readwrite", st => { for (const n of block.notes) st.put(n); });
  await ndRender();
  return block.notes.length;
}

function wireNotes(){
  const drop = document.getElementById("ndDrop"), files = document.getElementById("ndFiles");
  if (!drop) return;
  const dsel = document.getElementById("ndDate");
  if (dsel && !dsel.value) dsel.value = PERIOD.end;
  drop.addEventListener("click", e => { if (e.target !== files) files.click(); });
  files.addEventListener("change", () => { ndAcceptFiles([...files.files]); files.value = ""; });
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => {
    e.preventDefault(); drop.classList.add("on");
  }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => {
    e.preventDefault(); drop.classList.remove("on");
  }));
  drop.addEventListener("drop", e => ndAcceptFiles([...(e.dataTransfer.files || [])]));
  document.addEventListener("paste", e => {
    if (!document.getElementById("secNotes")) return;
    const items = [...((e.clipboardData || {}).items || [])].filter(i => /^image\//.test(i.type));
    if (!items.length) return;
    ndAcceptFiles(items.map(i => i.getAsFile()).filter(Boolean));
  });
  document.getElementById("ndAdd").addEventListener("click", ndAddNote);
}
"""
