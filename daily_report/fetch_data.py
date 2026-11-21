"""Fetch all report/atlas source data into daily_report/data/.

Everything comes from r4m.example.local (no other host):

1. R4M cube export API  -> data/<name>.parquet   (14 datasets)
2. R4M app grades endpoint (the one behind the R4M Aurora "Grades / Leyes"
   report) -> data/r4m_grades.json
      GET /duckdb/sensor/getGradeBlockAndPolygonData/?startDate=&endDate=
   returns, per hauling cycle, the source polygon's registered grades
   {"grades": {"au", "ag"}} (BOTH metals - the cube's polygon_grades parquet
   export only carries one grade per polygon, almost always Ag) plus the
   block-model grades of the dump position ("block" list, unused here).
   Grades are constant per Id Polygon (verified on 28k cycles), so the file
   keeps a per-polygon map {Id Polygon: [Au, Ag]}.  The endpoint only lists
   cycles whose polygon has grades, so it is fetched month by month for the
   mine year and gzip-encoded (~15 MB/yr raw -> ~1.2 MB on the wire).
3. R4M HPGPS backend polygon register (the endpoints behind the embedded
   "HPGPS" / "Adherence" fronts, /fronts/r4m_hpgps/) -> data/r4m_polygons.json
      GET /dimensions/polygon/getAllPolygonData/            (currently OPEN polygons)
      GET /dimensions/polygon/getAllPolygonDataByDate/?dateIni=&dateFin=
                                                            (polygons CLOSED in the window)
   Each row: {id (== cube Id Polygon), name, nivel (bench), coors: [[lat, lon], ...],
   actualmined, percentagemined}. Rings are WGS84 and are converted here to
   UTM zone 47N (the mine grid used by every other coordinate).  Open + closed
   since Jan 1 covers ~81% of the year's hauled tonnes (polygons closed before
   HPGPS went live on 2026-05-12 are gone for good).
   The register carries no dates, so each polygon's CLOSE date is recovered by
   asking the closed-in-window endpoint one day at a time (dateIni=d,
   dateFin=d+1 -> polygons closed on d; a same-day window returns nothing).
   Stored per polygon as "c" (last day it was closed; absent = never closed in
   the fetched range) next to "k", the polygon's C4M display colour.

Auth: since ~2026-09 R4M needs a logged-in session (cookie + DPoP). Start
`python serve_local.py --login` and point this script at it:
      set R4M_HOST=http://127.0.0.1:8123      (PowerShell: $env:R4M_HOST=...)
The proxy adds the session to every /cube/, /duckdb/ and /dimensions/ call.

Run:  python fetch_data.py
"""
import datetime as dt
import gzip
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

HOST = os.environ.get("R4M_HOST", "https://r4m.example.local").rstrip("/")
BASE = HOST + "/cube/dynamic/api/export"
GRADES = HOST + "/duckdb/sensor/getGradeBlockAndPolygonData/"
POLY_OPEN = HOST + "/dimensions/polygon/getAllPolygonData/"
POLY_CLOSED = HOST + "/dimensions/polygon/getAllPolygonDataByDate/"
CLOSE_FROM = dt.date(2026, 5, 1)   # HPGPS went live 2026-05-12: no closures recorded before
UTM_ZONE = 47   # R4M MAP_CONFIG: zone 47T (northern hemisphere)
YEAR = 2026  # mine operating year; single place to roll forward
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TIMEOUT = 300

DATASETS = [
    ("facts",      "production",      {"year": YEAR, "month": "all"}),
    ("facts",      "sensor_data",     {"year": YEAR, "month": "all"}),
    ("dimensions", "polygon",         {}),
    ("dimensions", "polygon_grades",  {}),
    ("dimensions", "location_dump",   {"year": YEAR}),
    ("dimensions", "location_load",   {"year": YEAR}),
    ("dimensions", "material",        {}),
    ("dimensions", "equipment",       {}),
    ("facts",      "status",          {"year": YEAR, "month": "all"}),
    ("facts",      "cycle_times",     {"year": YEAR, "month": "all"}),
    ("facts",      "hourmeter",       {"year": YEAR, "month": "all"}),
    ("dimensions", "status_detail",   {}),
    ("dimensions", "crew",            {}),
    ("dimensions", "employee",        {}),
]

# Internal host uses a self-signed cert; disable verification.
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

