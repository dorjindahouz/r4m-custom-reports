-- Checklist structure: every item with its parent section (id_struct) and group; roots have is_struct = true.
select
  s.id_checkliststruc                                              as item_id,
  s.id_struct                                                      as section_id,
  regexp_replace(coalesce(p.nombre, ''), '[\t\r\n]+', ' ', 'g')    as section,
  regexp_replace(coalesce(s.nombre, ''), '[\t\r\n]+', ' ', 'g')    as item,
  s.id_flota                                                       as fleet_id,
  s.is_struct,
  s.ordinal,
  s.group_id,
  g.name_group
from public.ts_checkliststruc s
left join public.ts_checkliststruc    p on p.id_checkliststruc = s.id_struct
left join public.ts_checklist_groups  g on g.id = s.group_id
where s.tiem_elimin is null
order by s.id_flota, s.id_struct, s.ordinal nulls last, s.id_checkliststruc;
