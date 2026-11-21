"""Build the Operator KPI page as one self-contained HTML file.

Data flow:
  fetch_operator_kpi.py -> data/{checklists,checklist_items,loads,status,logins}.parquet + dim_*.parquet + meta.json
  this script           -> operator_kpi.html  (everything embedded as compact column tables; period filtering,
                           ranking, charts and the three CSV downloads run client-side; works offline)

What is embedded (see operator_kpi_template.py for how the page uses it):
  ops      one row per shift date x shift x equipment x operator: loads + phase sums (trucks), loads loaded +
           loading/hang sums (loaders), status hours bucketed through lookups/status_detail.json, checklist
           counts, over-speed counts / worst / steep (report rule applied, see osev)
  osev     one row per over-speed event of the Over-speed page (../overspeed/data/episodes_s<G>.parquet, G from its
           meta.json; same report rule as that page: >= 8 s and average >= limit + 2 km/h), attributed to the operator
           logged in on the truck (telemetry login id -> dim_workers; name, then login sessions as fallbacks). Never
           any peak-sample speed (user rule for every page).
  reasons  non-productive hours per shift date x shift x operator x status detail (delay reasons chart)
  forms    one row per checklist form;  items = per-form arrays of answered item ids and NOT-OK item ids
  dimItems the checklist structure in template/section order (wide CSV columns);  dimEq / dimWk lookups

Run:  python build_operator_kpi.py [--fetch [fetch args...]] [--out PATH]
      e.g.  python build_operator_kpi.py --fetch --from 2026-07-01
"""
import argparse
import base64
import glob
import json
import math
import os
import subprocess
import sys

import pandas as pd

from operator_kpi_template import CSS, HTML, JS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
DAILY = os.path.join(ROOT, "daily_report")
OUT = os.path.join(HERE, "operator_kpi.html")
LOOKUP = os.path.join(HERE, "lookups", "status_detail.json")
OVERSPEED = os.path.join(ROOT, "overspeed")
sys.path.insert(0, OVERSPEED)
try:                                   # one source of truth for the over-speed report rule
    from build_overspeed import apply_rule, MIN_DURATION_S, TOLERANCE_KMH
except Exception:  # noqa: BLE001     overspeed/ absent: the same rule, local copy
    MIN_DURATION_S, TOLERANCE_KMH = 8, 2.0

    def apply_rule(df, rule):
        df = df.copy()
        df["over_kmh"] = (df["avg_speed_kmh"] - df["limit_kmh"]).round(1)
        return df[(df["duration_s"] >= rule[0]) & (df["over_kmh"] >= rule[1])].reset_index(drop=True)
OS_RULE = (MIN_DURATION_S, TOLERANCE_KMH)

KEYS = ["shift_date", "shift", "id_equipo", "id_worker"]
HAUL_SUMS = ["loads", "tonnes", "n_queue", "s_queue", "n_spot", "s_spot", "n_load", "s_load", "n_haul", "s_haul",
             "n_atdump", "s_atdump", "n_dump", "s_dump", "n_empty", "s_empty"]
LOAD_SUMS = ["loads_ld", "tonnes_ld", "n_ldg", "s_ldg", "n_hang", "s_hang", "trucks_served"]
HOUR_COLS = ["h_prod", "h_ready_other", "h_delay", "h_standby", "h_maint", "h_oop", "h_unknown", "min_shiftchange"]
CHK_COLS = ["forms", "forms_rej", "forms_pend", "items", "items_nok"]
OS_COLS = ["os_n", "os_s", "os_max", "os_steep"]


