"""Read-only discovery of the C4M over-speed data: prints what schema_notes.md documents.

Run:  python discover_schema.py [--pattern REGEX] [--db ControlSenseDB]
Searches every non-system schema for tables/columns whose name matches the pattern, then
describes the speed-limit register, the segment limits, the telemetry table and the
dimension tables used by sql/*.sql. Nothing is written to the database.
"""
import argparse

import pandas as pd

import db

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_colwidth", 120)

DEFAULT_PATTERN = r"veloc|speed|exces|limit|alert|alarm|infrac|overspeed"


def q(sql, **params):
    try:
        return db.run_query(sql, params or None)
    except Exception as e:  # noqa: BLE001
        print("  ERROR:", str(e).splitlines()[0][:200])
        return pd.DataFrame()


def section(title):
    print("\n" + "=" * 100 + f"\n{title}\n" + "=" * 100)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pattern", default=DEFAULT_PATTERN)
    ap.add_argument("--db", default="ControlSenseDB")
    a = ap.parse_args()

    print("connection:", db.connect())
    print("databases:", q("select datname from pg_database where not datistemplate order by 1").iloc[:, 0].tolist())
    db.switch_db(a.db)
    print("server timezone:", q("show timezone").iloc[0, 0], "| now:", q("select now()").iloc[0, 0])

    section(f"Tables / columns matching /{a.pattern}/i in {a.db}")
    print(q("""
        select c.table_schema, c.table_name, c.column_name, c.data_type, coalesce(s.n_live_tup, 0) rows_est
        from information_schema.columns c
        left join pg_stat_user_tables s on s.schemaname = c.table_schema and s.relname = c.table_name
        where c.table_schema not in ('pg_catalog', 'information_schema')
          and (c.column_name ~* %(p)s or c.table_name ~* %(p)s)
        order by rows_est desc, 1, 2, 3""", p=a.pattern).to_string())

    section("Speed Limit Register: public.ta_speed_limits_exceeded (view en_schm.at_speed_limits_exceeded)")
    print(q("select regexp_replace(pg_get_viewdef('en_schm.at_speed_limits_exceeded'::regclass, true), '\\s+', ' ', 'g') v").iloc[0, 0])
    print(q("""select count(*) n, count(tiem_elimin) deleted, min(tiemp_inicio) first_event, max(tiemp_inicio) last_event
               from public.ta_speed_limits_exceeded""").to_string())
    print(q("""select date_trunc('month', tiemp_inicio)::date month, count(*) n
               from public.ta_speed_limits_exceeded group by 1 order by 1""").to_string())

    section("Segment limits: public.tp_tramosstat (x100) + change log public.ta_limitesvelocidad")
    print(q("""select limitevelcod lld, limitevelcdo ldl, limiteveldod eld, limitevelddo edl, count(*) segments
               from public.tp_tramosstat where tiem_elimin is null group by 1, 2, 3, 4 order by 5 desc""").to_string())
    print(q("select * from public.ta_limitesvelocidad order by id").to_string())

    section("Telemetry: public.ta_datacamion_historic (1 row per equipment-hour, 2 s arrays, speed x100)")
    print(q("""select count(*) rows, min(tiem_creac) first_hour, max(tiem_creac) last_hour,
                      max(cardinality(velocidad)) samples_per_row, max(frecuencia) frecuencia_s
               from public.ta_datacamion_historic""").to_string())
    print(q("""with u as (select v.vel, v.isl, v.tr from public.ta_datacamion_historic h,
                          unnest(h.velocidad, h.isload, h.tramosids) v(vel, isl, tr)
                          where h.tiem_creac > now() - interval '7 days')
               select isl loaded, (tr <> -1) on_segment, count(*) samples, max(vel) / 100.0 max_kmh,
                      count(*) filter (where (isl and vel > 5000) or (not isl and vel > 6000)) over_mine_limit
               from u group by 1, 2 order by 1, 2""").to_string())

    section("Dimensions")
    print(q("select id, nombre, alias, id_flota from public.ts_equipos where tiem_elimin is null order by nombre").to_string())
    print(q("select id, fleet, main_fleet_id from public.fleets order by id").to_string())
    print(q("select id_guardias, nombre from public.ta_guardias where tiem_elimin is null order by 1").to_string())
    print(q("select id_turnos, nombre, shortname, time_start::time start, time_end::time stop from public.ts_turnos where tiem_elimin is null order by 1").to_string())


if __name__ == "__main__":
    main()
