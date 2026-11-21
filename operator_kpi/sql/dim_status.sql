-- C4M status details (ids match the R4M status dimension used for the READY/DELAY/... buckets).
select d.id as id_status_detail,
       regexp_replace(coalesce(d.name, ''), '[\t\r\n]+', ' ', 'g') as status_name,
       d.id_status_kind, d.id_fleet
from en_schm.st_status_detail d
order by d.id;
