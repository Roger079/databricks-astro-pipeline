"""Classify quality without deleting repeated item occurrences."""
from pyspark import pipelines as dp

@dp.materialized_view(name='silver_pos_classified')
def classified():
    return spark.sql("""
      WITH measured AS (
        SELECT *, (unix_micros(end_time) - unix_micros(begin_time)) / 1000000.0 raw_duration
        FROM silver_pos_typed
      )
      SELECT *,
        store_id IS NOT NULL AND business_date IS NOT NULL AND check_number IS NOT NULL
        AND total IS NOT NULL AND tax IS NOT NULL AND total_discount IS NOT NULL
        AND quantity IS NOT NULL AND menu_price IS NOT NULL AND item_discount IS NOT NULL
        AND item_voided IS NOT NULL AND order_voided IS NOT NULL AS valid_record,
        count(*) OVER (PARTITION BY source_row_hash) identical_row_count,
        total < 0 OR tax < 0 OR total_discount < 0 OR menu_price < 0 OR item_discount < 0
        OR quantity <= 0 OR quantity > 100 OR total > 1000 OR menu_price > 500
        OR item_voided != 0 OR order_voided != 0
        OR transaction_type IS NULL OR transaction_type NOT IN ('sale', 'regular sale') AS financial_review,
        -- A negative clock difference is not sufficient evidence of midnight rollover.
        -- Four hours is a provisional service-time bound, not a financial exclusion.
        CASE WHEN raw_duration BETWEEN 0 AND 14400 THEN raw_duration
          WHEN raw_duration < 0 AND hour(begin_time) >= 20 AND hour(end_time) <= 4
            AND raw_duration + 86400 BETWEEN 0 AND 14400 THEN raw_duration + 86400
          ELSE NULL END duration_seconds,
        CASE WHEN begin_time IS NULL OR end_time IS NULL THEN 'missing_or_unparseable'
          WHEN raw_duration BETWEEN 0 AND 14400 THEN 'valid_same_day'
          WHEN raw_duration < 0 AND hour(begin_time) >= 20 AND hour(end_time) <= 4
            AND raw_duration + 86400 BETWEEN 0 AND 14400 THEN 'assumed_overnight'
          ELSE 'invalid_or_excessive' END duration_status,
        nullif(concat_ws('; ',
          CASE WHEN store_id IS NULL THEN 'invalid_store' END,
          CASE WHEN business_date IS NULL THEN 'invalid_date' END,
          CASE WHEN check_number IS NULL THEN 'missing_check_number' END,
          CASE WHEN total IS NULL OR tax IS NULL OR total_discount IS NULL THEN 'invalid_check_amount' END,
          CASE WHEN quantity IS NULL OR menu_price IS NULL OR item_discount IS NULL
            OR item_voided IS NULL OR order_voided IS NULL THEN 'invalid_item_amount_or_quantity' END), '') reject_reason
      FROM measured
    """)

@dp.materialized_view(name='silver_pos_quarantine')
def quarantine():
    return spark.sql('SELECT * FROM silver_pos_classified WHERE NOT valid_record')

@dp.materialized_view(name='silver_pos', cluster_by=['business_date', 'store_id'])
@dp.expect_all_or_fail({'valid_key': 'store_id IS NOT NULL AND business_date IS NOT NULL AND check_number IS NOT NULL', 'valid_total': 'total IS NOT NULL'})
def clean():
    return spark.sql('SELECT * FROM silver_pos_classified WHERE valid_record')
