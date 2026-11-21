"""Sheet 1 of daily_report_v3: Erdene's one-page "Bayankhundii Gold Mine Master Report".

The client's own Excel (Master Report Example.xlsm, sheet REPORT V1) is the model:
12 numbered sections (this page produces only 4 Mining, 5 ROM inventories, 7 Mill feeding - see
SHOW_SECS), columns TODAY | MTD | (MTD SURVEY) | QTD | YTD | MONTHLY PLAN |
MONTHLY EXECUTION | ANNUAL PLAN | ANNUAL EXECUTION, one A4 page, signed.

ONE spec (MASTER_ROWS, below) drives everything: the rendered table, the manual series
seeded into inputs.manual (group "master", keys "mr_<id>"), the "Master Report" and
"Budget" sheets of the input workbook, and the import of the client's own Work_Order
(budget) sheet. Row kinds:

  cube    mining rows from the live R4M cube, reusing the daily report's MP_ROWS
          (src.mp = MP row id) - identical numbers by construction
  feed    mill-feed rows, reusing MF_ROWS (src.mf)
  rom     ROM balances by class (romState() of the daily report, summed by pile prefix)
  calc    sums of other rows (src.sum) or a named formula (src.calc)
  manual  typed / imported per day (agg: sum | mean | wavg:<id> | last = a balance)

Periods are whole calendar windows ending on the report date D: TODAY [D],
MTD [1st of month, D], QTD [1st of quarter, D], YTD [1 Jan, D]. Plan columns come
from inputs.budget = {row id: {"YYYY-MM": v, "YYYY": annual total}} (the client's
approved budget, Work_Order sheet); section 5's annual plan is the December value.
"""
import json

SECS = [
    (1, "SAFETY & Environment", "std"),
    (2, "GRADE CONTROL", "std"),
    (3, "DRILL & BLAST", "std"),
    (4, "MINING", "mining"),
    (5, "ROM INVENTORIES", "rom"),
    (6, "ORE CRUSH", "std"),
    (7, "MILL FEEDING", "mining"),
    (8, "PROCESSING⁴", "std"),
    (9, "SITE SERVICES & INFRASTRUCTURE", "std"),
    (10, "FUEL (DIESEL)", "std"),
    (11, "CHEMICAL", "std"),
    (12, "EXPLOSIVES MATERIAL", "std"),
]
MASTER_SECS = [{"sec": s, "title": t, "cols": c} for s, t, c in SECS]

MRSET_DEFAULT = {
    "dept": "Mining department - Dispatch section",
    "email": "dispatch@example.com",
    "reviewed": "Khurtsbaatar B. / Senior Chief Engineer",
    "prepared": "Name / Senior Dispatcher",
}

MASTER_ROWS = []


def _row(sec, id_, label, kind, **kw):
    r = {"sec": sec, "id": id_, "label": label, "kind": kind, "ind": 0, "fmt": "int",
         "exec": "pct", "budget": [label]}
    r.update(kw)
    if r["budget"] is None:
        r["budget"] = []
    MASTER_ROWS.append(r)
    return r


def _man(sec, id_, label, unit, agg="sum", **kw):
    kw.setdefault("budget", [label])
    return _row(sec, id_, label, "manual", unit=unit, agg=agg, **kw)


def _stock(sec, id_, label, unit, **kw):
    kw.setdefault("budget", None)
    kw.setdefault("exec", None)
    return _row(sec, id_, label, "manual", unit=unit, agg="last", stock=True, **kw)


def _sum(sec, id_, label, ids, **kw):
    return _row(sec, id_, label, "calc", src={"sum": ids}, **kw)


def _grades(sec, parent, kind, src_au, src_ag, ind, labels=("Au grade, g/t", "Ag grade, g/t"),
            budget=True, **kw):
    for met, src, lab in (("au", src_au, labels[0]), ("ag", src_ag, labels[1])):
        bud = (["Au grade, g/t"] if met == "au" else ["Ag grade, g/t"]) + ([lab] if lab not in
                                                                          ("Au grade, g/t", "Ag grade, g/t") else [])
        _row(sec, parent + "." + met, lab, kind, ind=ind, fmt="d2", exec="diff", parent=parent,
             src=src, budget=bud if budget else None, **kw)


# ---------------------------------------------------------------- 1. safety
for _id, _lab in (("lti", "Lost Time Injury (LTI)"), ("rtw", "Alternative Work Injury (RTW)"),
                  ("mti", "Medical Treatment Injury (MTI)"), ("fai", "First Aid Injury (FAI)"),
                  ("prd", "Property Damage (PrD)"), ("nm", "Near Miss (NM)"), ("spill", "Spillage")):
    _man(1, "saf." + _id, _lab, "count", budget=None, exec=None)

# ---------------------------------------------------------- 2. grade control
for _b, _p, _n in (("bk", "BK", "2.1"), ("dh", "DH", "2.2")):
    g = "gc." + _b
    _sum(2, g + ".drill", _n + ".1 Total Drilling, m (" + _p + ")", [g + ".rc", g + ".core"], bold=True,
         budget=["Total Drilling, m (" + _p + ")"])
    _man(2, g + ".rc", "RC, m", "m", ind=1, parent=g + ".drill")
    _man(2, g + ".core", "Core, m", "m", ind=1, parent=g + ".drill")
    _sum(2, g + ".samp", _n + ".2 Sample analysing, pcs (" + _p + ")",
         [g + ".std", g + ".blank", g + ".dup", g + ".routine"], bold=True,
         budget=["Sample analysing, pcs (" + _p + ")"])
    for _k, _l in (("std", "STD, pcs"), ("blank", "BLANK, pcs"), ("dup", "DUP, pcs"), ("routine", "ROUTINE, pcs")):
        _man(2, g + "." + _k, _l, "pcs", ind=1, parent=g + ".samp")
    _sum(2, g + ".assay", _n + ".3 Assay result, pcs (" + _p + ")", [g + ".als", g + ".uback", g + ".ubsgs"],
         bold=True, budget=["Assay result, pcs (" + _p + ")"])
    for _k, _l in (("als", "On site ALS, pcs"), ("uback", "UB ALS, pcs"), ("ubsgs", "UB SGS, pcs")):
        _man(2, g + "." + _k, _l, "pcs", ind=1, parent=g + ".assay")

# ----------------------------------------------------------- 3. drill & blast
_sum(3, "db.drill", "3.1 Total Drilling, m", ["db.d89", "db.d102", "db.d115", "db.d140"], bold=True)
for _d in ("89", "102", "115", "140"):
    _man(3, "db.d" + _d, "Drilling-" + _d + "mm, m", "m", ind=1)
_man(3, "db.samp", "3.1.1 Sample analysing, pcs", "pcs", bold=True)
_sum(3, "db.expl", "3.2 Total explosive, kg", ["db.emul", "db.anfo"], bold=True)
_man(3, "db.emul", "Emulsion, kg", "kg", ind=1)
_man(3, "db.anfo", "Anfo, kg", "kg", ind=1)
_sum(3, "db.blast", "3.2.1 Total Blasted material, m3", ["db.waste", "db.ore"], bold=True)
_man(3, "db.waste", "Blasted waste, m3", "m3", ind=1)
_man(3, "db.ore", "Blasted ore, m3", "m3", ind=1)
_row(3, "db.pf", "PF, kg/m3", "calc", ind=1, fmt="d2", exec="diff", src={"calc": "pf"},
     note="Total explosive ÷ total blasted material")

# ------------------------------------------------------------------ 4. mining
_SV_ROM = ["sv_hg", "sv_mg", "sv_lg2", "sv_lg1"]
_sum(4, "mn.tm", "4.1 Total Movement, t", ["mn.ts", "mn.fd", "mn.bw", "mn.cm", "mn.nonrom", "mn.rom"], bold=True,
     budget=["Total Movement, t"],
     note="Topsoil + Freedig + Blasted Waste + Common Mineral + Non-Rom ore + Rom ore, ex-rehandle "
          "(engineering work and tailings transport are not material movement here)")
_row(4, "mn.ts", "Topsoil, t", "cube", src={"mp": "ts"}, sv=["sv_ts"], bold=True)
_row(4, "mn.fd", "Freedig Waste, t", "cube", src={"mp": "fd"}, sv=["sv_fd"], bold=True)
_row(4, "mn.bw", "Blasted Waste, t", "cube", src={"mp": "bw"}, sv=["sv_w"], bold=True,
     budget=["Waste, t", "Blasted Waste, t"], note="Budget line: 'Waste, t'")
_row(4, "mn.cm", "Common Mineral, t", "cube", src={"mp": "cm_t"}, sv=["sv_bas"], ind=1,
     budget=["Common Miner", "Common Mineral, t"])
