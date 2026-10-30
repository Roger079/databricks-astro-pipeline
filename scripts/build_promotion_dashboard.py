"""Build native AI/BI dashboard and curated Genie configuration; no source mutations."""
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
DB = 'workspace.astro_taco_main_real'
WAREHOUSE = '2b3b47b4d4cf4f3d'
datasets = []


def dataset(name, sql):
    datasets.append({'name': name, 'displayName': name.replace('_', ' ').title(),
                     'queryLines': sql.splitlines(keepends=True)})


for name, table in [('daily', 'gold_daily_sales'), ('hourly', 'gold_hourly_sales'),
                    ('channels', 'gold_channel_hourly'), ('menu', 'gold_menu_performance'),
                    ('coverage', 'gold_publication_coverage'), ('quality', 'gold_quality_summary')]:
    dataset(name, f'SELECT * FROM {DB}.{table} WHERE is_demo = false')
dataset('tickets', f'''SELECT business_date, store_id, check_number, channel, financial_profile,
 customer_total, merchandise_after_discount, reported_discount, reported_tax,
 CASE WHEN reported_discount > 0 THEN 'Ticket discount present' ELSE 'No ticket discount' END discount_cohort
 FROM {DB}.silver_checks WHERE is_demo = false''')
dataset('reviews', f'''SELECT business_date, store_id, check_number, financial_profile,
 review_reason, reconciliation_residual FROM {DB}.silver_checks_review WHERE is_demo = false''')
dataset('profiles', f'''SELECT business_date, store_id, financial_profile, is_publishable,
 reconciliation_residual FROM {DB}.silver_checks_profile WHERE is_demo = false''')
dataset('snapshot', f'''SELECT _astro_source source_table, _astro_source_version delta_version,
 min(_astro_loaded_at) loaded_at, count(*) source_rows
 FROM {DB}.bronze_pos WHERE _astro_demo = false
 GROUP BY _astro_source, _astro_source_version''')
dataset('decisions', f'''WITH c AS (
 SELECT count(*) published_checks, count(DISTINCT business_date) observed_days,
 count(DISTINCT store_id) observed_stores,
 sum(CASE WHEN reported_discount > 0 THEN 1 ELSE 0 END) discounted_checks
 FROM {DB}.silver_checks WHERE is_demo = false),
 r AS (SELECT count(*) review_checks FROM {DB}.silver_checks_review WHERE is_demo = false)
 SELECT 'Investigate' action, 'Financial exceptions' topic,
 concat(CAST(review_checks AS STRING), ' checks withheld; ', CAST(published_checks AS STRING), ' published') evidence,
 'Descriptive / reconciled' confidence,
 'Review exception reasons and source records before expanding financial reporting.' next_step,
 'No estimate of withheld sales' limitation FROM c CROSS JOIN r
 UNION ALL SELECT 'Design a test', 'Discount effectiveness',
 concat(CAST(discounted_checks AS STRING), ' published checks with positive ticket discount'),
 'Descriptive; selection bias remains',
 'Identify an offer and compare equivalent stores, baskets and time windows; plan a controlled test.',
 'Discount cohort differences are not causal promotion lift' FROM c
 UNION ALL SELECT 'Prepare history', 'Lift and seasonality',
 concat(CAST(observed_days AS STRING), ' observed days across ', CAST(observed_stores AS STRING), ' stores'),
 'Insufficient evidence',
 'Normalize historical source by store and period; verify missing days and a comparable baseline.',
 'Two holiday dates do not establish seasonal demand' FROM c
 UNION ALL SELECT 'Investigate', 'Menu mix and substitution',
 'Published item and category units are available', 'Descriptive only',
 'Confirm offer fingerprints, substitute sets and bundle components before comparing category change.',
 'Product revenue, causal cannibalization and margin are unavailable' FROM c
 UNION ALL SELECT 'Defer keep / stop / return', 'Promotion portfolio',
 'No confirmed campaign IDs, schedule or costs', 'Insufficient evidence',
 'Validate offer identity and baseline before issuing portfolio recommendations.',
 'No ROI, profit, retention or causal claims' FROM c''')

pages = []
serial = 0


def page(name, title, description):
    p = {'name': name, 'displayName': title, 'pageType': 'PAGE_TYPE_CANVAS',
         'layoutVersion': 'GRID_V1', 'layout': []}
    pages.append(p)
    text(p, f'# {title}\n\n{description}', 0, 0, 12, 3)
    return p


def place(p, widget, x, y, w, h):
    global serial
    serial += 1
    widget['name'] = f'w_{serial}'
    p['layout'].append({'widget': widget, 'position': {'x': x, 'y': y, 'width': w, 'height': h}})


