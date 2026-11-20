CREATE OR REFRESH MATERIALIZED VIEW gold_menu_discount_comparison
AS
WITH comparable_days AS (
  SELECT is_demo, store_id, business_date,
         SUM(CASE WHEN reported_discount > 0 THEN 1 ELSE 0 END) AS discounted_tickets,
         SUM(CASE WHEN reported_discount = 0 THEN 1 ELSE 0 END) AS zero_discount_tickets
  FROM silver_checks
  GROUP BY is_demo, store_id, business_date
  HAVING SUM(CASE WHEN reported_discount > 0 THEN 1 ELSE 0 END) > 0
     AND SUM(CASE WHEN reported_discount = 0 THEN 1 ELSE 0 END) > 0
), coverage AS (
  SELECT is_demo, COUNT(DISTINCT store_id) AS comparable_stores,
         COUNT(*) AS comparable_store_days, MIN(business_date) AS first_date, MAX(business_date) AS last_date,
         SUM(discounted_tickets) AS discounted_tickets, SUM(zero_discount_tickets) AS zero_discount_tickets
  FROM comparable_days
  GROUP BY is_demo
), per_store AS (
  -- A missing item contributes zero to both numerators. Coverage counts those days separately.
  SELECT s.is_demo, s.report_group, s.menu_item, s.store_id,
         SUM(s.discounted_with_item) AS discounted_with_item,
         SUM(s.zero_discount_with_item) AS zero_discount_with_item,
         SUM(1.0 * d.discounted_tickets * s.zero_discount_with_item / d.zero_discount_tickets)
           AS matched_zero_discount_count
  FROM gold_menu_discount_scorecard s
  JOIN comparable_days d USING (is_demo, store_id, business_date)
  GROUP BY s.is_demo, s.report_group, s.menu_item, s.store_id
), item_totals AS (
  SELECT is_demo, report_group, menu_item,
         SUM(CASE WHEN discounted_with_item - matched_zero_discount_count > 0.000001 THEN 1 ELSE 0 END) AS stores_higher,
         SUM(CASE WHEN discounted_with_item - matched_zero_discount_count < -0.000001 THEN 1 ELSE 0 END) AS stores_lower,
         SUM(discounted_with_item) AS discounted_with_item,
         SUM(zero_discount_with_item) AS zero_discount_with_item,
         SUM(matched_zero_discount_count) AS matched_zero_discount_count
  FROM per_store
  GROUP BY is_demo, report_group, menu_item
)
SELECT i.is_demo, i.report_group, i.menu_item, c.comparable_stores, c.comparable_store_days,
       c.first_date, c.last_date, i.stores_higher, i.stores_lower,
       c.comparable_stores - i.stores_higher - i.stores_lower AS stores_equal,
       i.discounted_with_item, c.discounted_tickets, i.zero_discount_with_item, c.zero_discount_tickets,
       100.0 * i.discounted_with_item / c.discounted_tickets AS discounted_per_100,
       100.0 * i.matched_zero_discount_count / c.discounted_tickets AS zero_discount_per_100,
       100.0 * i.zero_discount_with_item / c.zero_discount_tickets AS unadjusted_zero_discount_per_100,
       100.0 * (i.discounted_with_item - i.matched_zero_discount_count) / c.discounted_tickets AS matched_gap_pp
FROM item_totals i JOIN coverage c USING (is_demo);
