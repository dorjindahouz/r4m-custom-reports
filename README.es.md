# Reportes personalizados de R4M: Erdene Mongol, Bayan Khundii

*English: [README.md](README.md)*

Son las páginas de reportes que Erdene añadió a **R4M Aurora**, en el menú **Safety Reports → CustomReport**. Cada página es un único archivo
HTML autónomo, generado con Python a partir del cubo de R4M y de la base de datos de C4M. Los archivos se sirven desde la VM de la aplicación
R4M. Este repositorio contiene todo el código: sin datos, sin páginas generadas y sin credenciales.

> **Versión pública.** No incluye datos del sitio: `Report Inputs.xlsx` es una plantilla vacía, el logo es un marcador, y se omiten el
> mapa de contornos de la mina, la guía de lectura y las notas internas. Las direcciones de servidores, los nombres de host y el nombre de
> usuario de abajo son marcadores (`192.0.2.x`, `*.example.local`, `deploy`).

## Páginas

| Página (archivo en `/opt/R4M/storage/www/r4m_custom_report/`) | Contenido | Datos | Se regenera |
|---|---|---|---|
| `daily_report_v3.html` | Pestañas: **Master Report** · **Daily Report & Mine Atlas** · **3D Dig Viewer** · **Over-speed** · **Operator KPI** | Cubo R4M, polígonos HPGPS de R4M, versiones de polígonos y enlaces de stockpiles de C4M | cron 07:40 |
| `overspeed_report.html` | Excesos de velocidad según la política de la mina: 40 km/h (30 km/h en caminos con pendiente) | GPS de camiones cada 2 s en C4M (`ta_datacamion_historic`) | cron 10:30 |
| `operator_kpi.html` | Hoja de turno con operadores rankeados, fichas de operador, PDF de KPIs del turno y PDF de checklists | Ciclos, estados, logins y checklists de C4M + los excesos de velocidad | cron 10:45 y botón **Refresh data** |
| `published_inputs.json` | Plan / metas / presupuesto / topografía ingresados en el panel Inputs del reporte | lo escribe el servicio de publicación | al pulsar **Publish inputs** |

Las pestañas Over-speed y Operator KPI del reporte diario son iframes que cargan las otras dos páginas desde la misma carpeta. URL:
`https://r4m.example.local/r4m_custom_report/<archivo>`; el menú de R4M embebe `/fronts/r4m_custom_report/daily_report_v3.html`.

## Cómo funciona

```
C4M DB 192.0.2.15 (ControlSenseDB) --SSH + sudo psql, solo SELECT--> fetch_*.py --+
API cubo / HPGPS de R4M (login + DPoP) ------------> daily_report/fetch_data.py --+--> build_*.py --> HTML autónomo
                                                                                             |   (código + snapshot embebido)
                                                                                             v
                                                            /opt/R4M/storage/www/r4m_custom_report/  (VM app R4M 192.0.2.18)
En el navegador, dentro de R4M: el reporte diario lee el cubo en vivo con la sesión R4M del propio usuario (cookie + DPoP firmado con la
clave de Aurora en IndexedDB). Fuera de R4M, o si eso falla, muestra el snapshot embebido.
"Publish inputs" (panel Inputs) / "Refresh data" (Operator KPI) --> gateway --> publish_server.py (172.18.0.1:8790)
```

## En la VM de la aplicación R4M (192.0.2.18, usuario SSH `deploy`)

