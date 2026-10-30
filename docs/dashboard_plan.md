# Taco Bueno: Pricing & Promotion Decision Lab

## Purpose and feasibility

Datathon brief supplied by the team: which promotions should continue, stop, or
return, using lift, seasonality and cannibalization. The dashboard should support
those decisions and let judges inspect the reliability of the supporting pipeline.

The two-day real pipeline is complete and remains the ingestion demonstration.
It supports price/discount diagnostics and basket comparisons, not seasonality or
credible before/after lift by itself. A strategy dashboard needs the historical
table already available to the team: tacos.pricing_data.pricing.

Read-only feasibility profile, 2026-10-30:

- 85,273,331 rows and 119 stores.
- 2025-01-22 through 2026-09-27; 573 distinct parsed dates. Missing calendar days
  and varying store coverage must be measured, not interpreted as zero demand.
- 1,620,670 item rows have positive Item Discount; these are not distinct redemptions.
- No explicit campaign ID, promotion schedule, costs, customer IDs or inventory
  fields were found in the available schema.
- Name search found Item Promo (225,136 rows), School Special (NR) (1,292),
  and Beef Muchaco (Promo) (one). These are candidate labels, not proof of
  distinct marketing campaigns. First/last appearance is not a confirmed schedule.

Historical normalization must be revalidated by store and time interval. The
current 114-store, two-day financial mapping must not be extrapolated to all 119
stores and twenty months. All strategic datasets must come through validated
Silver/Gold transformations rather than reinstating raw dashboard aggregations.

## The story the dashboard should tell

1. Which observed offer patterns deserve attention?
2. Do quantity and merchandise amounts improve against a defensible baseline?
3. Is that increase offset by discount spend or displacement of other products?
4. Where and when does the pattern hold, and how strong is the evidence?
5. Can the viewer trace the recommendation to reconciled data and a successful run?

Use evidence badges: descriptive, estimated association, comparison-supported
estimate, insufficient evidence. No badge should imply randomized causal proof.
Never display a keep/kill recommendation when an offer cannot be identified
reliably or lacks a credible comparison. Offer a test candidate instead.

## Six planned pages

| Page | Decision | Main visuals | Guardrails |
|---|---|---|---|
| 1. Promotion decision board | Continue, test, reconsider, or revisit? | Offer-cohort scorecard; target-item lift versus category/basket change; discount spend; evidence confidence; recommendation explanation | Recommendations gated on identity, sample size, comparable coverage and a baseline; no profit claims |
| 2. Pricing and discounts | Where are prices and discounts inconsistent? | Observed unit-price distributions for comparable SKUs; store/period price matrix; discount incidence; ticket-discount depth; zero-price components and signed promo adjustments separately | Unit versus extended prices normalized first; bundle components not treated as standalone priced sales; ticket discounts not arbitrarily allocated to products |
| 3. Lift and seasonality | When is the observed response stronger? | Store-day panel; comparable-weekday baseline; observed versus expected volume; uncertainty bands where defensible; weekday/hour and calendar-month summaries | Incomplete days are missing, not zero; twenty months supports limited calendar comparisons, not a robust multi-year seasonal model |
| 4. Basket mix and possible cannibalization | Does the offer grow the category or shift purchases? | Target versus substitute-item volumes; category totals; basket merchandise amounts; attach rates; estimated displacement alongside net category change | Product overlap and association are not causal proof; related products affected by the offer are not automatically valid control products |
| 5. Store and channel execution | Where should we test or adjust execution? | Volume versus average-ticket matrix; comparable-store rankings; reported-hour/channel heatmap; promotion-cohort outcomes by store | Same comparison window, source coverage and exclusion rates shown; channel codes require interpretation; clocks are POS-reported, not an assumed timezone |
| 6. Trust and pipeline evidence | Why should we trust the recommendation? | Financial normalization example; separate row and ticket reconciliations; exception explorer; coverage heatmap; run ID, source Delta version, DAG and expectations | Do not put rows and tickets in one funnel; distinguish structural quarantine from financial review; performance claims need measured evidence |

The judge walkthrough should use pages 1, 3, 4 and 6; the other pages provide
depth for questions. Each page answers one question and ends with a concise
finding, action and limitation. Charts should earn their space rather than repeat KPIs.

## Defining offer cohorts with the available data

Start by validating stable product identifiers using POS Code, Menu Item, category
and store history. POS Code is not assumed to be a campaign identifier. Separate
renames, unit quantities, bundles and price changes before comparing products.

Build transparent candidate offer fingerprints from identifiable product/basket
patterns, observed menu prices and discount signatures. Keep generic Item Promo
as an adjustment until it can be associated with a specific offer from the data.
Document confidence and ambiguity. Cohorts are analytical constructs, not official
campaign names. A single rare Promo label is not enough for a decision.

## Analytical methods

- Descriptive layer: discount frequency, ticket-discount depth, product mix,
  basket amounts and same-store comparisons. Separate discounted versus
  non-discounted observations without calling their difference causal lift.
- Baseline layer: compare equivalent stores, weekdays and seasonal windows;
  use per-observed-store-day rates and check whether store-day coverage changes.
