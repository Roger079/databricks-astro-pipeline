-- customer_total es la métrica comparable normalizada; reported_total conserva semánticas mixtas.
-- Consultas para datasets de COPIAS futuras de los dashboards.
-- No ejecutadas. Requieren desplegar/validar primero las tablas nuevas.
-- No son reemplazo directo del JSON existente: configurar medidas y visuales.

-- KPI por conjunto filtrado: ticket promedio ponderado.
SELECT is_demo, sum(customer_total) AS customer_total,
       sum(transactions) AS transactions,
       sum(customer_total) / nullif(sum(transactions), 0) AS average_ticket
FROM workspace.astro_taco_main_real.gold_daily_sales
GROUP BY is_demo;

-- Diario/tienda: sumar importes y tickets; no sumar average_ticket.
SELECT business_date AS txn_date, store_id, is_demo, customer_total, merchandise_after_discount,
       reported_tax, reported_discount, transactions
FROM workspace.astro_taco_main_real.gold_daily_sales;

-- Dos días reales: no presentar el cambio de año como crecimiento anual.
SELECT business_date, is_demo,
       sum(customer_total) AS customer_total, sum(transactions) AS transactions,
       sum(customer_total) / nullif(sum(transactions), 0) AS average_ticket,
       count(DISTINCT store_id) AS stores
FROM workspace.astro_taco_main_real.gold_daily_sales
GROUP BY business_date, is_demo;

-- Categorías: el importe es NULL si el grano es check; usar unidades.
SELECT business_date, store_id, report_group, menu_item, is_demo,
       units, reported_line_total, item_discount
FROM workspace.astro_taco_main_real.gold_menu_performance;

-- Heatmap: weekday_sunday_1 usa domingo=1; no rellenar horas desconocidas con 0.
SELECT business_date, store_id, weekday_sunday_1, start_hour, is_demo,
       transactions, customer_total, merchandise_after_discount
FROM workspace.astro_taco_main_real.gold_hourly_sales;

-- Calidad y cobertura: los conteos de incidencias pueden solaparse.
SELECT * FROM workspace.astro_taco_main_real.gold_quality_summary;
SELECT 'published' AS scope, count(*) AS tickets FROM workspace.astro_taco_main_real.silver_checks
UNION ALL
SELECT 'review', count(*) FROM workspace.astro_taco_main_real.silver_checks_review;

-- Mostrar cobertura y no confundir tickets excluidos con ventas cero.
SELECT *, identifiable_checks - published_checks AS review_checks
FROM workspace.astro_taco_main_real.gold_publication_coverage;

SELECT * FROM workspace.astro_taco_main_real.gold_channel_hourly;