def text(p, content, x, y, w, h):
    place(p, {'multilineTextboxSpec': {'lines': [content]}}, x, y, w, h)


def viz(p, ds, title, fields, kind, x, y, w, h, raw=False):
    names = list(fields)
    spec = {'version': 2 if kind in ('counter', 'table') else 3, 'widgetType': kind,
            'frame': {'showTitle': True, 'title': title}}
    if kind == 'counter':
        percentage = title.startswith(('Share of tickets', 'Ticket discount depth', 'Published / identifiable'))
        spec['encodings'] = {'value': {'fieldName': names[0], 'rowNumber': 0,
            'format': {'type': 'number-percent' if percentage else 'number-plain',
                       'decimalPlaces': {'type': 'max', 'places': 2}}}}
    elif kind == 'table':
        spec['encodings'] = {'columns': [{'fieldName': n, 'displayName': n.replace('_', ' ').title()} for n in names]}
    else:
        spec['encodings'] = {
            'x': {'fieldName': names[0], 'scale': {'type': 'categorical'}},
            'y': {'fieldName': names[1], 'scale': {'type': 'quantitative'}}}
    place(p, {'queries': [{'name': 'main_query', 'query': {'datasetName': ds,
           'fields': [{'name': n, 'expression': e} for n, e in fields.items()], 'disaggregated': raw}}],
           'spec': spec}, x, y, w, h)


p = page('overview', '1. Business overview',
 'Validated real POS extract: **2025-12-31 and 2026-01-01**. Amounts are in source monetary units; currency is unconfirmed. '
 'Customer amount includes tax; merchandise amount excludes tax after ticket discount. These are reconciled POS amounts, not audited revenue. '
 'Use Ask Genie for questions; use Genie Code in Edit mode to refine the dashboard.')
for i, (title, expr) in enumerate([
 ('Customer amount incl. tax', 'SUM(customer_total)'),
 ('Merchandise amount excl. tax', 'SUM(merchandise_after_discount)'),
 ('Published tickets', 'SUM(transactions)'),
 ('Weighted average ticket', 'SUM(customer_total)/NULLIF(SUM(transactions),0)')]):
    viz(p, 'daily', title, {'value': expr}, 'counter', i*3, 3, 3, 3)
viz(p, 'daily', 'Customer amount by observed date', {'business_date': '`business_date`', 'customer_amount': 'SUM(customer_total)'}, 'bar', 0, 6, 6, 5)
viz(p, 'daily', 'Tickets by observed date', {'business_date': '`business_date`', 'tickets': 'SUM(transactions)'}, 'bar', 6, 6, 6, 5)
viz(p, 'daily', 'Store comparison — same two-day scope', {'store_id': '`store_id`', 'tickets': 'SUM(transactions)',
    'customer_amount': 'SUM(customer_total)', 'average_ticket': 'SUM(customer_total)/NULLIF(SUM(transactions),0)'}, 'table', 0, 11, 12, 6)

p = page('pricing', '2. Pricing and discounts',
 'Compare ticket discount cohorts descriptively. A difference in basket value is **not promotion lift**. '
 'Ticket discount depth = sum(ticket discount) / sum(merchandise after discount + ticket discount). '
 'This is a ticket-level source field, not a product allocation or validated campaign redemption.')
viz(p, 'tickets', 'Share of tickets with a positive ticket discount', {'value': 'AVG(CASE WHEN reported_discount > 0 THEN 1.0 ELSE 0.0 END)'}, 'counter', 0, 3, 4, 3)
viz(p, 'tickets', 'Ticket discount depth', {'value': 'SUM(reported_discount)/NULLIF(SUM(merchandise_after_discount+reported_discount),0)'}, 'counter', 4, 3, 4, 3)
viz(p, 'tickets', 'Reported ticket discounts — once per check', {'value': 'SUM(reported_discount)'}, 'counter', 8, 3, 4, 3)
viz(p, 'tickets', 'Discount cohorts — descriptive comparison', {'discount_cohort': '`discount_cohort`',
    'tickets': 'COUNT(*)', 'average_customer_amount': 'AVG(customer_total)',
    'average_merchandise_amount': 'AVG(merchandise_after_discount)', 'ticket_discount': 'SUM(reported_discount)'}, 'table', 0, 6, 12, 6)
text(p, '**Price analysis gate:** unit-price normalization and comparable SKU identity must be validated before adding price distributions. '
 'Do not interpret bundle components, zero-price components, or Item Promo adjustments as standalone full-price products.', 0, 12, 12, 2)

