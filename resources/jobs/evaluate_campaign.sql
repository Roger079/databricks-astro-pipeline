-- Optional Databricks SQL analysis. Run in the schema containing the Silver/Gold tables
-- after loading these two inputs. Keep this outside Lakeflow discovery until inputs exist.
-- campaign_store_days: offer_id, store_id, business_date, is_demo, arm ('test'/'control'),
-- phase ('before'/'during'), target_category, other_variable_cost (store-day amount).
-- Supply one row for every planned store/day in both arms, including baseline days;
-- use the same dates across stores. Use explicit zero for known zero ancillary costs.
-- menu_unit_costs: store_id, business_date, is_demo, report_group, menu_item, unit_cost.
-- Costs must use the POS currency. Supply nonoverlapping unit costs for sold items and
-- free components (use zero for costs already rolled into their parent). Include other
-- variable costs once per store-day; discounts are already deducted from merchandise.
WITH plan AS (
  SELECT offer_id, store_id, business_date, is_demo, MIN(arm) AS arm, MIN(phase) AS phase,
         MIN(target_category) AS category, MIN(other_variable_cost) AS other_cost, COUNT(*) AS entries
  FROM campaign_store_days GROUP BY offer_id, store_id, business_date, is_demo
), costs AS (
  SELECT store_id, business_date, is_demo, report_group, menu_item,
         CASE WHEN COUNT(*)=1 AND MIN(unit_cost)>=0 THEN MIN(unit_cost) END AS unit_cost
  FROM menu_unit_costs GROUP BY store_id, business_date, is_demo, report_group, menu_item
), lines AS (
  SELECT p.store_id, p.business_date, p.is_demo, p.report_group,
         SUM(CASE WHEN p.menu_price>0 THEN p.quantity ELSE 0 END) AS priced_units,
         COUNT(*) AS lines, COUNT(k.unit_cost) AS costed_lines, SUM(p.quantity*k.unit_cost) AS item_cost
  FROM silver_pos p JOIN silver_checks c USING (store_id,business_date,is_demo,check_number)
  LEFT JOIN costs k USING (store_id,business_date,is_demo,report_group,menu_item)
  WHERE p.record_role IN ('sale_item','discounted_item','zero_price_component') AND p.quantity>0
  GROUP BY p.store_id,p.business_date,p.is_demo,p.report_group
), days AS (
  SELECT p.offer_id,p.is_demo,p.store_id,p.business_date,p.phase,p.arm,p.category,p.entries,
         d.transactions, SUM(CASE WHEN l.report_group=p.category THEN l.priced_units ELSE 0 END) AS category_units,
         CASE WHEN SUM(l.lines)=SUM(l.costed_lines) AND p.other_cost>=0
              THEN d.merchandise_after_discount-SUM(l.item_cost)-p.other_cost END AS margin
  FROM plan p LEFT JOIN gold_daily_sales d USING (store_id,business_date,is_demo)
  LEFT JOIN lines l ON l.store_id=p.store_id AND l.business_date=p.business_date AND l.is_demo=p.is_demo
  GROUP BY p.offer_id,p.is_demo,p.store_id,p.business_date,p.phase,p.arm,p.category,p.entries,
           d.transactions,d.merchandise_after_discount,p.other_cost
), calendar AS (
  SELECT offer_id,is_demo,business_date, MIN(phase) AS phase,
         COUNT(DISTINCT phase) AS phases, COUNT(DISTINCT store_id) AS stores
  FROM days GROUP BY offer_id,is_demo,business_date
), design AS (
  SELECT offer_id,is_demo,COUNT(DISTINCT store_id) AS stores,
         COUNT(DISTINCT category) AS categories,COUNT(*) AS planned_store_days,
         COUNT(transactions) AS observed_store_days,COUNT(margin) AS costed_store_days,
         SUM(CASE WHEN entries<>1 OR phase IS NULL OR phase NOT IN ('before','during')
           OR arm IS NULL OR arm NOT IN ('test','control') OR category IS NULL THEN 1 ELSE 0 END) AS invalid_days
  FROM days GROUP BY offer_id,is_demo
), assignments AS (
  SELECT offer_id,is_demo,store_id,COUNT(DISTINCT arm) AS arms
  FROM days GROUP BY offer_id,is_demo,store_id
), periods AS (
  SELECT offer_id,is_demo,phase,arm,AVG(margin) AS margin,AVG(transactions) AS traffic,
         AVG(category_units) AS units
  FROM days GROUP BY offer_id,is_demo,phase,arm
), estimates AS (
  SELECT offer_id,is_demo,COUNT(*) AS cells,
         SUM(CASE WHEN (arm='test' AND phase='during') OR (arm='control' AND phase='before') THEN margin ELSE -margin END) AS margin_delta,
         SUM(CASE WHEN (arm='test' AND phase='during') OR (arm='control' AND phase='before') THEN traffic ELSE -traffic END) AS traffic_delta,
         SUM(CASE WHEN (arm='test' AND phase='during') OR (arm='control' AND phase='before') THEN units ELSE -units END) AS units_delta
  FROM periods GROUP BY offer_id,is_demo
), checked AS (
  SELECT d.*, e.margin_delta,e.traffic_delta,e.units_delta,
         CASE WHEN d.invalid_days=0 AND d.categories=1 AND e.cells=4
           AND c.min_stores=d.stores AND c.max_phases=1 AND a.max_arms=1 AND c.last_before<c.first_during
           AND d.planned_store_days=d.observed_store_days THEN 1 ELSE 0 END AS comparable
  FROM design d JOIN estimates e USING (offer_id,is_demo)
  JOIN (SELECT offer_id,is_demo,MIN(stores) AS min_stores,MAX(phases) AS max_phases,
               MAX(CASE WHEN phase='before' THEN business_date END) AS last_before,
               MIN(CASE WHEN phase='during' THEN business_date END) AS first_during
        FROM calendar GROUP BY offer_id,is_demo) c USING (offer_id,is_demo)
  JOIN (SELECT offer_id,is_demo,MAX(arms) AS max_arms FROM assignments GROUP BY offer_id,is_demo) a USING (offer_id,is_demo)
)
SELECT offer_id,is_demo,stores,planned_store_days,observed_store_days,costed_store_days,comparable,
       CASE WHEN comparable=1 AND planned_store_days=costed_store_days THEN margin_delta END AS margin_change_per_store_day,
       CASE WHEN comparable=1 THEN traffic_delta END AS ticket_change_per_store_day,
       CASE WHEN comparable=1 THEN units_delta END AS category_unit_change_per_store_day
FROM checked;
