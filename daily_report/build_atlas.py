"""Build the Mine Atlas - spatial & material-lifecycle companion to the daily report.

Sections: interactive mine map (contour backdrop + GPS dig/dump footprints + dig/dump points +
haul-flow arcs + day playback), material life-cycle sankey (pit polygon -> class ->
destination -> crusher), polygon depletion explorer, stockpile balances, haul
efficiency, hour-of-day heatmap, bench progression.

Everything is aggregated here and embedded as JSON; the page is one self-contained
HTML file with hand-rolled SVG (no external libraries).

Run:  python build_atlas.py          (data must exist: fetch_data.py + prepare_contour.py)
Out:  mine_atlas.html
"""
import base64
import datetime as dt
import json
import os
import re

import numpy as np
import pandas as pd
from shapely.geometry import MultiPoint

from build_report import load_joined, DATA, EXCLUDE_EQUIP, ACTIVE_PILE_DAYS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "mine_atlas.html")

GRID = 12.0          # metres, dig/dump point binning
FLOW_MIN_T = 60.0    # arcs below this tonnage are dropped (declutter)
TOP_POLYS = 30       # sankey stage-1: polygons named individually
TOP_BLASTS = 15      # ... then the rest grouped by blast block ("1210_043 · other cuts")
BLAST_RE = r"^(?:[A-Za-z]+_)?(\d{4}(?:\.\d)?_\d{2,3})"
TOP_PILES = 10       # sankey destination piles


# --------------------------------------------------------------------------- #
def dest_group(row):
    if row["is_crush"]:
        return "Crusher"
    if row["is_rom"]:
        return row["Location Dump"]
    r = row["Region"] if isinstance(row["Region"], str) else ""
    if r == "IWF":
        return "IWF"
    if r.startswith("Top Soil"):
        return "Topsoil"
    if r == "Min Waste Stockpile":
        return "Min-Waste"
    if r == "SG Stockpile":
        return "SG Stockpile"
    if r == "LG-1 Stockpile":
        return "S_48 (LG-1)"
    if r == "Erdene Mongol":
        return "In-pit dumps"
    if r == "Bayan Khundii":
        return "Pit ramps"
    return r or "Other"


def crushed_original(name):
    """Name of the pile a crushed stock polygon came from (SMG-1C-41, SHG-1-C-10, SM_25_2_C, ST_51C -> no C), else None."""
    for pat, rep in ((r"^(.+-\d+)C(-.+)$", r"\g<1>\g<2>"), (r"^(.+)-C-(.+)$", r"\g<1>-\g<2>"), (r"^(.+?)[_-]?C$", r"\g<1>")):
        if re.match(pat, name):
            return re.sub(pat, rep, name)
    return None


def crushed_sources(info, pit_src):
    """Crushed piles take their original's source polygons (client rule, 2026-11-06). C4M records almost no dumps
    into them, so a pile's tonnes = the larger of dumped in and loaded out; pit polygons dumped straight into it keep
    their own tonnes, the rest is split by each polygon's share of the original's tonnes (weighted over every original
    of that name). A pile's dumps booked to itself or its original are not a source. Sets srcs + cr on each crushed pile."""
    names = {v["name"] for v in info.values()}
    for v in info.values():
        orig = crushed_original(v["name"])
        if not orig or orig not in names:
            continue
        skip = {v["name"], orig}
        base = {k: t for k, t in pit_src.get(orig, {}).items() if k[0] not in skip}
        own = {}
        for p_, t, c_s in v["srcs"]:
            if p_ not in skip:
                own[(p_, c_s)] = t
        t_in = sum(d[0] for d in v["days"].values())
        t_out = sum(d[1] for d in v["days"].values())
        total = max(t_in, t_out)
        v["cr"] = {"o": orig, "t": round(total, 1), "b": "out" if t_out >= t_in else "in", "n": len(base)}
        if not base or total <= 0:
            continue
        rest = max(0.0, total - sum(own.values()))
        whole = sum(base.values())
        for k, t in base.items():
            own[k] = own.get(k, 0.0) + rest * t / whole
        top = sorted(own.items(), key=lambda x: -x[1])[:10]
        v["srcs"] = [[k[0], round(t, 1), k[1]] for k, t in top]