p = page('demand', '3. Demand and comparison readiness',
 'Observed demand by POS-reported hour and channel. Dates straddle New Year; changes are descriptive. '
 '**Seasonality, expected demand, promotion lift and confidence intervals are unavailable until historical normalization and baseline validation.**')
viz(p, 'hourly', 'Published tickets by POS hour', {'start_hour': '`start_hour`', 'tickets': 'SUM(transactions)'}, 'bar', 0, 3, 7, 6)
viz(p, 'channels', 'Published tickets by source channel', {'channel': '`channel`', 'tickets': 'SUM(transactions)'}, 'bar', 7, 3, 5, 6)
viz(p, 'daily', 'Observed daily comparison', {'business_date': '`business_date`', 'stores': 'COUNT(DISTINCT store_id)',
    'tickets': 'SUM(transactions)', 'customer_amount': 'SUM(customer_total)',
    'average_ticket': 'SUM(customer_total)/NULLIF(SUM(transactions),0)'}, 'table', 0, 9, 12, 5)

p = page('mix', '4. Menu mix and substitution signals',
 'Units from reconciled, published checks only. Reported item/component units can include bundle components; '
 'summing them is not a count of unique standalone products. Voided items and promo monetary adjustments contribute zero units. '
 '**No allocated product revenue or proven cannibalization.**')
viz(p, 'menu', 'Reported units by source category', {'report_group': '`report_group`', 'units': 'SUM(units)'}, 'bar', 0, 3, 12, 5)
viz(p, 'menu', 'Item and component detail — explore categories first', {'report_group': '`report_group`', 'menu_item': '`menu_item`',
    'units': 'SUM(units)', 'source_lines': 'SUM(line_count)', 'item_discount_field': 'SUM(item_discount)'}, 'table', 0, 8, 12, 7)

p = page('decisions', '5. Decisions and next experiments',
 'Datathon question: **Which promotions should live, die, or come back?** '
 'This board separates actions supported today from decisions needing more evidence. '
 '**Whole validated snapshot: date/store filters do not change this board.** No invented promotion names or keep/stop/return rankings.')
viz(p, 'decisions', 'Evidence → decision → next step', {n: f'`{n}`' for n in
    ['action', 'topic', 'evidence', 'confidence', 'next_step', 'limitation']}, 'table', 0, 3, 12, 9, raw=True)
text(p, '**Release gate for promotion recommendations:** reliable offer identity; adequate observed sample; comparable stores and periods; '
 'validated baseline; target and substitute-category outcomes; sensitivity and uncertainty. '
 'When these fail, recommend an investigation or controlled test. Costs are required for margin/ROI.', 0, 12, 12, 3)

p = page('trust', '6. Trust and pipeline evidence',
 'Source snapshot → Bronze → typed/classified Silver → reconciled tickets → Gold → validation. '
 'Financial profiles differ by store and are valid only for the mapped dates. Legitimate repeated item occurrences remain; '
 'financial exceptions are withheld. Row quarantine and ticket financial review are separate measures.')
viz(p, 'coverage', 'Published / identifiable checks', {'value': 'SUM(published_checks)*1.0/NULLIF(SUM(identifiable_checks),0)'}, 'counter', 0, 3, 4, 3)
viz(p, 'reviews', 'Financial review checks', {'value': 'COUNT(*)'}, 'counter', 4, 3, 4, 3)
viz(p, 'coverage', 'Equation exception checks (overlapping review reason)', {'value': 'SUM(equation_exception_checks)'}, 'counter', 8, 3, 4, 3)
viz(p, 'reviews', 'Review reasons — reasons can overlap', {'review_reason': '`review_reason`', 'tickets': 'COUNT(*)'}, 'table', 0, 6, 7, 5)
viz(p, 'profiles', 'Store-specific financial profiles', {'financial_profile': '`financial_profile`',
    'identifiable_checks': 'COUNT(*)', 'published_checks': 'SUM(CASE WHEN is_publishable THEN 1 ELSE 0 END)'}, 'table', 7, 6, 5, 5)
viz(p, 'snapshot', 'Source provenance — whole snapshot, unfiltered', {n: f'`{n}`' for n in
    ['source_table', 'delta_version', 'loaded_at', 'source_rows']}, 'table', 0, 11, 12, 4, raw=True)
viz(p, 'quality', 'Structural row quality — whole snapshot, unfiltered', {n: f'`{n}`' for n in
    ['source_rows', 'quarantined_rows', 'financial_review_rows', 'duplicate_candidate_rows', 'invalid_duration_rows', 'assumed_overnight_rows']}, 'table', 0, 15, 12, 4, raw=True)
