"""Item units without attributing a full check total to every item."""
from pyspark import pipelines as dp

@dp.materialized_view(name='gold_menu_performance')
def menu():
    return spark.sql("""SELECT p.business_date, p.store_id, p.report_group, p.menu_item, p.is_demo,
      sum(CASE WHEN p.record_role IN ('voided_item', 'promo_adjustment', 'unresolved_adjustment') THEN 0 ELSE p.quantity END) units, count(*) line_count,
      sum(CAST(NULL AS DECIMAL(20,4))) reported_line_total,
      sum(p.item_discount) item_discount FROM silver_pos p INNER JOIN silver_checks c
      ON p.store_id = c.store_id AND p.business_date = c.business_date AND p.check_number = c.check_number AND p.is_demo = c.is_demo
      GROUP BY p.business_date, p.store_id, p.report_group, p.menu_item, p.is_demo""")