def atlas_payload(df=None):
    """Aggregate everything the atlas half needs; returns (payload, contour_b64)."""
    if df is None:
        df = load_joined()

    poly = pd.read_parquet(os.path.join(DATA, "polygon.parquet"))
    ll = pd.read_parquet(os.path.join(DATA, "location_load.parquet"))[
        ["Id Location Load", "Zone", "Location Load"]].rename(
        columns={"Zone": "LoadZone", "Location Load": "lname"})
    sd = pd.read_parquet(os.path.join(DATA, "sensor_data.parquet"))

    df = df.merge(poly[["Id Polygon", "Polygon", "Bench", "Initial Tonnes", "Mined Tonnes"]],
                  on="Id Polygon", how="left")
    df = df.merge(ll, on="Id Location Load", how="left")
    sd = sd.rename(columns={"C4M ID Hauling": "cid"})
    df = df.merge(sd, left_on="C4M ID Hauling", right_on="cid", how="left")

    # coordinates: bucket first, loader-equipment fallback; dump coords are x100
    bx = df["Loading Bucket X Coordinate"].where(df["Loading Bucket X Coordinate"] > 1000)
    by = df["Loading Bucket Y Coordinate"].where(df["Loading Bucket Y Coordinate"] > 1000)
    ex = df["Loading Equipment X Coordinate"].where(df["Loading Equipment X Coordinate"] > 1000)
    ey = df["Loading Equipment Y Coordinate"].where(df["Loading Equipment Y Coordinate"] > 1000)
    df["lx"] = bx.fillna(ex)
    df["ly"] = by.fillna(ey)
    df["dx"] = (df["Hauling Coor X at Dump"] / 100.0).where(df["Hauling Coor X at Dump"] > 100000)
    df["dy"] = (df["Hauling Coor Y at Dump"] / 100.0).where(df["Hauling Coor Y at Dump"] > 100000)
    cov = df["lx"].notna().mean() * 100, df["dx"].notna().mean() * 100
    print(f"coordinate coverage: load {cov[0]:.0f}%  dump {cov[1]:.0f}%")

    df["month"] = df["date"].str[:7]
    df["dest"] = df.apply(dest_group, axis=1)
    df["pname"] = df["Polygon"].fillna("(unknown)")
    # reclaim = REHANDLE (loaded off a stockpile or dump; build_report.is_reh).
    # The sankey additionally keeps crusher deliveries out of stages 1-2 so the
    # mill is fed only through stage 3; the polygon explorer and stock balances
    # count direct pit->crusher tonnes as mined, like the report does.
    df["reclaim"] = df["is_reh"].fillna(False).astype(bool)
    # mill-feed source label: the load-location name is the per-shift "detail"
    # (which stock fed the 1237_* finger, e.g. "1237_SL_18_2" = SL_18_2);
    # fall back to the polygon name where the location is generic/missing
    _lab = df["lname"].fillna("").astype(str).str.strip()
    df["feedlab"] = (_lab.where(_lab != "", df["Polygon"].fillna("(unknown)"))
                         .str.replace(r"^1237[_ ]", "", regex=True))
    months = sorted(df["month"].unique())
    iso = pd.to_datetime(df["date"]).dt.isocalendar()
    df["week"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    weeks = sorted(df["week"].unique())
    days = sorted(df["date"].unique())

    # ---- polygon attributes: cube polygon dim (+ R4M grades already joined
    # into df), looked up in PSTAT. Planned polygon BOUNDARIES come from the
    # R4M HPGPS backend register (fetch_data.py -> data/r4m_polygons.json:
    # UTM rings, open + closed polygons, id == cube Id Polygon); the map draws
    # them as dashed outlines next to each polygon's GPS dig footprint (below).
    cube_p = poly.set_index("Polygon")
    DESIGN = {}                      # name -> [[id, bench, "open"|"closed", [[x, y], ...]], ...]
    geo_path = os.path.join(DATA, "r4m_polygons.json")
    if os.path.exists(geo_path):
        geo = json.load(open(geo_path, encoding="utf-8"))
        for pid, g_ in geo["polygons"].items():
            if len(g_["r"]) < 3 or not g_["n"]:
                continue
            # drop test polygons (Polygon_Example @ bench 5900 etc.) that sit outside the mine window
            if not any(482_300 <= x <= 485_500 and 4_859_400 <= y <= 4_863_600 for x, y in g_["r"]):
                continue
            ring = [[round(x, 1), round(y, 1)] for x, y in g_["r"]]
            DESIGN.setdefault(g_["n"], []).append([int(pid), g_["b"], g_["s"], ring])
        print(f"planned polygon boundaries: {sum(len(v) for v in DESIGN.values())} rings for "
              f"{len(DESIGN)} polygons ({geo['open']} open + {geo['closed']} closed, fetched {geo['fetched']})")
    else:
        print("WARNING: data/r4m_polygons.json missing - run fetch_data.py; no planned polygon outlines")

    # ---- corridor ribbons: hub (250m dig clusters) -> destination zone -------
    def matgroup(code, zone):
        if zone == "Crusher":
            return "Mill feed"
        if code in ("HG", "MG", "LG2"):
            return "Ore"
        if code in ("SG", "MW", "LG1"):
            return "Marginal"
        return "Waste"

    W_LO, W_HI = 482_300, 485_500
    H_LO, H_HI = 4_859_400, 4_863_600

    def corridors_for(sub):
        f = sub.dropna(subset=["lx", "ly", "dx", "dy"])
        f = f[f["lx"].between(W_LO, W_HI) & f["ly"].between(H_LO, H_HI)
              & f["dx"].between(W_LO, W_HI) & f["dy"].between(H_LO, H_HI)].copy()
        if f.empty:
            return [], 0.0
        f["hx"] = (f["lx"] // 250) * 250 + 125
        f["hy"] = (f["ly"] // 250) * 250 + 125
        # merge small hubs into the nearest big one (big = >=15% of the largest)
        hubs = f.groupby(["hx", "hy"])["t"].sum().reset_index()
        thr = max(hubs["t"].max() * 0.15, 500)
        big = hubs[hubs["t"] >= thr]
        if big.empty:
            big = hubs.nlargest(1, "t")
        bx, by = big["hx"].to_numpy(), big["hy"].to_numpy()
        def snap(r):
            d2 = (bx - r["hx"]) ** 2 + (by - r["hy"]) ** 2
            i = int(np.argmin(d2))
            return bx[i], by[i]
        small = hubs[hubs["t"] < 5000]
        remap = {(r["hx"], r["hy"]): snap(r) for _, r in small.iterrows()}
        keys = list(zip(f["hx"], f["hy"]))
        f["hx"] = [remap.get(k, k)[0] for k in keys]
        f["hy"] = [remap.get(k, k)[1] for k in keys]
        f["zone"] = f["dest"].where(~f["is_rom"], "ROM Pad")
        f["grp"] = [matgroup(c, z) for c, z in zip(f["code"], f["zone"])]
        g = f.groupby(["hx", "hy", "zone", "grp"]).agg(
            t=("t", "sum"), x0=("lx", "mean"), y0=("ly", "mean"),
            x1=("dx", "mean"), y1=("dy", "mean"), n=("t", "size")).reset_index()
        g = g[g["t"] >= 200]
        out = [[round(r.x0, 0), round(r.y0, 0), round(r.x1, 0), round(r.y1, 0),
                round(r.t, 1), r.grp, r.zone, int(r.n)] for r in g.itertuples()]
        return out, f["t"].sum()

    CORR = {}
    corr_all, cov_t = corridors_for(df)
    CORR["all"] = corr_all
    for m in months:
        CORR[m], _ = corridors_for(df[df["month"] == m])
    for w in weeks:
        CORR[w], _ = corridors_for(df[df["week"] == w])
    for d in days:
        CORR[d], _ = corridors_for(df[df["date"] == d])
    corr_t = sum(c[4] for c in CORR["all"])
    print(f"corridors: all={len(CORR['all'])} arcs "
          f"(+{len(months)} months, {len(weeks)} weeks, {len(days)} days), "
          f"{corr_t:,.0f} t of {cov_t:,.0f} t coord-covered "
          f"({corr_t/cov_t*100 if cov_t else 0:.1f}%; remainder = sub-200t routes)")

    # zone centroids + labels (tonnage-weighted dump coords)
    zdf = df.dropna(subset=["dx", "dy"])
    zdf = zdf[zdf["dx"].between(W_LO, W_HI) & zdf["dy"].between(H_LO, H_HI)].copy()
    zdf["zone"] = zdf["dest"].where(~zdf["is_rom"], "ROM Pad")
    ZONES = {}
    for z, s in zdf.groupby("zone"):
        w = s["t"].clip(lower=0.001)
        ZONES[z] = [round(float(np.average(s["dx"], weights=w)), 0),
                    round(float(np.average(s["dy"], weights=w)), 0),
                    round(float(s["t"].sum()), 0)]

    # ---- dig/dump footprint areas per period ---------------------------------
    # Buffer-union of the GPS points (15 m discs, simplified) traces the actual
    # worked area of each polygon (R4M has no polygon boundaries to clip to)
    # and of each dump zone / ROM pile.
    def footprint(xs, ys, clip=None, buf=15.0, simp=5.0, snap=5.0):
        # snap to a 5 m grid first - invisible under the 15 m buffer + 5 m
        # simplify, and it collapses ~25k GPS fixes to ~5k points, which is the
        # difference between a 4 s and a 10 min GEOS union on the "all" key
        pts = {(round(float(x) / snap) * snap, round(float(y) / snap) * snap)
               for x, y in zip(xs, ys)}
        geom = MultiPoint(list(pts)).buffer(buf, quad_segs=2).simplify(simp)
        if clip is not None:
            try:
                inter = geom.intersection(clip)
                if not inter.is_empty:
                    geom = inter
            except Exception:
                pass
        parts = [g for g in getattr(geom, "geoms", [geom])
                 if g.geom_type == "Polygon" and not g.is_empty]
        if parts:
            # a lone 8-gon disc (~640 m2) is one stray GPS fix, not a worked
            # area - drop satellites below ~2 merged fixes, keep the main part
            biggest = max(parts, key=lambda g: g.area)
            parts = [g for g in parts if g.area >= 800 or g is biggest]
        return [[[int(round(x)), int(round(y))] for x, y in g.exterior.coords]
                for g in parts]

    # identical footprints recur across day/week/month/all keys (a polygon dug
    # on one day has the same geometry in all four) - store rings once, refer
    # to them by index
    ring_pool, ring_idx = [], {}

    def pool(rings):
        key = json.dumps(rings)
        i = ring_idx.get(key)
        if i is None:
            i = len(ring_pool)
            ring_pool.append(rings)
            ring_idx[key] = i
        return i

    fdig = df.dropna(subset=["lx", "ly"])
    fdig = fdig[fdig["lx"].between(W_LO, W_HI) & fdig["ly"].between(H_LO, H_HI)]
    fdump = df.dropna(subset=["dx", "dy"])
    fdump = fdump[fdump["dx"].between(W_LO, W_HI) & fdump["dy"].between(H_LO, H_HI)].copy()
    fdump["zone"] = fdump["dest"].where(~fdump["is_rom"], "ROM Pad")

    def dig_fp(sub):
        out = []
        for p, s in sub.groupby("pname"):
            t = s["t"].sum()
            if t < 10:
                continue
            rings = footprint(s["lx"], s["ly"])
            if rings:
                out.append([p, pool(rings), round(float(t), 1)])
        return out

    def dump_fp(sub):
        out = []
        for z, s in sub.groupby("zone"):
            t = s["t"].sum()
            if t < 10:
                continue
            rings = footprint(s["dx"], s["dy"])
            if rings:
                out.append([z, pool(rings), round(float(t), 1)])
        return out

    DIGFP = {"all": dig_fp(fdig)}
    DUMPFP = {"all": dump_fp(fdump)}
    for col, keys in (("month", months), ("week", weeks), ("date", days)):
        for k in keys:
            sub_d = fdig[fdig[col] == k]
            sub_u = fdump[fdump[col] == k]
            DIGFP[k] = dig_fp(sub_d)
            DUMPFP[k] = dump_fp(sub_u)
    print(f"footprints: dig all={len(DIGFP['all'])} polys, dump all={len(DUMPFP['all'])} zones, "
          f"{len(DIGFP)} period keys, {len(ring_pool)} unique ring sets")

    # ---- Ore Inventory: R4M STOCK POLYGONS, as open on the C4M map -------
    # The map shows the stock polygons (bench 1237 of the R4M/HPGPS register)
    # that were OPEN - i.e. drawn on the C4M mine map - at any time in the
    # selected period; dispatchers close a stock polygon once it is used up
    # and it disappears from C4M. Open interval per polygon:
    #   close "c" = the day the register's closed-in-window endpoint lists it
    #               (fetch_data: one call per day; still-open polygons have none;
    #               closed ones with no day were closed before daily history);
    #   open  "o" = ESTIMATED - the register has no creation date, but ids are
    #               issued in creation order, so a polygon existed before any
    #               later id was first dug: o(X) = min first-load date over ids >= X.
    # Activity per day (for the card): dumped in = ROM-pad cycles at the dump area C4M
    # had assigned to the polygon at the time (ts_stockpiles, read from the C4M DB at
    # build time - the link is not in R4M); loaded out = cycles loaded from it (cycle
    # Id Polygon, any C4M version of it).
    from shapely.geometry import Polygon as SPolygon
    OPEN_SLACK = pd.Timedelta(days=3)      # o(X) is an upper bound: allow a few days early
    # C4M writes a new polygon id at every edit (SMG-1C-21 #4166 -> #4169, #4195, #4245, ...); the
    # R4M register lists only the original id, the cycles carry the version -> map to the original
    # (data/c4m_polygon_versions.json from fetch_c4m_polygon_versions.py; absent -> exact ids)
    ver_path = os.path.join(DATA, "c4m_polygon_versions.json")
    vj = json.load(open(ver_path, encoding="utf-8")) if os.path.exists(ver_path) else {}
    VER = {int(k): int(v[0]) for k, v in vj.get("versions", {}).items()}
    # planned floor per polygon id = the planners' uploaded level (C4M level_real) where it differs from nivel (3D viewer)
    PLEVEL = vj.get("lvl", {})
    # when each original was on the C4M map, to the second (UTC+8): [[created, closed|None], ...]
    LIFE = {int(k): v for k, v in vj.get("life", {}).items() if v[1] == 1237}
    df["rpid"] = df["Id Polygon"].map(lambda i: VER.get(int(i), int(i)) if pd.notna(i) else np.nan)
    romi = df[df["is_rom"]]
    last_date = pd.Timestamp(df["date"].max())
    first_date = pd.Timestamp(df["date"].min())
    reg = json.load(open(geo_path, encoding="utf-8"))["polygons"] if os.path.exists(geo_path) else {}
    # o(X): suffix-min of first-load date over the id sequence
    fl = df.groupby("rpid")["date"].agg(["min", "size"])
    fl = fl[fl["size"] >= 3]["min"]
    ids = sorted(int(k) for k in reg)
    o_est, run = {}, None
    for pid in reversed(ids):
        d_ = fl.get(pid)
        if d_ is not None and (run is None or d_ < run):
            run = d_
        o_est[pid] = run
    # One pile per ORIGINAL polygon id (C4M id_poligono). The R4M register holds outlines of some of
    # its versions (an open polygon is listed under its current version, closed ones under the version
    # that was closed) -> every version outline is kept in PILE_GEO[key]["v"] and the page draws the
    # one on the C4M map in its window.
    VLIFE = {int(k): v for k, v in vj.get("vlife", {}).items()}
    stock = []                                # one entry per version outline
    for k_, v in reg.items():
        vid = int(k_)
        if v.get("b") != 1237 or len(v.get("r") or []) < 3:
            continue
        if not any(W_LO <= x <= W_HI and H_LO <= y <= H_HI for x, y in v["r"]):
            continue
        root = VER.get(vid, vid)
        is_open = v.get("s") == "open"
        c_ = None if is_open else (v.get("c") or "2026-04-30")
        o_ = o_est.get(vid) or (c_ or str(last_date.date()))
        if root in LIFE:                      # C4M's own open / close times replace R4M's estimate
            sp_ = LIFE[root][2]
            o_ = sp_[0][0][:10]
            c_ = sp_[-1][1][:10] if sp_[-1][1] else None
            is_open = c_ is None
        if c_ and c_ < str(first_date.date()):
            continue                                  # closed before the data starts
        ring = [[round(x, 1), round(y, 1)] for x, y in v["r"]]
        g_ = SPolygon(ring)
        if not g_.is_valid:
            g_ = g_.buffer(0)
        stock.append((vid, root, v.get("n") or f"#{root}", "open" if is_open else "closed",
                      v.get("k") or "", o_, c_, ring, g_))
    # Dumped in = C4M's own stockpile assignment (ts_stockpiles: dump area -> stock polygon, from / to):
    # a ROM-pad cycle counts for the pile its dump area fed at the dump time (shift date + Hauling Hour,
    # mid-hour). Dumps at a dump area C4M had not assigned stay unassigned (no GPS guess).
    DROOT = {int(k): int(v[0]) for k, v in vj.get("dumps", {}).items()}       # cube Id Location Dump -> original
    DLINK = {}
    for p_, d_, a_, b_ in vj.get("links", []):
        DLINK.setdefault(int(d_), []).append((pd.Timestamp(a_), pd.Timestamp(b_) if b_ else pd.Timestamp("2100-01-01"), VER.get(int(p_), int(p_))))
    tmid = (pd.to_datetime(romi["date"]) + pd.to_timedelta(romi["Hauling Hour"].fillna(0).astype(int), unit="h")
            + pd.to_timedelta((romi["Hauling Hour"].fillna(0) < 7).astype(int), unit="D") + pd.Timedelta(minutes=30))

    def linked(dump_id, t):
        for a_, b_, p_ in DLINK.get(DROOT.get(int(dump_id), int(dump_id)), ()):
            if a_ <= t < b_:
                return p_
        return 0
    sp = [linked(d_, t) if pd.notna(d_) else 0 for d_, t in zip(romi["Id Location Dump"], tmid)]
    inn = romi.assign(sp=sp)
    # piles = every stock-bench original C4M had on its map in the data period (C4M lifetime), plus
    # register polygons C4M does not know; outline only where R4M's register holds one
    d0 = str(first_date.date())
    roots = {s_[1] for s_ in stock} | {r for r, v in LIFE.items() if v[2][-1][1] is None or v[2][-1][1][:10] >= d0}
    inn = inn[inn["sp"].isin(list(roots))]
    piles = {}                                # root -> its version entries, newest version last
    for s_ in sorted(stock, key=lambda s_: s_[0]):
        piles.setdefault(s_[1], []).append(s_)
    outs = df[df["rpid"].isin(list(roots)) & (df["t"] > 0)]
    def head(root):                           # name, status, colour, open, close
        if root in piles:
            vs = piles[root]
            return vs[-1][2], vs[-1][3], vs[-1][4], min(s_[5] for s_ in vs), vs[-1][6]
        sp_ = LIFE[root][2]
        c0 = sp_[-1][1][:10] if sp_[-1][1] else None
        return LIFE[root][0] or f"#{root}", "closed" if c0 else "open", "", sp_[0][0][:10], c0
    dupn = {}
    for root in roots:
        dupn[head(root)[0]] = dupn.get(head(root)[0], 0) + 1
    PILE_GEO, PILE_INFO = {}, {}
    PIT_SRC = {}                              # pile name -> {(source polygon, class): t}, every source of every original with that name
    for root in sorted(roots):
        name, st, colr, o_, c_ = head(root)
        i_ = inn[inn["sp"] == root]
        o2 = outs[outs["rpid"] == root]
        key = name if dupn[name] == 1 else f"{name} #{root}"
        pdays = {}
        for d, r in i_.groupby("date")[["t", "au_g", "ag_g"]].sum().iterrows():
            pdays[d] = [round(float(r["t"]), 1), 0.0, round(float(r["au_g"]), 1), round(float(r["ag_g"]), 1), 0]
        for d, g in o2.groupby("date")["t"]:     # [t in, t out, Au g, Ag g, loads out]
            v = pdays.setdefault(d, [0.0, 0.0, 0.0, 0.0, 0])
            v[1], v[4] = round(float(g.sum()), 1), int(len(g))
        byc = (i_ if len(i_) else o2).groupby("code")["t"].sum()
        for (p_, c_s), v_ in i_.groupby(["pname", "code"])["t"].sum().items():
            if v_ > 0:
                sd_ = PIT_SRC.setdefault(name, {})
                sd_[(p_, c_s)] = sd_.get((p_, c_s), 0.0) + float(v_)
        srcs = (i_.groupby(["pname", "code"])["t"].sum()
                  .sort_values(ascending=False).head(10))
        locs = i_.groupby("Location Dump")["t"].sum().sort_values(ascending=False).head(8)
        PILE_INFO[key] = {
            "pid": root, "name": name, "st": st, "k": colr,
            "o": str(pd.Timestamp(o_).date()), "c": c_, "x": root in LIFE,
            "cls": byc.idxmax() if len(byc) else "",
            "n": int(len(i_)),
            "days": dict(sorted(pdays.items())),
            "srcs": [[p, round(float(v), 1), c] for (p, c), v in srcs.items()],
            "locs": [[l_, round(float(v), 1)] for l_, v in locs.items()],
        }
        if root in piles:
            vs = piles[root]
            PILE_GEO[key] = {"c": vs[-1][7], "rings": [vs[-1][7]], "v": {str(s_[0]): s_[7] for s_ in vs}}
    crushed_sources(PILE_INFO, PIT_SRC)
    stock_ids = set(piles)
    print(f"  stock piles: {len(PILE_INFO)} (C4M originals on the map in the data period + register-only); "
          f"outlines for {len(PILE_GEO)} ({len(stock)} register versions)")
    # every bench-1237 original's C4M lifetime (also the piles created after this build, which the
    # page draws from R4M's live polygon register), version -> original, and each version's own
    # life (which outline was on the map when)
    PLIFE = {str(k): [v[0], v[2]] for k, v in LIFE.items()}
    PVER = {str(v): r for v, r in VER.items() if r in LIFE or r in stock_ids}
    PVLIFE = {str(k): v for k, v in VLIFE.items()}
    # for the page's live window: cube dump id -> original dump area, and each dump area's stockpile links
    PDROOT = {k: v[0] for k, v in vj.get("dumps", {}).items()}
    PDLINK = {}
    for p_, d_, a_, b_ in vj.get("links", []):
        PDLINK.setdefault(str(d_), []).append([VER.get(int(p_), int(p_)), a_, b_])
    ROMDAY = {}
    for d, t in romi.groupby("date")["t"].sum().items():
        ROMDAY[d] = [round(float(t), 1), 0.0]
    for d, t in inn.groupby("date")["t"].sum().items():
        ROMDAY.setdefault(d, [0.0, 0.0])[1] = round(float(t), 1)

    # viewport = the dense pad cluster (polygons within 600 m of the weighted
    # centre), framed on the polygons open in the last 30 days of data
    lo_ = str((last_date - pd.Timedelta(days=ACTIVE_PILE_DAYS)).date())
    recent = {k for k, i in PILE_INFO.items() if i["c"] is None or i["c"] >= lo_}
    cents = {}
    for k, g_ in PILE_GEO.items():
        if recent and k not in recent:
            continue
        cx = sum(c[0] for c in g_["c"]) / len(g_["c"])
        cy = sum(c[1] for c in g_["c"]) / len(g_["c"])
        cents[k] = (cx, cy, 1.0)
    if cents:
        mx = sum(v[0] for v in cents.values()) / len(cents)
        my = sum(v[1] for v in cents.values()) / len(cents)
        core = [p for p, (cx, cy, _) in cents.items() if (cx - mx)**2 + (cy - my)**2 <= 600**2]
        if not core:
            core = list(cents)
        xs = [c[0] for p in core for r in PILE_GEO[p]["rings"] for c in r]
        ys = [c[1] for p in core for r in PILE_GEO[p]["rings"] for c in r]
        ROMBOX = [min(xs) - 100, min(ys) - 100, max(xs) + 100, max(ys) + 100]
    else:
        ROMBOX = [483200, 4860300, 484000, 4861000]
    cov = inn["t"].sum() / romi["t"].sum() * 100 if romi["t"].sum() else 0
    print(f"ore inventory: {len(PILE_INFO)} R4M stock polygons open at some point "
          f"{first_date.date()}..{last_date.date()} ({sum(1 for i in PILE_INFO.values() if i['st'] == 'open')} open now); "
          f"{cov:.0f}% of ROM-pad tonnage assigned to one by C4M (ts_stockpiles); {len(recent)} open in the last "
          f"{ACTIVE_PILE_DAYS} d frame the viewport")

    # ---- flow arcs per month (and 'all') ------------------------------------
    def flows_for(sub):
        f = sub.dropna(subset=["lx", "ly", "dx", "dy"])
        # clip to the map window - a handful of cycles carry bogus GPS fixes
        f = f[f["lx"].between(482_300, 485_500) & f["ly"].between(4_859_400, 4_863_600)
              & f["dx"].between(482_300, 485_500) & f["dy"].between(4_859_400, 4_863_600)]
        g = f.groupby(["pname", "dest", "code"]).agg(
            t=("t", "sum"), x0=("lx", "mean"), y0=("ly", "mean"),
            x1=("dx", "mean"), y1=("dy", "mean"), n=("t", "size"))
        g = g[g["t"] >= FLOW_MIN_T].reset_index()
        return [[r.pname, r.dest, r.code, round(r.t, 1),
                 round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1), int(r.n)]
                for r in g.itertuples()]

    FLOWS = {"all": flows_for(df)}
    for m in months:
        FLOWS[m] = flows_for(df[df["month"] == m])
    print(f"flow arcs: all={len(FLOWS['all'])}")

    # ---- dig/dump points per day (grid-binned) -------------------------------
    def binpts(sub, xc, yc):
        s = sub.dropna(subset=[xc, yc])
        s = s[s[xc].between(482_300, 485_500) & s[yc].between(4_859_400, 4_863_600)]
        if s.empty:
            return []
        gx = (s[xc] / GRID).round().astype(int) * GRID
        gy = (s[yc] / GRID).round().astype(int) * GRID
        g = s.groupby([gx, gy])["t"].sum()
        return [[int(x), int(y), round(t, 1)] for (x, y), t in g.items()]

    DIG, DUMP = {}, {}
    for d, sub in df.groupby("date"):
        DIG[d] = binpts(sub, "lx", "ly")
        DUMP[d] = binpts(sub, "dx", "dy")

    # ---- sankey links per month + all ----------------------------------------
    def sankey_for(sub):
        exr = sub[~(sub["reclaim"] | sub["is_crush"])]
        # Erdene 2026-10-17: show the pit polygon names, not "Other pit polygons".
        # Hundreds of small cuts per month: the biggest TOP_POLYS keep their own
        # name, the rest are grouped by their blast block (name prefix
        # bench_block, e.g. 1210_043), and only what has no block name and is
        # outside the top falls into "Other pit polygons".
        top = exr.groupby("pname")["t"].sum().nlargest(TOP_POLYS).index
        blast = exr["pname"].astype(str).str.extract(BLAST_RE, expand=False)
        tail = ~exr["pname"].isin(top)
        top_b = exr[tail & blast.notna()].groupby(blast[tail & blast.notna()])["t"].sum().nlargest(TOP_BLASTS).index
        pgrp = exr["pname"].where(~tail, "Other pit polygons")
        in_b = tail & blast.isin(top_b)
        pgrp = pgrp.where(~in_b, blast + " \u00b7 other cuts")
        s1 = exr.assign(pg=pgrp).groupby(["pg", "code"])["t"].sum()
        top_piles = exr[exr["is_rom"]].groupby("dest")["t"].sum().nlargest(TOP_PILES).index
        dgrp = exr["dest"].where(~exr["is_rom"] | exr["dest"].isin(top_piles), "Other ROM piles")
        s2 = exr.assign(dg=dgrp).groupby(["code", "dg"])["t"].sum()
        rec = sub[sub["is_crush"]]
        s3 = rec.groupby(["feedlab", "code"])["t"].sum()
        links = []
        for (a, b), t in s1.items():
            if t > 0.5: links.append([0, a, b, round(t, 1)])
        for (a, b), t in s2.items():
            if t > 0.5: links.append([1, a, b, round(t, 1)])
        for (a, b), t in s3.items():
            if t > 0.5: links.append([2, a, "Crusher (mill feed)", round(t, 1), b])
        return links

    SANKEY = {"all": sankey_for(df)}
    for m in months:
        SANKEY[m] = sankey_for(df[df["month"] == m])
    tot_ex = df.loc[~(df["reclaim"] | df["is_crush"]), "t"].sum()
    s1t = sum(l[3] for l in SANKEY["all"] if l[0] == 0)
    s3t = sum(l[3] for l in SANKEY["all"] if l[0] == 2)
    feed_t = df.loc[df["is_crush"], "t"].sum()
    print(f"sankey reconciliation: stage1 {s1t:,.0f} vs ex-reclaim movement {tot_ex:,.0f} | "
          f"stage3 {s3t:,.0f} vs mill feed {feed_t:,.0f}")

    # ---- polygon explorer: per-polygon daily extraction + destinations -------
    exr = df[~df["reclaim"]]
    PDAY = {}
    for (p, d), t in exr.groupby(["pname", "date"])["t"].sum().items():
        PDAY.setdefault(p, {})[d] = round(t, 1)
    PDEST = {}
    for (p, g), t in exr.groupby(["pname", "dest"])["t"].sum().items():
        if t >= 1:
            PDEST.setdefault(p, {})[g] = round(t, 1)
    PSTAT = []
    for p, hauled in exr.groupby("pname")["t"].sum().sort_values(ascending=False).items():
        if p == "(unknown)":
            continue
        cp = cube_p.loc[p] if p in cube_p.index else None
        if isinstance(cp, pd.DataFrame):
            cp = cp.iloc[0]
        init = float(cp["Initial Tonnes"] or 0) if cp is not None else 0
        mnd = float(cp["Mined Tonnes"] or 0) if cp is not None else 0
        sub = exr[exr["pname"] == p]
        au = sub["au_g"].sum() / hauled if hauled else 0
        ag = sub["ag_g"].sum() / hauled if hauled else 0
        cls = sub.groupby("code")["t"].sum().idxmax()
        PSTAT.append({"p": p, "cls": cls, "bench": str(cp["Bench"]) if cp is not None else "",
                      "init": round(init, 1), "mined": round(mnd, 1),
                      "hauled": round(float(hauled), 1),
                      "au": round(float(au), 3), "ag": round(float(ag), 3)})

    # ---- haul efficiency per day ----------------------------------------------
    HAUL = {}
    for d, s in df.groupby("date"):
        t = s["t"].sum()
        w = s["t"].clip(lower=0.001)
        efh = s["Loaded EFH (Km)"].fillna(0)
        HAUL[d] = {
            "t": round(t, 1),
            "tkm": round(float((s["t"] * efh).sum()), 1),
            "dist": round(float(np.average(s["Distance Loaded (m)"].fillna(0), weights=w)), 0),
            "vl": round(float(np.average(s["Loaded Speed (Km/h)"].fillna(0), weights=w)), 1),
            "ve": round(float(np.average(s["Empty Speed (Km/h)"].fillna(0), weights=w)), 1),
            "trucks": int(s["Id Equipment Hauling"].nunique()),
        }

    # ---- hour-of-day heatmap ----------------------------------------------------
    HOURS = {}
    hh = df.groupby(["date", "Hauling Hour"])["t"].sum()
    for (d, h), t in hh.items():
        if 0 <= int(h) <= 23:
            HOURS.setdefault(d, [0] * 24)[int(h)] = round(t, 1)

    # ---- equipment time model (status + hourmeter), split Loading / Hauling ---
    # The equipment dim classifies the fleet authoritatively: Type R4M is
    # Loading (R1250 / HL780XTD-9 / HX520L-T3 = EX/LO units), Hauling (TL875B
    # = TR trucks) or Auxiliar (excluded).
    EQ_DAY, EQ_SMU, EQ_MODELS, EQ_STAT = {}, {}, {}, {}
    try:
        eq = pd.read_parquet(os.path.join(DATA, "equipment.parquet"))[
            ["Id Equipment", "Equipment", "Type R4M", "Fleet Category"]]
        eq = eq[~eq["Equipment"].isin(EXCLUDE_EQUIP)]
        st = pd.read_parquet(os.path.join(DATA, "status.parquet"))
        st = st.merge(eq, left_on="Id Equipment Status", right_on="Id Equipment", how="left")
        st["date"] = st["Date Cube Status"].astype(str).str[:10]
        hm = pd.read_parquet(os.path.join(DATA, "hourmeter.parquet"))
        hm = hm.merge(eq, left_on="Id Equipment Hourmeter", right_on="Id Equipment", how="left")
        hm["date"] = hm["Date Cube Hourmeter"].astype(str).str[:10]
        hm_delta = (hm.groupby(["Type R4M", "Equipment", "date"])["Hourmeter"]
                      .agg(lambda s: s.max() - s.min()))
        hm_delta = hm_delta[(hm_delta > 0.2) & (hm_delta <= 24)]
        for gk, tname in (("load", "Loading"), ("haul", "Hauling")):
            stg = st[st["Type R4M"] == tname]
            EQ_DAY[gk] = {}
            for d, s in stg.groupby("date"):
                tot = s["Total Hours"].sum()
                oop = s["Out of plan"].sum()
                mnt = s["Maint"].sum()
                EQ_DAY[gk][d] = {"sched": round(tot - oop, 1), "maint": round(mnt, 1),
                                 "ready": round(s["Ready"].sum(), 1),
                                 "delay": round(s["Delay"].sum(), 1),
                                 "standby": round(s["Stand by"].sum(), 1)}
            EQ_MODELS[gk] = sorted(stg["Fleet Category"].dropna().unique().tolist())
            # per machine: average hours per day in each dispatch status. Paired
            # with the hourmeter deltas below this is the closest we can get to
            # Erdene's request 07 (motor hours beside the status histogram),
            # which is really a change to R4M's own Fleet Management module.
            EQ_STAT[gk] = {}
            for e, s in stg.groupby("Equipment"):
                nd = s["date"].nunique()
                if not nd:
                    continue
                EQ_STAT[gk][str(e)] = [
                    round(float(s[c].sum()) / nd, 2)
                    for c in ("Ready", "Delay", "Stand by", "Maint", "Out of plan")
                ] + [int(nd)]
            EQ_SMU[gk] = {}
            dg = hm_delta.loc[tname] if tname in hm_delta.index.get_level_values(0) else None
            if dg is not None:
                cover = dg.groupby("Equipment").size().sort_values(ascending=False)
                for e in cover.index:      # every unit with hourmeter coverage
                    EQ_SMU[gk][str(e)] = {d: round(float(v), 1)
                                          for (e2, d), v in dg.items() if e2 == e}
        print(f"equipment time model: load {len(EQ_DAY['load'])} days / "
              f"{len(EQ_SMU['load'])} SMU ({', '.join(EQ_MODELS['load'])}), "
              f"haul {len(EQ_DAY['haul'])} days / {len(EQ_SMU['haul'])} SMU "
              f"({', '.join(EQ_MODELS['haul'])})")
    except Exception as exc:  # noqa: BLE001
        print(f"NOTE: equipment time model skipped ({type(exc).__name__}: {exc})")

    # ---- cycle anatomy (cycle_times) -------------------------------------------
    CYC = {}
    try:
        ct = pd.read_parquet(os.path.join(DATA, "cycle_times.parquet"))
        ct = ct.merge(df[["C4M ID Hauling", "date"]], on="C4M ID Hauling", how="inner")
        SEGS = {
            "Travel empty": ["Cycle Hauling (01) Time Previous Traveling Empty (s)"],
            "Queue & spot": ["Cycle Hauling (02) Time Queue (s)",
                             "Cycle Hauling (03) Time Ready Parking (s)",
                             "Cycle Hauling (04) Time Parking (s)",
                             "Cycle Hauling (05) Time Parked (s)"],
            "Loading": ["Cycle Hauling (06) Time Loading (s)"],
            "Haul loaded": ["Cycle Hauling (07) Time Hauling (s)"],
            "At dump": ["Cycle Hauling (08) Time Waiting (s)",
                        "Cycle Hauling (09) Time Backing (s)",
                        "Cycle Hauling (10) Time Ready Dumping (s)"],
            "Dumping": ["Cycle Hauling (11) Time Dumping (s)"],
        }
        HANG = "Cycle Loading (02) Time Hang (s)"
        allcols = [c for cols in SEGS.values() for c in cols] + [HANG]
        ct[allcols] = ct[allcols].clip(lower=0, upper=1800)  # cap 30 min/segment (parked-overnight artifacts)
        for d, s in ct.groupby("date"):
            CYC[d] = {name: round(float(s[cols].sum(axis=1).mean()) / 60, 2)
                      for name, cols in SEGS.items()}
            CYC[d]["Excavator hang"] = round(float(s[HANG].mean()) / 60, 2)
        tot_min = np.mean([sum(v for k, v in c.items() if k != "Excavator hang") for c in CYC.values()])
        hang_min = np.mean([c["Excavator hang"] for c in CYC.values()])
        print(f"cycle anatomy: {len(CYC)} days, avg cycle {tot_min:.1f} min, avg hang {hang_min:.1f} min")
    except Exception as exc:  # noqa: BLE001
        print(f"NOTE: cycle anatomy skipped ({type(exc).__name__}: {exc})")

    # ---- crew & operator performance -------------------------------------------
    CREWDAY, OPS_HAUL, OPS_LOAD = {}, [], []
    try:
        crew = pd.read_parquet(os.path.join(DATA, "crew.parquet"))[["Id Crew", "Crew"]]
        crew = crew.drop_duplicates("Id Crew")
        emp = pd.read_parquet(os.path.join(DATA, "employee.parquet"))[
            ["Id Employee", "Complete Name"]]
        emp = emp[~emp["Complete Name"].astype(str).str.contains("test", case=False)]
        pr = df.merge(crew, left_on="Id Crew Hauling", right_on="Id Crew", how="left")
        for c, s in pr.dropna(subset=["Crew"]).groupby("Crew"):
            CREWDAY[str(c)] = {d: round(float(v), 1)
                               for d, v in s.groupby("date")["t"].sum().items()}
        QCOLS = ["Cycle Hauling (02) Time Queue (s)",
                 "Cycle Hauling (03) Time Ready Parking (s)",
                 "Cycle Hauling (04) Time Parking (s)",
                 "Cycle Hauling (05) Time Parked (s)"]
        HANGC = "Cycle Loading (02) Time Hang (s)"
        ctq = pd.read_parquet(os.path.join(DATA, "cycle_times.parquet"),
                              columns=["C4M ID Hauling"] + QCOLS + [HANGC])
        ctq[QCOLS + [HANGC]] = ctq[QCOLS + [HANGC]].clip(lower=0, upper=1800)
        ctq["queue_min"] = ctq[QCOLS].sum(axis=1) / 60
        ctq["hang_min"] = ctq[HANGC] / 60
        pr = pr.merge(ctq[["C4M ID Hauling", "queue_min", "hang_min"]],
                      on="C4M ID Hauling", how="left")

        hop = pr.merge(emp, left_on="Id Employee Hauling", right_on="Id Employee",
                       how="inner")
        g = (hop.groupby("Complete Name")
                .agg(days=("date", "nunique"), cycles=("t", "size"),
                     t=("t", "sum"), q=("queue_min", "mean"))
                .sort_values("t", ascending=False).head(30))
        OPS_HAUL = [[n, int(r.days), int(r.cycles), round(float(r.t), 1),
                     round(float(r.cycles / r.days), 1),
                     round(float(r.q), 1) if pd.notna(r.q) else None]
                    for n, r in g.iterrows()]

        lop = pr.merge(emp, left_on="Id Employee Loading", right_on="Id Employee",
                       how="inner")
        lop = lop.assign(passes=lop["Number of passes"].where(lop["Number of passes"] > 0))
        g2 = (lop.groupby("Complete Name")
                 .agg(days=("date", "nunique"), cycles=("t", "size"),
                      t=("t", "sum"), hang=("hang_min", "mean"), p=("passes", "mean"))
                 .sort_values("t", ascending=False).head(30))
        OPS_LOAD = [[n, int(r.days), int(r.cycles), round(float(r.t), 1),
                     round(float(r.hang), 1) if pd.notna(r.hang) else None,
                     round(float(r.p), 1) if pd.notna(r.p) else None]
                    for n, r in g2.iterrows()]
        print(f"crew & operators: {len(CREWDAY)} crews, "
              f"{len(OPS_HAUL)} haul + {len(OPS_LOAD)} loading operators")
    except Exception as exc:  # noqa: BLE001
        print(f"NOTE: crew/operator section skipped ({type(exc).__name__}: {exc})")

    # ---- dig compliance: GPS-detected polygon vs dispatcher-assigned ------------
    DIGC_DAY, DIGC_POLY, DIGC_LOADER = {}, [], []
    try:
        ex2 = df[~df["reclaim"]].copy()   # reclaim loads come from piles, not polygons
        hp = pd.to_numeric(ex2["Polygon HPGPS"], errors="coerce")
        ex2["hp"] = hp.where(hp > 0)
        ex2["cov"] = ex2["hp"].notna() & ex2["Id Polygon"].notna()
        ex2["ok"] = ex2["cov"] & (ex2["hp"].fillna(-1).astype("int64")
                                  == ex2["Id Polygon"].fillna(-2).astype("int64"))
        for d, s in ex2.groupby("date"):
            DIGC_DAY[d] = [round(float(s.loc[s["ok"], "t"].sum()), 1),
                           round(float(s.loc[s["cov"] & ~s["ok"], "t"].sum()), 1),
                           round(float(s.loc[~s["cov"], "t"].sum()), 1)]
        pmap = poly.drop_duplicates("Id Polygon").set_index("Id Polygon")["Polygon"]
        mm = ex2[ex2["cov"] & ~ex2["ok"]].copy()
        mm["gpsname"] = mm["hp"].astype("int64").map(pmap).fillna("(unknown id)")
        ptot = ex2[ex2["cov"]].groupby("pname")["t"].sum()
        rows = []
        for pn, s in mm.groupby("pname"):
            bad_t = float(s["t"].sum())
            top_gps = s.groupby("gpsname")["t"].sum().idxmax()
            share = bad_t / float(ptot.get(pn, bad_t)) * 100
            rows.append([pn, top_gps, round(bad_t, 1), int(len(s)), round(share, 1)])
        DIGC_POLY = sorted(rows, key=lambda r: -r[2])[:15]
        eqn = (pd.read_parquet(os.path.join(DATA, "equipment.parquet"))
                 [["Id Equipment", "Equipment"]].drop_duplicates("Id Equipment"))
        eqn = eqn[~eqn["Equipment"].isin(EXCLUDE_EQUIP)]
        le = ex2[ex2["cov"]].merge(eqn, left_on="Id Equipment Loading",
                                   right_on="Id Equipment", how="left")
        for e, s in le.groupby("Equipment"):
            tt = float(s["t"].sum())
            bt = float(s.loc[~s["ok"], "t"].sum())
            if tt >= 1000:
                DIGC_LOADER.append([str(e), round(bt, 1), round(bt / tt * 100, 1)])
        DIGC_LOADER.sort(key=lambda r: -r[2])
        cov_t = ex2.loc[ex2["cov"], "t"].sum()
        bad_share = mm["t"].sum() / cov_t * 100 if cov_t else 0
        print(f"dig compliance: {bad_share:.1f}% of GPS-covered tonnage off-polygon, "
              f"{len(DIGC_POLY)} worst polygons, {len(DIGC_LOADER)} loaders")
    except Exception as exc:  # noqa: BLE001
        print(f"NOTE: dig compliance skipped ({type(exc).__name__}: {exc})")

    # ---- contour raster ----------------------------------------------------------
    png_path = os.path.join(DATA, "contour_bg.png")
    meta_path = os.path.join(DATA, "contour_bg.json")
    if os.path.exists(png_path) and os.path.exists(meta_path):
        b64 = base64.b64encode(open(png_path, "rb").read()).decode()
        cmeta = json.load(open(meta_path))
        print(f"contour raster embedded ({len(b64)//1024} KB base64)")
    else:
        b64, cmeta = "", {"x0": 482300, "x1": 485500, "y0": 4859400, "y1": 4863600}
        print("WARNING: contour raster missing - run prepare_contour.py")

    payload = {
        "dates": days,
        "months": months,
        "built": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "contour": cmeta,
        # flows/corr/zones/digfp/dumpfp/fprings/dig/dump/weeks fed the corridor map and hours the
        # rhythm heatmap - both removed from the page 2026-10-27 (user), so they are no longer shipped
        "eqday": EQ_DAY, "smu": EQ_SMU, "eqstat": EQ_STAT,
        "eqmodels": EQ_MODELS, "cyc": CYC,
        "crewday": CREWDAY, "opshaul": OPS_HAUL, "opsload": OPS_LOAD,
        "digcday": DIGC_DAY, "digcpoly": DIGC_POLY, "digcloader": DIGC_LOADER,
        "pilegeo": PILE_GEO, "pileinfo": PILE_INFO, "pver": PVER, "plife": PLIFE, "pvlife": PVLIFE, "droot": PDROOT, "dlink": PDLINK, "stockbench": 1237, "romday": ROMDAY, "rombox": ROMBOX,
        "sankey": SANKEY,
        "pstat": PSTAT, "pday": PDAY, "pdest": PDEST,
        "design": DESIGN, "plevel": PLEVEL,
        "haul": HAUL,
    }
    return payload, b64


if __name__ == "__main__":
    print("build_atlas.py is a library now - run build_combined.py instead")
