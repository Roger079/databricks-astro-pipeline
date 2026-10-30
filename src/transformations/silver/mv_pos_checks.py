"""Profile and publish each store/date/check once."""
from pyspark import pipelines as dp

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
        min(hour(begin_time)) start_hour,
        CASE WHEN count(duration_seconds) = count(*) THEN max(duration_seconds) END duration_seconds,
        max(CASE WHEN duration_status = 'assumed_overnight' THEN 1 ELSE 0 END) assumed_overnight,
        CASE WHEN count(DISTINCT channel) = 1 THEN max(channel) ELSE 'Mixed/Unknown' END channel,
        count(DISTINCT tender_type) tender_types, max(tender_type) tender_type
      FROM silver_pos_classified
      WHERE store_id IS NOT NULL AND business_date IS NOT NULL AND check_number IS NOT NULL
      GROUP BY store_id, business_date, check_number, amount_grain, is_demo
    """)

# Identical rows are diagnostic candidates, not proof of ingestion duplication.
# Keep legitimate repeated items and count their check total exactly once.
publishable = """invalid_lines = 0 AND review_lines = 0
  AND (amount_grain = 'line' OR (amount_grain = 'check' AND min_total = max_total
  AND min_tax = max_tax AND min_discount = max_discount))"""

@dp.materialized_view(name='silver_checks_review')
def review():
    return spark.sql(f"""SELECT *, concat_ws('; ',
      CASE WHEN invalid_lines > 0 THEN 'invalid_record' END,
      CASE WHEN review_lines > 0 THEN 'financial_or_transaction_type_review' END,
      CASE WHEN amount_grain = 'check' AND
        (min_total != max_total OR min_tax != max_tax OR min_discount != max_discount)
        THEN 'inconsistent_check_amounts' END,
      CASE WHEN amount_grain NOT IN ('check', 'line') OR amount_grain IS NULL
        THEN 'unconfirmed_amount_grain' END) review_reason
      FROM silver_checks_profile WHERE NOT ({publishable})""")

@dp.materialized_view(name='silver_checks', cluster_by=['business_date', 'store_id'])
def checks():
    return spark.sql(f"""SELECT *,
      CASE WHEN amount_grain = 'check' THEN max_total ELSE sum_total END reported_total,
      CASE WHEN amount_grain = 'check' THEN max_tax ELSE sum_tax END reported_tax,
      CASE WHEN amount_grain = 'check' THEN max_discount ELSE sum_discount END reported_discount
      FROM silver_checks_profile WHERE {publishable}""")
