const { test } = require('node:test');
const assert = require('node:assert/strict');
const { DatabaseSync } = require('node:sqlite');
const { readFileSync } = require('node:fs');
const path = require('node:path');

test('promotion metrics use published checks, cohort-specific denominators and pre-tax discount depth', () => {
  const db = new DatabaseSync(':memory:');
  db.exec(`
    CREATE TABLE silver_checks (store_id, business_date, is_demo, check_number,
                                reported_discount, merchandise_after_discount);
    CREATE TABLE silver_pos (store_id, business_date, is_demo, check_number,
                             report_group, menu_item, record_role, quantity, menu_price);
  `);
  const check = db.prepare('INSERT INTO silver_checks VALUES (1, 20260101, 0, ?, ?, ?)');
  const item = db.prepare("INSERT INTO silver_pos VALUES (1, 20260101, 0, ?, 'Menu', ?, ?, ?, ?)");
  for (const row of [[1, 0, 20], [2, 0, 10], [3, 2, 18], [4, 5, 15],
                     [5, 1, 19], [6, 10, 0], [7, 0, 0]]) check.run(...row);
  for (const row of [[1, 'Taco', 2], [1, 'Soda', 1], [2, 'Taco', 1], [3, 'Taco', 1],
                     [3, 'Tea', 1], [3, 'Tea', 1], [4, 'Soda', 1], [5, 'Taco', 1],
                     [6, 'Taco', 1], [99, 'Unpublished', 1]]) {
    item.run(row[0], row[1], 'sale_item', row[2], 5);
  }
  item.run(1, 'Free', 'discounted_item', 5, 0);
  item.run(3, 'Void', 'voided_item', 1, 5);
  // Reused check number in a different scope must not affect these baskets.
  db.exec("INSERT INTO silver_checks VALUES (1, 20260101, 1, 1, 0, 5)");
  db.exec("INSERT INTO silver_pos VALUES (1, 20260101, 1, 1, 'Menu', 'Demo', 'sale_item', 1, 5)");
  for (const name of ['menu_discount_scorecard', 'menu_pair_discounts', 'discount_depth_baskets']) {
    const sql = readFileSync(path.join(__dirname, '../../src/transformations/gold/mv_' + name + '.sql'), 'utf8');
    db.exec(sql.replace(/^CREATE OR REFRESH MATERIALIZED VIEW/, 'CREATE VIEW'));
  }
  const pair = db.prepare('SELECT * FROM gold_menu_pair_discounts WHERE menu_item=? AND companion_item=?');
  const soda = pair.get('Taco', 'Soda');
  assert.deepEqual([soda.zero_discount_pairs, soda.zero_discount_anchor, soda.zero_discount_tickets,
    soda.zero_discount_attach_pct, soda.discounted_pairs, soda.discounted_anchor,
    soda.discounted_attach_pct, soda.discounted_companion_baseline_pct], [1, 2, 3, 50, 0, 3, 0, 25]);
  assert.ok(Math.abs(soda.zero_discount_companion_baseline_pct - 100 / 3) < 1e-8);
  const tea = pair.get('Tea', 'Taco');
  assert.deepEqual([tea.zero_discount_attach_pct, tea.discounted_pairs, tea.discounted_attach_pct], [null, 1, 100]);
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM gold_menu_pair_discounts').get().n, 4);
  const bands = db.prepare('SELECT * FROM gold_discount_depth_baskets WHERE is_demo=0 ORDER BY discount_band').all();
  assert.deepEqual(bands.map(b => [b.discount_band, b.published_tickets, b.priced_units,
    b.avg_units_per_ticket, b.avg_merchandise_per_ticket]), [
    ['(0%,10%)', 1, 1, 1, 19], ['0%', 2, 4, 2, 15], ['100%', 1, 1, 1, 0],
    ['[10%,25%)', 1, 3, 3, 18], ['[25%,100%)', 1, 1, 1, 15], ['undefined', 1, 0, 0, 0],
  ]);
  db.close();
});
