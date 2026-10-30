"""Execute the pipeline's actual aggregation SQL against small DuckDB fixtures.

DuckDB is a local semantic check, not a replacement for a Lakeflow workspace run.
"""
import ast
import datetime
import hashlib
import re
from pathlib import Path
import sys
import types
import unittest
import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.db = duckdb.connect()
        self.db.execute("CREATE MACRO pmod(a,b) AS ((a % b + b) % b)")
        self.db.execute("CREATE MACRO unix_timestamp(a) AS epoch(a)")
        self.db.execute("CREATE MACRO unix_micros(a) AS epoch_us(a)")
        self.db.execute("""CREATE TABLE silver_pos_typed AS SELECT
          1::BIGINT store_id, DATE '2025-12-31' business_date, '100' check_number,
          'Taco' menu_item, 'Tacos' report_group, 'Cash' tender_type, 'sale' transaction_type,
          'Drive Thru' channel,
          10.8::DECIMAL(20,4) total, 0.8::DECIMAL(20,4) tax, 0::DECIMAL(20,4) total_discount,
          5::DECIMAL(20,4) menu_price, 0::DECIMAL(20,4) item_discount,
          0::DECIMAL(20,4) item_voided, 0::DECIMAL(20,4) order_voided, 1::DECIMAL(20,4) quantity,
          TIMESTAMP '1970-01-01 10:00:00' begin_time, TIMESTAMP '1970-01-01 10:03:00' end_time,
          'a' source_row_hash, 'check' amount_grain, true is_demo,
          TIMESTAMP '2026-01-01' loaded_at, 'demo' source_table,
          'A_TAX_INCLUSIVE' financial_profile, 'pos-two-day-v1' rule_version""")
        self.db.execute("INSERT INTO silver_pos_typed SELECT * REPLACE ('Drink' AS menu_item, 'b' AS source_row_hash) FROM silver_pos_typed")
        self.definitions = []
        def materialized_view(**options):
            def register(fn):
                self.definitions.append((options['name'], fn))
                return fn
            return register
        dp = types.SimpleNamespace(materialized_view=materialized_view,
            expect=lambda *a, **k: lambda f: f, expect_all_or_fail=lambda *a, **k: lambda f: f)
        module = types.ModuleType('pyspark')
        module.pipelines = dp
        previous = sys.modules.get('pyspark')
        sys.modules['pyspark'] = module
        spark = types.SimpleNamespace(conf=types.SimpleNamespace(get=lambda k: 'astro_demo' if k == 'astro.schema' else 'workspace'), sql=lambda sql: sql)
        try:
            paths = [
                'silver/mv_store_financial_profiles.py',
                'silver/mv_pos_typed.py', 'silver/mv_pos_classified.py',
                'silver/mv_pos_checks.py', 'gold/mv_store_daily.py',
                'gold/mv_channel_hourly.py', 'gold/mv_item_daily.py',
                'gold/mv_data_quality.py',
            ]
            for path in paths:
                source = ROOT/'src/transformations'/path
                exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), {'spark': spark})
        finally:
            if previous is None:
                sys.modules.pop('pyspark', None)
            else:
                sys.modules['pyspark'] = previous

    def run_sql(self):
        for name, fn in self.definitions:
            if name != 'silver_pos_typed':
                self.db.execute(f'CREATE OR REPLACE VIEW {name} AS {fn()}')

    def scalar(self, sql):
        return self.db.execute(sql).fetchone()[0]

    def test_check_total_not_multiplied_and_category_not_allocated(self):
        self.run_sql()
        self.assertAlmostEqual(float(self.scalar('SELECT reported_total FROM silver_checks')), 10.8)
        self.assertEqual(self.scalar('SELECT merchandise_after_discount FROM silver_checks'), 10)
        self.assertEqual(self.scalar('SELECT transactions FROM gold_daily_sales'), 1)
        self.assertEqual(self.scalar('SELECT sum(reported_line_total) FROM gold_menu_performance'), None)
        self.assertAlmostEqual(float(self.scalar('SELECT customer_total FROM gold_hourly_sales')), 10.8)

    def test_line_grain_is_not_silently_interpreted_as_check_grain(self):
        self.db.execute("UPDATE silver_pos_typed SET amount_grain='line'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)
        self.assertIn('unsupported_amount_grain', self.scalar('SELECT review_reason FROM silver_checks_review'))

    def test_conflicting_check_totals_go_to_review(self):
        self.db.execute("UPDATE silver_pos_typed SET total=11 WHERE source_row_hash='b'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks_review'), 1)

    def test_duplicate_candidates_not_silently_removed(self):
        self.db.execute("INSERT INTO silver_pos_typed SELECT * FROM silver_pos_typed WHERE source_row_hash='a'")
        self.db.execute('UPDATE silver_pos_typed SET total=16.2, tax=1.2')
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos'), 3)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 1)
        self.assertAlmostEqual(float(self.scalar('SELECT reported_total FROM silver_checks')), 16.2)
        self.assertEqual(self.scalar('SELECT sum(units) FROM gold_menu_performance'), 3)
        self.assertEqual(self.scalar('SELECT duplicate_candidate_rows FROM gold_quality_summary'), 2)

    def test_invalid_line_blocks_entire_ticket(self):
        self.db.execute("UPDATE silver_pos_typed SET quantity=NULL WHERE source_row_hash='b'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos_quarantine'), 1)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks_review'), 1)

    def test_negative_amount_and_unexplained_void_require_review(self):
        for assignment in ('total=-5', 'order_voided=1'):
            with self.subTest(assignment=assignment):
                self.db.execute("UPDATE silver_pos_typed SET total=10.8, quantity=1, order_voided=0 WHERE source_row_hash='b'")
                self.db.execute(f"UPDATE silver_pos_typed SET {assignment} WHERE source_row_hash='b'")
                self.run_sql()
                self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)

    def test_midnight_duration(self):
        self.db.execute("UPDATE silver_pos_typed SET begin_time=TIMESTAMP '1970-01-01 23:59:00', end_time=TIMESTAMP '1970-01-01 00:02:00'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT duration_seconds FROM silver_checks'), 180)

    def test_fractional_time_duration(self):
        self.db.execute("UPDATE silver_pos_typed SET begin_time=TIMESTAMP '1970-01-01 23:59:59.750000', end_time=TIMESTAMP '1970-01-01 00:00:00.250000'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT duration_seconds FROM silver_checks'), 0.5)

    def test_backwards_daytime_clock_does_not_become_24_hour_service(self):
        self.db.execute("UPDATE silver_pos_typed SET begin_time=TIMESTAMP '1970-01-01 10:03:00', end_time=TIMESTAMP '1970-01-01 09:53:00'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT duration_seconds FROM silver_checks'), None)
        self.assertEqual(self.scalar('SELECT transactions FROM gold_daily_sales'), 1)
        self.assertEqual(self.scalar('SELECT duration_observations FROM gold_daily_sales'), 0)
        self.assertEqual(self.scalar('SELECT invalid_duration_rows FROM gold_quality_summary'), 2)

    def test_partially_missing_ticket_duration_is_not_reported_as_complete(self):
        self.db.execute("UPDATE silver_pos_typed SET end_time=NULL WHERE source_row_hash='b'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT duration_seconds FROM silver_checks'), None)

    def test_void_label_blocks_publication_even_with_zero_void_amounts(self):
        self.db.execute("UPDATE silver_pos_typed SET transaction_type='void'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)
        self.assertIn('unresolved_financial_record', self.scalar('SELECT review_reason FROM silver_checks_review'))

    def test_channel_metrics_count_each_check_once(self):
        self.run_sql()
        self.assertEqual(self.scalar('SELECT transactions FROM gold_channel_hourly'), 1)
        self.assertAlmostEqual(float(self.scalar('SELECT customer_total FROM gold_channel_hourly')), 10.8)
        self.assertEqual(self.scalar('SELECT channel FROM gold_channel_hourly'), 'Drive Thru')

    def test_publication_coverage_reconciles(self):
        self.run_sql()
        self.assertEqual(self.scalar('SELECT sum(identifiable_checks) FROM gold_publication_coverage'), 1)
        self.assertEqual(self.scalar('SELECT sum(published_checks) FROM gold_publication_coverage'), 1)

    def test_quarantine_has_reason(self):
        self.db.execute("UPDATE silver_pos_typed SET business_date=NULL WHERE source_row_hash='b'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT reject_reason FROM silver_pos_quarantine'), 'invalid_date')

    def test_repeated_refresh_has_same_business_totals(self):
        self.run_sql()
        first = self.db.execute('SELECT * FROM gold_daily_sales').fetchall()
        self.run_sql()
        self.assertEqual(first, self.db.execute('SELECT * FROM gold_daily_sales').fetchall())

    def test_demo_expected_results(self):
        self.db.execute('DELETE FROM silver_pos_typed')
        tree = ast.parse((ROOT/'notebooks/00_demo_source.py').read_text())
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'rows' for t in n.targets))
        rows = ast.literal_eval(assignment.value)
        for row in rows:
            store, date, check, begin, end, total, tax, discount, void, item, price, item_discount, item_void, qty, transaction, category, tender = row
            try:
                business_date = datetime.datetime.strptime(date, '%m/%d/%Y').date()
            except ValueError:
                business_date = None
            values = [int(store), business_date, check, item, category or 'Unknown', tender or 'Unknown', transaction.lower(), 'Unknown', total, tax, discount, price, item_discount, item_void, void, qty,
                datetime.datetime.fromisoformat('1970-01-01 '+begin), datetime.datetime.fromisoformat('1970-01-01 '+end), hashlib.sha256(repr(row).encode()).hexdigest(), 'check', True, datetime.datetime(2026, 1, 1), 'demo',
                'A_TAX_INCLUSIVE' if store == '1' else 'B_PRE_DISCOUNT' if store == '2' else None, 'pos-two-day-v1']
            self.db.execute('INSERT INTO silver_pos_typed VALUES ('+','.join('?' for _ in values)+')', values)
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos_typed'), 12)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos'), 11)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos_quarantine'), 1)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 5)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks_review'), 2)
        self.assertAlmostEqual(float(self.scalar('SELECT sum(reported_total) FROM gold_daily_sales')), 38.76)
        self.assertAlmostEqual(float(self.scalar('SELECT sum(customer_total) FROM gold_daily_sales')), 37.96)
        self.assertEqual(self.scalar('SELECT sum(merchandise_after_discount) FROM gold_daily_sales'), 35)

    def test_b_profile_discount_is_subtracted_once_and_tax_added_once(self):
        self.db.execute("DELETE FROM silver_pos_typed WHERE source_row_hash='b'")
        self.db.execute("UPDATE silver_pos_typed SET financial_profile='B_PRE_DISCOUNT', total=18.53, tax=1.22, total_discount=3.71, item_discount=3.71, menu_price=18.53, transaction_type='discount'")
        self.run_sql()
        self.assertAlmostEqual(float(self.scalar('SELECT merchandise_after_discount FROM silver_checks')), 14.82)
        self.assertAlmostEqual(float(self.scalar('SELECT customer_total FROM silver_checks')), 16.04)

    def test_zero_quantity_component_does_not_block_b_profile(self):
        self.db.execute("UPDATE silver_pos_typed SET financial_profile='B_PRE_DISCOUNT', total=10")
        self.db.execute("INSERT INTO silver_pos_typed SELECT * REPLACE (99 AS menu_price, 0 AS quantity, 'c' AS source_row_hash) FROM silver_pos_typed WHERE source_row_hash='a'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 1)
        self.assertEqual(self.scalar('SELECT sum(units) FROM gold_menu_performance'), 2)

    def test_partial_void_removes_units_without_discarding_valid_b_ticket(self):
        self.db.execute("UPDATE silver_pos_typed SET financial_profile='B_PRE_DISCOUNT', total=10")
        self.db.execute("INSERT INTO silver_pos_typed SELECT * REPLACE (0 AS menu_price, 3 AS item_voided, 'void' AS transaction_type, 'c' AS source_row_hash) FROM silver_pos_typed WHERE source_row_hash='a'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 1)
        self.assertEqual(self.scalar('SELECT sum(units) FROM gold_menu_performance'), 2)

    def test_signed_item_promo_reconciles_without_adding_product_units(self):
        self.db.execute("UPDATE silver_pos_typed SET total=9.72, tax=.72")
        self.db.execute("INSERT INTO silver_pos_typed SELECT * REPLACE (-1 AS menu_price, 'Item Promo' AS menu_item, 'c' AS source_row_hash) FROM silver_pos_typed WHERE source_row_hash='a'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT merchandise_after_discount FROM silver_checks'), 9)
        self.assertEqual(self.scalar('SELECT sum(units) FROM gold_menu_performance'), 2)

    def test_added_duplicate_without_changed_check_total_is_flagged_by_reconciliation(self):
        self.db.execute("INSERT INTO silver_pos_typed SELECT * FROM silver_pos_typed WHERE source_row_hash='a'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos'), 3)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)
        self.assertIn('accounting_equation_mismatch', self.scalar('SELECT review_reason FROM silver_checks_review'))

    def test_unknown_profile_is_not_guessed_from_number_shape(self):
        self.db.execute('UPDATE silver_pos_typed SET financial_profile=NULL')
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)
        self.assertIn('unknown_store_profile', self.scalar('SELECT review_reason FROM silver_checks_review'))

    def test_zero_total_positive_tax_stays_in_review_even_when_equation_matches(self):
        self.db.execute("UPDATE silver_pos_typed SET financial_profile='B_PRE_DISCOUNT', total=0, quantity=0")
        self.run_sql()
        self.assertIn('zero_source_total_positive_tax', self.scalar('SELECT review_reason FROM silver_checks_review'))

    def test_fully_discounted_b_ticket_is_a_valid_zero_customer_amount(self):
        self.db.execute("UPDATE silver_pos_typed SET financial_profile='B_PRE_DISCOUNT', total=10, total_discount=10, tax=0, item_discount=5, transaction_type='discount'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT customer_total FROM silver_checks'), 0)

    def test_store_profile_map_has_unique_scoped_entries(self):
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_store_financial_profiles WHERE NOT is_demo'), 114)
        self.assertEqual(self.scalar("SELECT count(*) FROM (SELECT store_id,is_demo FROM silver_store_financial_profiles GROUP BY store_id,is_demo HAVING count(*)>1)"), 0)

    def test_notebook_syntax_and_bundle_paths(self):
        for path in [*ROOT.glob('notebooks/*.py'), *ROOT.glob('src/transformations/**/*.py')]:
            ast.parse(path.read_text(encoding='utf-8'))
        for path in [ROOT/'databricks.yml', *ROOT.glob('resources/**/*.yml')]:
            parsed = yaml.safe_load(path.read_text())
            self.assertIsInstance(parsed, dict)
        job = yaml.safe_load((ROOT/'resources/jobs/daily_orchestration_job.yml').read_text())['resources']['jobs']['daily_orchestration']
        libraries = yaml.safe_load((ROOT/'resources/pipelines/lakeflow_pipeline.yml').read_text())['resources']['pipelines']['taco_pipeline']['libraries']
        self.assertEqual(libraries, [{'glob': {'include': '../../src/transformations/**'}}])
        self.assertEqual(job['schedule']['pause_status'], 'PAUSED')
        keys = {task['task_key'] for task in job['tasks']}
        for task in job['tasks']:
            self.assertNotIn('existing_cluster_id', task)
            self.assertNotIn('new_cluster', task)
            for dep in task.get('depends_on', []):
                self.assertIn(dep['task_key'], keys)
            if 'notebook_task' in task:
                self.assertTrue((ROOT/'resources/jobs'/task['notebook_task']['notebook_path']).resolve().is_file())

    def test_ingestion_preserves_demo_marker_and_normalizes_source(self):
        tree = ast.parse((ROOT/'notebooks/01_ingest.py').read_text())
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'names' for t in n.targets))
        expr = compile(ast.Expression(assignment.value), 'names', 'eval')
        names = eval(expr, {'df': types.SimpleNamespace(columns=['Store #', 'Begin Time', '_astro_demo']), 're': re})
        self.assertEqual(names, {'Store #': 'store_id', 'Begin Time': 'begin_time', '_astro_demo': '_astro_demo'})

    def test_foreign_pipeline_is_rejected_before_bronze_write(self):
        tree = ast.parse((ROOT/'notebooks/01_ingest.py').read_text(encoding='utf-8'))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check_pipeline_owners')
        namespace = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'ownership_guard', 'exec'), namespace)
        guard = namespace['check_pipeline_owners']
        guard([], 'ours')
        guard([('silver_pos', 'ours')], 'ours')
        for owner, expected in [('theirs', 'ours'), (None, 'ours'), ('ours', '')]:
            with self.subTest(owner=owner, expected=expected):
                with self.assertRaisesRegex(AssertionError, 'Destino ocupado'):
                    guard([('silver_pos', owner)], expected)

if __name__ == '__main__':
    unittest.main()
