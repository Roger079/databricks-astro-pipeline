# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Snapshot Bronze
# MAGIC Fuente: tabla POS existente. No modifica la fuente. Confirmar si los campos
# MAGIC Total, Tax y Total Discount representan un renglón (`line`) o un ticket (`check`).
# COMMAND ----------
import re
from pyspark.sql import functions as F
for key, default in [('catalog', 'workspace'), ('schema', 'astro_taco_dev'), ('source_table', 'workspace.default.tb_daily_tld_01_01_2026_m'), ('amount_grain', 'unconfirmed')]:
    dbutils.widgets.text(key, default)
catalog, schema, source, grain = [dbutils.widgets.get(k) for k in ('catalog', 'schema', 'source_table', 'amount_grain')]
dbutils.widgets.text('team_principals', 'a01236573@tec.mx,a00842807@tec.mx,a01381456@tec.mx')
principals = [p.strip() for p in dbutils.widgets.get('team_principals').split(',') if p.strip()]
assert principals and all(re.fullmatch(r'[A-Za-z0-9_.+@-]+', p) for p in principals), 'Lista de usuarios inválida'
def quote(name, count):
    parts = name.split('.')
    assert len(parts) == count and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', p) for p in parts), f'Identificador inválido: {name}'
    return '.'.join(f'`{p}`' for p in parts)
target = quote(f'{catalog}.{schema}', 2)
assert schema.startswith('astro_'), 'Usar un esquema exclusivo astro_; no escribir en default ni en tablas existentes del equipo'
source_sql = quote(source, 3)
assert grain in ('line', 'check'), 'Confirmar amount_grain: line o check'
assert source.lower() != f'{catalog}.{schema}.bronze_pos'.lower()
df = spark.table(source_sql)
required = {'Store #', 'Date', 'Check Number', 'Total', 'Tax', 'Total Discount', 'Menu Item', 'Menu Price', 'Item Discount', 'Item Voided', 'Order Voided', 'Quantity', 'Transaction Type', 'Begin Time', 'End Time', 'Report Group', 'Tender Type'}
assert not required - set(df.columns), f'Columnas faltantes: {required - set(df.columns)}'
assert not any(c.startswith('_astro_') and c != '_astro_demo' for c in df.columns), 'Prefijo reservado _astro_'
assert not df.isEmpty(), 'Fuente vacía; no se reemplaza Bronze'
# Stable Delta-safe names: original source has spaces and '#'. TIME(6) is encoded
# as text at this boundary, preserving fractions without requiring TIME on Bronze.
names = {c: (c if c == '_astro_demo' else 'store_id' if c == 'Store #' else re.sub(r'[^a-z0-9_]+', '_', c.lower()).strip('_')) for c in df.columns}
assert all(names.values()) and len(set(names.values())) == len(names), 'Colisiones al normalizar nombres'
df = df.select(*[(F.col(f'`{c}`').cast('string') if c in ('Begin Time', 'End Time') else F.col(f'`{c}`')).alias(names[c]) for c in df.columns])
# Pop is optional for older extracts and the synthetic fixture. Do not infer a channel.
if 'pop' not in df.columns:
    df = df.withColumn('pop', F.lit(None).cast('string'))
spark.sql(f'CREATE SCHEMA IF NOT EXISTS {target}')
# A grant on workspace.default does not cover sibling astro_* schemas.
# Schema ownership lets the deployer grant the team access without changing ownership.
for principal in principals:
    spark.sql(f'GRANT ALL PRIVILEGES ON SCHEMA {target} TO `{principal}`')
    spark.sql(f'GRANT MANAGE ON SCHEMA {target} TO `{principal}`')
if '_astro_demo' not in df.columns:
    df = df.withColumn('_astro_demo', F.lit(False))
df = (df.withColumn('_astro_source', F.lit(source))
      .withColumn('_astro_loaded_at', F.current_timestamp())
      .withColumn('_astro_amount_grain', F.lit(grain)))
df.write.format('delta').mode('overwrite').option('overwriteSchema', 'true').saveAsTable(f'{catalog}.{schema}.bronze_pos')
display(spark.table(f'{catalog}.{schema}.bronze_pos').groupBy('_astro_source', '_astro_demo', '_astro_amount_grain').count())
