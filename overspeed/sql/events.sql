-- C4M Speed Limit Register (Alerts > Speed Limit Register), one row per violation.
-- Period: shift dates %(date_from)s .. %(date_to)s inclusive (shift day starts at %(shift_start)s:00).
-- All speeds km/h; coordinates converted from the stored x100 integers to metres.
with per as (
  select (%(date_from)s::date + make_interval(hours => %(shift_start)s)) as t0,
         (%(date_to)s::date + interval '1 day' + make_interval(hours => %(shift_start)s)) as t1
)
select
  v.id,
  to_char(v.tiemp_inicio, 'YYYY-MM-DD HH24:MI:SS')                       as event_ts,
  to_char(v.tiemp_fin,    'YYYY-MM-DD HH24:MI:SS')                       as event_end_ts,
  (v.tiemp_inicio - make_interval(hours => %(shift_start)s))::date::text  as shift_date,
  case when extract(hour from v.tiemp_inicio) >= %(shift_start)s
        and extract(hour from v.tiemp_inicio) <  %(shift_start)s + 12 then 'DS' else 'NS' end as shift,
  e.nombre                                                                as equipment,
  coalesce(fm.fleet, f.fleet)                                             as fleet,
  f.fleet                                                                 as model,
  nullif(trim(coalesce(w.nombre,'') || ' ' || coalesce(w.apellidop,'')), '') as operator,
  w.login_id                                                              as operator_login,
  g.nombre                                                                as crew,
  coalesce(s.nombre_tramo, '(off segment)')                               as segment,
  v.id_tramo                                                              as id_segment,
  v.limiteroto                                                            as limit_kmh,
  v.velocidad                                                             as speed_kmh,
  v.avg_speed                                                             as avg_speed_kmh,
  v.velocidad - v.limiteroto                                              as over_kmh,
  round(extract(epoch from (v.tiemp_fin - v.tiemp_inicio))::numeric, 1)   as duration_s,
  v.isload                                                                as is_loaded,
  v.id_cargadescarga                                                      as id_cycle,
  v.coorx_ini / 100.0                                                     as x,
  v.coory_ini / 100.0                                                     as y,
  v.coorz_ini / 100.0                                                     as z,
  v.porcen_tramo_ini                                                      as segment_pct_start,
  v.porcen_tramo_fin                                                      as segment_pct_end,
  v.is_viewed                                                             as acknowledged
from public.ta_speed_limits_exceeded v
cross join per
left join public.ts_equipos     e on e.id = v.id_equipo
left join public.fleets         f on f.id = e.id_flota
left join public.fleets         fm on fm.id = f.main_fleet_id and f.main_fleet_id > 0
left join public.tp_trabajador  w on w.id = v.id_operador
left join public.ta_guardias    g on g.id_guardias = w.id_crew and g.tiem_elimin is null
left join public.tp_tramosstat  s on s.id = v.id_tramo
where v.tiem_elimin is null
  and v.tiemp_inicio >= per.t0 and v.tiemp_inicio < per.t1
order by v.tiemp_inicio;
