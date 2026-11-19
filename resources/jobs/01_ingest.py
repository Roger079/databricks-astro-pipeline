# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Snapshot Bronze
# MAGIC Fuente: tabla POS existente. No modifica la fuente. Confirmar si los campos
# MAGIC Total, Tax y Total Discount representan un renglón (`line`) o un ticket (`check`).
# COMMAND ----------
import re
from pyspark.sql import functions as F
for key, default in [('catalog', 'workspace'), ('schema', 'astro_taco_main_real'), ('source_table', 'workspace.default.tb_daily_tld_01_01_2026_m'), ('amount_grain', 'check')]:
    dbutils.widgets.text(key, default)
catalog, schema, source, grain = [dbutils.widgets.get(k) for k in ('catalog', 'schema', 'source_table', 'amount_grain')]
dbutils.widgets.text('team_principals', 'a01236573@tec.mx,a00842807@tec.mx,a01381456@tec.mx')
principals = [p.strip() for p in dbutils.widgets.get('team_principals').split(',') if p.strip()]
assert principals and all(re.fullmatch(r'[A-Za-z0-9_.+@-]+', p) for p in principals), 'Lista de usuarios inválida'
dbutils.widgets.text('expected_pipeline_id', '')
expected_pipeline_id = dbutils.widgets.get('expected_pipeline_id')

def check_pipeline_owners(owners, expected_id):
    for table_name, owner in owners:
        assert expected_id and owner == expected_id, (
            f'Destino ocupado: {table_name} pertenece a pipeline {owner or "sin identificar"}; '
            f'se esperaba {expected_id or "ID no proporcionado"}. Elegir otro esquema antes de escribir Bronze.'
        )
def quote(name, count):
    parts = name.split('.')
    assert len(parts) == count and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', p) for p in parts), f'Identificador inválido: {name}'
    return '.'.join(f'`{p}`' for p in parts)
target = quote(f'{catalog}.{schema}', 2)
assert schema.startswith('astro_'), 'Usar un esquema exclusivo astro_; no escribir en default ni en tablas existentes del equipo'
source_sql = quote(source, 3)
assert grain == 'check', 'Este contrato usa grano check verificado; no interpretar Total como importe de línea'
assert source.lower() != f'{catalog}.{schema}.bronze_pos'.lower()
# Pin the Delta source version so the evidence identifies the exact snapshot read.
source_version = int(spark.sql(f'DESCRIBE HISTORY {source_sql} LIMIT 1').select('version').first()[0])
df = spark.read.option('versionAsOf', source_version).table(source_sql)
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
owners = []
for entry in spark.sql(f'SHOW TABLES IN {target}').collect():
    name = entry['tableName']
    if name.startswith(('silver_', 'gold_')):
        props = {r['key']: r['value'] for r in spark.sql(f'SHOW TBLPROPERTIES {target}.`{name}`').collect()}
        owners.append((name, props.get('pipelines.pipelineId')))
check_pipeline_owners(owners, expected_pipeline_id)
# A grant on workspace.default does not cover sibling astro_* schemas.
# Schema ownership lets the deployer grant the team access without changing ownership.
for principal in principals:
    spark.sql(f'GRANT ALL PRIVILEGES ON SCHEMA {target} TO `{principal}`')
    spark.sql(f'GRANT MANAGE ON SCHEMA {target} TO `{principal}`')
if '_astro_demo' not in df.columns:
    df = df.withColumn('_astro_demo', F.lit(False))
df = (df.withColumn('_astro_source', F.lit(source))
      .withColumn('_astro_source_version', F.lit(source_version))
      .withColumn('_astro_loaded_at', F.current_timestamp())
      .withColumn('_astro_amount_grain', F.lit(grain)))
df.write.format('delta').mode('overwrite').option('overwriteSchema', 'true').saveAsTable(f'{catalog}.{schema}.bronze_pos')
display(spark.table(f'{catalog}.{schema}.bronze_pos').groupBy('_astro_source', '_astro_demo', '_astro_amount_grain').count())