text(p, '[Successful real pipeline run](https://dbc-cfb7f93a-b497.cloud.databricks.com/jobs/621214800098362/runs/435278296555206?o=7474644614542766) '
 '| [Source and definitions](https://github.com/Roger079/databricks-astro-pipeline/blob/main/docs/data_contract.md). '
 'Profile A: customer amount = source Total; merchandise = Total − Tax. '
 'Profile B: customer amount = Total − ticket discount + Tax; merchandise = Total − ticket discount. '
 'Unknown store/date rules are withheld. The raw Total field mixes these meanings.', 0, 19, 12, 3)

# Explicitly bind each filter to every applicable dataset, never snapshot-wide facts.
filter_page = {'name': 'filters', 'displayName': 'Filters', 'pageType': 'PAGE_TYPE_GLOBAL_FILTERS',
               'layoutVersion': 'GRID_V1', 'layout': []}
for index, (field, kind, title) in enumerate([
    ('business_date', 'filter-date-range-picker', 'Business date — validated two days'),
    ('store_id', 'filter-multi-select', 'Store')]):
    queries = []
    encodings = []
    for ds in ['daily', 'hourly', 'channels', 'menu', 'coverage', 'tickets', 'reviews', 'profiles']:
        name = f'{ds}_{field}'
        queries.append({'name': name, 'query': {'datasetName': ds,
            'fields': [{'name': field, 'expression': f'`{field}`'}], 'disaggregated': False}})
        encodings.append({'fieldName': field, 'displayName': title, 'queryName': name})
    place(filter_page, {'queries': queries, 'spec': {'version': 2, 'widgetType': kind,
          'encodings': {'fields': encodings}, 'frame': {'showTitle': True, 'title': title}}}, index*6, 0, 6, 2)
pages.append(filter_page)

dashboard = {'datasets': datasets, 'pages': pages, 'uiSettings': {'theme': {
    'canvasBackgroundColor': {'light': '#FAF7F2', 'dark': '#202123'},
    'widgetBackgroundColor': {'light': '#FFFFFF', 'dark': '#292B2E'},
    'fontColor': {'light': '#292321', 'dark': '#F7F3EC'},
    'selectionColor': {'light': '#C83830', 'dark': '#F38B79'},
    'visualizationColors': ['#C83830', '#E7A23B', '#28877C', '#506E95', '#8D6593', '#708350'],
    'widgetHeaderAlignment': 'LEFT'}}}

instructions = '''You are the Taco Bueno Pricing & Promotion Decision Lab analyst. Use only the attached validated real tables in workspace.astro_taco_main_real, always is_demo=false. Current scope is 2025-12-31 and 2026-01-01, 114 stores. Do not query raw historical tacos.pricing_data.pricing as if normalized or extrapolate the store-date financial mapping. Historical normalization remains pending.
Primary customer amount = SUM(customer_total); merchandise amount excluding tax after discount = SUM(merchandise_after_discount); tickets = SUM(transactions) in gold_daily_sales or COUNT(*) in silver_checks. Weighted average ticket = SUM(customer_total)/SUM(transactions), never AVG(average_ticket). Currency is unconfirmed: say source monetary units, not USD. These POS amounts are not audited net revenue or settled payment proof. reported_total has mixed financial definitions and must never be the primary revenue measure.
Use one fact table for each metric. Never join daily, hourly, menu or channel facts at raw grain. If necessary aggregate separately to common store/date grain before joining. Ticket identity is store_id + business_date + check_number + is_demo; check_number alone is not unique. silver_checks includes only publishable checks; silver_checks_profile includes all identifiable checks; silver_checks_review contains withheld exceptions. Their flags may overlap. Do not sum overlapping review reasons. Preserve legitimate repeated items. Keep source rows, structural quarantined rows, tickets and financial review tickets separate.
Discounted cohort means reported_discount > 0 at check grain, not a campaign redemption. Ticket discount depth = SUM(reported_discount)/SUM(merchandise_after_discount+reported_discount). A difference between discounted and non-discounted checks is descriptive, not causal lift. Do not allocate ticket totals or discounts to products arbitrarily. gold_menu_performance supports units, not product revenue; reported_line_total is deliberately NULL. Components may overlap within bundles; void and promo adjustments contribute zero units. No profit, margin, ROI, loyalty or retention without missing inputs.
No proven seasonality, promotion lift, cannibalization or keep/kill/return decisions from two holiday days. When asked which promotions should live/die/return, explain missing campaign identity, baseline and history; suggest a controlled test or investigation and give measurable evidence and next step. Do not invent campaign names. Evidence labels: descriptive, estimated association, comparison-supported estimate, insufficient evidence. No causal badge without a design supporting it.
Default answers explain observation window, filters, sample count, metric definition, evidence strength and limitation concisely. gold_quality_summary is a whole-snapshot fact with no date/store dimensions; do not pretend date/store filters apply. Source loaded_at is ingestion time, not a sales date. Duration is POS-reported; do not assume timezone or treat overnight duration assumptions as confirmed.'''