- Lift layer: observed minus expected units and merchandise amounts. Use matched
  unexposed stores or staggered exposure only if the data supports them. Inspect
  pre-trends; otherwise label the estimate as associational or unavailable.
- Cannibalization layer: inspect target, likely substitutes, category and total
  basket outcomes together. A product-level increase with flat category demand
  is a substitution signal, not automatically incremental business.
- Uncertainty layer: sample counts, observation windows, excluded observations,
  baseline sensitivity and intervals when the sample/structure supports them.
- Decision layer: no margin/ROI without costs; no loyalty/retention without
  customer identifiers. Recommend a controlled test when evidence is incomplete.

For the two-day demonstration, a standout but honest feature is an arithmetic
volume-versus-ticket-value waterfall. With revenue-like amount R = N * A,
decompose the difference symmetrically:

    volume contribution = (N2 - N1) * (A1 + A2) / 2
    ticket-value contribution = (A2 - A1) * (N1 + N2) / 2

These sum exactly to the observed amount difference. They are an arithmetic
decomposition, not explanations of why customer behavior changed.

## Interaction and visual design

- Persistent scope banner: real versus synthetic, analysis window, source version,
  last successful validation, ticket coverage and financial rule version.
- Real dashboard datasets exclude is_demo=true at query level. No synthetic
  values appear as live results or in recommendation rankings.
- Global date/store filters where grains support them; page-level item/category,
  channel and offer-cohort filters. Show active filters and clear reset controls.
- Click a candidate to inspect its supporting store/product evidence, then its
  quality exceptions. Cross-filtering requires compatible/shared datasets; use
  explicit drill-through mappings across different datasets.
- A quality measure must respond to its selected scope. Snapshot-level audit
  counters that cannot follow a product filter must be labeled as whole-snapshot.
- Accessible, consistent colors: neutral business metrics, teal favorable signal,
  amber uncertainty/review, red confirmed rule failure. Do not rely on color alone.
- Avoid crowded pies, currency assumptions, unlabeled denominators, arbitrary
  top-ten cutoffs and red/green recommendations unsupported by a baseline.

## Data models to prepare before building

Existing two-day models: gold_daily_sales, gold_channel_hourly,
gold_menu_performance, gold_quality_summary and gold_publication_coverage.

Additional proposed models under src/transformations/gold:

| Model | Grain | Why it is needed |
|---|---|---|
| gold_store_item_day | Store/date/normalized item/record role | Historical comparable-item panel, priced units versus components |
| gold_offer_cohort_day | Store/date/inferred offer cohort | Transparent exposure, discount signature, baseline eligibility and confidence |
| gold_basket_associations | Store/date/target/complement or substitute | Attach rates and substitution indicators without joining item rows twice |
| gold_quality_store_day | Store/date/rule | Scoped quality and coverage; unknown-date/key records remain separately visible |
| gold_run_audit | Run/source version/rule version | Persistent dashboard-accessible execution evidence from API/event logs |

These are planned models, not claims of completed implementation. Historical
profiling and offer identification are feasibility gates before advanced lift charts.
Use preaggregated Gold datasets; do not point the dashboard at 85 million raw rows.

## Rubric mapping

| Criterion | Visible evidence |
|---|---|
| GitHub and documentation | Dashboard JSON, resource configuration, metric dictionary, analytical methods and build/run instructions |
| Job and pipeline design | Source-to-Gold DAG, stage status, source version and failure/recovery example |
| Transformations and table value | Two financial conventions, ticket/item separation, record roles and normalized metrics |
| Streaming, MVs, clustering, expectations | Explain why batch fits the snapshot; show actual MVs/expectations and evaluated clustering, without inventing speedups |
| Data quality | Row/ticket reconciliation, 49 current tickets under review, scoped coverage and drillable reasons |
| Analysis and value | Evidence-qualified pricing/promotion recommendations and basket/category outcomes |
| Communication | Clear question per page, consistent measures and traceable recommendation rationale |

## Build sequence and acceptance checks

1. Preserve the successful two-day demo and rerun evidence.
2. Audit historical coverage, store-time financial profiles and product identifiers.
3. Decide whether offers can be identified. If not, make the board a pricing and
   discount opportunity board with test candidates rather than fabricated campaigns.
4. Define Gold models, denominators, baseline eligibility and confidence labels.
5. Design the six pages and a short judge walkthrough before implementation.
6. Build/version a new native Databricks dashboard, without replacing old dashboards.
7. Validate filters across grains, weighted averages, empty selections, unknown
   profiles, published/review totals, synthetic exclusion and teammate access.
8. Publish only after data validation; then add a dashboard refresh task dependent
   on successful validation/analysis. No unsolicited email subscribers.

Native features verified in official documentation:
- Filters and drill-through: https://docs.databricks.com/aws/en/dashboards/manage/filters/
- Dashboard task after validation: https://docs.databricks.com/aws/en/jobs/tasks/dashboard
- Versioning/developer workflow: https://docs.databricks.com/aws/en/dashboards/automate
