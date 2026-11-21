-- Checklist answers, one row per item of every form filed in the period (is_ok = the box was ticked).
with per as (
  select (%(date_from)s::date + make_interval(mins => %(day_start_min)s)) as t0,
         (%(date_to)s::date + interval '1 day' + make_interval(mins => %(day_start_min)s)) as t1
)
select
  d.id_checklist,
  d.id_checklistitem                    as item_id,
  d.is_on                               as is_ok,
  nullif(d.id_checklistsi, 0)           as defect_id,
  si.nivel_criticidad                   as defect_criticality
from public.ta_checklistdetalle d
join public.ta_checklist c on c.id_checklist = d.id_checklist and c.tiem_elimin is null
cross join per
left join public.ts_checklistsi si on si.id_checklistsi = d.id_checklistsi and d.id_checklistsi <> 0
where d.tiem_elimin is null and c.tiem_creac >= per.t0 and c.tiem_creac < per.t1
order by d.id_checklist, d.id_checklistdetalle;