| Qué | Dónde |
|---|---|
| Código, venv, caché de datos, logs | `~/r4m_overspeed/` (`daily_report/`, `overspeed/`, `operator_kpi/`, `venv/`, `logs/`) |
| Login de C4M para las extracciones | `~/r4m_overspeed/.env` (solo C4M_DB_*, modo 600, lo escribe `overspeed/server/install_server.py`) |
| Login de R4M para extraer el cubo | `~/.config/r4m_custom_report/r4m_login` (2 líneas: usuario, contraseña; modo 600; lo crea el dueño de la cuenta, nunca un script). Sin él, el job nocturno usa el cubo en caché. |
| Clave de publicación (también es la contraseña de meses cerrados) | `~/.config/r4m_custom_report/publish.key` (se lee en cada solicitud; sobrescribirla para cambiarla) |
| Servicio de publicación / refresco | `~/server/publish_server.py`, unidad systemd **de usuario** `r4m-custom-report-publish` (linger activado) |
| Cron (hora del servidor UTC+8) | `40 7` `daily_report/server/refresh_daily_report.sh` · `30 10` `overspeed/server/refresh_overspeed.sh` · `45 10` `operator_kpi/server/refresh_operator_kpi.sh` |
| Rutas del gateway (gestor del gateway R4M, `config.db`) | `/r4m_custom_report/publish` (exact) y `/r4m_custom_report/refresh` (prefix_stop) → servicio `custom_report_publish` → `172.18.0.1:8790`; ufw permite 8790/tcp desde 172.18.0.0/16 |
| Respaldos | el job nocturno guarda los últimos 7 `daily_report_v3.html.bak-*-nightly`; cada publicación queda en `plan_history/` |

Cada job escribe su log en `~/r4m_overspeed/logs/<job>_<fecha>.log`. Si un build falla, la página publicada no se toca. Más detalle del servicio
en [daily_report/server/README_publish.md](daily_report/server/README_publish.md).

## Modificar un reporte

**Los jobs nocturnos generan las páginas desde la copia del código que está en el servidor.** Si solo se sube una página generada, el job de
la noche siguiente la vuelve a generar con el código viejo y deshace el cambio. Después de cualquier cambio de código:

```bash
cp .env.example .env                      # una vez; completar los logins R4M_APP_* y C4M_DB_*
pip install -r requirements.txt
python daily_report/server/install_daily_refresh.py --no-run     # sube el código del reporte diario (nunca --seed-data: sobrescribe los datos más nuevos del servidor)
python overspeed/server/install_server.py --no-run --skip-pip    # sube el código de over-speed + operator KPI y reescribe las líneas de cron
# regenerar ahora en vez de esperar a la noche (en la VM):
bash ~/r4m_overspeed/daily_report/server/refresh_daily_report.sh
```

## Generar en un PC

```bash
# Reporte diario: necesita daily_report/data/ (snapshot del cubo + versiones de polígonos de C4M)
python daily_report/serve_local.py --login              # proxy con login de R4M en 127.0.0.1:8123 (pide la contraseña)
R4M_HOST=http://127.0.0.1:8123 python daily_report/fetch_data.py
python daily_report/fetch_c4m_polygon_versions.py
python daily_report/build_combined.py                    # -> daily_report/daily_report_v3.html (unos 5,5 MB; unos minutos)

python overspeed/build_overspeed.py --fetch              # -> overspeed/overspeed_report.html
python operator_kpi/build_operator_kpi.py --fetch        # -> operator_kpi/operator_kpi.html
python overspeed/deploy_r4m.py --only daily overspeed opkpi   # sube las páginas generadas (antes respalda la copia del servidor)
```

Python 3 con `requirements.txt`. Las extracciones guardan caché por día en `data/days/`, así que las siguientes corridas solo traen los días nuevos.

## Reglas de cálculo

- **Día de turno** 07:00 → 07:00: DS 07–19, NS 19–07. Los checklists usan un día que empieza a las 06:20, porque los formularios se llenan
  antes del cambio de turno.
- **Minado** = cargado en el rajo. El re-manejo (cargas desde un stockpile o zona de descarga) no cuenta en Minado ni en Total Movement.
- **Alimentación a planta** = ubicación de descarga `crush|үйлдвэр`. El chancador se alimenta desde los stockpiles 1237_ (fingers).
- **Master Report**: solo las secciones 4 (minería), 5 (ROM) y 7 (alimentación a planta). Columnas TODAY / MTD / QTD / YTD; el plan sale de
  `inputs.budget`. Los meses cerrados están bloqueados con la clave de publicación.
