-- Speed profile per shift date x shift x truck x load state x road-grade band, from raw GPS
-- telemetry: seconds moving, peak / p99 speed and seconds above 30/35/40/45/50 km/h.
-- Grade bands (|GPS grade| %%): 0 = < 6 (or stationary), 1 = 6-8, 2 = 8-10, 3 = 10-12, 4 = >= 12, so the
-- page can treat "steep" as >= 6, 8, 10 or 12 %% without re-querying (band 4 added 2026-10-16). Same grade method as
-- telemetry_episodes.sql. Period: shift dates %(date_from)s .. %(date_to)s (shift day starts %(shift_start)s:00).
with per as (
  select (%(date_from)s::date + make_interval(hours => %(shift_start)s)) as t0,
         (%(date_to)s::date + interval '1 day' + make_interval(hours => %(shift_start)s)) as t1
),
h as (
  select h.id_equipo, h.tiem_creac, h.frecuencia, h.velocidad, h.isload, h.xcoor, h.ycoor, h.zcoor
  from public.ta_datacamion_historic h, per
  where h.tiem_creac >= per.t0 - interval '1 hour' and h.tiem_creac < per.t1
    and cardinality(h.velocidad) > 0
),
s as (
  select h.id_equipo, h.frecuencia,
         h.tiem_creac + make_interval(secs => (u.ord - 1) * h.frecuencia) as ts,
         u.vel / 100.0 as speed, u.isl as is_loaded, u.x / 100.0 as x, u.y / 100.0 as y, u.z / 100.0 as z
  from h
  cross join lateral unnest(h.velocidad, h.isload, h.xcoor, h.ycoor, h.zcoor) with ordinality as u(vel, isl, x, y, z, ord)
  where u.vel is not null and u.x is not null and u.y is not null and u.z is not null
),
w as (
  select s.*,
         lag(x,  %(grade_window)s) over eq as x0, lead(x, %(grade_window)s) over eq as x1,
         lag(y,  %(grade_window)s) over eq as y0, lead(y, %(grade_window)s) over eq as y1,
         lag(z,  %(grade_window)s) over eq as z0, lead(z, %(grade_window)s) over eq as z1
  from s
  window eq as (partition by id_equipo order by ts)
),
g as (
  select w.*,
         abs(case when sqrt((x1 - x0)^2 + (y1 - y0)^2) >= 15
                  then 100.0 * (z1 - z0) / sqrt((x1 - x0)^2 + (y1 - y0)^2) end) as grade
  from w, per where ts >= per.t0 and ts < per.t1
),
s2 as (
  select g.*,
         (ts - make_interval(hours => %(shift_start)s))::date as shift_date,
         case when extract(hour from ts) >= %(shift_start)s
               and extract(hour from ts) <  %(shift_start)s + 12 then 'DS' else 'NS' end as shift,
         case when grade is null or grade < 6 then 0 when grade < 8 then 1 when grade < 10 then 2 when grade < 12 then 3 else 4 end as grade_band
  from g
)
select
  shift_date::text as shift_date, shift, e.nombre as equipment, s2.is_loaded, s2.grade_band,
  count(*) * max(frecuencia)                                   as sec_total,
  count(*) filter (where speed > 1) * max(frecuencia)         as sec_moving,
  max(speed)                                                   as max_kmh,
  round((percentile_cont(0.99) within group (order by speed))::numeric, 1) as p99_kmh,
  round((avg(speed) filter (where speed > 1))::numeric, 1)    as avg_moving_kmh,
  count(*) filter (where speed > 30) * max(frecuencia)        as sec_gt30,
  count(*) filter (where speed > 35) * max(frecuencia)        as sec_gt35,
  count(*) filter (where speed > 40) * max(frecuencia)        as sec_gt40,
  count(*) filter (where speed > 45) * max(frecuencia)        as sec_gt45,
  count(*) filter (where speed > 50) * max(frecuencia)        as sec_gt50
from s2
left join public.ts_equipos e on e.id = s2.id_equipo
group by 1, 2, 3, 4, 5
order by 1, 2, 3, 4, 5;