# Unattended runs (the nightly job on the R4M VM): --login-file PATH (or R4M_LOGIN_FILE) = a mode-600
# file with two lines, R4M username and password, written by the account owner on the server. The
# fetch then logs in like the R4M app (r4m_session cookie + per-request DPoP proof, serve_local's
# R4MSession). The password is never printed.
SESSION = None


def _open(req):
    """urlopen, or through the signed R4M session when a login file was given."""
    if SESSION is None:
        return urllib.request.urlopen(req, context=_SSL, timeout=TIMEOUT)
    for attempt in (0, 1):
        r = urllib.request.Request(req.full_url, headers={k: v for k, v in req.header_items() if k.lower() != "dpop"})
        r.add_header("DPoP", SESSION.proof("GET", r.full_url))
        try:
            return SESSION.opener.open(r, timeout=TIMEOUT)
        except urllib.error.HTTPError as e:
            if e.code != 401 or attempt or not SESSION.login():
                raise


def _login(path):
    global SESSION
    import serve_local
    with open(path, encoding="utf-8") as fh:
        lines = [ln.rstrip("\r\n") for ln in fh]
    if len(lines) < 2 or not lines[0] or not lines[1]:
        sys.exit(f"{path}: expected two lines (username, password)")
    s_ = serve_local.R4MSession(lines[0], lines[1])
    if not s_.login():
        sys.exit("R4M login failed - nothing fetched")
    SESSION = s_


def export(api_type, name, **params):
    query = {"type": api_type, "name": name, "format": "parquet", **params}
    qs = "&".join(f"{k}={v}" for k, v in query.items())
    with _open(urllib.request.Request(f"{BASE}?{qs}")) as resp:
        data = resp.read()
    if data[:4] != b"PAR1":
        raise RuntimeError(f"{name}: response is not parquet (got {data[:16]!r})")
    return data


def month_windows(year, until=None):
    """[(start, end)] calendar months of `year`, clamped to `until` (default: tomorrow)."""
    until = until or (dt.date.today() + dt.timedelta(days=1))
    out = []
    for m in range(1, 13):
        start = dt.date(year, m, 1)
        if start > until:
            break
        end = (dt.date(year + 1, 1, 1) if m == 12 else dt.date(year, m + 1, 1)) - dt.timedelta(days=1)
        out.append((start, min(end, until)))
    return out


def fetch_r4m_grades(year=YEAR):
    """Per-polygon [Au, Ag] from the R4M app grades endpoint (month-chunked, gzip)."""
    pmap, cycles, months = {}, 0, 0
    for start, end in month_windows(year):
        req = urllib.request.Request(
            f"{GRADES}?startDate={start}&endDate={end}",
            headers={"Accept": "application/json", "Accept-Encoding": "gzip"})
        with _open(req) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
        rows = json.loads(raw).get("polygon") or []
        for r in rows:
            pid = r.get("Id Polygon")
            g = r.get("grades") or {}
            if pid is None:
                continue
            cur = pmap.setdefault(int(pid), [None, None])
            if cur[0] is None and g.get("au") is not None:
                cur[0] = float(g["au"])
            if cur[1] is None and g.get("ag") is not None:
                cur[1] = float(g["ag"])
        cycles += len(rows)
        months += 1
    return {"source": GRADES, "fetched": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "year": year, "months": months, "cycles": cycles,
            "polygon": {str(k): v for k, v in sorted(pmap.items())}}


def ll_to_utm(lat, lon, zone=UTM_ZONE):
    """WGS84 lat/lon (deg) -> UTM easting/northing (m), northern hemisphere. Standard
    transverse-Mercator series (mm-level), no external dependency."""
    import math
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    phi, lam = math.radians(lat), math.radians(lon) - lon0
    sp, cp = math.sin(phi), math.cos(phi)
    N = a / math.sqrt(1 - e2 * sp * sp)
    T = (sp / cp) ** 2
    C = ep2 * cp * cp
    A = cp * lam
    M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi)
             - (35 * e2 ** 3 / 3072) * math.sin(6 * phi))
    E = 500000 + k0 * N * (A + (1 - T + C) * A ** 3 / 6
                           + (5 - 18 * T + T * T + 72 * C - 58 * ep2) * A ** 5 / 120)
    Nn = k0 * (M + N * (sp / cp) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * A ** 4 / 24
                                    + (61 - 58 * T + T * T + 600 * C - 330 * ep2) * A ** 6 / 720))
    return round(E, 2), round(Nn, 2)


