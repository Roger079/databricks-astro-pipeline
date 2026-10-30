# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Lakeflow Silver y Gold
# MAGIC Ejecutar como biblioteca del pipeline Lakeflow. Snapshot batch con materialized
# MAGIC views, expectations y liquid clustering. Sin streaming append sobre snapshots mutables.
# COMMAND ----------
import re
from pyspark import pipelines as dp
catalog, schema = [spark.conf.get(k) for k in ('astro.catalog', 'astro.schema')]
assert all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for x in (catalog, schema))
assert schema.startswith('astro_'), 'Destino exclusivo astro_ requerido'
bronze = f'`{catalog}`.`{schema}`.bronze_pos'

@dp.materialized_view(name='silver_pos_typed')
@dp.expect('valid_date', 'business_date IS NOT NULL')
@dp.expect('valid_total', 'total IS NOT NULL')
def typed():
    return spark.sql(f"""
      SELECT try_cast(store_id AS BIGINT) store_id,
        coalesce(cast(try_to_timestamp(trim(cast(`date` AS STRING)), 'M/d/yyyy') AS DATE),
                 try_cast(`date` AS DATE)) business_date,
        nullif(trim(cast(check_number AS STRING)), '') check_number,
        nullif(trim(cast(menu_item AS STRING)), '') menu_item,
        coalesce(nullif(trim(report_group), ''), 'Unknown') report_group,
        coalesce(nullif(trim(tender_type), ''), 'Unknown') tender_type,
        lower(trim(transaction_type)) transaction_type,
        try_cast(total AS DECIMAL(20,4)) total,
        try_cast(tax AS DECIMAL(20,4)) tax,
        try_cast(total_discount AS DECIMAL(20,4)) total_discount,
        try_cast(menu_price AS DECIMAL(20,4)) menu_price,
        try_cast(item_discount AS DECIMAL(20,4)) item_discount,
        try_cast(item_voided AS DECIMAL(20,4)) item_voided,
        try_cast(order_voided AS DECIMAL(20,4)) order_voided,
        try_cast(quantity AS DECIMAL(20,4)) quantity,
        try_to_timestamp(concat('1970-01-01 ', trim(cast(begin_time AS STRING))), 'yyyy-MM-dd HH:mm:ss[.SSSSSS]') begin_time,
        try_to_timestamp(concat('1970-01-01 ', trim(cast(end_time AS STRING))), 'yyyy-MM-dd HH:mm:ss[.SSSSSS]') end_time,
        sha2(to_json(struct(*)), 256) source_row_hash,
        _astro_amount_grain amount_grain, _astro_demo is_demo,
        _astro_loaded_at loaded_at, _astro_source source_table
      FROM {bronze}
    """)

@dp.materialized_view(name='silver_pos_classified')
def classified():
    return spark.sql("""
      SELECT *,
        store_id IS NOT NULL AND business_date IS NOT NULL AND check_number IS NOT NULL
        AND total IS NOT NULL AND tax IS NOT NULL AND total_discount IS NOT NULL
        AND quantity IS NOT NULL AND menu_price IS NOT NULL AND item_discount IS NOT NULL
        AND item_voided IS NOT NULL AND order_voided IS NOT NULL AS valid_record,
        count(*) OVER (PARTITION BY source_row_hash) identical_row_count,
        total < 0 OR tax < 0 OR total_discount < 0 OR menu_price < 0 OR item_discount < 0
        OR quantity <= 0 OR quantity > 100 OR total > 1000 OR menu_price > 500
        OR item_voided != 0 OR order_voided != 0 AS financial_review,
        CASE WHEN begin_time IS NULL OR end_time IS NULL THEN NULL ELSE
          pmod(unix_micros(end_time) - unix_micros(begin_time), 86400000000) / 1000000.0 END duration_seconds,
        nullif(concat_ws('; ',
          CASE WHEN store_id IS NULL THEN 'invalid_store' END,
          CASE WHEN business_date IS NULL THEN 'invalid_date' END,
          CASE WHEN check_number IS NULL THEN 'missing_check_number' END,
          CASE WHEN total IS NULL OR tax IS NULL OR total_discount IS NULL THEN 'invalid_check_amount' END,
          CASE WHEN quantity IS NULL OR menu_price IS NULL OR item_discount IS NULL
            OR item_voided IS NULL OR order_voided IS NULL THEN 'invalid_item_amount_or_quantity' END), '') reject_reason
      FROM silver_pos_typed
    """)

@dp.materialized_view(name='silver_pos_quarantine')
def quarantine():
    return spark.sql('SELECT * FROM silver_pos_classified WHERE NOT valid_record')

@dp.materialized_view(name='silver_pos', cluster_by=['business_date', 'store_id'])
@dp.expect_all_or_fail({'valid_key': 'store_id IS NOT NULL AND business_date IS NOT NULL AND check_number IS NOT NULL', 'valid_total': 'total IS NOT NULL'})
def clean():
    return spark.sql('SELECT * FROM silver_pos_classified WHERE valid_record')

