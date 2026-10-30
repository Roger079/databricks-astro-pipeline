"""Capture actual demo run status, reconciliation and expectations using ASTRO.

Read-only apart from issuing SELECT statements and saving local evidence JSON.
Does not deploy resources or change grants. Run after the demo Job finishes.
"""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import time
from zoneinfo import ZoneInfo

PIPELINE = '1d827004-d26d-4ade-8ea9-51f0c31597e8'
WAREHOUSE = '2b3b47b4d4cf4f3d'
ROOT = Path(__file__).resolve().parents[1]

def cli(*args):
    output = subprocess.check_output(['databricks', *args, '--profile', 'ASTRO', '--output', 'json'], text=True)
    return json.loads(output)

def query(sql):
    result = cli('api', 'post', '/api/2.0/sql/statements', '--json', json.dumps({
        'warehouse_id': WAREHOUSE, 'statement': sql, 'wait_timeout': '10s', 'row_limit': 20,
    }))
    for _ in range(45):
        state = result['status']['state']
        if state == 'SUCCEEDED':
            columns = [c['name'] for c in result['manifest']['schema']['columns']]
            return {'statement_id': result['statement_id'], 'rows': [dict(zip(columns, row)) for row in result.get('result', {}).get('data_array', [])]}
        if state in ('FAILED', 'CANCELED', 'CLOSED'):
            raise RuntimeError(result['status'])
        time.sleep(2)
        result = cli('api', 'get', f"/api/2.0/sql/statements/{result['statement_id']}")
    raise TimeoutError('SQL did not finish within the capture window')

parser = argparse.ArgumentParser()
parser.add_argument('--run-id', required=True)
args = parser.parse_args()
run = cli('jobs', 'get-run', args.run_id)
assert run['state'].get('result_state') == 'SUCCESS', run['state']
assert all(t['state'].get('result_state') == 'SUCCESS' for t in run['tasks']), 'Not all tasks succeeded'

metrics = query("""SELECT
  (SELECT count(*) FROM workspace.astro_taco_demo.bronze_pos) source_rows,
  (SELECT count(*) FROM workspace.astro_taco_demo.silver_pos) silver_rows,
  (SELECT count(*) FROM workspace.astro_taco_demo.silver_pos_quarantine) quarantine_rows,
  (SELECT count(*) FROM workspace.astro_taco_demo.silver_checks) published_checks,
  (SELECT count(*) FROM workspace.astro_taco_demo.silver_checks_review) review_checks,
  (SELECT sum(reported_total) FROM workspace.astro_taco_demo.gold_daily_sales) reported_total,
  (SELECT count(*) FROM workspace.astro_taco_demo.bronze_pos WHERE _astro_demo IS NULL OR NOT _astro_demo) unmarked_demo_bronze_rows,
  (SELECT count(*) FROM workspace.astro_taco_demo.gold_daily_sales WHERE is_demo IS NULL OR NOT is_demo) unmarked_demo_gold_rows
""")
row = metrics['rows'][0]
for key, expected in [('source_rows', 8), ('silver_rows', 7), ('quarantine_rows', 1), ('published_checks', 2), ('review_checks', 3), ('unmarked_demo_bronze_rows', 0), ('unmarked_demo_gold_rows', 0)]:
    assert int(row[key]) == expected, (key, row[key])
assert float(row['reported_total']) == 18.0

expectations = query(f"""SELECT timestamp, origin.update_id update_id,
    origin.flow_name flow_name, details:flow_progress.data_quality.expectations expectations
  FROM event_log('{PIPELINE}')
  WHERE event_type = 'flow_progress'
    AND details:flow_progress.data_quality.expectations IS NOT NULL
  ORDER BY timestamp DESC LIMIT 10""")

evidence = {
    'captured_at': datetime.datetime.now(ZoneInfo('America/Monterrey')).isoformat(),
    'data_kind': 'synthetic_demo_only',
    'real_source_status': 'SELECT denied; business amount grain still unconfirmed',
    'run_id': run['run_id'], 'run_url': run['run_page_url'], 'state': run['state'],
    'tasks': [{'task_key': t['task_key'], 'run_id': t['run_id'], 'state': t['state']} for t in run['tasks']],
    'reconciliation': metrics, 'expectations': expectations,
}
path = ROOT/'docs/evidence/demo-verification.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'state': 'verified', 'run_id': run['run_id'], 'metrics': row, 'evidence_file': str(path)}, ensure_ascii=False))