_sum(4, "mn.nonrom", "Non-Rom Ore, t", ["mn.sg", "mn.mw"], bold=True, budget=["Non-ROM Ore ,t"])
_row(4, "mn.sg", "Subgrade (0.35-0.45 g/t), t", "cube", src={"mp": "sg"}, sv=["sv_sg"], ind=1, bold=True)
_grades(4, "mn.sg", "cube", {"mp": "sg.au"}, {"mp": "sg.ag"}, 2)
_row(4, "mn.mw", "MinWaste (0.1-0.35 g/t), t", "cube", src={"mp": "mw"}, sv=["sv_mw"], ind=1, bold=True)
_grades(4, "mn.mw", "cube", {"mp": "mw.au"}, {"mp": "mw.ag"}, 2)
_sum(4, "mn.rom", "Rom Ore, (>0.45 g/t), t", ["mn.hg", "mn.mg", "mn.lg2", "mn.lg1"], bold=True)
_grades(4, "mn.rom", "cube", {"mp": "ore.au"}, {"mp": "ore.ag"}, 1)
for _c, _lab, _alias in (("hg", "High-Grade ore (>6.0 g/t), t", None),
                         ("mg", "Mid-Grade ore (2.0-6.0 g/t), t", None),
                         ("lg2", "Low-Grade2 ore (0.7-2.0 g/t), t", "Low-Grade2ore (0.7-2.0 g/t), t"),
                         ("lg1", "Low-Grade1 ore (0.45-0.7 g/t), t", None)):
    _row(4, "mn." + _c, _lab, "cube", src={"mp": _c}, sv=["sv_" + _c], ind=1, bold=True,
         budget=[_lab] + ([_alias] if _alias else []))
    _grades(4, "mn." + _c, "cube", {"mp": _c + ".au"}, {"mp": _c + ".ag"}, 2)
_SR = "Master Report definitions (the client's): Waste = Blasted Waste + Topsoil; m3/t uses the LCM densities. " \
      "The daily report's SOP strip ratios are defined differently."
_row(4, "mn.sr.sub.tt", "Strip ratio (included Sub+MinW), t/t", "calc", ind=1, fmt="d2", exec="diff",
     src={"calc": "sr_sub_tt"}, note="(Blasted Waste + Topsoil) ÷ (Rom + Non-Rom ore). " + _SR)
_row(4, "mn.sr.sub.m3t", "Strip ratio (included Sub+MinW), m3/t", "calc", ind=1, fmt="d2", exec="diff",
     src={"calc": "sr_sub_m3t"}, note="(Blasted Waste + Topsoil) in m3 ÷ (Rom + Non-Rom ore) t. " + _SR)
_row(4, "mn.sr.tot.tt", "Strip ratio (Total Ore) (t/t)", "calc", ind=1, fmt="d2", exec="diff",
     src={"calc": "sr_tot_tt"}, note="(Blasted Waste + Topsoil + Non-Rom ore) ÷ Rom ore. " + _SR)
_row(4, "mn.sr.tot.m3t", "Strip ratio (Total Ore) (m3/t)", "calc", ind=1, fmt="d2", exec="diff",
     src={"calc": "sr_tot_m3t"}, note="(Blasted Waste + Topsoil + Non-Rom ore) in m3 ÷ Rom ore t. " + _SR)
_EOM = "It will be updated once at the end of the month"
_stock(4, "mn.loss", "Metal loss %", "%", fmt="d2", cols="mtd", empty=_EOM)
_stock(4, "mn.dil", "Ore Dilution %", "%", fmt="d2", cols="mtd", empty=_EOM)

# ---------------------------------------------------------------- 5. ROM
_row(5, "rom.all", "Stockpile ore balance, (>0.45 g/t), t", "rom", src={"cls": "ALL", "val": "t"}, bold=True,
     budget=None, plan={"sum": ["rom.hg", "rom.mg", "rom.lg2"]},
     sv={"stock": ["sv_rom_hg", "sv_rom_mg", "sv_rom_lg2", "sv_rom_lg1"], "fallback": "sv_romstock"})
_grades(5, "rom.all", "rom", {"cls": "ALL", "val": "au"}, {"cls": "ALL", "val": "ag"}, 1, budget=False,
        plan={"wavg": "rom"})
for _c, _lab, _alias in (("hg", "High-Grade ore (>6.0 g/t), t", "High-Grade ore (Au>6.0 g/t), t"),
                         ("mg", "Mid-Grade ore (2.0-6.0 g/t), t", "Mid-Grade ore (6.0 g/t >Au>2.0 g/t), t"),
                         ("lg2", "Low-Grade2 ore (0.7-2.0 g/t), t", "Low-Grade ore (2.0 g/t >Au>0.45 g/t), t"),
                         ("lg1", "Low-Grade1 ore (0.45-0.7 g/t), t", None)):
    kw = {}
    if _c == "lg2":
        kw = {"execActual": ["rom.lg2", "rom.lg1"],
              "note": "The budget plans Low-Grade ore (2.0>Au>0.45) as one line: execution = (LG2 + LG1) ÷ that plan"}
    _row(5, "rom." + _c, _lab, "rom", src={"cls": _c.upper(), "val": "t"}, ind=1, bold=True,
         sv={"stock": ["sv_rom_" + _c]}, budget=([_lab, _alias] if _alias else None), **kw)
    _grades(5, "rom." + _c, "rom", {"cls": _c.upper(), "val": "au"}, {"cls": _c.upper(), "val": "ag"}, 2,
            budget=_c != "lg1")

# ------------------------------------------------------------- 6. ore crush
_sum(6, "cr.all", "Crushed Total Ore, (>0.45 g/t), t", ["cr.hg", "cr.mg", "cr.lg", "cr.prehg"], bold=True,
     note="Mobile crusher - entered by hand (the crusher is not in the FMS)")
_man(6, "cr.hg", "High-Grade ore (>6.0 g/t), t", "t", ind=1, budget=None)
_man(6, "cr.mg", "Mid-Grade ore (2.0-6.0 g/t), t", "t", ind=1, budget=None)
_man(6, "cr.lg", "Low-Grade ore (0.7-2.0 g/t), t", "t", ind=1, budget=None)
_man(6, "cr.prehg", "Pre-HG ore, t", "t", ind=1, budget=None)

# ----------------------------------------------------------- 7. mill feeding
# Survey side (client deck, slide 12): tonnes = the plant's month-end reconciliation per class
# (7.1 MILLFEED_PP, sv_ff_*), grades = R4M dispatch grades; total = sum of the classes.
_FF_SV = {"hg": ["sv_ff_hg"], "mg": ["sv_ff_mg"], "lg": ["sv_ff_lg2", "sv_ff_lg1"]}
_row(7, "ff.t", "Total Ore Feed, t", "feed", src={"mf": "feed"}, bold=True,
     sv=_FF_SV["hg"] + _FF_SV["mg"] + _FF_SV["lg"])
_row(7, "ff.au", "Feed Head Grade Au g/t", "feed", src={"mf": "feed.au"}, ind=1, fmt="d2", exec="diff",
     parent="ff.t", budget=["Au grade, g/t", "Feed Head Grade Au g/t"])
_row(7, "ff.aukg", "Contained Gold, kg", "feed", src={"mf": "feed.aukg"}, ind=1, fmt="d2",
     budget=None, plan={"kg": ["ff.t", "ff.au"]})
_row(7, "ff.ag", "Feed Head Grade Ag g/t", "feed", src={"mf": "feed.ag"}, ind=1, fmt="d2", exec="diff",
     parent="ff.t", budget=["Ag grade, g/t", "Feed Head Grade Ag g/t"])
_row(7, "ff.agkg", "Contained Silver, kg", "feed", src={"mf": "feed.agkg"}, ind=1, fmt="d2",
     budget=None, plan={"kg": ["ff.t", "ff.ag"]})
for _c, _lab, _alias, _glab in (
        ("hg", "High-Grade ore (>6.0 g/t), t", "High-Grade ore (Au>6.0 g/t), t", "High-Grade ore"),
        ("mg", "Mid-Grade ore (2.0-6.0 g/t), t", "Mid-Grade ore (6.0 g/t >Au>2.0 g/t), t", "Mid-Grade ore"),
        ("lg", "Low-Grade2 ore (0.7-2.0 g/t), t", "Low-Grade ore (2.0 g/t >Au>0.45 g/t), t", "Low-Grade")):
    _row(7, "ff." + _c, _lab, "feed", src={"mf": "feed." + _c}, ind=1, bold=True, budget=[_lab, _alias], sv=_FF_SV[_c],
         note=("LG1 + LG2 crusher deliveries" if _c == "lg" else None))
    _grades(7, "ff." + _c, "feed", {"mf": "feed." + _c + ".au"}, {"mf": "feed." + _c + ".ag"}, 2,
            labels=(_glab + " Au grade, g/t", _glab + " Ag grade, g/t"))
_row(7, "ff.blend", "Blend ratio, %", "feed", src={"mf": "feed.blend"}, bold=True, fmt="pct", exec="diff",
     bpct=True, budget=["Blend ratio, %", "Mill Feeding ratio,%"])
for _c, _lab, _alias in (("hg", "High-Grade ore (>6.0 g/t), %", "Highgrade ore (Au>6.0 g/t), %"),
                         ("mg", "Mid-Grade ore (2.0-6.0 g/t), %", "Mediumgrade ore (6.0 g/t >Au<2.0 g/t), %"),
                         ("lg", "Low-Grade ore (0.45-2.0 g/t), %", "Lowgrade ore (2.0 g/t >Au<0.45 g/t), %")):
    _row(7, "ff.pct." + _c, _lab, "feed", src={"mf": "feed." + _c + ".pct"}, ind=1, fmt="pct", exec="diff",
         bpct=True, budget=[_lab, _alias])

