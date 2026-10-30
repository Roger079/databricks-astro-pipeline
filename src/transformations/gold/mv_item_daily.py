"""Item units without attributing a full check total to every item."""
from pyspark import pipelines as dp

@dp.materialized_view(name='gold_menu_performance')
def menu():
    return spark.sql("""SELECT p.business_date, p.store_id, p.report_group, p.menu_item, p.is_demo,
      sum(p.quantity) units, count(*) line_count,
      sum(CASE WHEN p.amount_grain = 'line' THEN p.total END) reported_line_total,
      sum(p.item_discount) item_discount FROM silver_pos p INNER JOIN silver_checks c
      ON p.store_id = c.store_id AND p.business_date = c.business_date AND p.check_number = c.check_number
      GROUP BY p.business_date, p.store_id, p.report_group, p.menu_item, p.is_demo""")