def table(df, round1=()):
    """DataFrame -> compact column table {"cols", "data", "dict"} (text columns dictionary-encoded)."""
    df = df.reset_index(drop=True)
    for c in round1:
        if c in df:
            df[c] = df[c].round(1)
    out = {"cols": list(df.columns), "data": {}, "dict": {}}
    for c in df.columns:
        s = df[c]
        if s.dtype == object or str(s.dtype) in ("string", "str"):
            codes, uniques = pd.factorize(s, use_na_sentinel=True)
            out["dict"][c] = [None if (isinstance(u, float) and math.isnan(u)) else u for u in uniques.tolist()]
            out["data"][c] = [None if k < 0 else int(k) for k in codes.tolist()]
        elif s.dtype == bool:
            out["data"][c] = [bool(v) for v in s.tolist()]
        else:
            vals = [None if (v is None or (isinstance(v, float) and math.isnan(v))) else (v.item() if hasattr(v, "item") else v) for v in s.tolist()]
            if all(v is None or float(v).is_integer() for v in vals):
                vals = [None if v is None else int(v) for v in vals]
            out["data"][c] = vals
    return out


def load(name):
    p = os.path.join(DATA, f"{name}.parquet")
    return pd.read_parquet(p) if os.path.exists(p) else pd.DataFrame()


def bucket_status(status, lookup, dim_status):
    """status rows -> hours per KEYS in the READY/DELAY/... buckets + shift-change minutes."""
    if status.empty:
        return pd.DataFrame(columns=KEYS + HOUR_COLS), pd.DataFrame()
    s = status.copy()
    s["id_status_detail"] = s["id_status_detail"].astype(int)
    lk = s["id_status_detail"].astype(str).map(lookup)
    s["main"] = lk.map(lambda v: v[0] if isinstance(v, list) else None)
    s["type"] = lk.map(lambda v: v[1] if isinstance(v, list) else None)
    names = dict(zip(dim_status["id_status_detail"].astype(int), dim_status["status_name"])) if not dim_status.empty else {}
    s["status_name"] = s["id_status_detail"].map(names).fillna(lk.map(lambda v: v[2] if isinstance(v, list) else None)).fillna("(unknown)")

    def bucket(r):
        m, t = r["main"], r["type"]
        if not isinstance(m, str):
            return "h_unknown"
        if m == "READY":
            return "h_prod" if str(t).lower().startswith("prod") else "h_ready_other"
        if m == "DELAY":
            return "h_delay"
        if m == "STANDBY":
            return "h_standby"
        if m.startswith("MANT"):
            return "h_maint"
        return "h_oop"
    s["bucket"] = s.apply(bucket, axis=1)
    # ids newer than the R4M lookup: bucket by C4M's own status kind, learned from the known ids
    if "id_status_kind" in dim_status.columns:
        kind_of = dict(zip(dim_status["id_status_detail"].astype(int), pd.to_numeric(dim_status["id_status_kind"], errors="coerce")))
        s["kind"] = s["id_status_detail"].map(kind_of)
        known = s[s["bucket"] != "h_unknown"]
        kind_bucket = known.groupby("kind")["bucket"].agg(lambda x: x.value_counts().index[0]).to_dict() if len(known) else {}
        fb = s["bucket"].eq("h_unknown") & s["kind"].map(kind_bucket).notna()
        s.loc[fb, "bucket"] = s.loc[fb, "kind"].map(kind_bucket)
    hours = s.pivot_table(index=KEYS, columns="bucket", values="hours", aggfunc="sum", fill_value=0.0).reset_index()
    for c in HOUR_COLS:
        if c not in hours:
            hours[c] = 0.0
    sc = s[s["status_name"].str.contains("Ээлж солилцох|shift change", case=False, regex=True, na=False)]
    sc = sc.groupby(KEYS)["hours"].sum().mul(60).rename("min_shiftchange").reset_index()
    hours = hours.drop(columns=["min_shiftchange"]).merge(sc, on=KEYS, how="left")
    hours["min_shiftchange"] = hours["min_shiftchange"].fillna(0.0)
    unknown = s.loc[s["bucket"] == "h_unknown", "id_status_detail"].value_counts()
    newer = s.loc[s["main"].isna() & (s["bucket"] != "h_unknown"), "id_status_detail"].nunique()
    if newer:
        print(f"  note: {newer} status detail ids newer than the R4M lookup were bucketed by C4M status kind - re-run make_lookups.py after the next R4M fetch")
    if len(unknown):
        print(f"  note: {len(unknown)} status detail ids could not be bucketed (h_unknown): {list(unknown.index[:8])}")
    reasons = (s[s["bucket"] != "h_prod"]
               .groupby(["shift_date", "shift", "id_worker", "id_status_detail", "status_name", "bucket"])["hours"]
               .sum().reset_index())
    reasons = reasons[reasons["hours"] >= 0.02]
    return hours[KEYS + HOUR_COLS], reasons


