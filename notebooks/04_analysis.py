# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Análisis Taco Bueno
# MAGIC `reported_total` es el importe reportado por POS. No se llama ingreso neto
# MAGIC hasta confirmar si incluye impuestos/descuentos. Solo tickets publicables.
# COMMAND ----------
import re
for k, v in [('catalog', 'workspace'), ('schema', 'astro_taco_dev')]:
    dbutils.widgets.text(k, v)
catalog, schema = [dbutils.widgets.get(k) for k in ('catalog', 'schema')]
assert all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for x in (catalog, schema))
def query(sql):
    return spark.sql(sql.replace('{db}', f'`{catalog}`.`{schema}`'))
display(query('SELECT * FROM {db}.gold_quality_summary'))
display(query("SELECT 'published' scope, count(*) checks FROM {db}.silver_checks UNION ALL SELECT 'review', count(*) FROM {db}.silver_checks_review"))
# COMMAND ----------
# MAGIC %md
# MAGIC ## Tendencia mensual
# MAGIC Revisar cobertura de tiendas y días antes de atribuir crecimiento a promociones.
# MAGIC Los meses al inicio/final pueden estar incompletos.
# COMMAND ----------
monthly = query("""SELECT trunc(business_date, 'MM') month, is_demo,
  sum(reported_total) reported_total, sum(transactions) transactions,
  sum(reported_total) / sum(transactions) average_ticket,
  count(DISTINCT store_id) stores, count(DISTINCT business_date) days
  FROM {db}.gold_daily_sales GROUP BY trunc(business_date, 'MM'), is_demo ORDER BY month""")
display(monthly)
# COMMAND ----------
# MAGIC %md
# MAGIC ## Horarios y categorías
# MAGIC Domingo=1. Horas desconocidas conservan NULL. Con grano `check`, no se asigna
# MAGIC el total del ticket a categorías: comparar unidades; importe de categoría queda NULL.
# COMMAND ----------
hourly = query("""SELECT weekday_sunday_1, start_hour, sum(reported_total) reported_total,
  sum(transactions) transactions FROM {db}.gold_hourly_sales
  GROUP BY weekday_sunday_1, start_hour ORDER BY weekday_sunday_1, start_hour""")
display(hourly)
categories = query("""SELECT report_group, sum(units) units,
  sum(reported_line_total) reported_line_total FROM {db}.gold_menu_performance
  GROUP BY report_group ORDER BY units DESC""")
display(categories)
# COMMAND ----------
# Bounded aggregates only; never collect raw POS rows to the driver.
import matplotlib.pyplot as plt
monthly_pdf = monthly.toPandas()
fig, ax = plt.subplots(figsize=(10, 4))
for demo, group in monthly_pdf.groupby('is_demo'):
    ax.plot(group['month'], group['reported_total'].astype(float), marker='o', label='Demo' if demo else 'Fuente')
ax.set(title='Importe reportado mensual · tickets publicables', xlabel='Mes', ylabel='Importe POS')
ax.legend()
fig.autofmt_xdate()
display(fig)
plt.close(fig)
category_pdf = categories.limit(15).toPandas()
fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(category_pdf['report_group'], category_pdf['units'].astype(float))
ax.set(title='Unidades por categoría · 15 principales', xlabel='Unidades')
fig.tight_layout()
display(fig)
plt.close(fig)
hour_pdf = hourly.filter('start_hour IS NOT NULL').toPandas()
if not hour_pdf.empty:
    heatmap = hour_pdf.pivot(index='weekday_sunday_1', columns='start_hour', values='reported_total').astype(float)
    fig, ax = plt.subplots(figsize=(10, 4))
    image = ax.imshow(heatmap, aspect='auto')
    ax.set_xticks(range(len(heatmap.columns)), heatmap.columns)
    ax.set_yticks(range(len(heatmap.index)), heatmap.index)
    ax.set(title='Importe por día de semana y hora', xlabel='Hora', ylabel='Domingo=1')
    fig.colorbar(image, ax=ax, label='Importe POS')
    display(fig)
    plt.close(fig)
# COMMAND ----------
# MAGIC %md
# MAGIC ## Conclusiones a completar con esta ejecución
# MAGIC - Presentar período, tiendas, tickets publicados y tickets bajo revisión.
# MAGIC - Explicar hallazgos con métricas de estas tablas, sin copiar cifras del PDF anterior.
# MAGIC - Separar asociación entre descuentos/ventas de causalidad.
# MAGIC - Tender Type desconocido limita análisis de pagos; no imputar efectivo/tarjeta.
# MAGIC - Recomendar una acción medible según horarios/categorías y explicar limitaciones.
