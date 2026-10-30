# Verificación normalizada actual · 30 de octubre de 2026

- [Primera ejecución real](https://dbc-cfb7f93a-b497.cloud.databricks.com/?o=7474644614542766#job/621214800098362/run/87723745066499): SUCCESS en las cuatro tareas.
- [Reejecución real](https://dbc-cfb7f93a-b497.cloud.databricks.com/?o=7474644614542766#job/621214800098362/run/435278296555206): SUCCESS; mismas métricas y versión Delta.
- [Demo normalizada](https://dbc-cfb7f93a-b497.cloud.databricks.com/?o=7474644614542766#job/822272637459337/run/362421565514746): SUCCESS; incluye los dos perfiles y casos de calidad.
- Destinos: workspace.astro_taco_main_real y workspace.astro_taco_main_demo.
- Fuente real: 284,428 filas, 40,306 tickets; 40,257 publicados y 49 en revisión.
- Importes normalizados publicados: customer_total 615,846.68 y
  merchandise_after_discount 571,874.16. La moneda/settlement no se infieren.
- Evidencia: normalized-real-first-run.json, normalized-real-verification.json y
  normalized-demo-verification.json, dentro de docs/evidence.
- El primer intento real (153617672473786) falló porque astro_taco_dev estaba
  administrado por otro pipeline. Se aisló el destino y se añadió una verificación
  de propiedad antes de escribir Bronze. Ver schema-collision-recovery.json.
- 28 pruebas locales pasan y ambos targets validan con --strict. Schedule pausado.
- Estado de pendientes en delivery_checklist.md; plan estratégico en dashboard_plan.md.

---

Los registros siguientes son históricos: conservan sus números y parámetros de
las versiones anteriores de la demo. No son el estado actual del pipeline.

> Registro histórico de la implementación original de Magda (4d2aef2). Los bloqueos de permisos y rutas descritos aquí corresponden a esa revisión. Para el estado corregido de main, ver README, delivery_checklist.md y la nueva evidencia main-demo-verification.json. No mezclar el importe sintético original 18 con el nuevo 28.

## Verificación de las correcciones de main

- Esquema aislado: `workspace.astro_taco_main_demo`. No se reemplazó el demo original.
- [Job completo corregido](https://dbc-cfb7f93a-b497.cloud.databricks.com/jobs/822272637459337/runs/323117183870679): SUCCESS en ingesta, transformación, validación y análisis.
- Pipeline `1e1836b0-dba3-4b08-ac67-e6eb31225c91`: update `aaac1c6b-e98c-4f15-9fdd-ff7d977a9746` COMPLETED, leyendo los archivos de src/transformations.
- API/SQL verificaron 8 Bronze, 7 Silver, 1 cuarentena, 3 tickets publicados,
  2 en revisión e importe sintético 28.0000. No hay filas demo sin marcar en Bronze/Gold.
- Evidence: `docs/evidence/main-demo-verification.json`, con estados de las tareas,
  métricas de expectations y hashes de los archivos probados.
- 18 pruebas locales pasan; bundle validate --strict pasa en dev y demo.
- Los tres miembros tienen ALL PRIVILEGES y MANAGE en ambos esquemas demo;
  la ingesta configura esos permisos para los nuevos esquemas mediante team_principals.
- El target dev sigue sin ejecutar: falta confirmar contrato de importes y registrar
  evidencia de la demostración real de dos días. No es necesario cargar 85 millones de filas.
- El nuevo JSON de dashboard en main apunta al demo corregido; su publicación y
  la construcción del dashboard real siguen pendientes, sin alterar los dashboards anteriores.

# Ejecución y evidencia · 29 de octubre de 2026 (America/Monterrey)

## Alcance

Entorno sintético aislado `workspace.astro_taco_demo`. No son ventas reales.
El target `dev` no se ha desplegado ni ejecutado. Los dashboards existentes y las
tablas del equipo en `workspace.default` se conservaron sin modificaciones.
La programación del Job sigue pausada.

## Recursos creados

- [Job de demo](https://dbc-cfb7f93a-b497.cloud.databricks.com/jobs/883217129446265?o=7474644614542766).
- [Pipeline Lakeflow](https://dbc-cfb7f93a-b497.cloud.databricks.com/pipelines/1d827004-d26d-4ade-8ea9-51f0c31597e8?o=7474644614542766).
- [Dashboard nuevo en borrador, DEMO sintética](https://dbc-cfb7f93a-b497.cloud.databricks.com/dashboardsv3/01f1d4187aef1b3bbc19ed1f4614fcae?o=7474644614542766).

## Pruebas comprobadas

- `databricks bundle validate --strict`: válido en targets dev y demo.
- Creación de la fuente sintética exitosa: run 790192215608927.
- Primer Job completo: run 1091416802476266, ingesta, transformación, validación y
  análisis terminaron SUCCESS. Permitió detectar que la normalización de nombres
  perdía `_astro_demo`; corregido y agregado un control explícito de esa marca.
- Las consultas de reconciliación devolvieron 8 filas fuente, 7 Silver, 1 cuarentena,
  2 tickets publicados, 3 en revisión e importe sintético 18.0000.
- SQL nativo TIME(6): 23:59:59.750000 → 00:00:00.250000 da 0.500000000 segundos.
- Event log del primer update: valid_date pasó 7 y falló 1 registro; valid_total
  pasó los 8; en Silver valid_key y valid_total pasaron sus 7 registros.
- 13 pruebas locales con DuckDB/PyYAML pasaron después de las correcciones.

La [reejecución corregida](https://dbc-cfb7f93a-b497.cloud.databricks.com/jobs/883217129446265/runs/1078180118409216?o=7474644614542766)
terminó SUCCESS en las cuatro tareas. Conservó las mismas cuentas e importe de
negocio, y verificó 0 filas sin marca sintética tanto en Bronze como en Gold.
La evidencia se guardó en `docs/evidence/demo-verification.json` mediante
`python scripts/capture_demo_evidence.py --run-id 1078180118409216`.
Ese archivo es evidencia de API/SQL; no sustituye la interpretación de datos reales.

## Bloqueo de datos reales

La consulta a `workspace.default.tb_daily_tld_01_01_2026_m` falló con
INSUFFICIENT_PERMISSIONS: la cuenta `a01381456@tec.mx` no tiene SELECT.
Statement ID: 01f1d417-b86b-1e72-98ea-66848b5d8a29.

El propietario o administrador debe conceder los permisos mínimos de
`docs/source_access.sql`. No se ejecutaron GRANT ni cambios de seguridad.
Después, ejecutar el diagnóstico de solo lectura del notebook 05, comparar
tickets con recibos/documentación y confirmar grano de Total/Tax/Total Discount.
El parámetro real conserva `unconfirmed` para impedir suponer una definición.

## Pendiente para cerrar la rúbrica

Permiso y contrato de fuente; ejecución real y reconciliación con trabajo previo;
copias de dashboards conectadas a Gold real; conclusiones basadas en resultados
reales y presentación por el equipo. Los archivos locales aún deben guardarse
en GitHub mediante commit/push revisado por el equipo.