# ------------------------------------------------------------- 8. processing
_man(8, "pr.avail", "Mill availability, %", "%", agg="mean", fmt="d2", exec="diff")
_man(8, "pr.tput", "Mill Throughput, t", "t", note="Preliminary until the laboratory closes the day")
_man(8, "pr.head", "Head grade, Au g/t", "g/t", agg="wavg:pr.tput", fmt="d2", exec="diff")
_man(8, "pr.rec", "Recovery, %", "%", agg="mean", fmt="d2", exec="diff")
_man(8, "pr.tails_t", "Tails tonnage, t /with moisture/", "t",
     budget=["Tails tonnage, t /with moisture/", "Dry Cake Tailings, t"])
_man(8, "pr.tails_au", "Tails grade Au g/t", "g/t", agg="wavg:pr.tails_t", fmt="d2", exec="diff")
_man(8, "pr.tails_moist", "Tails moisture, %", "%", agg="mean", fmt="d2", exec="diff",
     budget=["Tails moisture, %", "Moisture, %"])
_stock(8, "pr.emerg", "Ore in the emegency stockpile, t", "t")

# ------------------------------------------------------- 9. site services
_man(9, "ss.power", "Power supply, kWh", "kWh")
_man(9, "ss.heat", "Heating supply, Gcal", "Gcal")
_man(9, "ss.water", "Water supply, m3", "m3")

# ------------------------------------------------------------------ 10. fuel
_FUEL = [("mining", "Mining, litre"), ("pp", "Process Plant, litre"), ("site", "Site service, litre"),
         ("constr", "Construction, litre"), ("water", "Water Supply, litre"), ("power", "Power Supply, litre"),
         ("contr", "Contractor, litre")]
_man(10, "fuel.in", "Inflow, litre", "litre", bold=True)
_sum(10, "fuel.use", "Fuel Usage, litre", ["fuel." + k for k, _ in _FUEL], bold=True)
for _k, _l in _FUEL:
    kw = {"bsec": 9, "budget": [_l, "Mining Equipment, litre"]} if _k == "mining" else {}
    _man(10, "fuel." + _k, _l, "litre", ind=1, **kw)
_stock(10, "fuel.bal", "Last balance, litre", "litre", fmt="d2", bold=True,
       days={"usage": "fuel.use", "text": "Diesel reserves for {n} days"})

# -------------------------------------------------------------- 11. chemical
for _g, _lab, _bud in (("in", "Inflow, kg", None), ("out", "Outflow, kg", True)):
    _sum(11, "ch." + _g, _lab, ["ch." + _g + ".lime", "ch." + _g + ".cn"], bold=True,
         budget=[_lab] if _bud else None)
    for _k, _l in (("lime", "Lime, kg"), ("cn", "Cyanide, kg")):
        _man(11, "ch." + _g + "." + _k, _l, "kg", ind=1, parent="ch." + _g, budget=[_l] if _bud else None)
_sum(11, "ch.bal", "Last balance, kg", ["ch.bal.lime", "ch.bal.cn"], bold=True, budget=None, exec=None, stock=True)
for _k, _l in (("lime", "Lime, kg"), ("cn", "Cyanide, kg")):
    _stock(11, "ch.bal." + _k, _l, "kg", ind=1, parent="ch.bal",
           days={"usage": "ch.out." + _k, "text": "{n} days of stock remaining"})

# ------------------------------------------------------------ 12. explosives
_EX = [("emul", "Emulsion, kg"), ("anfo", "Anfo, kg"), ("an", "Ammonium nitrate, kg")]
for _g, _lab, _bud in (("in", "Inflow, kg", None), ("out", "Outflow, kg", True)):
    _sum(12, "ex." + _g, _lab, ["ex." + _g + "." + k for k, _ in _EX], bold=True,
         budget=[_lab] if _bud else None)
    for _k, _l in _EX:
        _man(12, "ex." + _g + "." + _k, _l, "kg", ind=1, parent="ex." + _g, budget=[_l] if _bud else None)
_sum(12, "ex.bal", "Last balance, kg", ["ex.bal." + k for k, _ in _EX], bold=True, budget=None, exec=None, stock=True)
for _k, _l in _EX:
    _stock(12, "ex.bal." + _k, _l, "kg", ind=1, parent="ex.bal",
           days={"usage": "ex.out." + _k, "text": "{n} days of stock remaining"})

MR_CALCS = {"pf", "sr_sub_tt", "sr_sub_m3t", "sr_tot_tt", "sr_tot_m3t"}

# The page produces only the FMS-backed sections 4, 5 and 7 (user, 2026-10-27); the other sections and
# every manual line (incl. Metal loss / Ore Dilution) stay defined above but are not rendered, seeded or
# exported. Widen SHOW_SECS / drop the manual filter to bring them back.
SHOW_SECS = (4, 5, 7)
MASTER_SECS = [s for s in MASTER_SECS if s["sec"] in SHOW_SECS]
MASTER_ROWS[:] = [r for r in MASTER_ROWS if r["sec"] in SHOW_SECS and r["kind"] != "manual"]


def selfcheck():
    ids = [r["id"] for r in MASTER_ROWS]
    assert len(ids) == len(set(ids)), "duplicate ids"
    by = {r["id"]: r for r in MASTER_ROWS}
    for r in MASTER_ROWS:
        if r.get("parent"):
            assert r["parent"] in by, (r["id"], r["parent"])
        if r["kind"] == "calc":
            src = r["src"]
            if "sum" in src:
                for c in src["sum"]:
                    assert c in by, (r["id"], c)
            else:
                assert src["calc"] in MR_CALCS, r["id"]
        if r["kind"] == "manual":
            assert r.get("unit") and r.get("agg"), r["id"]
        assert r["sec"] in {s["sec"] for s in MASTER_SECS}
    return len(MASTER_ROWS)


def master_defs():
    """manual-series definitions for every manual row (group "master")."""
    return [{"key": "mr_" + r["id"], "name": r["label"], "unit": r["unit"], "group": "master",
             "kind": "stock" if r["agg"] == "last" else "flow", "cmp": "", "sec": r["sec"]}
            for r in MASTER_ROWS if r["kind"] == "manual"]


MR_TAB_HTML = '  <button data-sheet="master">Master Report</button>\n'

