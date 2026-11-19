CREATE OR REFRESH MATERIALIZED VIEW gold_menu_discount_scorecard
AS
WITH cohort_sizes AS (
  SELECT store_id, business_date, is_demo,
         SUM(CASE WHEN reported_discount > 0 THEN 1 ELSE 0 END) AS discounted_tickets,
         SUM(CASE WHEN reported_discount = 0 THEN 1 ELSE 0 END) AS zero_discount_tickets
  FROM silver_checks
  GROUP BY store_id, business_date, is_demo
),
item_presence AS (
  -- Count a named item once per basket, regardless of quantity or repeated lines.
  SELECT DISTINCT p.store_id, p.business_date, p.is_demo, p.check_number,
         p.report_group, p.menu_item, c.reported_discount
  FROM silver_pos p
  INNER JOIN silver_checks c USING (store_id, business_date, is_demo, check_number)
  WHERE p.record_role IN ('sale_item', 'discounted_item')
    AND p.quantity > 0 AND p.menu_price > 0 AND p.menu_item IS NOT NULL
),
item_counts AS (
  SELECT store_id, business_date, is_demo, report_group, menu_item,
         SUM(CASE WHEN reported_discount > 0 THEN 1 ELSE 0 END) AS discounted_with_item,
         SUM(CASE WHEN reported_discount = 0 THEN 1 ELSE 0 END) AS zero_discount_with_item
  FROM item_presence
  GROUP BY store_id, business_date, is_demo, report_group, menu_item
),
rates AS (
  SELECT i.*, c.discounted_tickets, c.zero_discount_tickets,
         100.0 * i.discounted_with_item / NULLIF(c.discounted_tickets, 0) AS discounted_per_100,
         100.0 * i.zero_discount_with_item / NULLIF(c.zero_discount_tickets, 0) AS zero_discount_per_100
  FROM item_counts i
  INNER JOIN cohort_sizes c USING (store_id, business_date, is_demo)
)
SELECT *, discounted_per_100 - zero_discount_per_100 AS gap_percentage_points
FROM rates;
