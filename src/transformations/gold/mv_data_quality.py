"""Quality and publication coverage before dashboard interpretation."""
from pyspark import pipelines as dp

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
      sum(CASE WHEN duration_status = 'invalid_or_excessive' THEN 1 ELSE 0 END) invalid_duration_rows,
      sum(CASE WHEN duration_status = 'assumed_overnight' THEN 1 ELSE 0 END) assumed_overnight_rows,
      sum(CASE WHEN channel = 'Unknown' THEN 1 ELSE 0 END) unknown_channel_rows,
      max(loaded_at) loaded_at FROM silver_pos_classified
      GROUP BY source_table, is_demo, amount_grain""")

@dp.materialized_view(name='gold_publication_coverage')
def publication_coverage():
    return spark.sql("""SELECT business_date, store_id, is_demo,
      count(*) identifiable_checks,
      sum(CASE WHEN is_publishable THEN 1 ELSE 0 END) published_checks,
      sum(CASE WHEN abs(reconciliation_residual) > 0.011 THEN 1 ELSE 0 END) equation_exception_checks,
      sum(CASE WHEN financial_profile IS NULL THEN 1 ELSE 0 END) unknown_profile_checks,
      sum(CASE WHEN duplicate_lines > 0 THEN 1 ELSE 0 END) checks_with_repeated_rows
      FROM silver_checks_profile GROUP BY business_date, store_id, is_demo""")
