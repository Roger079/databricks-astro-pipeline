const { test } = require('node:test');
const assert = require('node:assert/strict');
const { DatabaseSync } = require('node:sqlite');
const { readFileSync } = require('node:fs');
const path = require('node:path');

test('published basket counts, comparable stores and directional menu pairs', () => {
  const db = new DatabaseSync(':memory:');
  db.exec(`
    CREATE TABLE silver_checks (store_id, business_date, is_demo, check_number, reported_discount);
    CREATE TABLE silver_pos (store_id, business_date, is_demo, check_number,
      report_group, menu_item, record_role, quantity, menu_price);
  `);
  const check = db.prepare('INSERT INTO silver_checks VALUES (?, ?, ?, ?, ?)');
  const item = db.prepare('INSERT INTO silver_pos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)');
  function basket(store, day, demo, id, discount, names) {
    check.run(store, day, demo, id, discount);
    for (const name of names) {
      item.run(store, day, demo, id, 'Menu', name, 'sale_item', 1, 5);
    }
  }
  basket('A', '2026-01-01', 0, 1, 2, ['Taco', 'Drink', 'Taco']);
  basket('A', '2026-01-01', 0, 2, 0, ['Taco']);
  basket('A', '2026-01-01', 0, 3, 0, []);
  basket('B', '2026-01-01', 0, 1, 2, ['Drink']);
  basket('B', '2026-01-01', 0, 2, 0, ['Taco']);
  basket('A', '2026-01-02', 0, 1, 2, ['Taco']); // One cohort only.
  basket('C', '2026-01-01', 0, 1, 2, ['Drink']); // Comparable, with zero Taco orders.
  basket('C', '2026-01-01', 0, 2, 0, ['Drink']);
  basket('A', '2026-01-01', 1, 1, 2, ['Taco', 'Drink']); // Separate demo.
  item.run('A', '2026-01-01', 0, 1, 'Menu', 'Voided', 'voided_item', 1, 5);
  item.run('A', '2026-01-01', 0, 1, 'Menu', 'Component', 'discounted_item', 1, 0);
  item.run('A', '2026-01-01', 0, 99, 'Menu', 'Unpublished', 'sale_item', 1, 5);

  for (const name of ['menu_discount_scorecard', 'menu_discount_comparison', 'menu_pairs']) {
    const file = path.join(__dirname, '../../src/transformations/gold', 'mv_' + name + '.sql');
    const sql = readFileSync(file, 'utf8');
    db.exec(sql.replace(/^CREATE OR REFRESH MATERIALIZED VIEW/, 'CREATE VIEW'));
  }
  const taco = db.prepare("SELECT * FROM gold_menu_discount_comparison WHERE is_demo=0 AND menu_item='Taco'").get();
  assert.deepEqual([taco.comparable_stores, taco.comparable_store_days, taco.stores_higher,
    taco.stores_lower, taco.stores_equal], [3, 3, 1, 1, 1]);
  assert.deepEqual([taco.discounted_with_item, taco.discounted_tickets,
    taco.zero_discount_with_item, taco.zero_discount_tickets], [1, 3, 2, 4]);
  assert.ok(Math.abs(taco.discounted_per_100 - 100 / 3) < 0.0001);
  assert.equal(taco.zero_discount_per_100, 50);
  assert.ok(Math.abs(taco.matched_gap_pp + 50 / 3) < 0.0001);
  const pairs = db.prepare('SELECT * FROM gold_menu_pairs WHERE is_demo=0 ORDER BY menu_item').all();
  assert.deepEqual(pairs.map(p => [p.menu_item, p.companion_item, p.pair_tickets,
    p.anchor_tickets, p.companion_tickets, p.published_tickets, p.companion_per_100_anchor]),
    [['Drink', 'Taco', 1, 1, 2, 3, 100], ['Taco', 'Drink', 1, 2, 1, 3, 50]]);
  assert.ok(Math.abs(pairs[1].companion_per_100_all - 100 / 3) < 0.0001);
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM gold_menu_discount_scorecard WHERE menu_item NOT IN ('Taco','Drink')").get().n, 0);
  db.close();
});
