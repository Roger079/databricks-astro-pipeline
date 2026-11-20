CREATE OR REFRESH MATERIALIZED VIEW gold_menu_pair_discounts
AS
-- Each directional pair observed in either cohort gets both cohort counts.
WITH basket_items AS (
  SELECT DISTINCT p.store_id, p.business_date, p.is_demo, p.check_number,
         p.report_group, p.menu_item, c.reported_discount
  FROM silver_pos p
  JOIN silver_checks c USING (store_id, business_date, is_demo, check_number)
  WHERE p.record_role IN ('sale_item', 'discounted_item') AND p.quantity > 0
    AND p.menu_price > 0 AND p.menu_item IS NOT NULL
), pairs AS (
  SELECT a.store_id, a.business_date, a.is_demo, a.report_group, a.menu_item,
         b.report_group AS companion_group, b.menu_item AS companion_item,
         SUM(CASE WHEN a.reported_discount = 0 THEN 1 ELSE 0 END) AS zero_discount_pairs,
         SUM(CASE WHEN a.reported_discount > 0 THEN 1 ELSE 0 END) AS discounted_pairs
  FROM basket_items a JOIN basket_items b USING (store_id, business_date, is_demo, check_number)
  WHERE a.report_group <> b.report_group OR a.menu_item <> b.menu_item
  GROUP BY a.store_id, a.business_date, a.is_demo, a.report_group, a.menu_item, b.report_group, b.menu_item
)
SELECT p.*, a.zero_discount_tickets, a.discounted_tickets,
       a.zero_discount_with_item AS zero_discount_anchor, a.discounted_with_item AS discounted_anchor,
       100.0 * p.zero_discount_pairs / NULLIF(a.zero_discount_with_item, 0) AS zero_discount_attach_pct,
       100.0 * p.discounted_pairs / NULLIF(a.discounted_with_item, 0) AS discounted_attach_pct,
       b.zero_discount_per_100 AS zero_discount_companion_baseline_pct,
       b.discounted_per_100 AS discounted_companion_baseline_pct
FROM pairs p
JOIN gold_menu_discount_scorecard a USING (store_id, business_date, is_demo, report_group, menu_item)
JOIN gold_menu_discount_scorecard b ON b.store_id = p.store_id AND b.business_date = p.business_date
  AND b.is_demo = p.is_demo AND b.report_group = p.companion_group AND b.menu_item = p.companion_item;
