# Databricks notebook source
# MAGIC %md
# MAGIC # Diagnóstico de la fuente · solo lectura
# MAGIC Ejecutar manualmente cuando el propietario conceda SELECT. No escribe tablas.
# MAGIC La repetición de importes es evidencia para discutir el contrato, no prueba
# MAGIC suficiente del significado del POS. Contrastar tickets con recibos/documentación.
# COMMAND ----------
import re
dbutils.widgets.text('source_table', 'workspace.default.tb_daily_tld_01_01_2026_m')
source = dbutils.widgets.get('source_table')
parts = source.split('.')
assert len(parts) == 3 and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', p) for p in parts)
source_sql = '.'.join(f'`{p}`' for p in parts)
df = spark.table(source_sql)
display(df.limit(25))
# COMMAND ----------
# No se descartan registros al inspeccionar el grano. Agrupación por clave propuesta.
profiles = spark.sql(f"""SELECT `Store #` store_id, `Date` source_date,
  `Check Number` check_number, count(*) lines,
  count(DISTINCT `Total`) total_values, min(`Total`) min_total, max(`Total`) max_total,
  sum(`Total`) summed_total, count(DISTINCT `Tax`) tax_values,
  count(DISTINCT `Total Discount`) discount_values,
  sum(CASE WHEN `Total` IS NULL THEN 1 ELSE 0 END) missing_total,
  sum(CASE WHEN `Tax` IS NULL THEN 1 ELSE 0 END) missing_tax,
  sum(CASE WHEN `Total Discount` IS NULL THEN 1 ELSE 0 END) missing_discount
  FROM {source_sql} GROUP BY `Store #`, `Date`, `Check Number`""")
display(profiles.filter('lines > 1').orderBy('store_id', 'source_date', 'check_number').limit(50))
profiles.createOrReplaceTempView('astro_source_ticket_diagnostics')
display(spark.sql("""SELECT count(*) proposed_tickets,
  sum(CASE WHEN lines > 1 THEN 1 ELSE 0 END) multi_line_tickets,
  sum(CASE WHEN lines > 1 AND total_values = 1 THEN 1 ELSE 0 END) repeated_total_tickets,
  sum(CASE WHEN total_values > 1 THEN 1 ELSE 0 END) varying_total_tickets,
  sum(CASE WHEN missing_total + missing_tax + missing_discount > 0 THEN 1 ELSE 0 END) incomplete_amount_tickets
  FROM astro_source_ticket_diagnostics"""))
# COMMAND ----------
# MAGIC %md
# MAGIC Registrar decisión validada con el equipo para Total, Tax y Total Discount.
# MAGIC Si tienen granos diferentes, adaptar el pipeline antes de activar datos reales.
# MAGIC Verificar además si POS Code es necesario para distinguir tickets.
