CREATE OR REFRESH MATERIALIZED VIEW gold_menu_discount_comparison
AS
WITH per_store AS (
  SELECT is_demo, report_group, menu_item, store_id,
         COUNT(*) AS observed_days, MIN(business_date) AS first_date, MAX(business_date) AS last_date,
         SUM(discounted_with_item) AS discounted_with_item, SUM(discounted_tickets) AS discounted_tickets,
         SUM(zero_discount_with_item) AS zero_discount_with_item, SUM(zero_discount_tickets) AS zero_discount_tickets,
         AVG(gap_percentage_points) AS mean_daily_gap
  FROM gold_menu_discount_scorecard
  WHERE discounted_tickets > 0 AND zero_discount_tickets > 0
  GROUP BY is_demo, report_group, menu_item, store_id
)
SELECT is_demo, report_group, menu_item, COUNT(*) AS comparable_stores,
       SUM(observed_days) AS comparable_store_days, MIN(first_date) AS first_date, MAX(last_date) AS last_date,
       SUM(CASE WHEN mean_daily_gap > 0 THEN 1 ELSE 0 END) AS stores_higher,
       SUM(CASE WHEN mean_daily_gap < 0 THEN 1 ELSE 0 END) AS stores_lower,
       SUM(CASE WHEN mean_daily_gap = 0 THEN 1 ELSE 0 END) AS stores_equal,
       SUM(discounted_with_item) AS discounted_with_item, SUM(discounted_tickets) AS discounted_tickets,
       SUM(zero_discount_with_item) AS zero_discount_with_item, SUM(zero_discount_tickets) AS zero_discount_tickets,
       100.0 * SUM(discounted_with_item) / SUM(discounted_tickets) AS discounted_per_100,
       100.0 * SUM(zero_discount_with_item) / SUM(zero_discount_tickets) AS zero_discount_per_100
FROM per_store
GROUP BY is_demo, report_group, menu_item;
