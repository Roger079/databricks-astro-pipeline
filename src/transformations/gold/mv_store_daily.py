"""Store-day amounts for publishable tickets, not audited net revenue."""
from pyspark import pipelines as dp

@dp.materialized_view(name='gold_daily_sales', cluster_by=['business_date', 'store_id'])
def daily():
    return spark.sql("""SELECT business_date, store_id, is_demo, count(*) transactions,
      sum(reported_total) reported_total, sum(reported_tax) reported_tax,
      sum(reported_discount) reported_discount, avg(reported_total) average_ticket,
      avg(duration_seconds) average_duration_seconds,
      count(duration_seconds) duration_observations,
      sum(duration_seconds) duration_seconds_sum FROM silver_checks
      GROUP BY business_date, store_id, is_demo""")
