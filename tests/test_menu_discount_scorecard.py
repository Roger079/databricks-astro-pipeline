from pathlib import Path
import unittest

import duckdb


class ScorecardTest(unittest.TestCase):
    def test_presence_cohort_denominators_and_missing_comparison(self):
        with duckdb.connect() as db:
            db.execute("""CREATE TABLE silver_checks AS SELECT * FROM (VALUES
                (1, DATE '2026-01-01', false, 10, 2), (1, DATE '2026-01-01', false, 11, 1),
                (1, DATE '2026-01-01', false, 12, 0), (2, DATE '2026-01-01', false, 10, 0)
            ) t(store_id, business_date, is_demo, check_number, reported_discount)""")
            db.execute("""CREATE TABLE silver_pos AS SELECT store_id, DATE '2026-01-01' business_date,
                false is_demo, check_number, 'Food' report_group, menu_item, record_role, quantity, menu_price
                FROM (VALUES (1,10,'Taco','discounted_item',2,5), (1,10,'Taco','sale_item',1,5),
                (1,11,'Side','zero_price_component',1,0), (1,12,'Burrito','sale_item',1,7),
                (1,12,'Void','voided_item',1,5), (1,13,'Held','sale_item',1,5),
                (2,10,'Taco','sale_item',1,5)) t(store_id,check_number,menu_item,record_role,quantity,menu_price)""")
            sql = (Path(__file__).resolve().parents[1] /
                   'src/transformations/gold/mv_menu_discount_scorecard.sql').read_text()
            db.execute(sql.replace('CREATE OR REFRESH MATERIALIZED VIEW', 'CREATE VIEW'))
            rows = db.execute("""SELECT store_id, menu_item, discounted_with_item, discounted_tickets,
                zero_discount_tickets, discounted_per_100, zero_discount_per_100, gap_percentage_points
                FROM gold_menu_discount_scorecard ORDER BY store_id, menu_item""").fetchall()
            self.assertEqual(rows, [(1,'Burrito',0,2,1,0,100,-100), (1,'Taco',1,2,1,50,0,50),
                                    (2,'Taco',0,0,1,None,100,None)])
