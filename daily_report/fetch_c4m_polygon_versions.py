"""C4M polygon versions -> data/c4m_polygon_versions.json (read-only SELECT on the C4M DB).

C4M writes a new ts_poligono row (new id) every time a polygon is edited and keeps the
original id in id_poligono (SMG-1C-21: #4166 -> #4169, #4195, #4245, #4482, ... one row per
edit, 16-24 Sep 2026). The R4M polygon register (getAllPolygonData*) lists only the original
id, while every cube cycle carries the version that was current when it was loaded, and the
cube's polygon dimension has no link back. build_atlas maps cycle -> original id with this file
(absent -> exact ids, as before 2026-10-29).

    python fetch_c4m_polygon_versions.py        (needs .env C4M_DB_* and the VPN; C4M_DB_MODE=ssh)
"""
import json, os, sys, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "overspeed"))
os.environ.setdefault("C4M_DB_MODE", "ssh")
import db  # noqa: E402

OUT = os.path.join(HERE, "data", "c4m_polygon_versions.json")
# wall clock at the mine (UTC+8), the same clock as the cube's shift dates and hours
SQL = """select id, id_poligono, nombre, nivel, level_real,
                to_char(tiem_creac at time zone 'Asia/Ulaanbaatar', 'YYYY-MM-DD HH24:MI:SS') creac,
                to_char(tiem_elimin at time zone 'Asia/Ulaanbaatar', 'YYYY-MM-DD HH24:MI:SS') elimin
         from ts_poligono where id_poligono is not null"""
# dump areas: every version (the cube's "Id Location Dump" = ts_descarga.id) -> original id_descarga
SQL_DUMP = """select id, id_descarga, nombre, nivel,
                     to_char(tiem_creac at time zone 'Asia/Ulaanbaatar', 'YYYY-MM-DD HH24:MI:SS') creac,
                     to_char(tiem_elimin at time zone 'Asia/Ulaanbaatar', 'YYYY-MM-DD HH24:MI:SS') elimin
              from ts_descarga"""
# C4M's stockpile assignment: which stock polygon a dump area fed, from when to when
SQL_LINK = """select id2_poligono, id2_descarga,
                     to_char(tiem_creac at time zone 'Asia/Ulaanbaatar', 'YYYY-MM-DD HH24:MI:SS') creac,
                     to_char(tiem_elimin at time zone 'Asia/Ulaanbaatar', 'YYYY-MM-DD HH24:MI:SS') elimin
              from ts_stockpiles order by tiem_creac"""


def _s(v):                  # psql nulls arrive as NaN
    return v if isinstance(v, str) and v else None


def _i(v):
    return None if v is None or v != v else int(v)


def main():
    df = db.run_query(SQL)
    parent = {int(r.id): int(r.id_poligono) for r in df.itertuples(index=False)}

    def root(i):            # id_poligono is the original id today; follow a chain defensively
        seen = set()
        while parent.get(i, i) != i and i not in seen:
            seen.add(i)
            i = parent[i]
        return i
    vers = {}
    for r in df.itertuples(index=False):
        rid = root(int(r.id))
        if rid != int(r.id):
            vers[str(int(r.id))] = [rid, str(r.nombre or ""), _i(r.nivel), _s(r.creac), _s(r.elimin)]
    # life[original id] = [name, bench, [[created, closed|None], ...]]: when the polygon (any of its
    # versions) was on the C4M map; an edit closes one version and opens the next at the same second
    spans = {}
    for r in df.itertuples(index=False):
        if _s(r.creac):
            spans.setdefault(root(int(r.id)), []).append([_s(r.creac), _s(r.elimin), str(r.nombre or ""), _i(r.nivel)])
    life = {}
    for rid, sp in spans.items():
        sp.sort(key=lambda x: x[0])
        merged = []
        for a, b, _, _ in sp:
            if merged and (merged[-1][1] is None or a <= merged[-1][1]):
                if merged[-1][1] is not None and (b is None or b > merged[-1][1]):
                    merged[-1][1] = b
            else:
                merged.append([a, b])
        last = sp[-1]
        life[str(rid)] = [last[2], last[3], merged]
    # vlife[id] = [created, closed|None] of every stock-bench row (originals and versions): which outline
    # was on the map when (the R4M register holds outlines of some versions, not only the original)
    vlife = {str(int(r.id)): [_s(r.creac), _s(r.elimin)] for r in df.itertuples(index=False)
             if _i(r.nivel) == 1237 and _s(r.creac)}
    # lvl[id] = the planners' uploaded level (level_real, decimals kept: 1192.5) where it differs from the whole-metre
    # nivel; a version saved by an edit in C4M has level_real empty -> the original's, else the newest version's that has one
    def _f(v):
        return None if v is None or v != v else float(v)
    own = {int(r.id): _f(r.level_real) for r in df.itertuples(index=False)}
    by_root = {}
    for r in sorted(df.itertuples(index=False), key=lambda r: (_s(r.creac) or "")):
        if own[int(r.id)] is not None:
            by_root[root(int(r.id))] = own[int(r.id)]          # newest wins ...
    for r in df.itertuples(index=False):
        rid = root(int(r.id))
        if own.get(rid) is not None:
            by_root[rid] = own[rid]                            # ... unless the original upload has one
    lvl = {}
    for r in df.itertuples(index=False):
        i = int(r.id)
        v = own[i] if own[i] is not None else by_root.get(root(i))
        if v is not None and (_i(r.nivel) is None or abs(v - _i(r.nivel)) > 1e-6):
            lvl[str(i)] = round(v, 2)
    dd = db.run_query(SQL_DUMP)
    dumps = {str(int(r.id)): [_i(r.id_descarga) or int(r.id), str(r.nombre or ""), _s(r.creac), _s(r.elimin)]
             for r in dd.itertuples(index=False)}
    lk = db.run_query(SQL_LINK)
    links = [[root(int(r.id2_poligono)), int(r.id2_descarga), _s(r.creac), _s(r.elimin)] for r in lk.itertuples(index=False)
             if _s(r.creac)]
    out = {"source": "C4M ControlSenseDB public.ts_poligono (id -> id_poligono, tiem_creac/tiem_elimin, UTC+8), "
                     "ts_descarga (dump area versions), ts_stockpiles (dump area -> stock polygon)",
           "fetched": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "rows": len(df), "versions": vers, "life": life,
           "vlife": vlife, "dumps": dumps, "links": links, "lvl": lvl}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    roots = len({v[0] for v in vers.values()})
    print(f"wrote {OUT}: {len(df):,} polygons, {len(vers):,} versions of {roots:,} originals, "
          f"{len(dumps):,} dump-area rows, {len(links):,} stockpile links, {len(lvl):,} real levels != nivel")


if __name__ == "__main__":
    main()
