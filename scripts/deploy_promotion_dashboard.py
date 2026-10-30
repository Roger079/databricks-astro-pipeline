"""Validate SQL, create/update the dedicated Genie/dashboard pair, publish and share.

Uses the current Databricks CLI profile; never reads or stores access tokens.
Existing asset IDs are reused only from this dashboard's deployment evidence.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import time

from build_promotion_dashboard import ROOT, WAREHOUSE, write

parser = argparse.ArgumentParser()
parser.add_argument('--profile', default='datathon')
parser.add_argument('--validate-only', action='store_true')
args = parser.parse_args()
TMP = ROOT / 'tmp/promotion-bi'
TMP.mkdir(parents=True, exist_ok=True)


def cli(*command):
    return json.loads(subprocess.check_output(['databricks', *command, '-p', args.profile,
        '-o', 'json'], text=True, encoding='utf-8'))


def api(method, endpoint, body=None):
    command = ['api', method, endpoint]
    if body is not None:
        path = TMP / 'request.json'
        path.write_text(json.dumps(body), encoding='utf-8')
        command += ['--json', '@' + str(path)]
    return cli(*command)


def query(sql):
    result = api('post', '/api/2.0/sql/statements', {
        'warehouse_id': WAREHOUSE, 'statement': sql, 'wait_timeout': '10s', 'row_limit': 5})
    for _ in range(90):
        state = result['status']['state']
        if state == 'SUCCEEDED':
            columns = [c['name'] for c in result['manifest']['schema']['columns']]
            return {'statement_id': result['statement_id'], 'state': state,
                    'rows': [dict(zip(columns, row)) for row in result.get('result', {}).get('data_array', [])]}
        if state in ('FAILED', 'CANCELED', 'CLOSED'):
            raise RuntimeError(result['status'])
        time.sleep(2)
        result = api('get', f"/api/2.0/sql/statements/{result['statement_id']}")
    raise TimeoutError('SQL validation timed out')


dashboard = json.loads((ROOT/'dashboards/promotion_decision_lab.lvdash.json').read_text(encoding='utf-8'))
space = json.loads((ROOT/'genie/promotion_decision_lab.geniespace.json').read_text(encoding='utf-8'))
evidence_path = ROOT/'docs/evidence/promotion-bi-deployment.json'
evidence = json.loads(evidence_path.read_text(encoding='utf-8')) if evidence_path.exists() else {}
validation = {}
sql_by_name = {d['name']: ''.join(d['queryLines']) for d in dashboard['datasets']}
for name, sql in sql_by_name.items():
    validation[name] = query(f'SELECT * FROM ({sql}) dashboard_data LIMIT 5')
    print('SQL validated:', name, flush=True)
# Execute actual widget expressions too, catching field-name and aggregation errors.
widget_count = 0
for page in dashboard['pages']:
    for item in page['layout']:
        widget = item['widget']
        if 'queries' not in widget or page['pageType'] != 'PAGE_TYPE_CANVAS':
            continue
        q = widget['queries'][0]['query']
        expressions = [f"{f['expression']} AS `{f['name']}`" for f in q['fields']]
        sql = f"SELECT {', '.join(expressions)} FROM ({sql_by_name[q['datasetName']]}) dashboard_data"
        if not q.get('disaggregated'):
            groups = [f['expression'] for f in q['fields'] if f['expression'].startswith('`')]
            if groups:
                sql += ' GROUP BY ' + ', '.join(groups)
        result = query(sql + ' LIMIT 5')
        widget_count += 1
        if widget['spec']['widgetType'] == 'counter':
            validation[widget['name']] = {'title': widget['spec']['frame']['title'], **result}
print(f'All {widget_count} data widgets executed successfully.', flush=True)
evidence['sql_validation'] = validation
evidence['validated_widget_count'] = widget_count
evidence['captured_at_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
write('tmp/promotion-bi/validation.json', evidence)
if args.validate_only:
    write('tmp/promotion-bi/validation.json', evidence)
    raise SystemExit(0)

space_body = {'title': 'Taco Bueno | Pricing & Promotion Decision Lab',
              'description': 'Validated real two-day POS analytics. Evidence-qualified pricing/promotion decisions; historical strategy analysis pending normalization.',
              'warehouse_id': WAREHOUSE, 'serialized_space': json.dumps(space)}
if evidence.get('genie_space_id'):
    space_result = api('patch', f"/api/2.0/genie/spaces/{evidence['genie_space_id']}", space_body)
else:
    space_result = api('post', '/api/2.0/genie/spaces', space_body)
    evidence['genie_space_id'] = space_result['space_id']
    write('docs/evidence/promotion-bi-deployment.json', evidence)
print('Genie space connected:', evidence['genie_space_id'], flush=True)
dashboard['uiSettings']['genieSpace'] = {'isEnabled': True,
    'overrideId': evidence['genie_space_id'], 'enablementMode': 'ENABLED'}
write('dashboards/promotion_decision_lab.lvdash.json', dashboard)
dashboard_body = {'display_name': 'Taco Bueno | Pricing & Promotion Decision Lab',
                  'warehouse_id': WAREHOUSE, 'dataset_catalog': 'workspace',
                  'dataset_schema': 'astro_taco_main_real', 'serialized_dashboard': json.dumps(dashboard)}
if evidence.get('dashboard_id'):
    dashboard_result = api('patch', f"/api/2.0/lakeview/dashboards/{evidence['dashboard_id']}", dashboard_body)
else:
    dashboard_result = api('post', '/api/2.0/lakeview/dashboards', dashboard_body)
    evidence['dashboard_id'] = dashboard_result['dashboard_id']
    write('docs/evidence/promotion-bi-deployment.json', evidence)
print('Dashboard created:', evidence['dashboard_id'], flush=True)

acl = {'access_control_list': [{'user_name': u, 'permission_level': 'CAN_MANAGE'} for u in
       ['a01236573@tec.mx', 'a00842807@tec.mx', 'a01381456@tec.mx']]}
for object_type, object_id in [('dashboards', evidence['dashboard_id']), ('genie', evidence['genie_space_id'])]:
    api('patch', f'/api/2.0/permissions/{object_type}/{object_id}', acl)
    evidence[object_type+'_permissions'] = api('get', f'/api/2.0/permissions/{object_type}/{object_id}')
published = api('post', f"/api/2.0/lakeview/dashboards/{evidence['dashboard_id']}/published",
                {'warehouse_id': WAREHOUSE, 'embed_credentials': False})
evidence['published'] = published
evidence['warehouse_id'] = WAREHOUSE
evidence['data_schema'] = 'workspace.astro_taco_main_real'
host = 'https://dbc-cfb7f93a-b497.cloud.databricks.com'
evidence['dashboard_url'] = f"{host}/dashboardsv3/{evidence['dashboard_id']}/published?o=7474644614542766"
evidence['dashboard_edit_url'] = f"{host}/dashboardsv3/{evidence['dashboard_id']}?o=7474644614542766"
evidence['genie_url'] = f"{host}/genie/rooms/{evidence['genie_space_id']}?o=7474644614542766"
saved = api('get', f"/api/2.0/lakeview/dashboards/{evidence['dashboard_id']}")
assert json.loads(saved['serialized_dashboard'])['uiSettings']['genieSpace']['overrideId'] == evidence['genie_space_id']
saved_space = api('get', f"/api/2.0/genie/spaces/{evidence['genie_space_id']}?include_serialized_space=true")
assert len(json.loads(saved_space['serialized_space'])['data_sources']['tables']) == len(space['data_sources']['tables'])
write('docs/evidence/promotion-bi-deployment.json', evidence)
print(json.dumps({k: evidence[k] for k in ['dashboard_url', 'dashboard_edit_url', 'genie_url']}), flush=True)
