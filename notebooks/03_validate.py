# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Validación de publicación
# MAGIC Detiene el Job si las tablas no reconcilian. Los problemas de los datos se
# MAGIC conservan en cuarentena/revisión y se muestran como cobertura del análisis.
# COMMAND ----------
import re
from pyspark.sql import functions as F
for key, default in [('catalog', 'workspace'), ('schema', 'astro_taco_main_real')]:
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
expected = table('silver_checks').groupBy('business_date', 'store_id', 'is_demo').agg(F.count('*').alias('transactions'), F.sum('reported_total').alias('reported_total'), F.sum('customer_total').alias('customer_total'), F.sum('merchandise_after_discount').alias('merchandise_after_discount'))
actual = table('gold_daily_sales').select(*expected.columns)
assert expected.exceptAll(actual).isEmpty() and actual.exceptAll(expected).isEmpty(), 'Gold diario no reconcilia por fecha/tienda'
hourly = table('gold_hourly_sales').agg(F.sum('reported_total'), F.sum('transactions'), F.sum('customer_total'), F.sum('merchandise_after_discount')).first()
reference = table('silver_checks').agg(F.sum('reported_total'), F.count('*'), F.sum('customer_total'), F.sum('merchandise_after_discount')).first()
assert tuple(hourly) == tuple(reference), 'Gold horario no reconcilia'
channels = table('gold_channel_hourly').agg(F.sum('reported_total'), F.sum('transactions'), F.sum('customer_total'), F.sum('merchandise_after_discount')).first()
assert tuple(channels) == tuple(reference), 'Gold de canales no reconcilia'
coverage = table('gold_publication_coverage').agg(F.sum('identifiable_checks'), F.sum('published_checks')).first()
assert coverage[0] == table('silver_checks_profile').count(), 'Cobertura de tickets no reconcilia'
assert coverage[1] == table('silver_checks').count(), 'Cobertura publicada no reconcilia'
assert table('silver_pos').filter('duration_seconds < 0 OR duration_seconds > 14400').isEmpty(), 'Duraciones fuera del rango documentado'
assert table('bronze_pos').count() == table('silver_pos_typed').count(), 'La unión de perfiles multiplicó filas'
assert table('silver_checks').filter('financial_profile IS NULL OR abs(reconciliation_residual) > 0.011').isEmpty(), 'Ticket sin reconciliar publicado'
assert table('silver_checks').filter('abs(customer_total - merchandise_after_discount - reported_tax) > 0.0001').isEmpty(), 'Importes normalizados no reconcilian con impuestos'
if schema.endswith('_demo'):
    assert (raw, clean, quarantine) == (12, 11, 1), 'Fixture demo inesperado'
    assert table('silver_checks').count() == 5 and table('silver_checks_review').count() == 2
    assert float(reference[0]) == 38.76 and float(reference[2]) == 37.96 and float(reference[3]) == 35.0
display(table('gold_quality_summary'))
display(table('silver_checks_review').limit(100))
print(f'Validación completa: {raw} Bronze, {clean} Silver y {quarantine} cuarentena')
