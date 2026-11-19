# Databricks notebook source
# MAGIC %md
# MAGIC # Synthetic fixture for both observed accounting conventions
# MAGIC Same date scope as the real extract; synthetic store IDs and is_demo=true.
# COMMAND ----------
import re
from pyspark.sql import functions as F
for k, v in [('catalog', 'workspace'), ('schema', 'astro_taco_main_demo')]:
    dbutils.widgets.text(k, v)
catalog, schema = [dbutils.widgets.get(k) for k in ('catalog', 'schema')]
assert all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for x in (catalog, schema))
assert schema.endswith('_demo')
spark.sql(f'CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`')
columns = ['Store #', 'Date', 'Check Number', 'Begin Time', 'End Time', 'Total', 'Tax', 'Total Discount', 'Order Voided', 'Menu Item', 'Menu Price', 'Item Discount', 'Item Voided', 'Quantity', 'Transaction Type', 'Report Group', 'Tender Type']
rows = [
 ('1','12/31/2025','100','10:00:00','10:03:00','10.8','0.8','0','0','Taco','5','0','0','1','Regular Sale','Tacos','Cash'),
 ('1','12/31/2025','100','10:00:00','10:03:00','10.8','0.8','0','0','Taco','5','0','0','1','Regular Sale','Tacos','Cash'),
 ('1','1/1/2026','101','23:59:00','00:02:00','8.64','0.64','2','0','Burrito','10','0','0','1','Regular Sale',None,None),
 ('2','12/31/2025','200','11:00:00','11:03:00','10','0.8','2','0','Taco','5','2','0','2','Discount','Tacos','Card'),
 ('2','12/31/2025','200','11:00:00','11:03:00','10','0.8','2','0','Modifier','99','0','0','0','Regular Sale','Other','Card'),
 ('1','1/1/2026','102','12:00:00','12:02:00','4.32','0.32','0','0','Taco','5','0','0','1','Regular Sale','Tacos','Card'),
 ('1','1/1/2026','102','12:00:00','12:02:00','4.32','0.32','0','0','Item Promo','-1','0','0','1','Regular Sale','Other','Card'),
 ('2','1/1/2026','201','13:00:00','13:02:00','5','0.4','0','0','Burrito','5','0','0','1','Regular Sale','Burritos','Card'),
 ('2','1/1/2026','201','13:00:00','13:02:00','5','0.4','0','0','Taco','0','0','3','1','Void','Tacos','Card'),
 ('2','bad-date','202','14:00:00','14:02:00','5','0.4','0','0','Taco','5','0','0','1','Regular Sale','Tacos','Card'),
 ('3','1/1/2026','300','14:00:00','14:02:00','5','0.4','0','0','Taco','5','0','0','1','Regular Sale','Tacos','Card'),
 ('2','1/1/2026','203','14:00:00','14:02:00','9','0.4','0','0','Taco','5','0','0','1','Regular Sale','Tacos','Card'),
]
spark.createDataFrame(rows, columns).withColumn('_astro_demo', F.lit(True)).write.format('delta').mode('overwrite').option('overwriteSchema', 'true').option('delta.columnMapping.mode', 'name').saveAsTable(f'{catalog}.{schema}.demo_pos_source')
# Expected: 12 Bronze, 11 Silver, 1 quarantine; 5 published, 2 review.
# Source total 38.76; normalized customer total 37.96; merchandise after discount 35.
print(f'source_table={catalog}.{schema}.demo_pos_source; amount_grain=check')
