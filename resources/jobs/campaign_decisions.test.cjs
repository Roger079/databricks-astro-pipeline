const { test } = require('node:test');
const assert = require('node:assert/strict');
const { DatabaseSync } = require('node:sqlite');
const { readFileSync } = require('node:fs');
const path = require('node:path');

function sql(file) {
  return readFileSync(path.join(__dirname, file), 'utf8');
}

test('smaller discount screen compares eligible cohorts within a single channel', () => {
  const db = new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE silver_checks(store_id,business_date,is_demo,check_number,channel,reported_discount,merchandise_after_discount);
    CREATE TABLE silver_pos(store_id,business_date,is_demo,check_number,quantity,menu_price,record_role);`);
  const check = db.prepare("INSERT INTO silver_checks VALUES (1,1,0,?,'Counter',?,?)");
  const item = db.prepare("INSERT INTO silver_pos VALUES (1,1,0,?,2,5,'sale_item')");
  for (let id=0; id<40; id++) {
    const discount = id<20 ? 1 : 2.5;
    check.run(id, discount, 10-discount);
    item.run(id);
  }
  db.exec("INSERT INTO silver_checks VALUES (1,1,0,40,'Counter',0,10),(1,1,0,41,'Drive',3,7)");
  db.exec(sql('../../src/transformations/gold/mv_discount_pilot_candidates.sql')
    .replace('CREATE OR REFRESH MATERIALIZED VIEW','CREATE VIEW'));
  const get = db.prepare('SELECT * FROM gold_discount_pilot_candidates WHERE channel=?');
  const row = get.get('Counter');
  assert.deepEqual([row.review_for_smaller_discount,row.deep_tickets,row.moderate_tickets,
    row.extra_units_per_deep_ticket,row.extra_merchandise_per_deep_ticket], [1,20,20,0,-1.5]);
  assert.ok(Math.abs(row.discount_amount_per_100_tickets-7000/41)<1e-8);
  assert.equal(get.get('Drive').extra_units_per_deep_ticket,null);
  db.close();
});

test('campaign uses change relative to controls and suppresses incomplete estimates', () => {
  const db = new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE campaign_store_days(offer_id,store_id,business_date,is_demo,arm,phase,target_category,other_variable_cost);
    CREATE TABLE menu_unit_costs(store_id,business_date,is_demo,report_group,menu_item,unit_cost);
    CREATE TABLE silver_checks(store_id,business_date,is_demo,check_number);
    CREATE TABLE silver_pos(store_id,business_date,is_demo,check_number,report_group,menu_item,record_role,quantity,menu_price);
    CREATE TABLE gold_daily_sales(store_id,business_date,is_demo,transactions,merchandise_after_discount);`);
  for (const [store,day,revenue,units,traffic] of [[1,1,100,10,10],[1,2,150,20,15],[2,1,90,10,9],[2,2,100,12,10]]) {
    db.prepare("INSERT INTO campaign_store_days VALUES ('A',?,?,0,?,?,'Tacos',2)").run(store,day,store===1?'test':'control',day===1?'before':'during');
    db.prepare("INSERT INTO menu_unit_costs VALUES (?,?,0,'Tacos','Beef',2)").run(store,day);
    db.prepare('INSERT INTO silver_checks VALUES (?,?,0,1)').run(store,day);
    db.prepare("INSERT INTO silver_pos VALUES (?,?,0,1,'Tacos','Beef','sale_item',?,5)").run(store,day,units);
    db.prepare('INSERT INTO gold_daily_sales VALUES (?,?,0,?,?)').run(store,day,traffic,revenue);
  }
  const evaluate = db.prepare(sql('evaluate_campaign.sql'));
  const row = evaluate.get();
  assert.deepEqual([row.comparable,row.margin_change_per_store_day,row.ticket_change_per_store_day,
    row.category_unit_change_per_store_day], [1,24,4,8]);
  db.exec('DELETE FROM menu_unit_costs WHERE store_id=1 AND business_date=2');
  assert.equal(evaluate.get().margin_change_per_store_day,null);
  assert.equal(evaluate.get().category_unit_change_per_store_day,8);
  db.exec('DELETE FROM campaign_store_days WHERE store_id=2 AND business_date=1');
  assert.equal(evaluate.get().ticket_change_per_store_day,null);
  db.close();
});