# ------------------------------------------------------------------ page CSS
MASTER_CSS = r"""
  /* ------------------------------------------------ Master Report (sheet 1) */
  #msheet{background:var(--color-bg-dashboard,#e8ecef);padding:10px 0 40px;color:#000}
  #msheet[hidden]{display:none !important}
  body.sheet-master .sheet,body.sheet-master #loadOverlay,body.sheet-master nav.toc{display:none !important}
  .mrbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;max-width:194mm;margin:0 auto 8px;
         font:13px/1.3 "Rubik",-apple-system,sans-serif;color:#333}
  .mrbar input[type=date]{font:inherit;font-weight:700;padding:4px 8px;border:1px solid #1B7F8F;border-radius:4px}
  .mrbar button{font:inherit;font-size:12.5px;padding:4px 10px;border:1px solid #b9c3ca;background:#fff;
         border-radius:4px;cursor:pointer}
  .mrbar button.pri{background:#1B7F8F;border-color:#1B7F8F;color:#fff;font-weight:700}
  .mrbar .mrhint{font-size:11.5px;color:#5c6670}
  .mrbar .spring{flex:1}
  .mrbar a{font-size:12px;color:#1B7F8F}
  .mrpage{width:194mm;margin:0 auto;background:#fff;padding:6mm 7mm;box-shadow:0 1px 6px rgba(0,0,0,.18);
          font-family:"Times New Roman",Times,serif;font-size:var(--mr-fs,10.5px);line-height:1.18;color:#000}
  .mrhead{display:flex;align-items:center;justify-content:space-between;gap:10px}
  .mrhead img{height:3.6em}
  .mrtitle{font-weight:700;font-size:2em;text-align:right}
  .mrmeta{margin:.5em 0 .4em;line-height:1.35}
  .mrmeta b{display:inline-block;min-width:6.5em}
  .mrmeta .mail{color:#0070C0}
  .mrmetarow{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
  .mrper{display:flex;gap:.9em;margin-top:.5em}
  .mrper label{display:flex;flex-direction:column;gap:2px;font-weight:700;font-size:.92em;color:#103644}
  .mrper select{font:inherit;font-weight:700;min-width:8.5em;padding:.25em .5em;border:2px solid #1B7F8F;border-radius:3px;
                background:#fff;color:#103644;cursor:pointer}
  body.print-master .mrper{margin-top:.2em}
  body.print-master .mrper select{appearance:none;-webkit-appearance:none;border-width:1px;padding:.05em .4em;min-width:7em}
  table.mr{border-collapse:collapse;width:100%;table-layout:fixed;font-variant-numeric:tabular-nums}
  table.mr td{padding:0 .35em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-bottom:1px solid #eee}
  table.mr td{text-align:left}
  table.mr td.n{text-align:right}
  table.mr td:nth-child(7){border-left:1px dotted #555}
  table.mr td:nth-child(10){border-right:1px dotted #555}
  table.mr td:first-child{border-left:1px dotted #555}
  table.mr tr.mr-time td{background:#D9D9D9;font-weight:700;text-align:center;border-top:1px dotted #555}
  table.mr tr.mr-time td:first-child{text-align:left}
  table.mr tr.mr-sec td{background:#1B7F8F;color:#fff;font-weight:700;text-transform:uppercase;text-align:center;
         font-size:.78em;border-bottom:none;white-space:normal;text-overflow:clip;line-height:1.05;
         padding-top:.15em;padding-bottom:.15em;vertical-align:middle}
  table.mr tr.mr-sec td.p{background:#103644}
  table.mr tr.mr-sec td:first-child{text-align:left;font-size:.95em}
  table.mr tr.mr-bold td{font-weight:700}
  table.mr tr.mr-sh1 td{background:#EDEDED}
  table.mr tr.mr-sh2 td{background:#F2F2F2}
  table.mr tr.mr-ind1 td:first-child{padding-left:1.4em}
  table.mr tr.mr-ind2 td:first-child{padding-left:2.8em}
  table.mr td.mrnote{text-align:center;font-weight:700;white-space:normal}
  table.mr td.callout{text-align:center;font-weight:700;white-space:normal;line-height:1.1}
  table.mr td[title]:first-child{text-decoration:underline dotted #9aa}
  .mrfoot{margin-top:.6em;font-style:italic;font-size:.86em;line-height:1.3}
  .mrfoot b{font-style:italic}
  .mrsign{margin-top:.8em;line-height:1.6}
  .mrsrc{margin-top:.5em;font-size:.8em;color:#666}
  #tblMaster td.mdname{text-align:left;white-space:nowrap;max-width:240px;overflow:hidden;text-overflow:ellipsis}
  #tblMaster tr.mrsec td{background:#e3f0f2;font-weight:700;text-align:left}
  #tblMaster tr.mrstock td.mdname{color:#1B7F8F}
  #tblMaster input{width:62px}
  .mrset{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;margin:6px 0}
  .mrset input{font:inherit;font-size:12px;padding:3px 6px;border:1px solid #c3cbd1;border-radius:4px;width:250px}
  @media print{
    body.print-master{background:#fff !important;padding:0 !important;margin:0 !important;min-height:0 !important}
    body.print-master > :not(#msheet){display:none !important}
    body.print-master #msheet{display:block !important;background:#fff;padding:0}
    body.print-master .mrbar{display:none !important}
    body.print-master .mrpage{width:auto;max-width:194mm;margin:0 auto;padding:7mm 0 5mm;box-shadow:none;font-size:var(--mr-fs-print,5px)}
    /* own top/bottom room + centred: the print dialog's "Minimum" margins remove the page's space (same as the operator KPI PDF) */
    #msheet table.mr tr.mr-sec td,#msheet table.mr tr.mr-time td,#msheet table.mr tr.mr-sh1 td,
    #msheet table.mr tr.mr-sh2 td{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  }
  .mrmeasure .mrpage{width:194mm !important;padding:0 !important;box-shadow:none !important;
                     font-size:var(--mr-fs-print,5px) !important}
  /* print geometry (also active while mrFit() measures): ~170 rows must fit one A4 page */
  body.print-master .mrpage{line-height:1.06}
  body.print-master table.mr td{border-bottom:0;padding-top:0;padding-bottom:0}
  body.print-master table.mr tr.mr-sec td{font-size:.74em;line-height:1.15}
  body.print-master table.mr tr.mr-sec td:first-child{font-size:.98em;line-height:1.05}
  body.print-master .mrhead img{height:2.6em}
  body.print-master .mrtitle{font-size:1.7em}
  body.print-master .mrmeta{margin:.2em 0;line-height:1.15}
  body.print-master .mrfoot{margin-top:.3em;line-height:1.12}
  body.print-master .mrsign{margin-top:.3em;line-height:1.3}
"""

# --------------------------------------------------------------- sheet HTML
MASTER_SECTION_HTML = r"""
<section id="msheet" class="mrsheet" hidden>
  <div class="mrbar noprint">
    <label>Report date <input type="date" id="mrDate"></label>
    <button type="button" id="mrPrev" title="previous day">&lsaquo;</button>
    <button type="button" id="mrNext" title="next day">&rsaquo;</button>
    <button type="button" id="mrLast">Last completed day</button>
    <span class="mrhint" id="mrHint"></span>
    <span class="spring"></span>
    <button type="button" id="mrPrint" class="pri">&#10515; Print Master Report</button>
  </div>
  <div class="mrpage" id="mrPage">
    <div class="mrhead">
      <img src="data:image/png;base64,__LOGO_B64__" alt="Erdene Mongol LLC">
      <div class="mrtitle">Bayankhundii Gold Mine Master Report</div>
    </div>
    <div class="mrmetarow">
      <div class="mrmeta" id="mrMeta"></div>
      <div class="mrper" title="report period: the month's last day, or the last completed day of the running month">
        <label>Month<select id="mrMon"></select></label>
        <label>Year<select id="mrYear"></select></label>
      </div>
    </div>
    <table class="mr" id="tblMR">
      <colgroup><col style="width:27%"><col style="width:7%"><col style="width:8%"><col style="width:8%">
      <col style="width:7.5%"><col style="width:8%"><col style="width:8.5%"><col style="width:8.5%">
      <col style="width:8.5%"><col style="width:9%"></colgroup>
      <tbody id="mrBody"></tbody>
    </table>
    <div class="mrfoot">
      <b>Additional information :</b><br>
      &sup2;ROM Inventories, Mining report numbers are updated at the end of the month based on surveyor measurements.<br>
      &sup3;Mill Feeding report numbers changes according to the approved numerical values from the processing plant section.<br>
      &ldquo;The MONTHLY PLAN and ANNUAL PLAN figures included in this report have been prepared in accordance with the company&rsquo;s approved budget.&rdquo;
    </div>
    <div class="mrsign" id="mrSign"></div>
    <div class="mrsrc" id="mrSrc"></div>
  </div>
</section>
"""

# ------------------------------------------------------- inputs panel block
MASTER_INPUTS_HTML = ""   # the manual-lines block was removed from Inputs (user, 2026-10-27)

