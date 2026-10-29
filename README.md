# Databricks Astro Pipeline

Repository template for the Databricks Datathon challenge. Keep orchestration in
`resources/` and table logic in `src/transformations/`.

```text
databricks-astro-pipeline/
├── resources/
│   ├── jobs/
│   │   └── daily_orchestration_job.yml
│   └── pipelines/
│       └── lakeflow_pipeline.yml
└── src/
    └── transformations/
        ├── silver/
        │   ├── st_orders_cleaned.py
        │   └── mv_customer_summary.sql
        └── gold/
            ├── st_daily_revenue.py
            └── mv_executive_kpis.sql
```

## Folder purpose

- `resources/jobs/`: Databricks job definitions, schedules, and task orchestration.
- `resources/pipelines/`: Lakeflow or Delta Live Tables pipeline configuration.
- `src/transformations/silver/`: Cleaned and standardized table logic.
- `src/transformations/gold/`: Business-ready tables, metrics, and reporting logic.

The files are placeholders using the reference template's example names. Add
challenge-specific configuration and table logic before running or deploying.

Structure based on Bruno Chavez's “Basic Databricks GitHub Repository Template”
(October 13, 2026).