def checklist_counts(forms):
    if forms.empty:
        return pd.DataFrame(columns=KEYS + CHK_COLS)
    f = forms.copy()
    f["forms"] = 1
    f["forms_rej"] = (f["form_status"] == "Rejected").astype(int)
    f["forms_pend"] = (f["form_status"] == "Not reviewed").astype(int)
    f["items"] = f["n_items"].fillna(0)
    f["items_nok"] = f["n_not_ok"].fillna(0)
    return f.groupby(KEYS)[CHK_COLS].sum().reset_index()


def episodes_file():
    """The episode cache the Over-speed page currently uses: overspeed/data/meta.json steep_grades[0] ->
    episodes_s<G>.parquet; else the newest episodes_s*.parquet. Returns (path, grade, how) or (None, None, None)."""
    d = os.path.join(OVERSPEED, "data")
    try:
        g = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))["steep_grades"][0]
        g = int(g) if float(g).is_integer() else g
        p = os.path.join(d, f"episodes_s{g}.parquet")
        if os.path.exists(p):
            return p, g, "from overspeed/data/meta.json"
    except Exception:  # noqa: BLE001
        pass
    files = sorted(glob.glob(os.path.join(d, "episodes_s*.parquet")), key=os.path.getmtime)
    if not files:
        return None, None, None
    p = files[-1]
    return p, os.path.basename(p)[len("episodes_s"):-len(".parquet")], "newest file, meta.json unusable"


def _by_session(ep, logins):
    """Login-session fallback: the operator whose at_worker_login session on the truck covers the event start."""
    out = pd.Series(0, index=ep.index, dtype="int64")
    if ep.empty or logins.empty:
        return out
    lg = logins.copy()
    lg["t0"] = pd.to_datetime(lg["login_ts"])
    lg["t1"] = pd.to_datetime(lg["logout_ts"])
    for eq, g in ep.groupby("id_equipo"):
        sess = lg[lg["id_equipo"] == eq].sort_values("t0")
        if sess.empty:
            continue
        ts = g["ts"].to_numpy()
        idx = sess["t0"].searchsorted(g["ts"], side="right") - 1
        w = sess["id_worker"].to_numpy()[idx.clip(0)]
        t1 = sess["t1"].to_numpy()[idx.clip(0)]
        hit = (idx >= 0) & (ts < t1)
        out.loc[g.index[hit]] = w[hit]
    return out


