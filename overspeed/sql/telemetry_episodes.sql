-- Over-speed EPISODES derived from raw GPS telemetry (ta_datacamion_historic, 2 s samples)
-- against the MINE POLICY: %(limit_flat)s km/h on normal roads, %(limit_steep)s km/h on steep roads.
--
-- Steepness comes from the GPS track itself (C4M's configured segment limits are 50/60 and most
-- driving is off any defined segment): for every sample the road grade is the elevation change
-- over the horizontal distance travelled between %(grade_window)s samples before and after
-- (±%(grade_window)s × 2 s). A sample is "steep" when |grade| >= %(steep_pct)s %%; stationary samples
-- (< 15 m travelled in the window) have no grade and count as flat.
--
-- Consecutive over-limit samples (gap <= 4 s, same limit) form one episode; episodes shorter than
-- %(min_dur)s s are dropped as GPS noise. Period: shift dates %(date_from)s .. %(date_to)s
-- (shift day starts at %(shift_start)s:00).
with per as (
  select (%(date_from)s::date + make_interval(hours => %(shift_start)s)) as t0,
         (%(date_to)s::date + interval '1 day' + make_interval(hours => %(shift_start)s)) as t1
),
h as (
  select h.id, h.id_equipo, h.tiem_creac, h.frecuencia,
         h.velocidad, h.isload, h.tramosids, h.id_trabajador, h.xcoor, h.ycoor, h.zcoor
  from public.ta_datacamion_historic h, per
  where h.tiem_creac >= per.t0 - interval '1 hour' and h.tiem_creac < per.t1
    and cardinality(h.velocidad) > 0
),
s as (
  select h.id_equipo,
         h.tiem_creac + make_interval(secs => (u.ord - 1) * h.frecuencia) as ts,
         u.vel / 100.0 as speed, u.isl as is_loaded, u.tr as id_segment, u.wk as id_worker,
         u.x / 100.0 as x, u.y / 100.0 as y, u.z / 100.0 as z
  from h
  cross join lateral unnest(h.velocidad, h.isload, h.tramosids, h.id_trabajador, h.xcoor, h.ycoor, h.zcoor)
       with ordinality as u(vel, isl, tr, wk, x, y, z, ord)
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
         case when sqrt((x1 - x0)^2 + (y1 - y0)^2) >= 15
              then 100.0 * (z1 - z0) / sqrt((x1 - x0)^2 + (y1 - y0)^2) end as grade
  from w, per where ts >= per.t0 and ts < per.t1
),
s2 as (
  select g.*,
         (abs(grade) >= %(steep_pct)s) is true as is_steep,
         case when (abs(grade) >= %(steep_pct)s) is true then %(limit_steep)s else %(limit_flat)s end as lim
  from g
),
o as (
  select * from s2 where speed > lim
),
b as (
  select *, case when ts - lag(ts) over (partition by id_equipo order by ts) <= interval '4 seconds'
                  and lim = lag(lim) over (partition by id_equipo order by ts)
                 then 0 else 1 end as brk
  from o
),
ep as (
  select *, sum(brk) over (partition by id_equipo order by ts rows unbounded preceding) as ep_no
  from b
),
agg as (
  select id_equipo, ep_no,
         min(ts) as t_start, max(ts) as t_end,
         max(speed) as max_speed, round(avg(speed)::numeric, 1) as avg_speed,
         min(lim) as lim, bool_or(is_steep) as is_steep, bool_or(is_loaded) as is_loaded,
         round(avg(abs(grade))::numeric, 1) as grade_pct,
         count(*) as n_samples,
         mode() within group (order by id_segment) as id_segment,
         mode() within group (order by id_worker)  as id_worker,
         (array_agg(x order by speed desc))[1] as x,
         (array_agg(y order by speed desc))[1] as y,
         (array_agg(z order by speed desc))[1] as z
  from ep group by id_equipo, ep_no
)
select
  to_char(a.t_start, 'YYYY-MM-DD HH24:MI:SS')                            as event_ts,
  to_char(a.t_end,   'YYYY-MM-DD HH24:MI:SS')                            as event_end_ts,
  (a.t_start - make_interval(hours => %(shift_start)s))::date::text       as shift_date,
  case when extract(hour from a.t_start) >= %(shift_start)s
        and extract(hour from a.t_start) <  %(shift_start)s + 12 then 'DS' else 'NS' end as shift,
  e.nombre                                                                as equipment,
  coalesce(fm.fleet, f.fleet)                                             as fleet,
  f.fleet                                                                 as model,
  nullif(trim(coalesce(w.nombre,'') || ' ' || coalesce(w.apellidop,'')), '') as operator,
  w.login_id                                                              as operator_login,
  g.nombre                                                                as crew,
  case when a.id_segment is null or a.id_segment = -1 then '(off segment)' else seg.nombre_tramo end as segment,
  a.id_segment,
  case when a.is_steep then 'steep' else 'flat' end                       as road,
  a.grade_pct,
  a.lim                                                                   as limit_kmh,
  a.max_speed                                                             as speed_kmh,
  a.avg_speed                                                             as avg_speed_kmh,
  round((a.max_speed - a.lim)::numeric, 1)                                as over_kmh,
  extract(epoch from (a.t_end - a.t_start))::int + 2                      as duration_s,
  a.is_loaded,
  a.x, a.y, a.z
from agg a
left join public.ts_equipos    e on e.id = a.id_equipo
left join public.fleets        f on f.id = e.id_flota
left join public.fleets        fm on fm.id = f.main_fleet_id and f.main_fleet_id > 0
left join public.tp_trabajador w on w.id = a.id_worker
left join public.ta_guardias   g on g.id_guardias = w.id_crew and g.tiem_elimin is null
left join public.tp_tramosstat seg on seg.id = a.id_segment
where extract(epoch from (a.t_end - a.t_start)) + 2 >= %(min_dur)s
order by a.t_start;
