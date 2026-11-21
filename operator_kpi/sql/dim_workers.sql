-- Workers (operators) with crew. Test accounts are dropped on the page by name.
select w.id as id_worker,
       nullif(trim(regexp_replace(coalesce(w.nombre,'') || ' ' || coalesce(w.apellidop,''), '[\t\r\n]+', ' ', 'g')), '') as operator,
       w.login_id as operator_login,
       g.nombre as crew,
       (w.tiem_elimin is not null) as deleted
from public.tp_trabajador w
left join public.ta_guardias g on g.id_guardias = w.id_crew and g.tiem_elimin is null
order by w.id;