def overspeed_events(dim_eq, dim_wk, logins, keys):
    """Over-speed events of the Over-speed page -> (event frame, aggregate per KEYS, info), or (None, None, info).
    keys = ops[KEYS] (the operator x machine x shift rows that exist), used to break ties between duplicated logins."""
    path, grade, how = episodes_file()
    info = {"file": os.path.basename(path) if path else None, "steep_grade": grade}
    if not path:
        print("  over-speed: no episodes file in overspeed/data - over-speed hidden on the page")
        return None, None, info
    raw = pd.read_parquet(path)
    print(f"  over-speed source: {os.path.basename(path)} (steep >= {grade} %, {how})")
    ep = apply_rule(raw, OS_RULE)                       # over_kmh = average - limit; the peak is never used
    name2eq = dict(zip(dim_eq["equipment"], dim_eq["id_equipo"].astype(int)))
    ep["id_equipo"] = ep["equipment"].map(name2eq)
    unknown = int(ep["id_equipo"].isna().sum())
    ep = ep.dropna(subset=["id_equipo"]).reset_index(drop=True)
    ep["id_equipo"] = ep["id_equipo"].astype(int)
    ep["ts"] = pd.to_datetime(ep["event_ts"])
    ep["id_worker"] = 0
    ep["how"] = "none"
    # 1) the login id the truck telemetry carries (tp_trabajador.login_id). A login duplicated in dim_workers ->
    #    the id that has a row on that truck in that shift, then the live (not deleted) row, then the highest id
    wk = dim_wk.copy()
    wk["operator_login"] = wk["operator_login"].astype("string").str.strip()
    wk["deleted"] = wk["deleted"].fillna(False).astype(bool) if "deleted" in wk else False
    cand = ep[["shift_date", "shift", "id_equipo", "operator_login"]].copy()
    cand["operator_login"] = cand["operator_login"].astype("string").str.strip()
    cand["ix"] = cand.index
    cand = cand.merge(wk[["operator_login", "id_worker", "deleted"]], on="operator_login", how="inner")
    amb = 0
    if not cand.empty:
        k = keys.drop_duplicates().assign(hit=1)
        cand["id_worker"] = cand["id_worker"].astype(int)
        cand = cand.merge(k, on=["shift_date", "shift", "id_equipo", "id_worker"], how="left")
        cand["hit"] = cand["hit"].fillna(0)
        cand = cand.sort_values(["ix", "hit", "deleted", "id_worker"], ascending=[True, False, True, False])
        amb = int((cand.groupby("ix").size() > 1).sum())
        best = cand.drop_duplicates("ix").set_index("ix")["id_worker"]
        ep.loc[best.index, "id_worker"] = best.astype(int).to_numpy()
        ep.loc[best.index, "how"] = "login"
    # 2) the operator name (live rows first)
    rest = ep["id_worker"] == 0
    if rest.any():
        n2w = wk.sort_values(["deleted", "id_worker"], ascending=[True, False]).drop_duplicates("operator")
        n2w = dict(zip(n2w["operator"], n2w["id_worker"].astype(int)))
        w = ep.loc[rest, "operator"].map(n2w)
        ok = w.notna()
        ep.loc[w[ok].index, "id_worker"] = w[ok].astype(int).to_numpy()
        ep.loc[w[ok].index, "how"] = "name"
    # 3) the at_worker_login session on the truck
    rest = ep["id_worker"] == 0
    if rest.any():
        w = _by_session(ep[rest], logins)
        ok = w > 0
        ep.loc[w[ok].index, "id_worker"] = w[ok].to_numpy()
        ep.loc[w[ok].index, "how"] = "session"
    n = len(ep)
    cnt = ep["how"].value_counts().to_dict()
    info.update({"n_cached": int(len(raw)), "n_rule": int(n), "unknown_equipment": unknown, "ambiguous_login": amb,
                 **{f"by_{h}": int(cnt.get(h, 0)) for h in ("login", "name", "session", "none")},
                 "from": str(raw["shift_date"].min()) if len(raw) else None,
                 "to": str(raw["shift_date"].max()) if len(raw) else None})

    def pc(h):
        return f"{cnt.get(h, 0)} ({cnt.get(h, 0) / n * 100:.1f} %)" if n else "0"
    print(f"  over-speed: {len(raw)} cached episodes -> {n} after the rule (>= {OS_RULE[0]} s, average >= limit + {OS_RULE[1]:g} km/h); "
          f"attributed by login {pc('login')}, by name {pc('name')}, by session {pc('session')}, unattributed {pc('none')}; "
          f"{int((ep['road'] == 'steep').sum())} steep; worst +{(ep['over_kmh'].max() if n else 0):.1f} km/h; "
          f"telemetry {info['from']}..{info['to']}; duplicated logins resolved {amb}; unknown trucks {unknown}")
    if not n:
        return None, None, info
    ev = pd.DataFrame({
        "shift_date": ep["shift_date"].astype(str), "shift": ep["shift"].astype(str), "id_worker": ep["id_worker"].astype(int),
        "equipment": ep["equipment"].astype(str), "t": ep["ts"].dt.strftime("%H:%M"), "dur": ep["duration_s"].astype(int),
        "avg": ep["avg_speed_kmh"].round(1), "lim": ep["limit_kmh"].round(0).astype(int), "over": ep["over_kmh"].round(1),
        "road": ep["road"].astype(str), "segment": ep["segment"].fillna("").astype(str),
        "loaded": ep["is_loaded"].fillna(False).astype(int)})
    ev = ev.sort_values(["shift_date", "shift", "equipment", "t"]).reset_index(drop=True)
    a = ep[ep["id_worker"] > 0].assign(steep=(ep["road"] == "steep").astype(int))
    agg = a.groupby(KEYS).agg(os_n=("duration_s", "size"), os_s=("duration_s", "sum"), os_max=("over_kmh", "max"),
                              os_steep=("steep", "sum")).reset_index()
    return ev, agg, info


