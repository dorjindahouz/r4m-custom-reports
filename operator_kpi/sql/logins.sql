-- Operator login sessions per equipment (who was on which machine when). A session ends at the
-- next login on the same equipment, or after 14 h. Used to attribute over-speed episodes.
with per as (
  select (%(date_from)s::date + make_interval(hours => %(shift_start)s)) as t0,
         (%(date_to)s::date + interval '1 day' + make_interval(hours => %(shift_start)s)) as t1
),
l as (
  select l.id_worker, l.id_equipment as id_equipo, l.time_start,
         least(coalesce(lead(l.time_start) over (partition by l.id_equipment order by l.time_start),
                        l.time_start + interval '14 hours'),
               l.time_start + interval '14 hours') as time_end
  from en_schm.at_worker_login l, per
  where l.time_eliminate is null
    and l.time_start >= per.t0 - interval '14 hours' and l.time_start < per.t1 + interval '1 day'
)
select l.id_worker, l.id_equipo,
       to_char(l.time_start, 'YYYY-MM-DD HH24:MI:SS') as login_ts,
       to_char(l.time_end,   'YYYY-MM-DD HH24:MI:SS') as logout_ts
from l, per
where l.id_worker > 0 and l.time_start < per.t1 and l.time_end > per.t0
order by l.time_start, l.id_equipo;
