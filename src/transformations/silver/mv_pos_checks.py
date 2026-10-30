"""Reconcile tickets against versioned store semantics before publishing money."""
from pyspark import pipelines as dp

@dp.materialized_view(name='silver_checks_profile')
def profile():
    return spark.sql("""
      WITH aggregated AS (
        SELECT store_id, business_date, check_number, amount_grain, is_demo,
          max(financial_profile) financial_profile, max(rule_version) rule_version,
          count(*) line_count, min(total) min_total, max(total) max_total,
          min(tax) min_tax, max(tax) max_tax,
          min(total_discount) min_discount, max(total_discount) max_discount,
          sum(menu_price) sum_menu_price,
          sum(menu_price * quantity) sum_extended_price, sum(item_voided) sum_item_voided,
          sum(item_discount) sum_item_discount,
          max(CASE WHEN NOT valid_record THEN 1 ELSE 0 END) invalid_lines,
          max(CASE WHEN financial_review THEN 1 ELSE 0 END) review_lines,
          max(CASE WHEN identical_row_count > 1 THEN 1 ELSE 0 END) duplicate_lines,
          min(hour(begin_time)) start_hour,
          CASE WHEN count(duration_seconds) = count(*) THEN max(duration_seconds) END duration_seconds,
          max(CASE WHEN duration_status = 'assumed_overnight' THEN 1 ELSE 0 END) assumed_overnight,
          CASE WHEN count(DISTINCT channel) = 1 THEN max(channel) ELSE 'Mixed/Unknown' END channel
        FROM silver_pos_classified
        WHERE store_id IS NOT NULL AND business_date IS NOT NULL AND check_number IS NOT NULL
        GROUP BY store_id, business_date, check_number, amount_grain, is_demo
      ), amounts AS (
        SELECT *,
          CASE financial_profile
            WHEN 'A_TAX_INCLUSIVE' THEN max_total - sum_menu_price + sum_item_voided + max_discount - max_tax
            WHEN 'B_PRE_DISCOUNT' THEN max_total - sum_extended_price END reconciliation_residual,
          CASE financial_profile
            WHEN 'A_TAX_INCLUSIVE' THEN max_total - max_tax
            WHEN 'B_PRE_DISCOUNT' THEN max_total - max_discount END merchandise_after_discount,
          CASE financial_profile
            WHEN 'A_TAX_INCLUSIVE' THEN max_total
            WHEN 'B_PRE_DISCOUNT' THEN max_total - max_discount + max_tax END customer_total
        FROM aggregated
      ), verdict AS (
        SELECT *, concat_ws('; ',
          CASE WHEN invalid_lines > 0 THEN 'invalid_record' END,
          CASE WHEN review_lines > 0 THEN 'unresolved_financial_record' END,
          CASE WHEN min_total != max_total OR min_tax != max_tax OR min_discount != max_discount
            THEN 'inconsistent_check_amounts' END,
          CASE WHEN amount_grain IS NULL OR amount_grain != 'check' THEN 'unsupported_amount_grain' END,
          CASE WHEN financial_profile IS NULL THEN 'unknown_store_profile_or_date' END,
          CASE WHEN abs(reconciliation_residual) > 0.011 THEN 'accounting_equation_mismatch' END,
          CASE WHEN financial_profile = 'B_PRE_DISCOUNT' AND abs(max_discount - sum_item_discount) > 0.011
            THEN 'discount_reconciliation_mismatch' END,
          CASE WHEN merchandise_after_discount < 0 OR customer_total < 0 THEN 'negative_normalized_amount' END,
          CASE WHEN max_total = 0 AND max_tax > 0 THEN 'zero_source_total_positive_tax' END
        ) review_reason
        FROM amounts
      )
      SELECT *, length(review_reason) = 0 is_publishable FROM verdict
    """)

@dp.materialized_view(name='silver_checks_review')
def review():
    return spark.sql('SELECT * FROM silver_checks_profile WHERE NOT is_publishable')

@dp.materialized_view(name='silver_checks', cluster_by=['business_date', 'store_id'])
@dp.expect_all_or_fail({'reconciled': 'abs(reconciliation_residual) <= 0.011',
                      'known_profile': 'financial_profile IS NOT NULL'})
def checks():
    return spark.sql("""SELECT *, max_total reported_total, max_tax reported_tax,
      max_discount reported_discount FROM silver_checks_profile WHERE is_publishable""")
