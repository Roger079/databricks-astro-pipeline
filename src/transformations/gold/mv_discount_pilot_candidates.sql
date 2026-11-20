CREATE OR REFRESH MATERIALIZED VIEW gold_discount_pilot_candidates
AS
-- Compare within a store, date and channel. Moderate = [10%,25%); deep = [25%,100%].
WITH units AS (
  SELECT store_id, business_date, is_demo, check_number, SUM(quantity) AS priced_units
  FROM silver_pos
  WHERE record_role IN ('sale_item','discounted_item') AND quantity > 0 AND menu_price > 0
  GROUP BY store_id, business_date, is_demo, check_number
), baskets AS (
  SELECT c.*, COALESCE(u.priced_units, 0) AS priced_units,
         CASE WHEN reported_discount > 0 AND reported_discount * 4 >= merchandise_after_discount + reported_discount THEN 'deep'
              WHEN reported_discount > 0 AND reported_discount * 10 >= merchandise_after_discount + reported_discount THEN 'moderate'
         END AS depth
  FROM silver_checks c LEFT JOIN units u USING (store_id, business_date, is_demo, check_number)
), segments AS (
  SELECT store_id, business_date, is_demo, channel, COUNT(*) AS published_tickets,
         100.0 * SUM(reported_discount) / COUNT(*) AS discount_amount_per_100_tickets,
         COUNT(CASE WHEN depth='moderate' THEN 1 END) AS moderate_tickets,
         COUNT(CASE WHEN depth='deep' THEN 1 END) AS deep_tickets,
         AVG(CASE WHEN depth='moderate' THEN priced_units END) AS moderate_units_per_ticket,
         AVG(CASE WHEN depth='deep' THEN priced_units END) AS deep_units_per_ticket,
         AVG(CASE WHEN depth='moderate' THEN merchandise_after_discount END) AS moderate_merchandise_per_ticket,
         AVG(CASE WHEN depth='deep' THEN merchandise_after_discount END) AS deep_merchandise_per_ticket
  FROM baskets GROUP BY store_id, business_date, is_demo, channel
)
-- Initial screening settings, not significance cutoffs. Sort flagged rows by
-- discount_amount_per_100_tickets and inspect the underlying sample sizes.
SELECT *, CASE WHEN moderate_tickets>=20 AND deep_tickets>=20
            AND channel NOT IN ('Unknown','Mixed/Unknown')
            AND ABS(deep_units_per_ticket-moderate_units_per_ticket)<=0.25
            AND deep_merchandise_per_ticket<=moderate_merchandise_per_ticket
          THEN 1 ELSE 0 END AS review_for_smaller_discount,
       deep_units_per_ticket - moderate_units_per_ticket AS extra_units_per_deep_ticket,
       deep_merchandise_per_ticket - moderate_merchandise_per_ticket AS extra_merchandise_per_deep_ticket
FROM segments;
