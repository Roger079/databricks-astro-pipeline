# Taco Bueno | Pricing & Promotion Analytics

A Databricks analytics project that transforms restaurant point-of-sale data into reliable business metrics and a foundation for pricing and promotion decisions.

The project explores a central question: **Which promotions should continue, stop, or return?** It brings together reproducible data processing, financial reconciliation, an interactive dashboard, and natural-language analysis through Databricks Genie.

## From transactions to decisions

The pipeline organizes data into three layers:

```text
POS source → Bronze snapshot → Silver validation and reconciliation → Gold analytics
                                                                          ↓
                                                                 AI/BI dashboard + Genie
```

- **Bronze** preserves a versioned source snapshot and ingestion provenance.
- **Silver** standardizes records, distinguishes sales from components and adjustments, and reconciles transactions using financial rules specific to each store and date.
- **Gold** provides daily, hourly, store, channel, and menu-level analytics, alongside data-quality and publication-coverage metrics.

The workflow orchestrates ingestion, Lakeflow transformations, validation, and analysis. Reprocessing the same source snapshot has produced identical business counts and amounts.

## Validated dataset

The current implementation processes a real POS extract covering **December 31, 2025, and January 1, 2026**.

| Measure | Verified result |
| --- | ---: |
| Stores represented | 114 |
| Source records | 284,428 |
| Identifiable transactions | 40,306 |
| Transactions published for analysis | 40,257 |
| Transactions held for financial review | 49 |
| Transaction publication coverage | 99.87843% |
| Normalized customer amount, including tax | 615,846.68 |
| Merchandise amount, after discounts and excluding tax | 571,874.16 |

Amounts are expressed in source monetary units; the currency has not been confirmed. Financial definitions are inferred from the supplied data and checked through reconciliation. These metrics represent reconciled POS amounts rather than audited revenue.

## Analytics experience

The AI/BI dashboard connects business performance with the evidence supporting it:

| Dashboard section | Purpose |
| --- | --- |
| Business overview | Compare transaction volume, normalized amounts, and average transaction value. |
| Pricing and discounts | Examine discount frequency, discount depth, and basket differences. |
| Demand | Explore activity by date, store, reported hour, and channel. |
| What people order | Understand the distribution of item and category units. |
| Decisions and experiments | Connect observations to recommended investigations, evidence strength, and next steps. |
| Data trust | Inspect source provenance, financial exceptions, reconciliation, and coverage. |

A connected Genie space supports natural-language questions over curated, validated tables using documented metric definitions.

## Data reliability

Ticket-level totals, taxes, and discounts are counted once per transaction. Legitimate repeated item occurrences are preserved. Structurally invalid records and transactions requiring financial review follow separate paths, with exclusions made visible through coverage metrics.

Store-specific financial rules normalize differing source definitions into comparable customer and merchandise amounts. Product analysis reports units without assigning an entire transaction's value to every item. Bundle components and monetary adjustments require separate interpretation.

## Scope and interpretation

The two-day extract demonstrates ingestion, reconciliation, and descriptive analysis. It supports comparisons of demand, discounts, and ordering patterns within the observed window.

Reliable promotion lift, seasonality, and cannibalization analysis require validated historical data, identifiable offers, and defensible comparison periods. Historical normalization and those strategic analyses remain future work. Profitability and return on investment also require cost data that is not available in the current dataset.

## Technology

Databricks · Delta Lake · Lakeflow · Python · SQL · AI/BI Dashboards · Genie

## Further reading

- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data_dictionary.md)
- [Data contract and financial definitions](docs/data_contract.md)
- [Analytical findings](docs/findings.md)
- [Promotion analytics methodology](docs/dashboard_plan.md)
