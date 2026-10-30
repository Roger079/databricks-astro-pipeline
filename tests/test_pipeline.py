"""Execute the notebook's actual aggregation SQL against small DuckDB fixtures.

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
          1::BIGINT store_id, DATE '2025-01-22' business_date, '100' check_number,
          'Taco' menu_item, 'Tacos' report_group, 'Cash' tender_type, 'sale' transaction_type,
          10::DECIMAL(20,4) total, 0.8::DECIMAL(20,4) tax, 0::DECIMAL(20,4) total_discount,
          5::DECIMAL(20,4) menu_price, 0::DECIMAL(20,4) item_discount,
          0::DECIMAL(20,4) item_voided, 0::DECIMAL(20,4) order_voided, 2::DECIMAL(20,4) quantity,
          TIMESTAMP '1970-01-01 10:00:00' begin_time, TIMESTAMP '1970-01-01 10:03:00' end_time,
          'a' source_row_hash, 'check' amount_grain, true is_demo,
          TIMESTAMP '2026-01-01' loaded_at, 'demo' source_table""")
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
            exec(compile((ROOT/'notebooks/02_transform.py').read_text(), '02_transform.py', 'exec'), {'spark': spark})
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
        self.assertEqual(self.scalar('SELECT reported_total FROM silver_checks'), 10)
        self.assertEqual(self.scalar('SELECT transactions FROM gold_daily_sales'), 1)
        self.assertEqual(self.scalar('SELECT sum(reported_line_total) FROM gold_menu_performance'), None)
        self.assertEqual(self.scalar('SELECT reported_total FROM gold_hourly_sales'), 10)

    def test_line_grain_sums_lines(self):
        self.db.execute("UPDATE silver_pos_typed SET amount_grain='line'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT reported_total FROM silver_checks'), 20)
        self.assertEqual(self.scalar('SELECT sum(reported_line_total) FROM gold_menu_performance'), 20)

    def test_conflicting_check_totals_go_to_review(self):
        self.db.execute("UPDATE silver_pos_typed SET total=11 WHERE source_row_hash='b'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks_review'), 1)

    def test_duplicate_candidates_not_silently_removed(self):
        self.db.execute("INSERT INTO silver_pos_typed SELECT * FROM silver_pos_typed WHERE source_row_hash='a'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos'), 3)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)
        self.assertEqual(self.scalar('SELECT duplicate_candidate_rows FROM gold_quality_summary'), 2)

    def test_invalid_line_blocks_entire_ticket(self):
        self.db.execute("UPDATE silver_pos_typed SET quantity=NULL WHERE source_row_hash='b'")
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos_quarantine'), 1)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 0)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks_review'), 1)

    def test_negative_zero_and_void_require_review(self):
        for assignment in ('total=-5', 'quantity=0', 'item_voided=1'):
            with self.subTest(assignment=assignment):
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
        rows.append(rows[-1])
        for row in rows:
            store, date, check, begin, end, total, tax, discount, void, item, price, item_discount, item_void, qty, transaction, category, tender = row
            try:
                business_date = datetime.datetime.strptime(date, '%m/%d/%Y').date()
            except ValueError:
                business_date = None
            values = [int(store), business_date, check, item, category or 'Unknown', tender or 'Unknown', transaction.lower(), total, tax, discount, price, item_discount, item_void, void, qty,
                datetime.datetime.fromisoformat('1970-01-01 '+begin), datetime.datetime.fromisoformat('1970-01-01 '+end), hashlib.sha256(repr(row).encode()).hexdigest(), 'check', True, datetime.datetime(2026, 1, 1), 'demo']
            self.db.execute('INSERT INTO silver_pos_typed VALUES ('+','.join('?' for _ in values)+')', values)
        self.run_sql()
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos_typed'), 8)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos'), 7)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_pos_quarantine'), 1)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks'), 2)
        self.assertEqual(self.scalar('SELECT count(*) FROM silver_checks_review'), 3)
        self.assertEqual(self.scalar('SELECT sum(reported_total) FROM gold_daily_sales'), 18)

    def test_notebook_syntax_and_bundle_paths(self):
        for path in (ROOT/'notebooks').glob('*.py'):
            ast.parse(path.read_text())
        for path in [ROOT/'databricks.yml', *ROOT.glob('resources/**/*.yml')]:
            parsed = yaml.safe_load(path.read_text())
            self.assertIsInstance(parsed, dict)
        job = yaml.safe_load((ROOT/'resources/jobs/daily_orchestration_job.yml').read_text())['resources']['jobs']['daily_orchestration']
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

if __name__ == '__main__':
    unittest.main()
