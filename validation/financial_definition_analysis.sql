-- Read-only profile of the complete two-day extract; no deduplication or financial filtering.
-- Numeric ticket shape separates the two observed store populations in this extract only.
-- It is not a universal POS-system identifier. All matches use DECIMAL and 1-cent tolerance.
WITH l AS (
SELECT `Store #` store_id, to_date(`Date`,'M/d/yyyy') business_date, `Check Number` check_number,
CAST(`Total` AS DECIMAL(20,4)) total, CAST(`Tax` AS DECIMAL(20,4)) tax,
CAST(`Total Discount` AS DECIMAL(20,4)) discount,
CAST(`Menu Price` AS DECIMAL(20,4)) price, CAST(`Quantity` AS DECIMAL(20,4)) qty,
CAST(`Item Discount` AS DECIMAL(20,4)) item_discount,
CAST(`Item Voided` AS DECIMAL(20,4)) item_voided,
CAST(`Order Voided` AS DECIMAL(20,4)) order_voided,
`Transaction Type` kind, `Menu Item` item, `Report Group` category,
`POS Code` pos_code
FROM workspace.default.tb_daily_tld_01_01_2026_m
), t AS (
SELECT store_id,business_date,check_number,COUNT(*) lines,MAX(total) total,MIN(total) min_total,
MAX(tax) tax,MIN(tax) min_tax,MAX(discount) discount,MIN(discount) min_discount,
SUM(price) prices,SUM(price*qty) extended_prices,SUM(item_discount) item_discounts,
SUM(item_voided) item_voids,MAX(order_voided) order_voided,
COUNT_IF(kind='Void') void_lines,COUNT_IF(kind='Discount') discount_lines,
SUM(CASE WHEN kind='Regular Sale' THEN price ELSE 0 END) regular_prices,
SUM(CASE WHEN kind='Discount' THEN price ELSE 0 END) discount_prices,
COUNT_IF(qty>1) multi_qty_lines,
COUNT_IF(total IS NULL OR tax IS NULL OR discount IS NULL OR price IS NULL OR qty IS NULL) missing,
COUNT(DISTINCT pos_code) pos_codes
FROM l GROUP BY store_id,business_date,check_number
) SELECT CASE WHEN check_number>1000000000000 THEN 'A_long_number' ELSE 'B_short_number' END family,
COUNT(DISTINCT store_id) stores,COUNT(*) tickets,SUM(lines) source_rows,
COUNT_IF(total<>min_total OR tax<>min_tax OR discount<>min_discount) conflicting_ticket_amounts,
COUNT_IF(abs(CASE WHEN check_number>1000000000000 THEN total-prices+discount-tax+item_voids ELSE total-extended_prices END)<=0.011) reconciled_tickets,
COUNT_IF(abs(CASE WHEN check_number>1000000000000 THEN total-prices+discount-tax+item_voids ELSE total-extended_prices END)>0.011) exception_tickets,
COUNT_IF(discount<>0) discounted_tickets,COUNT_IF(void_lines>0 OR item_voids<>0) void_affected_tickets,
COUNT_IF(discount_lines>0) tickets_with_discount_rows,
COUNT_IF(discount_lines>0 AND abs(discount-item_discounts)<=0.011) discount_matches_item_discount_sum,
SUM(total) unnormalized_total_once, SUM(tax) tax_once, SUM(discount) discount_once
FROM t GROUP BY 1 ORDER BY 1;
