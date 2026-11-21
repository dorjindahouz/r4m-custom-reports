-- Equipment status time (tp_estados) cut at the 12 h shift boundaries and rolled up per shift date x
-- shift x equipment x operator x status detail. Rows without end_time are closed by the next row on
-- the same equipment (or now), never longer than 24 h. Rows without an operator take the last worker
-- login on that equipment; still unknown -> id_worker 0. Status detail ids are bucketed on the page
-- through the R4M status dimension (lookups/status_detail.json).
with per as (
  select (%(date_from)s::date + make_interval(hours => %(shift_start)s)) as t0,
         (%(date_to)s::date + interval '1 day' + make_interval(hours => %(shift_start)s)) as t1
),
w as (
  select gs as w_start, gs + interval '12 hours' as w_end,
         (gs - make_interval(hours => %(shift_start)s))::date::text as shift_date,
         case when extract(hour from gs) = %(shift_start)s then 'DS' else 'NS' end as shift
  from per, generate_series(per.t0, per.t1 - interval '12 hours', interval '12 hours') as gs
),
s as (
  select s.id_equipo, s.id_detal_estado, s.id_trabajador, s.tiempo_inicio as t_start,
         least(coalesce(s.end_time,
                        lead(s.tiempo_inicio) over (partition by s.id_equipo order by s.tiempo_inicio),
                        now()),
               s.tiempo_inicio + interval '24 hours') as t_end
  from public.tp_estados s, per
  where s.tiem_elimin is null
    and s.tiempo_inicio >= per.t0 - interval '2 days' and s.tiempo_inicio < per.t1 + interval '1 day'
),
x as (
  select w.shift_date, w.shift, s.id_equipo, s.id_detal_estado,
         coalesce(nullif(s.id_trabajador, 0), lg.id_worker, 0) as id_worker,
         extract(epoch from (least(s.t_end, w.w_end) - greatest(s.t_start, w.w_start))) / 3600.0 as hours
  from s
  join w on s.t_start < w.w_end and s.t_end > w.w_start
  left join lateral (
    select l.id_worker from en_schm.at_worker_login l
    where l.id_equipment = s.id_equipo and l.time_eliminate is null
      and l.time_start <= s.t_start and l.time_start > s.t_start - interval '14 hours'
    order by l.time_start desc limit 1
  ) lg on (s.id_trabajador is null or s.id_trabajador = 0)
)
select shift_date, shift, id_equipo, id_worker, id_detal_estado as id_status_detail,
       round(sum(hours)::numeric, 3) as hours, count(*) as n
from x where hours > 0
group by 1, 2, 3, 4, 5
order by 1, 2, 3, 4, 5;