- **Stockpiles**: las pilas se agrupan por el id *original* del polígono de C4M (cada edición en C4M crea una nueva versión en `ts_poligono`).
  Las toneladas descargadas en una pila siguen el enlace zona de descarga → stockpile de C4M (`ts_stockpiles`) vigente al momento de la descarga.
- **3D Dig Viewer**: el piso planificado es `ts_poligono.level_real` (el nivel decimal de los planificadores) y el bloque tiene 2,5 m de alto.
  El piso excavado sale de los puntos de excavación del balde. La excavación de EX215 entre 2026-10-30 08:00 y 2026-11-14 13:00 queda fuera,
  porque su inclinómetro de balde estaba muerto (`BAD_TIP` en `dig3d_template.py`; agregar ahí una entrada cuando falle el sensor de balde de
  una pala).
- **Over-speed**: 40 km/h, o 30 km/h donde la pendiente GPS del camino es ≥ 10 %. Un evento dura ≥ 8 s con un promedio ≥ 2 km/h sobre el
  límite, y "exceso" = promedio − límite. No se muestran velocidades pico. Cada evento se asigna al operador logueado en el camión
  (`operator_login` de la telemetría).
- **Operator KPI**: ranking dentro del turno por cada KPI, sin puntaje combinado. Las toneladas son nominales (52,8 t por carga; los camiones
  no tienen balanza).

## Mapa del repositorio

| Ruta | Qué |
|---|---|
| `daily_report/build_combined.py` | Punto de entrada: genera `daily_report_v3.html` con los módulos de abajo |
| `build_report.py` · `master_template.py` · `xlsx_template.py` · `manual_template.py` · `notes_template.py` · `customize_template.py` | Tablas y gráficos del reporte diario, Master Report, importación/exportación del libro de Inputs, series manuales, notas de ingeniería, capa de mostrar/ocultar/reordenar |
| `build_atlas.py` · `atlas_template.py` | Secciones del Mine Atlas (ciclo de vida, agotamiento de polígonos, cumplimiento de excavación, stockpiles del ROM pad, equipos, cuadrillas, ciclo, acarreo) |
| `dig3d_template.py` | 3D Dig Viewer (three.js): selector de fecha + turno, piso excavado vs bloque planificado, exportación DXF/CSV |
| `overspeed_sheet.py` · `operator_kpi_sheet.py` | Las pestañas iframe de las dos páginas de C4M |
| `fetch_data.py` · `serve_local.py` · `fetch_c4m_polygon_versions.py` | Extracción del cubo/HPGPS de R4M, proxy con login de R4M (DPoP), versiones de polígonos + enlaces de stockpiles de C4M |
| `daily_report/server/` | Job nocturno, instalador, servicio de publicación/refresco |
| `overspeed/` | Página de excesos de velocidad; además `db.py` / `env.py` (acceso compartido a C4M y a `.env`) y `deploy_r4m.py`. Ver [overspeed/README.md](overspeed/README.md) |
| `operator_kpi/` | Página Operator KPI. Ver [operator_kpi/README.md](operator_kpi/README.md) |
| `Report Inputs.xlsx`, `build_inputs_workbook.py`, `r4m-design-schema.css` | Libro de inputs (plantilla vacía) y CSS compartido que usan los builds |

Archivos de terceros incluidos: three.js (MIT), hyparquet (MIT), fuente Rubik (OFL).

## Trabajos pendientes

- **3D Dig Viewer.** El contorno y el piso excavados todavía no se han comparado con un levantamiento topográfico.
- **Saldos del ROM** (`romState` en `build_report.py`). Un saldo manual (`romadj`) de una pila sin recepciones se ignora, y las pilas que
  una topografía no incluye no se ponen en cero. Corregir ambos antes de usar topografías para reiniciar los saldos.
- **Pruebas.** No hay suite de pruebas automáticas; los cambios se verificaron con scripts de navegador puntuales.
- **`publish_server.py`** (detalle cosmético). `/refresh/status?job=overspeed` puede mostrar la cola del log de operator KPI, porque los
  nombres de log comparten prefijo.
