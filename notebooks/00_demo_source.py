# Databricks notebook source
# MAGIC %md
# MAGIC # Datos sintéticos para probar el flujo
# MAGIC Ejecutar manualmente antes del Job en un esquema exclusivo terminado en `_demo`.
# MAGIC No son ventas reales. Los totales de ticket se repiten por renglón: amount_grain=check.
# COMMAND ----------
import re
from pyspark.sql import functions as F
for k, v in [('catalog', 'workspace'), ('schema', 'astro_taco_demo')]:
    dbutils.widgets.text(k, v)
catalog, schema = [dbutils.widgets.get(k) for k in ('catalog', 'schema')]
assert all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for x in (catalog, schema))
assert schema.endswith('_demo'), 'Usar un esquema exclusivo de demo'
spark.sql(f'CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`')
columns = ['Store #', 'Date', 'Check Number', 'Begin Time', 'End Time', 'Total', 'Tax', 'Total Discount', 'Order Voided', 'Menu Item', 'Menu Price', 'Item Discount', 'Item Voided', 'Quantity', 'Transaction Type', 'Report Group', 'Tender Type']
rows = [
 ('1','1/22/2025','100','10:00:00','10:03:00','10','0.8','0','0','Taco','5','0','0','2','Sale','Tacos','Cash'),
 ('1','1/22/2025','100','10:00:00','10:03:00','10','0.8','0','0','Drink','2','0','0','1','Sale','Drinks','Cash'),
 ('1','1/23/2025','101','23:59:00','00:02:00','8','0.64','1','0','Burrito','8','1','0','1','Sale',None,None),
 ('2','bad-date','102','11:00:00','11:01:00','5','0.4','0','0','Taco','5','0','0','1','Sale','Tacos','Card'),
 ('2','1/23/2025','103','16:00:00','16:01:00','-5','-0.4','0','0','Taco','-5','0','0','1','Refund','Tacos','Card'),
 ('2','1/23/2025','104','17:00:00','17:01:00','0','0','0','5','Taco','5','0','5','0','Sale','Tacos','Card'),
 ('2','1/23/2025','105','17:00:00','17:01:00','5','0.4','0','0','Taco','5','0','0','1','Sale','Tacos','Card'),
]
rows.append(rows[-1])  # Candidate duplicate, requires review; never silently drop.
spark.createDataFrame(rows, columns).withColumn('_astro_demo', F.lit(True)).write.format('delta').mode('overwrite').option('overwriteSchema', 'true').option('delta.columnMapping.mode', 'name').saveAsTable(f'{catalog}.{schema}.demo_pos_source')
print(f'source_table={catalog}.{schema}.demo_pos_source; amount_grain=check')
# Expected: 8 source rows, 1 quarantine row, 2 published tickets, reported_total=18.
