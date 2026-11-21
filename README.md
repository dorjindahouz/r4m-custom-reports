# R4M custom reports: Erdene Mongol, Bayan Khundii

*Español: [README.es.md](README.es.md)*

These are the report pages Erdene added to **R4M Aurora**, under the menu **Safety Reports → CustomReport**. Each page is a single
self-contained HTML file built by Python from the R4M cube and the C4M database. The files are served from the R4M app VM. This repo holds
all of the code: no data, no built pages and no credentials.

> **Public version.** Site data is not included: `Report Inputs.xlsx` is a blank template, the logo is a placeholder, and the mine
> contour map, the reader's guide and internal notes are left out. Server addresses, host names and the login name below are
> placeholders (`192.0.2.x`, `*.example.local`, `deploy`).

## Pages

| Page (file in `/opt/R4M/storage/www/r4m_custom_report/`) | Content | Data | Rebuilt |
|---|---|---|---|
| `daily_report_v3.html` | Tabs: **Master Report** · **Daily Report & Mine Atlas** · **3D Dig Viewer** · **Over-speed** · **Operator KPI** | R4M cube, R4M HPGPS polygons, C4M polygon versions and stockpile links | cron 07:40 |
| `overspeed_report.html` | Over-speed events against the mine policy, 40 km/h (30 km/h on steep roads) | C4M 2 s truck GPS (`ta_datacamion_historic`) | cron 10:30 |
| `operator_kpi.html` | Shift sheet with ranked operators, operator cards, shift KPI PDF, checklist PDF | C4M cycles, statuses, logins, checklists + the over-speed events | cron 10:45 and the **Refresh data** button |
| `published_inputs.json` | Plan / targets / budget / survey entered in the report's Inputs panel | written by the publish service | on **Publish inputs** |

The Over-speed and Operator KPI tabs of the daily report are iframes that load the two other pages from the same folder. URLs:
`https://r4m.example.local/r4m_custom_report/<file>`; the R4M menu embeds `/fronts/r4m_custom_report/daily_report_v3.html`.

## How it works

```
C4M DB 192.0.2.15 (ControlSenseDB) --SSH + sudo psql, SELECT only--> fetch_*.py --+
R4M cube / HPGPS API (login + DPoP) ----------------> daily_report/fetch_data.py --+--> build_*.py --> self-contained HTML
                                                                                              |   (code + baked snapshot)
                                                                                              v
                                                             /opt/R4M/storage/www/r4m_custom_report/  (R4M app VM 192.0.2.18)
In the browser, inside R4M: the daily report reads the cube live with the viewer's own R4M session (cookie + DPoP signed with
Aurora's key in IndexedDB). Off R4M, or when that fails, it shows the baked snapshot.
Inputs panel "Publish inputs" / Operator KPI "Refresh data" --> gateway --> publish_server.py (172.18.0.1:8790)
```

## On the R4M app VM (192.0.2.18, SSH user `deploy`)

| What | Where |
|---|---|
| Code, venv, data caches, logs | `~/r4m_overspeed/` (`daily_report/`, `overspeed/`, `operator_kpi/`, `venv/`, `logs/`) |
| C4M login for the fetches | `~/r4m_overspeed/.env` (C4M_DB_* only, mode 600, written by `overspeed/server/install_server.py`) |
| R4M login for the cube fetch | `~/.config/r4m_custom_report/r4m_login` (2 lines: user, password; mode 600; written by the account owner, never by a script). Without it the nightly job rebuilds from the cached cube. |
| Publish key (also the closed-month password) | `~/.config/r4m_custom_report/publish.key` (read on every request; overwrite to change it) |
| Publish / refresh service | `~/server/publish_server.py`, systemd **user** unit `r4m-custom-report-publish` (linger on) |
| Cron (server time UTC+8) | `40 7` `daily_report/server/refresh_daily_report.sh` · `30 10` `overspeed/server/refresh_overspeed.sh` · `45 10` `operator_kpi/server/refresh_operator_kpi.sh` |
| Gateway routes (R4M gateway manager, `config.db`) | `/r4m_custom_report/publish` (exact) and `/r4m_custom_report/refresh` (prefix_stop) → service `custom_report_publish` → `172.18.0.1:8790`; ufw allows 8790/tcp from 172.18.0.0/16 |
| Backups | nightly job keeps the last 7 `daily_report_v3.html.bak-*-nightly`; every publish is kept in `plan_history/` |

Each job logs to `~/r4m_overspeed/logs/<job>_<date>.log`. A failed build leaves the served page untouched. More detail on the service is in
[daily_report/server/README_publish.md](daily_report/server/README_publish.md).

## Changing a report

**The nightly jobs build from the server's copy of the code.** If you deploy only a built page, the next night's job rebuilds from the old code
and undoes your change. After any code change:

```bash
cp .env.example .env                      # once; fill in the R4M_APP_* and C4M_DB_* logins
pip install -r requirements.txt
python daily_report/server/install_daily_refresh.py --no-run     # upload daily report code (never --seed-data: it overwrites the server's newer data)
python overspeed/server/install_server.py --no-run --skip-pip    # upload over-speed + operator KPI code, re-write the cron lines
# rebuild now instead of waiting for the night (on the VM):
bash ~/r4m_overspeed/daily_report/server/refresh_daily_report.sh
```

