CREATE OR REFRESH MATERIALIZED VIEW gold_discount_depth_baskets
AS
WITH units AS (
  -- Count quantities, including repeated sales, but skip voids, free components and adjustments.
  SELECT store_id, business_date, is_demo, check_number, SUM(quantity) AS priced_units
  FROM silver_pos
  WHERE record_role IN ('sale_item', 'discounted_item') AND quantity > 0 AND menu_price > 0
  GROUP BY store_id, business_date, is_demo, check_number
), baskets AS (
  SELECT c.*, c.merchandise_after_discount + c.reported_discount AS merchandise_before_discount,
         COALESCE(u.priced_units, 0) AS priced_units
  FROM silver_checks c LEFT JOIN units u USING (store_id, business_date, is_demo, check_number)
), banded AS (
  SELECT *, CASE
      WHEN merchandise_before_discount <= 0 THEN 'undefined'
      WHEN reported_discount = 0 THEN '0%'
      WHEN reported_discount * 10 < merchandise_before_discount THEN '(0%,10%)'
      WHEN reported_discount * 4 < merchandise_before_discount THEN '[10%,25%)'
      WHEN reported_discount < merchandise_before_discount THEN '[25%,100%)'
      ELSE '100%'
    END AS discount_band
  FROM baskets
)
SELECT store_id, business_date, is_demo, discount_band, COUNT(*) AS published_tickets,
       SUM(priced_units) AS priced_units, AVG(priced_units) AS avg_units_per_ticket,
       SUM(merchandise_after_discount) AS merchandise_after_discount,
       AVG(merchandise_after_discount) AS avg_merchandise_per_ticket
FROM banded
GROUP BY store_id, business_date, is_demo, discount_band;
