"""Save API/SQL evidence for the normalized synthetic or real two-day run."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--run-id', required=True)
parser.add_argument('--pipeline-id', required=True)
parser.add_argument('--schema', required=True)
parser.add_argument('--kind', choices=['demo', 'real'], required=True)
parser.add_argument('--profile', default='datathon')
args = parser.parse_args()
assert re.fullmatch(r'astro_[A-Za-z0-9_]+', args.schema)
assert re.fullmatch(r'[A-Za-z0-9-]+', args.pipeline_id)
db = f'workspace.{args.schema}'

def cli(*command):
    return json.loads(subprocess.check_output(
        ['databricks', *command, '-p', args.profile, '-o', 'json'],
        text=True, encoding='utf-8'))

def query(sql):
    result = cli('api', 'post', '/api/2.0/sql/statements', '--json', json.dumps({
        'warehouse_id': '2b3b47b4d4cf4f3d', 'statement': sql,
        'wait_timeout': '10s', 'row_limit': 100,
    }))
    for _ in range(90):
        state = result['status']['state']
        if state == 'SUCCEEDED':
            columns = [c['name'] for c in result['manifest']['schema']['columns']]
            return {'statement_id': result['statement_id'], 'rows': [dict(zip(columns, row))
                for row in result.get('result', {}).get('data_array', [])]}
        if state in ('FAILED', 'CANCELED', 'CLOSED'):
            raise RuntimeError(result['status'])
        time.sleep(2)
        result = cli('api', 'get', f"/api/2.0/sql/statements/{result['statement_id']}")
    raise TimeoutError('SQL evidence timed out')

run = cli('jobs', 'get-run', args.run_id)
assert run['state'].get('result_state') == 'SUCCESS', run['state']
assert all(t['state'].get('result_state') == 'SUCCESS' for t in run['tasks'])
assert any(t.get('pipeline_task', {}).get('pipeline_id') == args.pipeline_id for t in run['tasks'])
metrics = query(f"""SELECT
  (SELECT count(*) FROM {db}.bronze_pos) source_rows,
  (SELECT count(*) FROM {db}.silver_pos) silver_rows,
  (SELECT count(*) FROM {db}.silver_pos_quarantine) quarantine_rows,
  (SELECT count(*) FROM {db}.silver_checks_profile) identifiable_checks,
  (SELECT count(*) FROM {db}.silver_checks) published_checks,
  (SELECT count(*) FROM {db}.silver_checks_review) review_checks,
  (SELECT count(*) FROM {db}.silver_checks_profile WHERE abs(reconciliation_residual)>0.011) equation_exceptions,
  (SELECT sum(reported_total) FROM {db}.gold_daily_sales) raw_source_total,
  (SELECT sum(customer_total) FROM {db}.gold_daily_sales) customer_total,
  (SELECT sum(merchandise_after_discount) FROM {db}.gold_daily_sales) merchandise_after_discount,
  (SELECT count(*) FROM {db}.bronze_pos WHERE _astro_demo IS NULL OR _astro_demo != {str(args.kind == 'demo').lower()}) wrong_data_kind_rows
""")
m = metrics['rows'][0]
assert int(m['source_rows']) == int(m['silver_rows']) + int(m['quarantine_rows'])
assert int(m['identifiable_checks']) == int(m['published_checks']) + int(m['review_checks'])
assert int(m['wrong_data_kind_rows']) == 0
if args.kind == 'demo':
    assert [int(m[k]) for k in ('source_rows', 'silver_rows', 'quarantine_rows', 'published_checks', 'review_checks')] == [12, 11, 1, 5, 2]
    assert float(m['customer_total']) == 37.96 and float(m['merchandise_after_discount']) == 35.0
else:
    assert int(m['source_rows']) == 284428 and int(m['identifiable_checks']) == 40306

reviews = query(f"SELECT review_reason, count(*) tickets FROM {db}.silver_checks_review GROUP BY review_reason ORDER BY tickets DESC")
source_snapshot = query(f"""SELECT _astro_source source_table, _astro_source_version delta_version,
    _astro_amount_grain amount_grain, count(*) source_rows,
    min(_astro_loaded_at) loaded_at FROM {db}.bronze_pos
    GROUP BY _astro_source, _astro_source_version, _astro_amount_grain""")
coverage = query(f"""SELECT financial_profile, count(*) identifiable_checks,
    sum(CASE WHEN is_publishable THEN 1 ELSE 0 END) published_checks,
    sum(CASE WHEN abs(reconciliation_residual)>0.011 THEN 1 ELSE 0 END) equation_exceptions
    FROM {db}.silver_checks_profile GROUP BY financial_profile""")
start, end = [dt.datetime.fromtimestamp(run[k]/1000, dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
              for k in ('start_time', 'end_time')]
expectations = query(f"""SELECT timestamp, origin.update_id update_id,
    origin.flow_name flow_name, details:flow_progress.data_quality.expectations expectations
    FROM event_log('{args.pipeline_id}')
    WHERE event_type='flow_progress' AND timestamp BETWEEN TIMESTAMP '{start}' AND TIMESTAMP '{end}'
      AND details:flow_progress.data_quality.expectations IS NOT NULL
    ORDER BY timestamp DESC LIMIT 30""")
evidence = {
    'captured_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'data_kind': 'synthetic_demo' if args.kind == 'demo' else 'real_two_day_extract',
    'schema': db, 'rule_version': 'pos-two-day-v1', 'run_id': run['run_id'],
    'pipeline_id': args.pipeline_id, 'run_url': run['run_page_url'], 'state': run['state'],
    'tasks': [{'task_key': t['task_key'], 'run_id': t['run_id'], 'state': t['state']} for t in run['tasks']],
    'metrics': metrics, 'source_snapshot': source_snapshot, 'review_reasons': reviews, 'profile_coverage': coverage,
    'expectations': expectations,
    'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [*sorted(ROOT.glob('src/transformations/**/*.py')),
                  *sorted(ROOT.glob('notebooks/*.py')), ROOT/'config/store_financial_profiles.json']},
}
path = ROOT/f'docs/evidence/normalized-{args.kind}-verification.json'
path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'state': 'verified', 'run_id': run['run_id'], 'metrics': m, 'evidence': str(path)}))
