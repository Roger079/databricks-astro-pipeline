# Genie Code dashboard authoring prompt

Open the **new Pricing & Promotion Decision Lab dashboard**, choose **Edit**, and
open **Genie Code**. Paste the prompt below there. The dashboard's **Ask Genie**
button opens the separately configured Genie space for questions about the data;
it is not the dashboard authoring panel.

The native dashboard and Genie space are provisioned by
`scripts/deploy_promotion_dashboard.py`. Live links and verification evidence are
in `docs/evidence/promotion-bi-deployment.json`; setup is in
`docs/promotion_dashboard_setup.md`.

```text
Refine this existing dashboard into “Taco Bueno — Pricing & Promotion Decision
Lab” for our Databricks datathon. The business question is: Which promotions
should continue, stop, or return? Investigate pricing, lift, seasonality and
possible cannibalization, while showing exactly what the available evidence
supports. Preserve the linked Genie space and existing dashboards elsewhere.

Use only the connected validated real data in workspace.astro_taco_main_real,
always is_demo=false. Current scope is 2025-12-31 and 2026-01-01, 114 stores.
This is a real ingestion demonstration, not a complete historical promotion
evaluation. Do not use synthetic/demo schemas or workspace.astro_taco_dev.
The raw historical tacos.pricing_data.pricing table is not normalized for these
metrics; do not attach or aggregate it as a trusted strategic dataset.

Create a polished, readable six-tab analytical dashboard with consistent date
and store filters. Retain the following sections and improve charts, tooltips,
number formats and layout. Prefer clear bars/tables to a false two-day trend.

1. Business overview: customer amount including tax, merchandise amount after
discount excluding tax, published tickets, weighted average ticket, active
stores and publication coverage. Show daily and comparable store breakdowns.
Explain the observation window and source monetary units; currency is unknown.

2. Pricing and discounts: positive ticket-discount incidence, ticket-discount
depth, discount amount and discounted versus non-discounted basket comparisons,
with sample counts. Label these descriptive cohorts, not campaigns or causal
lift. Do not add SKU price distributions until comparable SKU identity and
unit-versus-extended price semantics are validated. Separate bundle components,
zero-price items and monetary adjustments in explanations.

3. Demand and comparison readiness: date, POS-reported hour and channel demand;
same-scope store/date comparisons. Clearly show that seasonal patterns,
promotion lift, expected demand and confidence intervals are unavailable until
historical rules and a credible baseline are validated. Do not fabricate them.

4. Menu mix and substitution signals: category and item/component units, with
category drill-down and a detail table. Explain bundle overlap. Present possible
substitution as a future investigation, not measured causal cannibalization.
Product revenue and margin are unavailable.

5. Decisions and next experiments: a prominent evidence-backed decision table
with action, topic, observation/evidence, confidence, next step and limitation.
Use the connected decisions dataset. Show Investigate / Design a test /
Prepare history / Defer keep-stop-return as appropriate. No invented promotion
names or unsupported rankings. Keep this board explicitly labeled as the
whole validated snapshot, unaffected by date/store filters. Explain the gates
for future recommendations: reliable offer identity, adequate sample, comparable
coverage, defensible baseline, target/substitute/category outcomes and
uncertainty. No profit/ROI without costs or retention without customer IDs.

6. Trust and pipeline: source snapshot and Delta version, ingestion timestamp,
Bronze→Silver→Gold flow, row quarantine, ticket review, publication coverage,
financial profile split, overlapping review reasons and the successful run link.
Keep snapshot-wide row-quality/provenance widgets explicitly unfiltered.
Do not combine rows and checks into one funnel.

Metric rules:
- gold_daily_sales: SUM(customer_total), SUM(merchandise_after_discount),
  SUM(transactions); weighted ticket = SUM(customer_total)/SUM(transactions).
  Never AVG(average_ticket) and never use mixed-definition reported_total as
  primary revenue. POS amounts are not audited revenue or settled payments.
- silver_checks: one publishable ticket per store_id + business_date +
  check_number + is_demo. Count ticket discounts once per check.
  Positive reported_discount identifies the descriptive discounted cohort.
  Discount depth = SUM(reported_discount) /
                   SUM(merchandise_after_discount + reported_discount).
- gold_publication_coverage: coverage = SUM(published_checks) /
  SUM(identifiable_checks). silver_checks_review holds excluded checks.
  Review flags can overlap; do not sum overlapping categories into a total.
- gold_menu_performance: units only; reported_line_total is intentionally NULL.
  Never allocate full ticket amounts or ticket discounts to each product.
- Use one fact table per analysis; aggregate facts separately before joining
  at compatible grain. Never join raw daily/hourly/menu/channel facts together.
- Global filters bind explicitly to every applicable dataset. They must update
  all related numerators and denominators. Snapshot-wide datasets remain labeled.
- Preserve legitimate repeated item occurrences. Do not apply blanket DISTINCT.

Baseline verification with all stores/dates selected: 40,257 published tickets,
40,306 identifiable checks, 49 review checks, 39 equation exceptions,
customer amount 615,846.68, merchandise amount 571,874.16 and publication
coverage 99.87843%. These are validation references, not hard-coded chart data.

Use evidence labels: Descriptive / Estimated association /
Comparison-supported estimate / Insufficient evidence, only where warranted.
Each tab should answer a business question and state an action and limitation.
Validate dataset SQL, filters, aggregate grain and the all-data KPI totals.
Keep the dashboard editable by all three project admins and retain Ask Genie.
```

For data questions in **Ask Genie**, try:

- “Summarize the primary business KPIs, observation window and publication coverage.”
- “Compare discounted and non-discounted baskets, with sample counts, without claiming causal lift.”
- “Which promotion decisions can we support today, and what evidence is missing for keep/stop/return?”
- “Explain the financial exceptions and how they affect published results.”

The fuller strategic scope remains in `docs/dashboard_plan.md`. The current
dashboard makes the two-day evidence usable; it does not complete historical
lift, seasonality or cannibalization analysis.
