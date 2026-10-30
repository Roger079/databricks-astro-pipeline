-- Run only after the job's validation task succeeds.
-- Normalized amounts are inferred analytical metrics, not settlement or audited revenue.
SELECT business_date, COUNT(DISTINCT store_id) stores,
       SUM(transactions) published_tickets, SUM(customer_total) customer_total,
       SUM(merchandise_after_discount) merchandise_after_discount,
       SUM(customer_total) / NULLIF(SUM(transactions), 0) average_ticket
FROM workspace.astro_taco_main_real.gold_daily_sales
GROUP BY business_date ORDER BY business_date;

SELECT store_id, SUM(transactions) published_tickets,
       SUM(customer_total) customer_total,
       COUNT(DISTINCT business_date) observed_days
FROM workspace.astro_taco_main_real.gold_daily_sales
GROUP BY store_id ORDER BY customer_total DESC LIMIT 5;

SELECT review_reason, COUNT(*) tickets
FROM workspace.astro_taco_main_real.silver_checks_review
GROUP BY review_reason ORDER BY tickets DESC;

SELECT record_role, COUNT(*) source_rows
FROM workspace.astro_taco_main_real.silver_pos_classified
GROUP BY record_role ORDER BY source_rows DESC;