def _get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Accept-Encoding": "gzip"})
    with _open(req) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return json.loads(raw)


def fetch_r4m_polygons(year=YEAR):
    """Polygon boundaries (UTM rings) for open + closed polygons from the HPGPS backend."""
    until = dt.date.today() + dt.timedelta(days=1)
    open_rows = _get_json(POLY_OPEN)
    closed_rows = _get_json(f"{POLY_CLOSED}?dateIni={year - 1}-01-01&dateFin={until}")
    polys = {}

    def add(rows, status):
        for p in rows or []:
            try:
                pid = int(p.get("id"))
            except (TypeError, ValueError):
                continue
            if pid in polys:            # open register wins over the closed history
                continue
            ring = []
            for c in p.get("coors") or []:
                if isinstance(c, (list, tuple)) and len(c) >= 2 and c[0] is not None and c[1] is not None:
                    ring.append(list(ll_to_utm(float(c[0]), float(c[1]))))
            polys[pid] = {"n": str(p.get("name") or ""), "b": p.get("nivel"), "s": status,
                          "k": str(p.get("color") or ""),
                          "m": float(p.get("actualmined") or 0), "r": ring}

    add(open_rows, "open")
    add(closed_rows, "closed")
    # close date per polygon: one closed-in-window call per day
    d, n_days = CLOSE_FROM, 0
    while d < until:
        for p in _get_json(f"{POLY_CLOSED}?dateIni={d}&dateFin={d + dt.timedelta(days=1)}") or []:
            try:
                pid = int(p.get("id"))
            except (TypeError, ValueError):
                continue
            if pid in polys:
                polys[pid]["c"] = str(d)          # ascending loop: keeps the LAST close
        d += dt.timedelta(days=1)
        n_days += 1
    print(f"  close dates: {sum(1 for v in polys.values() if 'c' in v)} polygons over {n_days} daily windows")
    n_ring = sum(1 for v in polys.values() if len(v["r"]) >= 3)
    return {"source": [POLY_OPEN, POLY_CLOSED], "fetched": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "zone": f"{UTM_ZONE}N", "open": len(open_rows or []), "closed": len(closed_rows or []),
            "with_ring": n_ring, "polygons": {str(k): v for k, v in sorted(polys.items())}}


def main():
    lf = os.environ.get("R4M_LOGIN_FILE")
    if "--login-file" in sys.argv[1:]:
        lf = sys.argv[sys.argv.index("--login-file") + 1]
    if lf:
        _login(os.path.expanduser(lf))
    os.makedirs(DATA_DIR, exist_ok=True)
    failures = 0
    for api_type, name, params in DATASETS:
        try:
            blob = export(api_type, name, **params)
            path = os.path.join(DATA_DIR, f"{name}.parquet")
            with open(path, "wb") as fh:
                fh.write(blob)
            print(f"  OK  {name:<16} {len(blob):>10,} bytes")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FAIL {name:<16} {type(exc).__name__}: {exc}")
    try:
        grades = fetch_r4m_grades()
        with open(os.path.join(DATA_DIR, "r4m_grades.json"), "w", encoding="utf-8") as fh:
            json.dump(grades, fh, ensure_ascii=False)
        n_au = sum(1 for v in grades["polygon"].values() if v[0] is not None)
        print(f"  OK  r4m_grades.json  {len(grades['polygon'])} polygons ({n_au} with Au) "
              f"from {grades['cycles']:,} graded cycles / {grades['months']} months")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"  FAIL r4m_grades.json {type(exc).__name__}: {exc}")
    try:
        geo = fetch_r4m_polygons()
        with open(os.path.join(DATA_DIR, "r4m_polygons.json"), "w", encoding="utf-8") as fh:
            json.dump(geo, fh, ensure_ascii=False)
        print(f"  OK  r4m_polygons.json  {geo['open']} open + {geo['closed']} closed polygons, "
              f"{geo['with_ring']} with a boundary ring (UTM {geo['zone']})")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"  FAIL r4m_polygons.json {type(exc).__name__}: {exc}")
    stale = os.path.join(DATA_DIR, "polygons.json")   # old GI register export
    if os.path.exists(stale):
        os.remove(stale)
        print("  removed data/polygons.json (GI register no longer used)")
    if failures:
        print(f"\n{failures} fetch(es) failed.", file=sys.stderr)
        sys.exit(1)
    print(f"\nDone -> {DATA_DIR}")


if __name__ == "__main__":
    main()
