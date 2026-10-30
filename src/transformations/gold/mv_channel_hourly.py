"""Hourly demand and channel coverage."""
from pyspark import pipelines as dp

@dp.materialized_view(name='gold_hourly_sales')
def hourly():
    return spark.sql("""SELECT business_date, dayofweek(business_date) weekday_sunday_1,
      start_hour, store_id, is_demo, count(*) transactions, sum(reported_total) reported_total,
      sum(customer_total) customer_total, sum(merchandise_after_discount) merchandise_after_discount
      FROM silver_checks GROUP BY business_date, dayofweek(business_date), start_hour, store_id, is_demo""")

@dp.materialized_view(name='gold_channel_hourly')
def channel_hourly():
    return spark.sql("""SELECT business_date, store_id, start_hour, channel, is_demo,
      count(*) transactions, sum(reported_total) reported_total,
      sum(customer_total) customer_total, sum(merchandise_after_discount) merchandise_after_discount
      FROM silver_checks GROUP BY business_date, store_id, start_hour, channel, is_demo""")