@dp.materialized_view(name='silver_checks_profile')
def profile():
    return spark.sql("""
      SELECT store_id, business_date, check_number, amount_grain, is_demo,
        count(*) line_count, min(total) min_total, max(total) max_total,
        min(tax) min_tax, max(tax) max_tax,
        min(total_discount) min_discount, max(total_discount) max_discount,
        sum(total) sum_total, sum(tax) sum_tax, sum(total_discount) sum_discount,
        max(CASE WHEN NOT valid_record THEN 1 ELSE 0 END) invalid_lines,
        max(CASE WHEN financial_review THEN 1 ELSE 0 END) review_lines,
        max(CASE WHEN identical_row_count > 1 THEN 1 ELSE 0 END) duplicate_lines,
        min(hour(begin_time)) start_hour, max(duration_seconds) duration_seconds,
        count(DISTINCT tender_type) tender_types, max(tender_type) tender_type
      FROM silver_pos_classified
      WHERE store_id IS NOT NULL AND business_date IS NOT NULL AND check_number IS NOT NULL
      GROUP BY store_id, business_date, check_number, amount_grain, is_demo
    """)

# Every identifiable ticket is either published or retained for review.
publishable = """invalid_lines = 0 AND review_lines = 0 AND duplicate_lines = 0
  AND (amount_grain = 'line' OR (amount_grain = 'check' AND min_total = max_total
  AND min_tax = max_tax AND min_discount = max_discount))"""

@dp.materialized_view(name='silver_checks_review')
def review():
    return spark.sql(f'SELECT * FROM silver_checks_profile WHERE NOT ({publishable})')

@dp.materialized_view(name='silver_checks', cluster_by=['business_date', 'store_id'])
def checks():
    return spark.sql(f"""SELECT *,
      CASE WHEN amount_grain = 'check' THEN max_total ELSE sum_total END reported_total,
      CASE WHEN amount_grain = 'check' THEN max_tax ELSE sum_tax END reported_tax,
      CASE WHEN amount_grain = 'check' THEN max_discount ELSE sum_discount END reported_discount
      FROM silver_checks_profile WHERE {publishable}""")

@dp.materialized_view(name='gold_daily_sales', cluster_by=['business_date', 'store_id'])
def daily():
    return spark.sql("""SELECT business_date, store_id, is_demo, count(*) transactions,
      sum(reported_total) reported_total, sum(reported_tax) reported_tax,
      sum(reported_discount) reported_discount, avg(reported_total) average_ticket,
      avg(duration_seconds) average_duration_seconds FROM silver_checks
      GROUP BY business_date, store_id, is_demo""")

@dp.materialized_view(name='gold_hourly_sales')
def hourly():
    return spark.sql("""SELECT business_date, dayofweek(business_date) weekday_sunday_1,
      start_hour, store_id, is_demo, count(*) transactions, sum(reported_total) reported_total
      FROM silver_checks GROUP BY business_date, dayofweek(business_date), start_hour, store_id, is_demo""")

@dp.materialized_view(name='gold_menu_performance')
def menu():
    return spark.sql("""SELECT p.business_date, p.store_id, p.report_group, p.menu_item, p.is_demo,
      sum(p.quantity) units, count(*) line_count,
      sum(CASE WHEN p.amount_grain = 'line' THEN p.total END) reported_line_total,
      sum(p.item_discount) item_discount FROM silver_pos p INNER JOIN silver_checks c
      ON p.store_id = c.store_id AND p.business_date = c.business_date AND p.check_number = c.check_number
      GROUP BY p.business_date, p.store_id, p.report_group, p.menu_item, p.is_demo""")

@dp.materialized_view(name='gold_quality_summary')
def quality():
    return spark.sql("""SELECT source_table, is_demo, amount_grain, count(*) source_rows,
      sum(CASE WHEN NOT valid_record THEN 1 ELSE 0 END) quarantined_rows,
      sum(CASE WHEN financial_review THEN 1 ELSE 0 END) financial_review_rows,
      sum(CASE WHEN identical_row_count > 1 THEN 1 ELSE 0 END) duplicate_candidate_rows,
      sum(CASE WHEN report_group = 'Unknown' THEN 1 ELSE 0 END) unknown_category_rows,
      sum(CASE WHEN tender_type = 'Unknown' THEN 1 ELSE 0 END) unknown_payment_rows,
      sum(CASE WHEN menu_item IS NULL THEN 1 ELSE 0 END) missing_menu_item_rows,
      sum(CASE WHEN duration_seconds IS NULL THEN 1 ELSE 0 END) missing_duration_rows,
      max(loaded_at) loaded_at FROM silver_pos_classified
      GROUP BY source_table, is_demo, amount_grain""")