# ------------------------------------------------------------------ page JS
MASTER_JS = r"""
/* ======================================================= MASTER REPORT (sheet 1)
   Erdene's one-page Master Report. Spec + rules: master_template.py. */
const MR_SPEC = __MR_SPEC__;
const MR_SECS = __MR_SECS__;
const MR_BY_ID = {};
MR_SPEC.forEach(r => { MR_BY_ID[r.id] = r; });
const MR_CHILDREN = {};          /* id -> ids of rows whose `parent` it is */
MR_SPEC.forEach(r => { if (r.parent) (MR_CHILDREN[r.parent] = MR_CHILDREN[r.parent] || []).push(r.id); });
const MR_IDX = {};               /* workbook section number -> rows (own section and budget section) */
MR_SPEC.forEach(r => { for (const s of new Set([r.sec, r.bsec].filter(Boolean))) (MR_IDX[s] = MR_IDX[s] || []).push(r); });
/* row labels compared without numbering ("3.2Total", "2.1.1 "), NBSPs, doubled spaces, spaces before commas or case */
const MR_NORM = s => String(s == null ? "" : s).replace(/ /g, " ").replace(/^\s*\d+(\.\d+)*\.?\s*(?=[A-Za-z])/, "")
  .replace(/\s+,/g, ",").replace(/\s+/g, " ").trim().toLowerCase();
const MR_SHIFT_H = 7;            /* the shift day starts at 07:00 */
const p2 = n => String(n).padStart(2, "0");
const isoDay = t => { const x = new Date(t); return x.getFullYear() + "-" + p2(x.getMonth() + 1) + "-" + p2(x.getDate()); };
const dayAdd = (d, n) => new Date(Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10) + n)).toISOString().slice(0, 10);
const dayDiff = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);

let MR_AUTO = true;               /* the date follows "last completed day" until the user picks one */
let MR_D = null, MR_P = null, MR_MEMO = {}, MR_DIRTY = true, MR_SVM = null, MR_ROMC = null;

function mrShiftDate(){ return isoDay(Date.now() - MR_SHIFT_H * 3600e3); }
/* the last COMPLETED operating day: the latest cube date before the shift day running now */
function mrDefaultDate(){
  const sd = mrShiftDate(), prev = DATES.filter(d => d < sd);
  return prev.length ? prev[prev.length - 1] : DATES[DATES.length - 1];
}
function mrPeriods(D){
  const y = D.slice(0, 4), M = D.slice(0, 7), m = +D.slice(5, 7), q = Math.floor((m - 1) / 3) + 1;
  const qStart = y + "-" + p2((q - 1) * 3 + 1) + "-01";
  const w = (key, from) => ({key, from, to: D, days: dayDiff(from, D) + 1});
  return {D, M, y, q, today: w("today", D), mtd: w("mtd", M + "-01"), msv: w("msv", M + "-01"),
          qtd: w("qtd", qStart), ytd: w("ytd", y + "-01-01"), d30: w("d30", dayAdd(D, -29)),
          monDays: monthDays(M).length, yearDays: dayDiff(y + "-01-01", y + "-12-31") + 1};
}
const mrDates = w => DATES.filter(d => d >= w.from && d <= w.to);
const mrSum = vals => { let x = 0, any = false; for (const v of vals) if (v !== null && v !== undefined && isFinite(v)){ x += v; any = true; } return any ? x : null; };

/* ---------------------------------------------------------- manual series */
function mrKey(r){ return "mr_" + r.id; }
function mdLastAt(key, to, from){        /* [date, value] of the latest value dated <= to (and >= from) */
  const m = inputs.manual.vals[key] || {};
  let best = null;
  for (const d in m) if (d <= to && (!from || d >= from) && m[d] !== null && m[d] !== "" && (!best || d > best)) best = d;
  return best ? [best, +m[best]] : null;
}
function mrManual(r, w){
  const key = mrKey(r), m = inputs.manual.vals[key] || {};
  if (r.agg === "last"){ const x = mdLastAt(key, w.to, r.cols === "mtd" ? w.from : null); return x ? x[1] : null; }
  if (r.agg === "sum") return mdSum(key, w.from, w.to);
  const days = Object.keys(m).filter(d => d >= w.from && d <= w.to && m[d] !== null && m[d] !== "");
  if (!days.length) return null;
  if (r.agg.startsWith("wavg:")){
    const wk = "mr_" + r.agg.slice(5), wm = inputs.manual.vals[wk] || {};
    let n = 0, s = 0;
    for (const d of days){ const wv = +wm[d]; if (wv > 0){ n += wv * +m[d]; s += wv; } }
    if (s > 0) return n / s;
  }
  return days.reduce((a, d) => a + +m[d], 0) / days.length;    /* mean */
}

/* ---------------------------------------------------- survey / dispatch mix */
function mrSurveyMonths(){                /* months with any surveyed movement (flow series with an R4M code) */
  if (MR_SVM) return MR_SVM;
  MR_SVM = new Set();
  for (const def of mdDefs("survey")){
    if (def.kind === "stock" || !def.cmp || /^(MILLFEED|ROMSTOCK|ROMCLS)/.test(def.cmp)) continue;
    for (const d in (inputs.manual.vals[def.key] || {})) MR_SVM.add(d.slice(0, 7));
  }
  return MR_SVM;
}
function mrSvSum(keys, from, to){ return mrSum(keys.map(k => mdSum(k, from, to))); }
function mrDisp(r, dd){ const s = rowById(r.src.mp || r.src.mf); return s ? s.v(dd, null) : null; }
/* QTD / YTD tonnes: a month with surveyor figures counts the survey, any other month the dispatch */
function mrMixed(r, w, svm){
  svm = svm || mrSurveyMonths();
  let x = 0, mo = w.from.slice(0, 7);
  while (mo <= w.to.slice(0, 7)){
    const md = monthDays(mo), a = md[0] > w.from ? md[0] : w.from, b = md[md.length - 1] < w.to ? md[md.length - 1] : w.to;
    x += svm.has(mo) ? (mrSvSum(r.sv, a, b) || 0) : (mrDisp(r, DATES.filter(d => d >= a && d <= b)) || 0);
    const [yy, mm] = mo.split("-").map(Number);
    mo = mm === 12 ? (yy + 1) + "-01" : yy + "-" + p2(mm + 1);
  }
  return x;
}
/* mill feeding (client deck, slide 12): MTD (SURVEY) tonnes = the plant's month-end reconciliation per
   class (sv_ff_*, dated the month end); QTD / YTD tonnes = that survey in reconciled months, dispatch in
   the others; grades always dispatch; contained metal, blend % and the total follow the column's tonnes */
let MR_FFM = null;
function mrFeedSurveyMonths(){
  if (MR_FFM) return MR_FFM;
  MR_FFM = new Set();
  for (const k of ["sv_ff_hg", "sv_ff_mg", "sv_ff_lg2", "sv_ff_lg1"])
    for (const d in (inputs.manual.vals[k] || {})) MR_FFM.add(d.slice(0, 7));
  return MR_FFM;
}
const MR_FF_CLS = ["hg", "mg", "lg"];
function mrFeed(r, wk, w){
  const id = r.id, V = id2 => mrVal(id2, wk);
  if (wk === "today" || wk === "mtd") return mrDisp(r, mrDates(w));
  if (r.sv) return wk === "msv" ? mrSvSum(r.sv, w.from, w.to) : mrMixed(r, w, mrFeedSurveyMonths());
  if (id === "ff.aukg" || id === "ff.agkg"){
    const t = V("ff.t"), g = V(id === "ff.aukg" ? "ff.au" : "ff.ag");
    return (t === null || g === null) ? null : t * g / 1000;
  }
  if (id.startsWith("ff.pct.")){ const t = V("ff.t"), c = V("ff." + id.slice(7)); return (c === null || !t) ? null : c / t; }
  if (id === "ff.blend") return mrSum(MR_FF_CLS.map(c => V("ff.pct." + c)));
  if (wk !== "msv") return mrDisp(r, mrDates(w));                       /* QTD / YTD grades: dispatch */
  if (id === "ff.au" || id === "ff.ag"){                                 /* survey t x dispatch class grade */
    let n = 0, s = 0;
    for (const c of MR_FF_CLS){ const t = V("ff." + c), g = V("ff." + c + id.slice(2)); if (t > 0 && g !== null){ n += t * g; s += t; } }
    return s ? n / s : null;
  }
  return V(r.parent) === null ? null : mrDisp(r, mrDates(w));          /* class grade: dispatch, where surveyed */
}

/* --------------------------------------------------------------- ROM pads */
function mrPileClass(p){
  const u = String(p).toUpperCase().replace(/^1237[_ ]/, "").trim();
  if (/^ST([\s_\-\d]|$)|TEST/.test(u)) return null;          /* test piles */
  if (/^SHG/.test(u)) return "HG";
  if (/^SMG|^SM[_\-]/.test(u)) return "MG";
  if (/^SLG-?1/.test(u)) return "LG1";
  if (/^SLG|^SL[_\-]|^S_\d/.test(u)) return "LG2";            /* incl. the long-term S_ piles */
  return ({HG: "HG", MG: "MG", LG: "LG2", LG2: "LG2", LG1: "LG1", "LG-1": "LG1"})[pileClass(p)] || null;
}
function mrRomByClass(D){
  if (MR_ROMC && MR_ROMC.D === D) return MR_ROMC;
  const by = {}, excl = [];
  for (const c of ["HG", "MG", "LG2", "LG1"]) by[c] = {t: 0, wt: 0, au: 0, ag: 0};
  for (const r of romState(D, D).rows){
    const c = mrPileClass(r.pile);
    if (!c){ if (Math.abs(r.bal) > 0.5) excl.push(r.pile + " " + Math.round(r.bal).toLocaleString("en-US") + " t"); continue; }
    const o = by[c], w = Math.max(r.bal, 0);
    o.t += r.bal; o.wt += w; o.au += w * (div(r.au, r.t) ?? 0); o.ag += w * (div(r.ag, r.t) ?? 0);
  }
  return (MR_ROMC = {D, by, excl});
}
function mrRomClassBal(cls, D){ const o = mrRomByClass(D).by[cls]; return o ? o.t : null; }
function mrRom(r, wk){
  const D = MR_P.D, cls = r.src.cls, val = r.src.val;
  if (wk === "mtd"){
    const by = mrRomByClass(D).by, cs = cls === "ALL" ? ["HG", "MG", "LG2", "LG1"] : [cls];
    const t = cs.reduce((a, c) => a + by[c].t, 0), wt = cs.reduce((a, c) => a + by[c].wt, 0);
    if (val === "t") return t;
    return wt ? cs.reduce((a, c) => a + by[c][val], 0) / wt : null;
  }
  if (wk === "msv" && val === "t" && r.sv){
    const xs = r.sv.stock.map(k => mdLastAt(k, D)).filter(Boolean);
    if (xs.length) return xs.reduce((a, x) => a + x[1], 0);
    if (r.sv.fallback){ const f = mdLastAt(r.sv.fallback, D); return f ? f[1] : null; }
  }
  return null;
}
function mrRomSurveyDate(D){
  let best = null;
  for (const k of ["sv_rom_hg", "sv_rom_mg", "sv_rom_lg2", "sv_rom_lg1", "sv_romstock"]){
    const x = mdLastAt(k, D); if (x && (!best || x[0] > best)) best = x[0];
  }
  return best;
}

/* ------------------------------------------------------------------- values */
const MR_CALC = {
  pf: V => { const e = V("db.expl"), b = V("db.blast"); return (e === null || !b) ? null : e / b; },
  sr_sub_tt: V => { const w = mrSum([V("mn.bw"), V("mn.ts")]), o = mrSum([V("mn.rom"), V("mn.nonrom")]); return (w === null || !o) ? null : w / o; },
  sr_sub_m3t: V => { const w = mrSum([V("mn.bw") === null ? null : V("mn.bw") / dens("W"), V("mn.ts") === null ? null : V("mn.ts") / dens("TS")]),
                         o = mrSum([V("mn.rom"), V("mn.nonrom")]); return (w === null || !o) ? null : w / o; },
  sr_tot_tt: V => { const w = mrSum([V("mn.bw"), V("mn.ts"), V("mn.nonrom")]), o = V("mn.rom"); return (w === null || !o) ? null : w / o; },
  sr_tot_m3t: V => { const bw = V("mn.bw"), ts = V("mn.ts"), nr = V("mn.nonrom"), o = V("mn.rom");
    const w = mrSum([bw === null ? null : bw / dens("W"), ts === null ? null : ts / dens("TS"), nr === null ? null : nr / dens("MW")]);
    return (w === null || !o) ? null : w / o; },
};
function mrVal(id, wk){
  const k = id + "|" + wk;
  if (k in MR_MEMO) return MR_MEMO[k];
  const r = MR_BY_ID[id], w = MR_P[wk];
  let v = null;
  if (r.kind === "cube"){
    if (wk === "msv") v = r.sv ? mrSvSum(r.sv, w.from, w.to) : null;
    else if ((wk === "qtd" || wk === "ytd") && r.sv) v = mrMixed(r, w);
    else v = mrDisp(r, mrDates(w));
  } else if (r.kind === "feed") v = mrFeed(r, wk, w);
  else if (r.kind === "rom") v = mrRom(r, wk);
  else if (r.kind === "manual") v = wk === "msv" ? null : mrManual(r, w);
  else if (r.kind === "calc"){
    const V = id2 => mrVal(id2, wk);
    v = r.src.sum ? mrSum(r.src.sum.map(V)) : MR_CALC[r.src.calc](V);
  }
  if (v !== null && !isFinite(v)) v = null;
  return (MR_MEMO[k] = v);
}

/* ------------------------------------------------------------------ budget */
function mrPlan(r, key){                  /* key "YYYY-MM" = month, "YYYY" = year total */
  const b = (inputs.budget || {})[r.id];
  if (b && b[key] !== undefined && b[key] !== null && isFinite(b[key])) return +b[key];
  if (b && key.length === 4 && r.exec === "pct"){            /* no total typed: add up the months */
    const ms = Object.keys(b).filter(k => k.length === 7 && k.slice(0, 4) === key);
    if (ms.length) return ms.reduce((a, k) => a + (+b[k] || 0), 0);
  }
  const pl = r.plan || (r.kind === "calc" && r.src.sum ? {sum: r.src.sum} : null);
  if (!pl) return null;
  if (pl.sum) return mrSum(pl.sum.map(id => mrPlan(MR_BY_ID[id], key)));
  if (pl.kg){ const t = mrPlan(MR_BY_ID[pl.kg[0]], key), g = mrPlan(MR_BY_ID[pl.kg[1]], key); return (t === null || g === null) ? null : t * g / 1000; }
  if (pl.wavg){                             /* the balance's grade = tonnage-weighted class grades */
    const met = r.id.slice(-2);
    let n = 0, s = 0;
    for (const c of ["hg", "mg", "lg2"]){
      const t = mrPlan(MR_BY_ID["rom." + c], key), g = mrPlan(MR_BY_ID["rom." + c + "." + met], key);
      if (t > 0 && g !== null){ n += t * g; s += t; }
    }
    return s ? n / s : null;
  }
  return null;
}
const mrAnnualKey = r => r.sec === 5 ? MR_P.y + "-12" : MR_P.y;    /* ROM: the year-end (December) balance */
function mrExec(r, a, p){
  if (a === null || p === null || !r.exec) return null;
  if (r.exec === "pct") return p ? a / p : null;
  return a - p;
}
function mrActualFor(r, wk){
  if (r.execActual) return mrSum(r.execActual.map(id => mrVal(id, wk)));
  return mrVal(r.id, wk);
}

/* --------------------------------------------------------------- formatting */
function mrFmt(v, fmt){
  if (v === null || v === undefined || !isFinite(v)) return "";
  const neg = v < 0, a = Math.abs(v);
  let s;
  if (fmt === "pct") s = Math.round(a * 100).toLocaleString("en-US") + "%";
  else if (fmt === "d2") s = a.toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  else s = a.toLocaleString("en-US", {maximumFractionDigits: 0});
  if (s === "0" || s === "0.00" || s === "0%") return "-";
  return neg ? "(" + s + ")" : s;
}
const mrE = s => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
const MR_COLS = {
  std:    q => ["TODAY", "MTD", "", "QTD " + q, "YTD"],
  mining: q => ["TODAY", "MTD (Dispatch)", "MTD (SURVEY)", "QTD " + q, "YTD"],
  rom:    q => ["", "MTD (Dispatch)", "MTD (SURVEY)", "", ""],
};
const MR_PLANCOLS = ["MONTHLY PLAN", "MONTHLY EXECUTION", "ANNUAL PLAN", "ANNUAL EXECUTION"];
function mrDaysNote(r){
  const bal = mrVal(r.id, "today"), use = mrVal(r.days.usage, "d30");
  if (bal === null) return "";
  if (!use || use <= 0) return "no usage in the last 30 days";
  return r.days.text.replace("{n}", Math.round(bal / (use / 30)).toLocaleString("en-US"));
}

/* ------------------------------------------------------------------- render */
function renderMaster(){
  const body = document.getElementById("mrBody");
  if (!body || !DATES.length) return;
  if (!MR_D || MR_AUTO) MR_D = mrDefaultDate();
  MR_P = mrPeriods(MR_D); MR_MEMO = {}; MR_SVM = null; MR_FFM = null; MR_ROMC = null; MR_DIRTY = false;
  const P = MR_P, M = P.M, set = Object.assign({}, inputs.mrset || {});
  const dEl = document.getElementById("mrDate"); if (dEl && dEl.value !== MR_D) dEl.value = MR_D;
  mrRenderPeriod();
  const hint = document.getElementById("mrHint");
  if (hint) hint.textContent = MR_D === mrDefaultDate() ? "last completed shift day (07:00 → 07:00)"
                               : (DATES.includes(MR_D) ? "" : "no R4M cycles on this date");
  document.getElementById("mrMeta").innerHTML =
    "<div><b>Department:</b> " + mrE(set.dept) + "</div><div><b>Email:</b> <span class=\"mail\">" + mrE(set.email) + "</span></div>" +
    "<div><b>Date:</b> " + new Date(Date.parse(MR_D + "T00:00:00")).toLocaleDateString("en-US") + "</div>";
  const h = [];
  const tr = (cls, cells) => h.push('<tr class="' + cls + '">' + cells + "</tr>");
  const td = (v, cls, extra) => '<td class="' + (cls === undefined ? "n" : cls) + '"' + (extra || "") + ">" + v + "</td>";
  tr("mr-time", td("Time Passed (days)", "") + td(1) + td(P.mtd.days) + td("") + td(P.qtd.days) + td(P.ytd.days) +
     td(P.monDays + " days") + td(Math.round(P.mtd.days / P.monDays * 100) + "%", "n", ' title="share of the month elapsed"') +
     td(P.yearDays + " days") + td(Math.round(P.ytd.days / P.yearDays * 100) + "%", "n", ' title="share of the year elapsed"'));
  const svDate = mrRomSurveyDate(MR_D);
  for (const S of MR_SECS){
    const caps = MR_COLS[S.cols](P.q);
    let secTip = "";
    if (S.sec === 4) secTip = "QTD / YTD tonnes: a month with surveyor figures counts the survey, any other month the R4M dispatch (ex-rehandle). Grades are always the dispatch grades. MTD (SURVEY) = surveyor figures dated in the month.";
    if (S.sec === 5) secTip = "MTD (Dispatch) = R4M balance on the report date (received - reclaimed since the last manual adjustment), piles grouped by name: SHG → HG, SMG → MG, SLG2 / SL_ / S_ → LG2, SLG1 → LG1, test piles left out.";
    if (S.sec === 7) secTip = "TODAY / MTD = R4M crusher deliveries. MTD (SURVEY) = the plant's month-end reconciled feed per class (7.1 MILLFEED_PP), dated the month end, with the R4M dispatch grades. QTD / YTD tonnes: a reconciled month counts the reconciliation, any other month the dispatch; grades are always the dispatch grades.";
    tr("mr-sec", td(S.sec + ". " + mrE(S.title), "", secTip ? ' title="' + mrE(secTip) + '"' : "") +
       caps.map(c => td(c, "a")).join("") + MR_PLANCOLS.map(c => td(c, "p")).join(""));
    let shade = 0;
    for (const r of MR_SPEC.filter(x => x.sec === S.sec)){
      const cls = ["mr-row", r.bold ? "mr-bold" : "", r.ind ? "mr-ind" + r.ind : "",
                   r.bold && !r.ind ? "mr-sh" + ((shade++ % 2) + 1) : ""].join(" ");
      const lab = td(mrE(r.label), "", (r.note ? ' title="' + mrE(r.note) + '"' : "") + ' data-id="' + r.id + '"');
      if (r.cols === "mtd"){                                   /* month-end figures (metal loss, dilution) */
        const v = mrVal(r.id, "mtd");
        tr(cls, lab + (v === null ? td(mrE(r.empty || ""), "mrnote", ' colspan="5"') : td("") + td(mrFmt(v, r.fmt)) + td("") + td("") + td("")) +
           td("") + td("") + td("") + td(""));
        continue;
      }
      if (r.stock){                                             /* balances: the value on D + days of stock */
        const v = mrVal(r.id, "today");
        tr(cls, lab + td(mrFmt(v, r.fmt)) + td(r.days ? mrE(mrDaysNote(r)) : "", "mrnote", ' colspan="8"'));
        continue;
      }
      const vals = ["today", "mtd", "msv", "qtd", "ytd"].map((wk, i) => {
        if (S.cols === "std" && wk === "msv") return null;
        if (S.cols === "rom" && wk !== "mtd" && wk !== "msv") return null;
        return mrVal(r.id, wk);
      });
      const pm = mrPlan(r, M), pa = mrPlan(r, mrAnnualKey(r));
      const aM = mrActualFor(r, "mtd");
      let aY = mrActualFor(r, "ytd");
      if (S.sec === 5){ const sv = mrActualFor(r, "msv"); aY = sv !== null ? sv : aM; }
      const xfmt = r.exec === "pct" ? "pct" : r.fmt;
      let cells = vals.map(v => td(mrFmt(v, r.fmt))).join("");
      if (S.sec === 5 && r.id === "rom.all")                    /* the survey callout sits in the empty QTD / YTD cells */
        cells = td(mrFmt(vals[0], r.fmt)) + td(mrFmt(vals[1], r.fmt)) + td(mrFmt(vals[2], r.fmt)) +
                td("SURVEY MEASURE<br>LAST UPDATED " + (svDate || "&ndash;"), "callout", ' colspan="2"');
      tr(cls, lab + cells + td(mrFmt(pm, r.fmt)) + td(mrFmt(mrExec(r, aM, pm), xfmt)) +
         td(mrFmt(pa, r.fmt)) + td(mrFmt(mrExec(r, aY, pa), xfmt)));
    }
  }
  body.innerHTML = h.join("");
  const ex = mrRomByClass(MR_D).excl;
  const romLab = body.querySelector('td[data-id="rom.all"]');
  if (romLab && ex.length) romLab.title = "Not counted (test / unclassified piles): " + ex.join(", ");
  document.getElementById("mrSign").innerHTML =
    "Reviewed by: ............................... /" + mrE(set.reviewed) + "/<br>" +
    "Prepared by: ............................... /" + mrE(set.prepared) + "/";
  const live = document.getElementById("liveStatus");
  document.getElementById("mrSrc").textContent = "Sections 4, 5, 7: R4M dispatch cube" +
    (live && live.textContent ? " (" + live.textContent.trim() + ")" : "") + " through " + DATES[DATES.length - 1] +
    " · plan: published budget · rendered " + isoDay(Date.now());
}
function mrRenderIfShown(){
  if (document.body.classList.contains("sheet-master")) renderMaster(); else MR_DIRTY = true;
}
function mrShow(on){
  const s = document.getElementById("msheet"); if (!s) return;
  s.hidden = !on;
  document.body.classList.toggle("sheet-master", !!on);
  if (on && (MR_DIRTY || !MR_P)) renderMaster();
}
function mrSetDate(d){ if (d){ MR_D = d; MR_AUTO = false; renderMaster(); } }
/* header Month / Year drop-downs (client deck, slide 2): a closed month shows its last day, the running
   month its last completed day. Options carry `selected` so the printed copy shows the period too. */
const MR_MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
function mrRenderPeriod(){
  const mEl = document.getElementById("mrMon"), yEl = document.getElementById("mrYear");
  if (!mEl || !yEl) return;
  const top = mrShiftDate(), y0 = +DATES[0].slice(0, 4), y1 = +top.slice(0, 4), y = +MR_D.slice(0, 4), m = +MR_D.slice(5, 7);
  let yo = "";
  for (let k = Math.min(y0, y); k <= Math.max(y1, y); k++) yo += '<option value="' + k + '"' + (k === y ? " selected" : "") + ">" + k + "</option>";
  yEl.innerHTML = yo;
  mEl.innerHTML = MR_MON.map((n, i) => {
    const mo = y + "-" + p2(i + 1);
    return '<option value="' + (i + 1) + '"' + (i + 1 === m ? " selected" : "") + (mo > mrShiftDate().slice(0, 7) ? " disabled" : "") + ">" + n + "</option>";
  }).join("");
}
function mrPickPeriod(y, m){
  const run = mrShiftDate();
  if (y + "-" + p2(m) > run.slice(0, 7)){ y = +run.slice(0, 4); m = +run.slice(5, 7); }   /* no future months */
  const end = monthDays(y + "-" + p2(m)).slice(-1)[0];
  if (end < run) mrSetDate(end);                 /* a closed month: its last day, even past the cube's last date */
  else { MR_AUTO = true; renderMaster(); }       /* the running month: the last completed day */
}

/* ------------------------------------------------------------ print (A4) */
const MR_PAGE_H = (283 - 12) * 96 / 25.4 * 0.95;   /* A4 height minus 7 mm margins and the 7 + 5 mm print padding, in CSS px, 5 % slack */
function mrFit(){
  const page = document.getElementById("mrPage");
  document.body.classList.add("mrmeasure");
  let fs = 10.4;
  for (; fs > 4.2; fs -= 0.2){
    document.body.style.setProperty("--mr-fs-print", fs.toFixed(1) + "px");
    if (page.scrollHeight <= MR_PAGE_H) break;
  }
  document.body.classList.remove("mrmeasure");
  return fs;
}
let MR_TITLE = null;
function mrPreparePrint(){
  if (!document.getElementById("mrPage")) return;
  if (MR_DIRTY || !MR_P) renderMaster();
  document.body.classList.add("print-master");
  mrFit();
  if (!document.getElementById("mrPageStyle")){
    const st = document.createElement("style");
    st.id = "mrPageStyle";
    st.textContent = "@page{size:A4 portrait;margin:7mm 8mm}";
    document.head.appendChild(st);
  }
  if (MR_TITLE === null){ MR_TITLE = document.title; document.title = "Master Report " + MR_D; }
}
function mrEndPrint(){
  document.body.classList.remove("print-master");
  const st = document.getElementById("mrPageStyle"); if (st) st.remove();
  if (MR_TITLE !== null){ document.title = MR_TITLE; MR_TITLE = null; }
}
/* The page lives inside R4M's iframe, where Chrome prints the whole R4M page (Ctrl+P) or does not keep
   the frame's A4 @page rule -> the Master Report is printed from its own top-level document instead. */
const MR_CSS = __MR_CSS__;
function mrPrintHtml(){
  mrPreparePrint();
  const fs = getComputedStyle(document.body).getPropertyValue("--mr-fs-print").trim() || "6px";
  const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
  const html = '<!doctype html><html><head><meta charset="utf-8"><title>' + esc(document.title) + '</title>'
    + '<style>' + MR_CSS + '\n  @page{size:A4 portrait;margin:7mm 8mm}\n  html,body{margin:0;background:#fff}'
    + '\n  @media screen{#msheet{padding:10px 0 40px}}</style></head>'
    + '<body class="print-master" style="--mr-fs-print:' + fs + '"><section id="msheet">'
    + document.getElementById("mrPage").outerHTML + '</section></body></html>';
  mrEndPrint();
  return html;
}
function mrPrint(){
  const html = mrPrintHtml();
  let w = null;
  try { w = window.open("", "_blank"); } catch (e) { w = null; }
  if (!w){ mrPreparePrint(); window.print(); setTimeout(mrEndPrint, 2000); return; }   /* popup blocked */
  w.document.open(); w.document.write(html); w.document.close();
  w.addEventListener("afterprint", () => w.close());
  const img = w.document.querySelector("img");
  const go = () => { w.focus(); w.print(); };
  if (img && img.decode) img.decode().then(go, go); else go();
}
function mrCtrlP(e){
  if ((e.ctrlKey || e.metaKey) && !e.altKey && (e.key === "p" || e.key === "P")
      && document.body.classList.contains("sheet-master")){ e.preventDefault(); mrPrint(); }
}
window.addEventListener("keydown", mrCtrlP);
/* Ctrl+P pressed in R4M's own page (same origin) while the Master Report tab is open */
try {
  if (window.parent !== window && window.parent.document){
    const par = window.parent;
    par.addEventListener("keydown", mrCtrlP);
    window.addEventListener("pagehide", () => { try { par.removeEventListener("keydown", mrCtrlP); } catch (e) {} });
  }
} catch (e) {}
window.addEventListener("beforeprint", () => { if (document.body.classList.contains("sheet-master")) mrPreparePrint(); });
window.addEventListener("afterprint", mrEndPrint);

/* ------------------------------------------------------ inputs panel grid */
const mrManualRows = () => MR_SPEC.filter(r => r.kind === "manual");
function renderMasterGrid(mon){
  const t = document.getElementById("tblMaster");
  if (!t) return;
  const lbl = document.getElementById("mrMonthLbl"); if (lbl) lbl.textContent = mon;
  const days = monthDays(mon);
  const h = ["<tr><th>Line</th><th>Unit</th>" + days.map(d => "<th>" + d.slice(8) + "</th>").join("") + "</tr>"];
  t.innerHTML = "";
  const head = document.createElement("tbody");
  head.innerHTML = h[0];
  t.appendChild(head);
  const tb = document.createElement("tbody");
  let sec = null;
  for (const r of mrManualRows()){
    if (r.sec !== sec){
      sec = r.sec;
      const s = MR_SECS.find(x => x.sec === sec);
      const sr = document.createElement("tr"); sr.className = "mrsec";
      sr.innerHTML = '<td colspan="' + (days.length + 2) + '">' + sec + ". " + mrE(s.title) + "</td>";
      tb.appendChild(sr);
    }
    const tr = document.createElement("tr");
    if (r.agg === "last") tr.className = "mrstock";
    const par = r.parent ? MR_BY_ID[r.parent].label.replace(/^[\d.]+\s*/, "") + " → " : "";
    tr.innerHTML = '<td class="mdname" title="' + mrE(par + r.label) + (r.agg === "last" ? " (balance on the day)" : "") + '">' +
      mrE(par + r.label) + '</td><td class="mdname" style="color:#6b747b">' + mrE(r.unit) + "</td>";
    const key = mrKey(r);
    for (const d of days){
      const c = document.createElement("td"), inp = document.createElement("input");
      inp.type = "number"; inp.step = "any";
      const v = mdGet(key, d); inp.value = v === null ? "" : v;
      inp.addEventListener("change", () => {
        mdSet(key, d, inp.value === "" ? null : parseFloat(inp.value));
        saveInputs();
        if (!window.__pasting) refresh(false);
      });
      c.appendChild(inp); tr.appendChild(c);
    }
    tb.appendChild(tr);
  }
  t.appendChild(tb);
  const set = inputs.mrset || (inputs.mrset = {});
  for (const [id, k] of [["mrsDept", "dept"], ["mrsEmail", "email"], ["mrsReviewed", "reviewed"], ["mrsPrepared", "prepared"]]){
    const el = document.getElementById(id); if (!el) continue;
    el.value = set[k] || "";
    if (!el.__mr){ el.__mr = 1; el.addEventListener("change", () => { inputs.mrset[k] = el.value; saveInputs(); mrRenderIfShown(); }); }
  }
}

/* -------------------------------------------- workbook: Master Report + Budget */
/* walk sheet rows section by section and match them to spec rows. keysOf(row) = the
   normalised labels a spec row answers to; a child row ("RC, m", "Lime, kg", "Au grade,
   g/t") only matches right after its parent or a sibling. fn(row, spec|null). */
function mrWalk(rows, labelCol, keysOf, fn){
  let sec = null, last = null;
  const used = new Set();
  for (const row of rows){
    const lab = row && row[labelCol];
    if (lab == null || String(lab).trim() === "") continue;
    const s = SOP_SEC(lab);
    if (s){ sec = +s; last = null; continue; }
    const k = MR_NORM(lab);
    const cands = (MR_IDX[sec] || []).filter(r => !used.has(r.id) && keysOf(r).includes(k));
    let pick = cands.find(r => r.parent && last && (r.parent === last.id || r.parent === last.parent)) || null;
    if (!pick) pick = cands.find(r => !r.parent) || null;
    if (pick){ used.add(pick.id); last = pick; } else last = null;
    fn(row, pick);
  }
}
function mrBudgetKeys(r){ return r.budget && r.budget.length ? r.budget.map(MR_NORM).concat([MR_NORM(r.label)]) : []; }

function mrSheets(){
  const M = inMon(), Y = M.slice(0, 4), days = monthDays(M);
  /* Master Report: the manual lines, one column per day (totals rows give the context) */
  const mr = [["Line", "Unit", "Kind"].concat(days)];
  for (const S of MR_SECS){
    const rows = MR_SPEC.filter(r => r.sec === S.sec && (r.kind === "manual" ||
      (r.kind === "calc" && r.src.sum && r.src.sum.some(id => MR_BY_ID[id].kind === "manual"))));
    if (!rows.length) continue;
    mr.push([S.sec + ". " + S.title]);
    for (const r of rows){
      if (r.kind !== "manual"){ mr.push([r.label, "", "total (calculated)"]); continue; }
      mr.push([r.label, r.unit, r.agg === "last" ? "balance" : r.agg === "sum" ? "flow" : "average"]
        .concat(days.map(d => mdGet(mrKey(r), d))));
    }
  }
  /* Budget: the client's Work_Order layout, one column per month + the year total */
  const months = Array.from({length: 12}, (_, i) => Y + "/" + (i + 1));
  const bg = [["Line", "End of " + (+Y - 1)].concat(months, ["Total"])];
  for (const S of MR_SECS){
    const rows = MR_SPEC.filter(r => r.sec === S.sec && r.budget && r.budget.length);
    if (!rows.length) continue;
    bg.push([S.sec + ". " + S.title]);
    for (const r of rows){
      const b = (inputs.budget || {})[r.id] || {}, f = r.bpct ? 100 : 1;
      const v = k => (b[k] === undefined || b[k] === null) ? null : Math.round(b[k] * f * 1e6) / 1e6;
      bg.push([r.label, null].concat(months.map((_, i) => v(Y + "-" + p2(i + 1))), [v(Y)]));
    }
  }
  return (mr.length > 1 ? [{name: "Master Report", rows: mr}] : []).concat([{name: "Budget", rows: bg}]);
}
function mrParseMaster(wb, patch, notes, unknown){
  const sh = wb["Master Report"];
  if (!sh || sh.length < 2 || !mrManualRows().length) return;
  const head = sh[0].map(XLSXIO.asDate);
  let cells = 0, lines = 0;
  mrWalk(sh.slice(1), 0, r => [MR_NORM(r.label)], (row, r) => {
    if (!r){ unknown.push("Master Report row “" + String(row[0]).trim() + "”"); return; }
    if (r.kind !== "manual") return;
    const tgt = patch.manual.vals[mrKey(r)] = patch.manual.vals[mrKey(r)] || {};
    let any = false;
    for (let c = 3; c < row.length; c++){
      if (!head[c]) continue;
      const v = row[c];
      if (typeof v === "number" && isFinite(v)){ tgt[head[c]] = v; cells++; any = true; }
    }
    if (any) lines++;
  });
  notes.push(["Master Report", lines + " line(s), " + cells + " daily value(s)"]);
}
/* any sheet with a header row of >= 6 "YYYY/M" cells is a budget: the planners' Work_Order or our Budget */
function mrBudgetSheets(wb){
  const out = [];
  for (const nm of (wb.__order || [])){
    const rows = wb[nm] || [];
    const hi = rows.findIndex(r => r && r.filter(v => /^\s*\d{4}\/\d{1,2}\s*$/.test(String(v == null ? "" : v))).length >= 6);
    if (hi >= 0) out.push({name: nm.trim(), rows, hi});
  }
  return out;
}
function mrParseBudget(sh, patch, notes, unknown){
  const head = sh.rows[sh.hi], cols = [];
  let labelCol = head.findIndex(v => v !== null && v !== undefined && String(v).trim() !== "");
  let lastYear = null;
  head.forEach((v, c) => {
    const s = String(v == null ? "" : v).trim(), m = /^(\d{4})\/(\d{1,2})$/.exec(s);
    if (m){ lastYear = m[1]; cols.push([c, m[1] + "-" + p2(+m[2])]); }
    else if (/^total/i.test(s) && lastYear) cols.push([c, lastYear]);
  });
  if (labelCol < 0 || labelCol >= cols[0][0]) labelCol = 0;
  const years = new Set(cols.map(([, k]) => k.slice(0, 4)));
  let lines = 0, mvals = 0, tvals = 0;
  mrWalk(sh.rows.slice(sh.hi + 1), labelCol, mrBudgetKeys, (row, r) => {
    const has = cols.some(([c]) => typeof row[c] === "number");
    if (!r){ if (has) unknown.push(sh.name + ": " + String(row[labelCol]).trim()); return; }
    if (!has) return;
    const tgt = patch.budget[r.id] = patch.budget[r.id] || {}, f = r.bpct ? 0.01 : 1;
    for (const [c, k] of cols){
      const v = row[c];
      if (typeof v !== "number" || !isFinite(v)) continue;
      tgt[k] = Math.round(v * f * 1e8) / 1e8;
      if (k.length === 4) tvals++; else mvals++;
    }
    patch.budgetYears[r.id] = [...years];
    lines++;
  });
  notes.push([sh.name + " (budget) · " + [...years].join(", "),
              lines + " line(s), " + mvals + " monthly value(s), " + tvals + " total(s) - replaces those years for those lines"]);
}
function mrApplyBudget(patch){
  if (!patch.budget) return;
  inputs.budget = inputs.budget || {};
  for (const id in patch.budget){
    const o = inputs.budget[id] = inputs.budget[id] || {};
    for (const y of (patch.budgetYears[id] || [])) for (const k in o) if (k.slice(0, 4) === y) delete o[k];
    Object.assign(o, patch.budget[id]);
  }
}

/* ------------------------------------------------------------------- wiring */
function wireMaster(){
  const on = (id, ev, fn) => { const el = document.getElementById(id); if (el) el.addEventListener(ev, fn); };
  const dEl = document.getElementById("mrDate");
  if (!dEl) return;
  if (!MR_D) MR_D = mrDefaultDate();
  dEl.min = DATES[0].slice(0, 4) + "-01-01";
  dEl.max = mrShiftDate();
  dEl.value = MR_D;
  on("mrDate", "change", () => mrSetDate(dEl.value));
  on("mrPrev", "click", () => mrSetDate(dayAdd(MR_D, -1)));
  on("mrNext", "click", () => mrSetDate(dayAdd(MR_D, 1)));
  on("mrLast", "click", () => { MR_AUTO = true; renderMaster(); });
  on("mrPrint", "click", mrPrint);
  const mEl = document.getElementById("mrMon"), yEl = document.getElementById("mrYear");
  on("mrMon", "change", () => mrPickPeriod(+yEl.value, +mEl.value));
  on("mrYear", "change", () => mrPickPeriod(+yEl.value, +mEl.value));
}
"""


def master_js():
    return (MASTER_JS.replace("__MR_SPEC__", json.dumps(MASTER_ROWS, ensure_ascii=False))
            .replace("__MR_SECS__", json.dumps(MASTER_SECS, ensure_ascii=False))
            .replace("__MR_CSS__", json.dumps(MASTER_CSS)))


if __name__ == "__main__":
    print(selfcheck(), "rows,", len(master_defs()), "manual")
