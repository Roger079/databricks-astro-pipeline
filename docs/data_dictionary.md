# Diccionario y grano de las tablas

Todas las tablas se crean en el esquema exclusivo configurado. is_demo distingue
datos sintéticos; source_table/loaded_at trazan la ingesta. Importes DECIMAL(20,4).

| Tabla | Una fila representa | Uso |
|---|---|---|
| bronze_pos | Una ocurrencia de fila fuente | Snapshot sin deduplicación; conserva procedencia |
| silver_store_financial_profiles | Tienda/población/ventana de fechas | Perfiles inferidos A/B y versión de regla |
| silver_pos_typed | Una ocurrencia tipada | Fecha, horas, importes y claves normalizados |
| silver_pos_classified | Una ocurrencia con indicadores | Validez, revisión financiera, repeticiones y calidad de duración |
| silver_pos_quarantine | Una fila estructuralmente inválida | reject_reason y evidencia |
| silver_pos | Una fila válida de artículo/ajuste | Conserva repeticiones legítimas |
| silver_checks_profile | Un ticket identificable | Clave tienda/fecha/check, consistencia, conteos y flags |
| silver_checks_review | Un ticket no publicable | review_reason y campos de diagnóstico |
| silver_checks | Un ticket publicable | reported_total/tax/discount según grano confirmado |
| gold_daily_sales | Tienda/fecha/is_demo | Importes, tickets, ticket promedio y observaciones de duración |
| gold_hourly_sales | Tienda/fecha/hora/is_demo | Demanda por hora; hora desconocida permanece NULL |
| gold_channel_hourly | Tienda/fecha/hora/canal/is_demo | Tickets e importes por canal |
| gold_menu_performance | Tienda/fecha/categoría/artículo/is_demo | Unidades y descuentos; importe de línea solo con grano line |
| gold_quality_summary | Fuente/is_demo/grano | Conteos de incidencias que pueden solaparse |
| gold_publication_coverage | Tienda/fecha/is_demo | Tickets identificables, publicados y con repeticiones |

## Fórmulas

- Ticket promedio global = SUM(customer_total) / SUM(transactions).
- Cobertura = SUM(published_checks) / SUM(identifiable_checks).
- Tickets en revisión = identifiable_checks - published_checks.
- Duración global = SUM(duration_seconds_sum) / SUM(duration_observations).
- Con grano check, reported_line_total permanece NULL: no se reparte un ticket
  arbitrariamente entre productos.
- duration_status distingue valid_same_day, assumed_overnight,
  missing_or_unparseable e invalid_or_excessive. Promediar solo duraciones válidas.
- channel proviene de Pop; NULL/vacío es Unknown y varios canales por ticket son
  Mixed/Unknown. Revisar etiquetas POS antes de interpretar diferencias de canal.

reported_total es un importe POS de tickets publicables; no es ingreso neto,
margen ni ventas auditadas. Tickets en revisión y filas sin clave se presentan
por separado para evitar ocultar el alcance de las exclusiones.

## Normalización financiera v1

customer_total incluye Tax según el perfil inferido; merchandise_after_discount
lo excluye y ya descuenta la rebaja de ticket. reported_total conserva el Total
fuente, que tiene significados distintos en A/B. reconciliation_residual expresa
la diferencia con la ecuación; review_reason e is_publishable controlan publicación.
record_role impide contar anulaciones y promos como unidades vendidas.
financial_profile/rule_version provienen del lookup versionado, sin heurística
de número de cheque en el runtime. Config y análisis justifican la selección.

Bronze incluye _astro_source_version, _astro_source y _astro_loaded_at: identifican
el snapshot Delta exacto leído. Las definiciones semánticas no cambian al reejecutar.