def item_order(dim_items, used_ids):
    """Leaf items in template -> section -> ordinal order; items answered but missing from the structure go last."""
    d = dim_items.copy()
    d["item_id"] = d["item_id"].astype(int)
    d["section_id"] = d["section_id"].fillna(0).astype(int)
    byid = {r.item_id: r for r in d.itertuples(index=False)}
    kids = {}
    for r in d.itertuples(index=False):
        kids.setdefault(r.section_id, []).append(r.item_id)
    for k in kids:
        kids[k].sort(key=lambda i: ((byid[i].ordinal if byid[i].ordinal == byid[i].ordinal else 1e9), i))
    roots = [r for r in d.itertuples(index=False) if bool(r.is_struct)]
    roots.sort(key=lambda r: (r.fleet_id if r.fleet_id == r.fleet_id else 0, r.item_id))
    rows, seen = [], set()

    def walk(node, template, section):
        for i in kids.get(node, []):
            r = byid[i]
            if i in kids:                      # a section
                walk(i, template, r.item)
            else:
                if i not in seen:
                    rows.append({"item_id": i, "template": template, "section": section, "item": r.item})
                    seen.add(i)
    for r in roots:
        walk(r.item_id, r.item, "")
    for i in sorted(set(int(x) for x in used_ids) - seen):
        r = byid.get(i)
        rows.append({"item_id": i, "template": "(other)", "section": r.section if r else "", "item": r.item if r else f"(item #{i})"})
    return pd.DataFrame(rows, columns=["item_id", "template", "section", "item"])


def read(path, default=""):
    return open(path, encoding="utf-8").read() if os.path.exists(path) else default


