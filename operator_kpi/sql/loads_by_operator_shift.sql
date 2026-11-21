-- Haul cycles (tp_cargadescarga) rolled up per shift date x shift x equipment x operator.
-- Phase timestamps verified against the R4M cube (same cycles, same seconds):
--   queue  = esperando - llegada      spot    = carga - esperando (ready parking + parking + parked)
--   load   = acarreo - carga          haul    = cola - acarreo
--   atdump = descarga - cola          dump    = viajando - descarga
--   empty  = next cycle's llegada - viajando (travel empty back to the loader)
-- Each phase is clipped to [0, 1800 s] (haul/empty 3600 s). The loader's operator comes from the
-- last worker login on that loader at load time (at_worker_login), attributing 99.9 pct of loads.
with per as (
  select (%(date_from)s::date + make_interval(hours => %(shift_start)s)) as t0,
         (%(date_to)s::date + interval '1 day' + make_interval(hours => %(shift_start)s)) as t1
),
c as (
  select l.id, l.id_equipo, coalesce(l.id_trabajador, 0) as id_worker, l.id_palanext as id_loader,
         l.tiem_llegada, l.tiem_esperando, l.tiem_carga, l.tiem_acarreo, l.tiem_cola, l.tiem_descarga, l.tiem_viajando,
         l.tonelaje,
         lead(l.tiem_llegada) over (partition by l.id_equipo   order by l.tiem_carga) as next_llegada,
         lead(l.tiem_carga)   over (partition by l.id_palanext order by l.tiem_carga) as next_load_same_loader
  from public.tp_cargadescarga l, per
  where l.tiem_elimin is null and l.tiem_carga >= per.t0 and l.tiem_carga < per.t1 + interval '1 day'
),
d as (
  select c.*,
         (c.tiem_carga - make_interval(hours => %(shift_start)s))::date::text as shift_date,
         case when extract(hour from c.tiem_carga) >= %(shift_start)s
               and extract(hour from c.tiem_carga) <  %(shift_start)s + 12 then 'DS' else 'NS' end as shift,
         least(1800, greatest(0, extract(epoch from (c.tiem_esperando - c.tiem_llegada))))   as queue_s,
         least(1800, greatest(0, extract(epoch from (c.tiem_carga - c.tiem_esperando))))     as spot_s,
         least(1800, greatest(0, extract(epoch from (c.tiem_acarreo - c.tiem_carga))))       as load_s,
         least(3600, greatest(0, extract(epoch from (c.tiem_cola - c.tiem_acarreo))))        as haul_s,
         least(1800, greatest(0, extract(epoch from (c.tiem_descarga - c.tiem_cola))))       as atdump_s,
         least(1800, greatest(0, extract(epoch from (c.tiem_viajando - c.tiem_descarga))))   as dump_s,
         least(3600, greatest(0, extract(epoch from (c.next_llegada - c.tiem_viajando))))    as empty_s,
         least(1800, greatest(0, extract(epoch from (c.next_load_same_loader - c.tiem_acarreo)))) as hang_s,
         coalesce(lg.id_worker, 0) as id_worker_loading
  from c cross join per
  left join lateral (
    select x.id_worker from en_schm.at_worker_login x
    where x.id_equipment = c.id_loader and x.time_eliminate is null
      and x.time_start <= c.tiem_carga and x.time_start > c.tiem_carga - interval '14 hours'
    order by x.time_start desc limit 1
  ) lg on true
  where c.tiem_carga < per.t1
)
select 'haul' as role, shift_date, shift, id_equipo, id_worker,
       count(*) as loads, round(sum(tonelaje)::numeric, 1) as tonnes,
       count(queue_s) as n_queue,   round(sum(queue_s))  as s_queue,
       count(spot_s)  as n_spot,    round(sum(spot_s))   as s_spot,
       count(load_s)  as n_load,    round(sum(load_s))   as s_load,
       count(haul_s)  as n_haul,    round(sum(haul_s))   as s_haul,
       count(atdump_s) as n_atdump, round(sum(atdump_s)) as s_atdump,
       count(dump_s)  as n_dump,    round(sum(dump_s))   as s_dump,
       count(empty_s) as n_empty,   round(sum(empty_s))  as s_empty,
       null::bigint as n_hang, null::numeric as s_hang, null::bigint as trucks_served
from d group by 1, 2, 3, 4, 5
union all
select 'load', shift_date, shift, id_loader, id_worker_loading,
       count(*), round(sum(tonelaje)::numeric, 1),
       null, null, null, null,
       count(load_s), round(sum(load_s)),
       null, null, null, null, null, null, null, null,
       count(hang_s), round(sum(hang_s)), count(distinct id_equipo)
from d where id_loader is not null group by 1, 2, 3, 4, 5
order by 2, 3, 1, 4, 5;
