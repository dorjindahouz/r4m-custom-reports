-- Equipment with its model fleet and main fleet; role = haul (trucks) / load (excavators, loaders) / aux.
select e.id as id_equipo, e.nombre as equipment, f.fleet as model, coalesce(fm.fleet, f.fleet) as fleet,
       case when coalesce(fm.fleet, f.fleet) = 'Acarreo en Mina' then 'haul'
            when coalesce(fm.fleet, f.fleet) = 'Carguio en Mina' then 'load' else 'aux' end as role
from public.ts_equipos e
left join public.fleets f  on f.id = e.id_flota
left join public.fleets fm on fm.id = f.main_fleet_id and f.main_fleet_id > 0
order by e.nombre;