def main():
    global DATA
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", nargs=argparse.REMAINDER, help="run fetch_operator_kpi.py first (remaining args are passed to it)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--data", default=DATA, help="data folder (default operator_kpi/data)")
    a = ap.parse_args()
    DATA = a.data
    if a.fetch is not None:
        cmd = [sys.executable, os.path.join(HERE, "fetch_operator_kpi.py")] + a.fetch
        print("fetching:", " ".join(cmd[1:]))
        subprocess.run(cmd, check=True, cwd=HERE)

    meta = json.load(open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
    lookup = json.load(open(LOOKUP, encoding="utf-8"))
    loads, status, logins = load("loads"), load("status"), load("logins")
    forms, items = load("checklists"), load("checklist_items")
    dim_eq, dim_wk, dim_items, dim_status = load("dim_equipment"), load("dim_workers"), load("dim_checklist_items"), load("dim_status")
    dim_wk = dim_wk[~dim_wk["operator"].fillna("").str.contains("test", case=False)]
    for df in (loads, status, forms, logins):
        if "id_worker" in df:
            df["id_worker"] = df["id_worker"].fillna(0).astype(int)
        if "id_equipo" in df:
            df["id_equipo"] = df["id_equipo"].fillna(0).astype(int)

    # ---- ops: one row per shift x equipment x operator --------------------------------------
    haul = loads[loads["role"] == "haul"][KEYS + HAUL_SUMS] if not loads.empty else pd.DataFrame(columns=KEYS + HAUL_SUMS)
    ld = loads[loads["role"] == "load"] if not loads.empty else pd.DataFrame()
    if not ld.empty:
        ld = ld.rename(columns={"loads": "loads_ld", "tonnes": "tonnes_ld", "n_load": "n_ldg", "s_load": "s_ldg"})[KEYS + LOAD_SUMS]
    else:
        ld = pd.DataFrame(columns=KEYS + LOAD_SUMS)
    hours, reasons = bucket_status(status, lookup, dim_status)
    chk = checklist_counts(forms)
    ops = haul.merge(ld, on=KEYS, how="outer").merge(hours, on=KEYS, how="outer").merge(chk, on=KEYS, how="outer")
    for c in ("id_equipo", "id_worker"):
        ops[c] = ops[c].astype(int)
    osev, osc, osinfo = overspeed_events(dim_eq, dim_wk, logins, ops[KEYS])
    if osc is not None:
        ops = ops.merge(osc, on=KEYS, how="outer")
    else:
        for c in OS_COLS:
            ops[c] = None
    for c in HAUL_SUMS + LOAD_SUMS + HOUR_COLS + CHK_COLS + OS_COLS:
        ops[c] = pd.to_numeric(ops[c], errors="coerce")
    for c in HOUR_COLS:
        ops[c] = ops[c].fillna(0.0).round(3)
    for c in CHK_COLS:
        ops[c] = ops[c].fillna(0).astype(int)
    eq_role = dict(zip(dim_eq["id_equipo"].astype(int), dim_eq["role"]))
    eq_name = dict(zip(dim_eq["id_equipo"].astype(int), dim_eq["equipment"]))
    eq_model = dict(zip(dim_eq["id_equipo"].astype(int), dim_eq["model"]))
    wk_name = dict(zip(dim_wk["id_worker"].astype(int), dim_wk["operator"]))
    wk_login = dict(zip(dim_wk["id_worker"].astype(int), dim_wk["operator_login"]))
    wk_crew = dict(zip(dim_wk["id_worker"].astype(int), dim_wk["crew"]))
    ops["role"] = ops["id_equipo"].map(eq_role).fillna("aux")
    ops["equipment"] = ops["id_equipo"].map(eq_name).fillna(ops["id_equipo"].map(lambda v: f"#{v}"))
    ops["model"] = ops["id_equipo"].map(eq_model)
    ops["operator"] = ops["id_worker"].map(wk_name)
    ops.loc[ops["id_worker"] == 0, "operator"] = None
    ops["operator_login"] = ops["id_worker"].map(wk_login)
    ops["crew"] = ops["id_worker"].map(wk_crew)
    ops = ops.sort_values(KEYS).reset_index(drop=True)
    ops_cols = ["role", "shift_date", "shift", "id_equipo", "equipment", "model", "id_worker", "operator", "operator_login", "crew"] \
        + HAUL_SUMS + LOAD_SUMS + HOUR_COLS + CHK_COLS + OS_COLS

    # ---- reasons / forms / items -------------------------------------------------------------
    if not reasons.empty:
        reasons["id_worker"] = reasons["id_worker"].astype(int)
        reasons["operator"] = reasons["id_worker"].map(wk_name)
        reasons["hours"] = reasons["hours"].round(3)
        reasons = reasons[["shift_date", "shift", "id_worker", "operator", "status_name", "bucket", "hours"]]
    if not forms.empty:
        forms = forms.sort_values(["created_ts", "id_checklist"]).reset_index(drop=True)
        forms["role"] = forms["id_equipo"].map(eq_role).fillna("aux")
        forms["crew"] = forms["crew"].fillna(forms["id_worker"].map(wk_crew))
        fcols = ["id_checklist", "created_ts", "shift_date", "shift", "id_equipo", "equipment", "model", "role", "id_worker", "operator",
                 "operator_login", "crew", "description", "form_status", "status_ts", "review_comment", "n_items", "n_not_ok"]
        forms = forms[fcols]
    if not items.empty:
        items["id_checklist"] = items["id_checklist"].astype(int); items["item_id"] = items["item_id"].astype(int)
        grp = items.groupby("id_checklist")
        ids_by = grp["item_id"].apply(list).to_dict()
        nok_by = items[~items["is_ok"].astype(bool)].groupby("id_checklist")["item_id"].apply(list).to_dict()
        order = forms["id_checklist"].astype(int).tolist()
        item_ids = [ids_by.get(i, []) for i in order]
        item_nok = [nok_by.get(i, []) for i in order]
        used = set(items["item_id"].tolist())
    else:
        item_ids, item_nok, used = [], [], set()
    dim_items_o = item_order(dim_items, used) if not dim_items.empty else pd.DataFrame(columns=["item_id", "template", "section", "item"])

    data = {
        "meta": meta,
        "ops": table(ops[ops_cols], round1=("tonnes", "tonnes_ld", "os_max")),
        "reasons": table(reasons) if not reasons.empty else None,
        "forms": table(forms) if not forms.empty else None,
        "items": {"ids": item_ids, "nok": item_nok},
        "dimItems": table(dim_items_o),
        "osev": table(osev) if osev is not None else None,
        "hasOverspeed": osc is not None,
    }
    meta["os_rule"] = [OS_RULE[0], OS_RULE[1]]
    meta["os_file"] = osinfo.get("file")
    meta["os_steep_grade"] = osinfo.get("steep_grade")
    meta["os_from"] = osinfo.get("from")
    meta["os_to"] = osinfo.get("to")
    meta["os_attrib"] = {k: v for k, v in osinfo.items() if k.startswith("by_") or k in ("n_cached", "n_rule", "ambiguous_login")}
    logo = base64.b64encode(open(os.path.join(DAILY, "erdene_logo.png"), "rb").read()).decode("ascii")
    schema = read(os.path.join(ROOT, "r4m-design-schema.css"))
    schema = "\n".join(l for l in schema.splitlines() if not l.strip().startswith("@import"))   # no Google Fonts call

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Operator KPI · {meta['date_from']} → {meta['date_to']}</title>
<style>
{read(os.path.join(DAILY, 'vendor_rubik.css'))}
{schema}
{CSS}
</style>
</head>
<body>
{HTML.replace('__LOGO__', logo)}
<script>
{JS.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))}
</script>
</body>
</html>
"""
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    n_forms = len(forms) if not forms.empty else 0
    print(f"wrote {a.out}  ({os.path.getsize(a.out) / 1e6:.1f} MB)  ops {len(ops)} rows, reasons {len(reasons)}, forms {n_forms}, "
          f"items {sum(len(x) for x in item_ids)}, dim items {len(dim_items_o)}  period {meta['date_from']}..{meta['date_to']}")
    # console cross-check of the headline numbers the page should show for the whole period
    h = ops
    print(f"check: loads {int(h['loads'].fillna(0).sum())} (trucks {int(ops.loc[ops['role'] == 'haul', 'loads'].fillna(0).sum())}, load-and-carry {int(ops.loc[ops['role'] != 'haul', 'loads'].fillna(0).sum())}), "
          f"nominal t {h['tonnes'].fillna(0).sum():,.0f}, productive h {ops['h_prod'].sum():,.0f}, "
          f"operators {ops.loc[ops['id_worker'] > 0, 'id_worker'].nunique()}, forms {n_forms}, items NOT OK "
          f"{int(forms['n_not_ok'].fillna(0).sum()) if n_forms else 0} of {int(forms['n_items'].fillna(0).sum()) if n_forms else 0}, "
          f"over-speed {len(osev) if osev is not None else 0} events ({int(ops['os_n'].fillna(0).sum())} attributed, "
          f"{ops.loc[ops['os_n'].fillna(0) > 0, 'id_worker'].nunique()} operators)")


if __name__ == "__main__":
    main()