## Building on a PC

```bash
# Daily report: needs daily_report/data/ (cube snapshot + C4M polygon versions)
python daily_report/serve_local.py --login              # R4M login proxy on 127.0.0.1:8123 (asks for the password)
R4M_HOST=http://127.0.0.1:8123 python daily_report/fetch_data.py
python daily_report/fetch_c4m_polygon_versions.py
python daily_report/build_combined.py                    # -> daily_report/daily_report_v3.html (about 5.5 MB; a few minutes)

python overspeed/build_overspeed.py --fetch              # -> overspeed/overspeed_report.html
python operator_kpi/build_operator_kpi.py --fetch        # -> operator_kpi/operator_kpi.html
python overspeed/deploy_r4m.py --only daily overspeed opkpi   # upload built pages directly (backs up the server copy first)
```

Python 3 with `requirements.txt`. The fetch scripts cache per day under `data/days/`, so later runs only pull new days.

## Rules the numbers follow

- **Shift day** 07:00 → 07:00: DS 07–19, NS 19–07. Checklists use a 06:20 day, because forms are filed before the shift change.
- **Mined** = loaded in the pit. Rehandle (loads from a stockpile or dump zone) is excluded from Mined and Total Movement.
- **Mill feed** = dump location `crush|үйлдвэр`. The crusher is fed from the 1237_ finger stockpiles.
- **Master Report**: sections 4 (mining), 5 (ROM) and 7 (mill feed) only. TODAY / MTD / QTD / YTD columns; plan from `inputs.budget`.
  Closed months are locked behind the publish key.
- **Stockpiles**: piles are grouped by the C4M *original* polygon id (every C4M edit writes a new `ts_poligono` version). Tonnes dumped into a
  pile follow C4M's dump-area → stockpile link (`ts_stockpiles`) at the time of the dump.
- **3D Dig Viewer**: the planned floor is `ts_poligono.level_real` (the planners' decimal level) and the block is 2.5 m high. The as-dug floor
  comes from the bucket dig points. EX215's digging from 2026-10-30 08:00 to 2026-11-14 13:00 is left out, because its bucket inclinometer
  was dead (`BAD_TIP` in `dig3d_template.py`; add an entry there whenever a shovel's bucket sensor fails).
- **Over-speed**: 40 km/h, or 30 km/h where the GPS road grade is ≥ 10 %. An event lasts ≥ 8 s with an average ≥ 2 km/h over the limit, and
  "over by" = average − limit. Peak speeds are not shown. Events are attributed to the operator logged in on the truck (telemetry `operator_login`).
- **Operator KPI**: ranks within the shift per KPI, with no combined score. Tonnes are nominal (52.8 t per load; the trucks have no scale).

## Repo map

| Path | What |
|---|---|
| `daily_report/build_combined.py` | Entry point: builds `daily_report_v3.html` from the modules below |
| `build_report.py` · `master_template.py` · `xlsx_template.py` · `manual_template.py` · `notes_template.py` · `customize_template.py` | Daily report tables and charts, Master Report, Inputs workbook import/export, manual series, engineering notes, show/hide/reorder layer |
| `build_atlas.py` · `atlas_template.py` | Mine Atlas sections (life-cycle, polygon depletion, dig compliance, ROM pad stockpiles, equipment, crews, cycle, haul) |
| `dig3d_template.py` | 3D Dig Viewer (three.js): date + shift picker, as-dug floor vs planned block, DXF/CSV exports |
| `overspeed_sheet.py` · `operator_kpi_sheet.py` | The iframe tabs for the two C4M pages |
| `fetch_data.py` · `serve_local.py` · `fetch_c4m_polygon_versions.py` | R4M cube/HPGPS fetch, R4M login proxy (DPoP), C4M polygon versions + stockpile links |
| `daily_report/server/` | Nightly job, installer, publish/refresh service |
| `overspeed/` | Over-speed page; also `db.py` / `env.py` (shared C4M + `.env` access) and `deploy_r4m.py`. See [overspeed/README.md](overspeed/README.md) |
| `operator_kpi/` | Operator KPI page. See [operator_kpi/README.md](operator_kpi/README.md) |
| `Report Inputs.xlsx`, `build_inputs_workbook.py`, `r4m-design-schema.css` | Inputs workbook (blank template) and shared CSS used by the builds |

Bundled third-party files: three.js (MIT), hyparquet (MIT), Rubik font (OFL).

## Remaining work

- **3D Dig Viewer.** The as-dug outline and floor have not yet been checked against a survey pickup.
- **ROM balances** (`romState` in `build_report.py`). A manual balance (`romadj`) for a pile with no receipts is ignored, and piles that a
  survey leaves out are not set to zero. Fix both before surveys are used to reset the balances.
- **Tests.** There is no automated test suite; changes were checked with one-off browser scripts.
- **`publish_server.py`** (cosmetic). `/refresh/status?job=overspeed` can show the operator KPI log tail, because the log names share a prefix.
