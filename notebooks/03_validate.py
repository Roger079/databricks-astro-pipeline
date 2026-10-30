# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Validación de publicación
# MAGIC Detiene el Job si las tablas no reconcilian. Los problemas de los datos se
# MAGIC conservan en cuarentena/revisión y se muestran como cobertura del análisis.
# COMMAND ----------
import re
from pyspark.sql import functions as F
for key, default in [('catalog', 'workspace'), ('schema', 'astro_taco_dev')]:
    dbutils.widgets.text(key, default)
catalog, schema = [dbutils.widgets.get(k) for k in ('catalog', 'schema')]
assert all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for x in (catalog, schema))
def table(name):
    return spark.table(f'{catalog}.{schema}.{name}')
raw, clean, quarantine = [table(t).count() for t in ('bronze_pos', 'silver_pos', 'silver_pos_quarantine')]
assert raw > 0, 'Bronze vacío'
if schema.endswith('_demo'):
    assert table('bronze_pos').filter('_astro_demo IS NULL OR NOT _astro_demo').isEmpty(), 'Demo sin marca sintética en Bronze'
    assert table('silver_pos_typed').filter('is_demo IS NULL OR NOT is_demo').isEmpty(), 'Demo sin marca sintética en Silver'
assert raw == clean + quarantine, 'Silver + cuarentena no reconcilian con Bronze'
assert table('silver_checks').count() > 0, 'Sin tickets publicables; revisar calidad'
assert table('silver_checks').groupBy('store_id', 'business_date', 'check_number').count().filter('count > 1').isEmpty(), 'Tickets duplicados'
assert table('silver_checks_profile').count() == table('silver_checks').count() + table('silver_checks_review').count(), 'Tickets sin clasificar'
expected = table('silver_checks').groupBy('business_date', 'store_id', 'is_demo').agg(F.count('*').alias('transactions'), F.sum('reported_total').alias('reported_total'))
actual = table('gold_daily_sales').select(*expected.columns)
assert expected.exceptAll(actual).isEmpty() and actual.exceptAll(expected).isEmpty(), 'Gold diario no reconcilia por fecha/tienda'
hourly = table('gold_hourly_sales').agg(F.sum('reported_total'), F.sum('transactions')).first()
reference = table('silver_checks').agg(F.sum('reported_total'), F.count('*')).first()
assert tuple(hourly) == tuple(reference), 'Gold horario no reconcilia'
display(table('gold_quality_summary'))
display(table('silver_checks_review').limit(100))
print(f'Validación completa: {raw} Bronze, {clean} Silver y {quarantine} cuarentena')
