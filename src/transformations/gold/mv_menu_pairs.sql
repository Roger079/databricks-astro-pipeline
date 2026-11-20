CREATE OR REFRESH MATERIALIZED VIEW gold_menu_pairs
AS
WITH basket_items AS (
  SELECT DISTINCT p.store_id, p.business_date, p.is_demo, p.check_number,
         p.report_group, p.menu_item
  FROM silver_pos p
  JOIN silver_checks c USING (store_id, business_date, is_demo, check_number)
  WHERE p.record_role IN ('sale_item', 'discounted_item')
    AND p.quantity > 0 AND p.menu_price > 0 AND p.menu_item IS NOT NULL
), pairs AS (
  -- Both directions are useful: P(drink | taco) has a different denominator from P(taco | drink).
  SELECT a.store_id, a.business_date, a.is_demo,
         a.report_group, a.menu_item, b.report_group AS companion_group, b.menu_item AS companion_item,
         COUNT(*) AS pair_tickets
  FROM basket_items a
  JOIN basket_items b USING (store_id, business_date, is_demo, check_number)
  WHERE a.report_group <> b.report_group OR a.menu_item <> b.menu_item
  GROUP BY a.store_id, a.business_date, a.is_demo, a.report_group, a.menu_item, b.report_group, b.menu_item
), frequencies AS (
  SELECT store_id, business_date, is_demo, report_group, menu_item,
         discounted_with_item + zero_discount_with_item AS item_tickets,
         discounted_tickets + zero_discount_tickets AS published_tickets
  FROM gold_menu_discount_scorecard
)
SELECT p.*, a.item_tickets AS anchor_tickets, b.item_tickets AS companion_tickets, a.published_tickets,
       100.0 * p.pair_tickets / a.item_tickets AS companion_per_100_anchor,
       100.0 * b.item_tickets / a.published_tickets AS companion_per_100_all
FROM pairs p
JOIN frequencies a USING (store_id, business_date, is_demo, report_group, menu_item)
JOIN frequencies b ON p.store_id = b.store_id AND p.business_date = b.business_date AND p.is_demo = b.is_demo
  AND p.companion_group = b.report_group AND p.companion_item = b.menu_item;
