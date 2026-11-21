-- Pre-start checklists, one row per form, filed between shift dates %(date_from)s .. %(date_to)s
-- (checklist day starts %(day_start_min)s minutes after midnight). Shift comes from the form's own idturno (ts_turnos.id,
-- A = day, B = night); the clock is the fallback. Free text is flattened to one line (TSV transport).
with per as (
  select (%(date_from)s::date + make_interval(mins => %(day_start_min)s)) as t0,
         (%(date_to)s::date + interval '1 day' + make_interval(mins => %(day_start_min)s)) as t1
)
select
  c.id_checklist,
  to_char(c.tiem_creac, 'YYYY-MM-DD HH24:MI:SS')                                   as created_ts,
  (c.tiem_creac - make_interval(mins => %(day_start_min)s))::date::text               as shift_date,
  case when t.shortname = 'A' then 'DS' when t.shortname = 'B' then 'NS'
       when extract(hour from c.tiem_creac) * 60 + extract(minute from c.tiem_creac) >= %(day_start_min)s
        and extract(hour from c.tiem_creac) * 60 + extract(minute from c.tiem_creac) <  %(day_start_min)s + 720 then 'DS' else 'NS' end as shift,
  c.id_equipo,
  e.nombre                                                                          as equipment,
  f.fleet                                                                           as model,
  coalesce(fm.fleet, f.fleet)                                                       as fleet,
  c.id_operador                                                                     as id_worker,
  nullif(trim(regexp_replace(coalesce(w.nombre,'') || ' ' || coalesce(w.apellidop,''), '[\t\r\n]+', ' ', 'g')), '') as operator,
  w.login_id                                                                        as operator_login,
  g.nombre                                                                          as crew,
  regexp_replace(coalesce(c.descripcion, ''), '[\t\r\n]+', ' ', 'g')                as description,
  case c.id_checklist_status when 1 then 'Approved' when 2 then 'Rejected' else 'Not reviewed' end as form_status,
  to_char(c.time_status, 'YYYY-MM-DD HH24:MI:SS')                                   as status_ts,
  regexp_replace(coalesce(c.comentario_aprobacion, ''), '[\t\r\n]+', ' ', 'g')      as review_comment,
  d.n_items,
  d.n_not_ok
from public.ta_checklist c
cross join per
left join public.ts_turnos     t  on t.id = c.idturno
left join public.ts_equipos    e  on e.id = c.id_equipo
left join public.fleets        f  on f.id = e.id_flota
left join public.fleets        fm on fm.id = f.main_fleet_id and f.main_fleet_id > 0
left join public.tp_trabajador w  on w.id = c.id_operador
left join public.ta_guardias   g  on g.id_guardias = w.id_crew and g.tiem_elimin is null
left join lateral (
  select count(*) as n_items, count(*) filter (where not d.is_on) as n_not_ok
  from public.ta_checklistdetalle d where d.id_checklist = c.id_checklist and d.tiem_elimin is null
) d on true
where c.tiem_elimin is null and c.tiem_creac >= per.t0 and c.tiem_creac < per.t1
order by c.tiem_creac, c.id_checklist;
