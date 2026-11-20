CREATE OR REFRESH MATERIALIZED VIEW gold_menu_category_substitution
AS
-- A ticket discount defines an observational cohort. The anchor can be any named item.
WITH item_units AS (
  SELECT p.store_id, p.business_date, p.is_demo, p.report_group, p.menu_item,
         SUM(CASE WHEN c.reported_discount > 0 THEN p.quantity ELSE 0 END) AS discounted_item_units,
         SUM(CASE WHEN c.reported_discount = 0 THEN p.quantity ELSE 0 END) AS zero_discount_item_units
  FROM silver_pos p
  JOIN silver_checks c USING (store_id, business_date, is_demo, check_number)
  WHERE p.record_role IN ('sale_item', 'discounted_item') AND p.quantity > 0 AND p.menu_price > 0
  GROUP BY p.store_id, p.business_date, p.is_demo, p.report_group, p.menu_item
), category_units AS (
  -- Include unnamed eligible lines in their category total.
  SELECT *, SUM(discounted_item_units) OVER (
           PARTITION BY store_id, business_date, is_demo, report_group) AS discounted_category_units,
         SUM(zero_discount_item_units) OVER (
           PARTITION BY store_id, business_date, is_demo, report_group) AS zero_discount_category_units
  FROM item_units
), rates AS (
  SELECT u.*, s.discounted_tickets, s.zero_discount_tickets,
         100.0 * u.discounted_item_units / NULLIF(s.discounted_tickets, 0) AS discounted_item_per_100,
         100.0 * u.zero_discount_item_units / NULLIF(s.zero_discount_tickets, 0) AS zero_discount_item_per_100,
         100.0 * (u.discounted_category_units - u.discounted_item_units)
           / NULLIF(s.discounted_tickets, 0) AS discounted_others_per_100,
         100.0 * (u.zero_discount_category_units - u.zero_discount_item_units)
           / NULLIF(s.zero_discount_tickets, 0) AS zero_discount_others_per_100,
         100.0 * u.discounted_category_units / NULLIF(s.discounted_tickets, 0) AS discounted_category_per_100,
         100.0 * u.zero_discount_category_units / NULLIF(s.zero_discount_tickets, 0) AS zero_discount_category_per_100
  FROM category_units u
  JOIN gold_menu_discount_scorecard s USING (store_id, business_date, is_demo, report_group, menu_item)
)
-- Category totals and cohort sizes repeat for every anchor. Filter to one anchor before pooling counts.
SELECT *, discounted_item_per_100 - zero_discount_item_per_100 AS item_gap_per_100,
       discounted_others_per_100 - zero_discount_others_per_100 AS others_gap_per_100,
       discounted_category_per_100 - zero_discount_category_per_100 AS category_gap_per_100
FROM rates;