def uid(label):
    return uuid.uuid5(uuid.NAMESPACE_URL, 'astro-taco/' + label).hex


examples = [
 ('What are the primary business KPIs?', f'''SELECT min(business_date) first_date, max(business_date) last_date,
 count(DISTINCT store_id) stores, sum(transactions) published_tickets,
 sum(customer_total) customer_amount, sum(merchandise_after_discount) merchandise_amount,
 sum(customer_total)/nullif(sum(transactions),0) weighted_average_ticket
 FROM {DB}.gold_daily_sales WHERE is_demo=false'''),
 ('How many checks were withheld and why?', f'''SELECT review_reason, count(*) review_checks
 FROM {DB}.silver_checks_review WHERE is_demo=false GROUP BY review_reason ORDER BY review_checks DESC'''),
 ('Compare discounted and non-discounted baskets without claiming lift', f'''SELECT
 CASE WHEN reported_discount>0 THEN 'Ticket discount present' ELSE 'No ticket discount' END cohort,
 count(*) tickets, avg(customer_total) average_customer_amount,
 avg(merchandise_after_discount) average_merchandise_amount, sum(reported_discount) ticket_discounts
 FROM {DB}.silver_checks WHERE is_demo=false GROUP BY 1'''),
 ('What is publication coverage?', f'''SELECT sum(identifiable_checks) identifiable_checks,
 sum(published_checks) published_checks, sum(published_checks)*1.0/nullif(sum(identifiable_checks),0) coverage_ratio
 FROM {DB}.gold_publication_coverage WHERE is_demo=false''')]
table_descriptions = {
 'gold_daily_sales': 'Published store-day ticket counts and normalized amounts. Primary executive KPI source; weight averages.',
 'gold_hourly_sales': 'Published store/date/POS-hour demand and normalized amounts; not a seasonality model.',
 'gold_channel_hourly': 'Published store/date/hour/channel facts. Source channels require interpretation.',
 'gold_menu_performance': 'Published store-day category/item units and source item discounts. No product revenue; bundle components present.',
 'gold_publication_coverage': 'Store-day identifiable and published ticket counts; financial exception and repeated-row flags may overlap.',
 'gold_quality_summary': 'Whole source snapshot ROW quality; no date/store grain. Unaffected by store/date filters.',
 'silver_checks': 'One publishable check per composite store/date/check/is_demo key. Normalized customer and merchandise amounts.',
 'silver_checks_review': 'One withheld check per composite key; reasons and residual. Never include withheld amounts in published KPIs.',
 'silver_checks_profile': 'All identifiable checks before publication, with is_publishable and financial profile. Use for reconciliation only.'}
space = {'version': 2, 'config': {'sample_questions': [
    {'id': uid('sample'+q), 'question': [q]} for q, _ in examples]},
    'data_sources': {'tables': [{'identifier': f'{DB}.{t}', 'description': [d]} for t, d in sorted(table_descriptions.items())]},
    'instructions': {'text_instructions': [{'id': uid('instructions'), 'content': [instructions]}],
                     'example_question_sqls': [{'id': uid(q), 'question': [q], 'sql': [s]} for q, s in examples]}}
space['config']['sample_questions'].sort(key=lambda x: x['id'])
space['instructions']['example_question_sqls'].sort(key=lambda x: x['id'])


def write(path, obj):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    # Preserve the explicit live association when rebuilding an already deployed asset.
    evidence = ROOT / 'docs/evidence/promotion-bi-deployment.json'
    if evidence.exists():
        deployed = json.loads(evidence.read_text(encoding='utf-8'))
        dashboard['uiSettings']['genieSpace'] = {'isEnabled': True,
            'overrideId': deployed['genie_space_id'], 'enablementMode': 'ENABLED'}
    write('dashboards/promotion_decision_lab.lvdash.json', dashboard)
    write('genie/promotion_decision_lab.geniespace.json', space)
    print(f'Built {len(datasets)} datasets, {len(pages)-1} content pages and a global filter page.')
