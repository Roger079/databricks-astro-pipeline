"""Build a draft Lakeview dashboard definition against the isolated demo schema."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = 'workspace.astro_taco_main_demo'
datasets = [
    {'name': 'daily', 'displayName': 'DEMO · Importe POS diario', 'config': {
        'version': '1.1', 'source': f'{DB}.gold_daily_sales',
        'measures': [
            {'name': 'reported_total', 'expr': 'SUM(reported_total)', 'displayName': 'Importe POS sintético'},
            {'name': 'transactions', 'expr': 'SUM(transactions)', 'displayName': 'Tickets publicados'},
            {'name': 'average_ticket', 'expr': 'SUM(reported_total) / NULLIF(SUM(transactions), 0)', 'displayName': 'Ticket promedio ponderado'},
        ],
        'dimensions': [
            {'name': 'business_date', 'expr': 'business_date', 'displayName': 'Fecha'},
            {'name': 'store_id', 'expr': 'store_id', 'displayName': 'Tienda'},
        ],
    }},
    {'name': 'quality', 'displayName': 'DEMO · Calidad', 'config': {
        'version': '1.1', 'source': f'{DB}.gold_quality_summary',
        'measures': [
            {'name': name, 'expr': f'SUM({name})', 'displayName': label}
            for name, label in [('source_rows', 'Filas fuente'), ('quarantined_rows', 'Filas en cuarentena'), ('duplicate_candidate_rows', 'Filas duplicadas candidatas')]
        ],
    }},
    {'name': 'menu', 'displayName': 'DEMO · Unidades por categoría', 'config': {
        'version': '1.1', 'source': f'{DB}.gold_menu_performance',
        'measures': [{'name': 'units', 'expr': 'SUM(units)', 'displayName': 'Unidades'}],
        'dimensions': [{'name': 'report_group', 'expr': 'report_group', 'displayName': 'Categoría'}],
    }},
]

def query(dataset, fields):
    return [{'name': 'main_query', 'query': {'datasetName': dataset, 'fields': fields, 'disaggregated': False}}]

def measure(name):
    return {'name': f'measure({name})', 'expression': f'MEASURE(`{name}`)'}

layout = []
for index, (dataset, metric, label) in enumerate([
    ('daily', 'reported_total', 'DEMO · Importe POS'),
    ('daily', 'transactions', 'DEMO · Tickets publicados'),
    ('daily', 'average_ticket', 'DEMO · Ticket promedio'),
    ('quality', 'source_rows', 'DEMO · Filas fuente'),
    ('quality', 'quarantined_rows', 'DEMO · Cuarentena'),
    ('quality', 'duplicate_candidate_rows', 'DEMO · Duplicados candidatos'),
]):
    layout.append({'widget': {'name': f'counter_{index}', 'queries': query(dataset, [measure(metric)]),
        'spec': {'version': 2, 'widgetType': 'counter', 'frame': {'showTitle': True, 'title': label},
                 'encodings': {'value': {'fieldName': f'measure({metric})', 'rowNumber': 0}},
                 'data': {'queryName': 'main_query'}}},
        'position': {'x': (index % 3) * 4, 'y': (index // 3) * 2, 'width': 4, 'height': 2}})

layout.append({'widget': {'name': 'category_units', 'queries': query('menu', [
    {'name': 'report_group', 'expression': '`report_group`'}, measure('units')]),
    'spec': {'version': 3, 'widgetType': 'bar',
             'frame': {'showTitle': True, 'title': 'DEMO · Unidades por categoría (datos inventados)'},
             'encodings': {
                 'x': {'fieldName': 'report_group', 'scale': {'type': 'categorical'}},
                 'y': {'fieldName': 'measure(units)', 'scale': {'type': 'quantitative'}},
             }, 'data': {'queryName': 'main_query'}}},
    'position': {'x': 0, 'y': 4, 'width': 12, 'height': 6}})

dashboard = {'datasets': datasets, 'pages': [{'name': 'demo', 'displayName': 'DEMO · Datos sintéticos',
    'pageType': 'PAGE_TYPE_CANVAS', 'layoutVersion': 'GRID_V1', 'layout': layout}]}
path = ROOT / 'dashboards/astro_demo.lvdash.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2)+'\n')
print(path)
