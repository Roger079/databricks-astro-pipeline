# Databricks notebook source
# MAGIC %md
# MAGIC # Demostración de dos días: importe POS de tickets publicables
# MAGIC No son ingresos netos auditados. Dos fechas no sustentan estacionalidad ni crecimiento anual.
# COMMAND ----------
import re
for k, v in [('catalog', 'workspace'), ('schema', 'astro_taco_dev')]:
    dbutils.widgets.text(k, v)
catalog, schema = [dbutils.widgets.get(k) for k in ('catalog', 'schema')]
assert all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for x in (catalog, schema))

def query(sql):
    return spark.sql(sql.replace('{db}', f'`{catalog}`.`{schema}`'))

display(query('SELECT * FROM {db}.gold_quality_summary'))
display(query('SELECT *, identifiable_checks - published_checks AS review_checks FROM {db}.gold_publication_coverage'))
display(query('SELECT business_date, is_demo, sum(reported_total) reported_total, sum(transactions) transactions, sum(reported_total)/nullif(sum(transactions),0) average_ticket, count(DISTINCT store_id) stores, sum(duration_seconds_sum)/nullif(sum(duration_observations),0) average_duration_seconds FROM {db}.gold_daily_sales GROUP BY business_date,is_demo ORDER BY business_date'))
# COMMAND ----------
stores = query('SELECT store_id, sum(reported_total) reported_total, sum(transactions) transactions, count(DISTINCT business_date) observed_days FROM {db}.gold_daily_sales GROUP BY store_id ORDER BY reported_total DESC LIMIT 20')
categories = query('SELECT report_group, sum(units) units, sum(reported_line_total) reported_line_total FROM {db}.gold_menu_performance GROUP BY report_group ORDER BY units DESC')
channels = query('SELECT channel, sum(transactions) transactions, sum(reported_total) reported_total FROM {db}.gold_channel_hourly GROUP BY channel ORDER BY transactions DESC')
display(stores)
display(categories)
display(channels)
# COMMAND ----------
# Only bounded aggregates reach the driver.
import matplotlib.pyplot as plt
for frame, category, value, title in [
    (stores, 'store_id', 'reported_total', 'Importe POS por tienda'),
    (categories.limit(15), 'report_group', 'units', 'Unidades por categoría'),
    (channels.limit(20), 'channel', 'transactions', 'Tickets por canal'),
]:
    pdf = frame.toPandas()
    if not pdf.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.barh(pdf[category].astype(str), pdf[value].astype(float))
        ax.set(title=title, xlabel=value)
        fig.tight_layout()
        display(fig)
        plt.close(fig)
# COMMAND ----------
# MAGIC %md
# MAGIC ## Evidencia para la entrega
# MAGIC - Informar fechas, tiendas, tickets publicados/en revisión y cobertura.
# MAGIC - Mostrar un ticket multiartículo contado una sola vez.
# MAGIC - Comparar tiendas mostrando días disponibles y tasas de exclusión.
# MAGIC - Con grano check, no asignar el total del ticket a cada producto.
# MAGIC - Duraciones inválidas no entran en promedios; rollover nocturno queda marcado como supuesto.
# MAGIC - Documentar tres hallazgos respaldados, una acción medible y limitaciones.
