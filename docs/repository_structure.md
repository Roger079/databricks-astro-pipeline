# Repository structure

The repository follows the Databricks template supplied for the challenge:
job orchestration belongs in `resources/jobs`, pipeline configuration belongs
in `resources/pipelines`, and Silver/Gold table definitions belong in
`src/transformations`.

```text
databricks-astro-pipeline/
|-- databricks.yml
|-- resources/
|   |-- jobs/
|   |   |-- daily_orchestration_job.yml
|   |   `-- demo_seed_job.yml
|   `-- pipelines/
|       `-- lakeflow_pipeline.yml
|-- src/
|   `-- transformations/
|       |-- silver/
|       |   |-- mv_store_financial_profiles.py
|       |   |-- mv_pos_typed.py
|       |   |-- mv_pos_classified.py
|       |   `-- mv_pos_checks.py
|       `-- gold/
|           |-- mv_store_daily.py
|           |-- mv_channel_hourly.py
|           |-- mv_item_daily.py
|           |-- mv_menu_discount_scorecard.sql
|           `-- mv_data_quality.py
|-- notebooks/
|-- config/
|-- dashboards/
|-- genie/
|-- scripts/
|-- tests/
|-- validation/
`-- docs/
```

## Required locations

| Location | Responsibility |
| --- | --- |
| `resources/jobs/daily_orchestration_job.yml` | Main job tasks, dependencies, retry, timeouts and paused daily schedule. |
| `resources/jobs/demo_seed_job.yml` | Source-fixture job enabled only in the demo target. |
| `resources/pipelines/lakeflow_pipeline.yml` | Lakeflow settings and transformation source discovery. |
| `src/transformations/silver/` | Typed records, record classification, scoped financial profiles and reconciled tickets. |
| `src/transformations/gold/` | Business aggregates, quality summaries and publication coverage. |

The root `databricks.yml` contains bundle identity, shared configuration,
permissions, targets and resource includes. All job definitions are in
`resources/jobs`, including the target-specific demo job. Relative notebook
paths in those files resolve from `resources/jobs`.

The template's order/customer table names illustrate the layout. This project
uses POS-specific names and `mv_` prefixes for its materialized views. Adding
unused order/customer files or renaming these views as streaming tables would
misrepresent the implementation.

## Supporting files

The additional folders support the required pipeline structure:

- `notebooks/`: source ingestion, synthetic-source preparation, diagnostics,
  publication validation and analysis. Silver/Gold table definitions remain
  under `src/transformations`.
- `config/`: versioned store/date financial rules.
- `dashboards/` and `genie/`: serialized analytics assets.
- `scripts/`: asset generation, BI provisioning and evidence capture utilities.
- `tests/`: automated checks.
- `validation/`: reproducible analysis and diagnostic SQL.
- `docs/`: architecture, definitions, evidence and presentation notes.

Generated PDFs and temporary files are excluded from Git. These supporting
folders supplement the required locations without moving orchestration or
Silver/Gold table definitions outside them.
