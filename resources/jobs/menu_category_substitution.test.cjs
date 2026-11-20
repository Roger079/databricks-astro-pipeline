const { test } = require('node:test');
const assert = require('node:assert/strict');
const { DatabaseSync } = require('node:sqlite');
const { readFileSync } = require('node:fs');
const path = require('node:path');

test('compares category mix per published ticket and preserves missing cohorts', () => {
  const db = new DatabaseSync(':memory:');
  db.exec(`
    CREATE TABLE silver_checks (store_id, business_date, is_demo, check_number, reported_discount);
    CREATE TABLE silver_pos (store_id, business_date, is_demo, check_number,
                             report_group, menu_item, record_role, quantity, menu_price);
    INSERT INTO silver_checks VALUES
      (1,1,0,1,2),(1,1,0,2,2),(1,1,0,3,0),(1,1,0,4,0),(1,1,1,1,2);
    INSERT INTO silver_pos VALUES
      (1,1,0,1,'Tacos','Beef','sale_item',2,5),
      (1,1,0,1,'Tacos','Beef','discounted_item',1,5),
      (1,1,0,1,'Tacos','Chicken','sale_item',1,3),
      (1,1,0,2,'Sides','Chips','sale_item',1,2),
      (1,1,0,3,'Tacos','Beef','sale_item',1,5),
      (1,1,0,3,'Tacos','Chicken','sale_item',2,3),
      (1,1,0,4,'Tacos',NULL,'sale_item',1,4),
      (1,1,0,4,'Tacos','Shell','zero_price_component',3,0),
      (1,1,0,4,'Tacos','Beef','voided_item',1,5),
      (1,1,0,99,'Tacos','Beef','sale_item',10,5),
      (1,1,1,1,'Tacos','Beef','sale_item',5,5);
  `);
  for (const name of ['menu_discount_scorecard', 'menu_category_substitution']) {
    const sql = readFileSync(path.join(__dirname, '../../src/transformations/gold', 'mv_' + name + '.sql'), 'utf8');
    db.exec(sql.replace(/^CREATE OR REFRESH MATERIALIZED VIEW/, 'CREATE VIEW'));
  }
  const results = db.prepare("SELECT * FROM gold_menu_category_substitution WHERE menu_item='Beef' ORDER BY is_demo").all();
  const [real, demo] = results;
  assert.equal(results.length, 2);
  assert.deepEqual([real.discounted_tickets, real.zero_discount_tickets, real.discounted_item_per_100,
    real.zero_discount_item_per_100, real.discounted_category_per_100, real.zero_discount_category_per_100],
    [2, 2, 150, 50, 200, 200]);
  assert.deepEqual([real.item_gap_per_100, real.others_gap_per_100, real.category_gap_per_100], [100, -100, 0]);
  assert.deepEqual([demo.discounted_tickets, demo.zero_discount_tickets, demo.category_gap_per_100], [1, 0, null]);
  assert.equal(db.prepare("SELECT zero_discount_item_per_100 AS rate FROM gold_menu_category_substitution WHERE menu_item='Chips'").get().rate, 0);
  db.close();
});
