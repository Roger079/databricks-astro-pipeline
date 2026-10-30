# Compatibilidad con el workspace del equipo

Revisión de metadatos realizada el 29 de octubre de 2026, perfil ASTRO.
No se ejecutaron consultas SQL, notebooks, jobs ni pipelines; no se inició compute.
Esta revisión no demuestra permisos de escritura ni disponibilidad de serverless Jobs/Lakeflow.

La sección anterior describe la revisión inicial de solo lectura. Posteriormente
se autorizó la ejecución: se desplegó y verificó el target demo con serverless Jobs
y Lakeflow. Ver `execution_evidence.md` para el estado actual y el bloqueo SELECT
de la fuente real. El inventario siguiente corresponde a antes del despliegue demo.

## Inventario accesible

Host: https://dbc-cfb7f93a-b497.cloud.databricks.com

| Recurso | Situación observada |
|---|---|
| workspace.default.tb_daily_tld_01_01_2026_m | Tabla original, columnas POS con espacios y horarios TIME(6) |
| workspace.default.tb_daily_tld_01_01_2026_m_silver | Tabla preparada con nombres normalizados y cleaned_at |
| workspace.default.tb_daily_tld_01_01_2026_m_quarantine | Registros rechazados con reject_reason y rejected_at |
| workspace.default.tb_daily_tld_01_01_2026_m_gold | Agregados tienda/fecha, ventas, descuentos y canales |
| Tacos POS Sales Analytics Dashboard | Fuente tacos.pricing_data.pricing |
| pricing 2026-10-09 01:12:34 | Fuente tacos.pricing_data.pricing |
| Daily Sales by Store — Gold Analysis | Fuente Gold de workspace.default |
| SQL Warehouse serverless | Serverless Starter Warehouse, detenido al revisar |
| Jobs, pipelines, clusters tradicionales | Ninguno listado para la identidad actual |

La cuenta actual no tiene USE SCHEMA sobre tacos.pricing_data. No se cambian
permisos ni se asume acceso a esa fuente. La tabla de workspace.default es la
fuente predeterminada del bundle, no se presupone que cubra el período completo del PDF.

Las estadísticas almacenadas indicaban 284428 filas originales, 180537 Silver,
11981 cuarentena y 228 Gold. No son conteos actuales verificados y pueden estar
desactualizadas o corresponder a distintas versiones. La diferencia entre las
primeras tres requiere investigar filtros, versiones y proceso anterior; no basta
para afirmar pérdida de registros. Gold tiene otro grano, por lo que no se compara por filas.

## Cambios preparados localmente

- Bundle apuntado al host del equipo y fuente conocida; destino nuevo workspace.astro_taco_dev.
- Tareas de notebook configuradas sin cluster tradicional para usar serverless.
  Requiere que serverless Jobs/notebooks esté habilitado; el warehouse no lo prueba.
- Bronze conserva valores fuente con nombres válidos de Delta y TIME(6) serializado.
- Silver acepta fracciones de segundo y calcula duración con microsegundos.
- Cuarentena incluye reject_reason; el pipeline conserva evidencia de exclusiones.
- Las tablas existentes y los dashboards no se sustituyen ni alteran.
- Las reglas anteriores no se pudieron recuperar de tablas materializadas: esta
  implementación usa reglas explícitas nuevas y no promete reproducir sus cifras.

## Migración de dashboards pendiente

Crear una copia de cada dashboard cuando se autorice su publicación y reemplazar
datasets por las consultas de `dashboard_queries.sql`. No apuntar el dashboard
actual a tablas que todavía no existen. Las columnas/nombres de medidas cambian:
reconfigurar cada visual explícitamente, no solo cambiar la fuente de toda la página.

| Visual actual | Fuente nueva / corrección |
|---|---|
| Ventas por tienda y fecha | gold_daily_sales.reported_total; rotular como importe POS |
| Transacciones | SUM(transactions) en Gold, clave tienda/fecha/ticket en Silver |
| Ticket promedio | SUM(reported_total) / SUM(transactions), no AVG de promedios |
| Tendencia mensual | Gold diario, mostrar tiendas y días incluidos |
| Categorías | gold_menu_performance; ingreso por categoría solo si amount_grain=line |
| Horarios | gold_hourly_sales; fechas tipadas y horas desconocidas conservadas |
| Calidad | gold_quality_summary + tickets bajo revisión + cuarentena |
| Canales, net_sales, gross_sales | Pendientes de definir; no hay equivalencia validada |

No sumar `distinct_menu_items` de varios días como productos únicos globales.
No reutilizar porcentajes de nulos escritos en los títulos como resultados actuales.
Los dashboards viejos aplican filtros distintos (Total>0 y Quantity>0): las cifras
nuevas pueden cambiar por exclusión de tickets completos y controles adicionales.

## Antes de autorizar ejecución

Confirmar grano común de Total/Tax/Total Discount; decidir definición de venta neta,
clave de ticket (si requiere POS Code), cobertura temporal y reglas de exclusión.
Verificar permisos y serverless; validar bundle y ejecutar primero demo en esquema
separado cuando se autorice. Después reconciliar con las tablas anteriores, explicar
diferencias y guardar evidencia real para la rúbrica.

Referencia de configuración serverless:
https://docs.databricks.com/aws/en/dev-tools/bundles/examples
