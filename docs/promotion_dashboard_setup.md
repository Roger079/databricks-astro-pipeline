# Pricing & Promotion Decision Lab

[Published dashboard](https://dbc-cfb7f93a-b497.cloud.databricks.com/dashboardsv3/01f1d42ecb9314b996d9c68d88de031e/published?o=7474644614542766)
| [Edit dashboard / Genie Code](https://dbc-cfb7f93a-b497.cloud.databricks.com/dashboardsv3/01f1d42ecb9314b996d9c68d88de031e?o=7474644614542766)
| [Genie Q&A](https://dbc-cfb7f93a-b497.cloud.databricks.com/genie/rooms/01f1d42ecb0a156c8ba220f1312dc57c?o=7474644614542766).

The native AI/BI dashboard uses eleven SQL datasets over the validated real
schema, `workspace.astro_taco_main_real`. Six content tabs cover business KPIs,
discount diagnostics, demand, menu mix, decisions, and pipeline trust. A shared
filter page explicitly binds business date and store to eight applicable
datasets. Decisions, source provenance, and whole-snapshot quality intentionally
remain unfiltered and are labeled accordingly.

The linked Genie space has nine curated tables, business instructions, four
example SQL questions, and starter questions. It has no attachment to the
unvalidated historical source. The deployment script grants CAN_MANAGE to
all three project members on both new assets. Published dashboard queries use
viewer credentials, so viewers also need warehouse/data permissions; the three
configured project members already have these.

Live asset URLs, IDs, SQL validation statement IDs, counter outputs, permissions,
and publish response are saved in `docs/evidence/promotion-bi-deployment.json`.
Existing dashboards and pipeline definitions are preserved. This deployment adds
BI assets; it does not recreate or change pipeline-owned tables.

## Rebuild and deploy

With Python and the Databricks CLI available, from the repository root:

```powershell
python scripts/build_promotion_dashboard.py
python scripts/deploy_promotion_dashboard.py --profile datathon
```

The builder produces `dashboards/promotion_decision_lab.lvdash.json` and
`genie/promotion_decision_lab.geniespace.json`. The deployer executes every dataset
SQL and every data-widget aggregation on the SQL warehouse before creating or
updating the assets. It then links Genie, applies team permissions, publishes,
and verifies the saved dashboard association and space table list through APIs.
Subsequent deployments reuse only IDs from this dashboard's evidence file.

```powershell
python scripts/deploy_promotion_dashboard.py --profile datathon --validate-only
```

Use validation-only to execute queries without changing BI assets. Do not delete
the evidence file before redeploying, as that would create a new pair of assets.
No token is stored in the repository; authentication uses the CLI profile.

## Use and refresh

Open the dashboard's Edit view and use Genie Code with
`docs/genie_dashboard_prompt.md` to refine the layout. Ask Genie on the published
dashboard opens the linked Q&A space. These are separate capabilities.

After a successful real pipeline run, refresh the dashboard to query current
Gold/Silver tables. There is no new automatic refresh schedule, subscription or
pipeline task in this change. Source provenance and the current pipeline output
reflect the data snapshot; the successful run link is a static evidence link and
must be updated if the referenced demonstration run changes.

The source scope is two holiday dates. For a strategic portfolio dashboard,
validate historical financial profiles and offer identity, then publish trusted
historical tables and extend the space/dashboard together. Do not extrapolate
the two-day mapping to all history. See `docs/dashboard_plan.md`.

## Verification limits

SQL execution, asset persistence, publication and permissions are checked through
Databricks APIs. Live Genie smoke checks also returned the correct KPI totals
and declined unsupported keep/stop/return and causal-effect conclusions;
the question/answer evidence is saved with the deployment record. Genie output
remains generated content and should be reviewed, including suggested follow-ups.
The dashboard still needs a human visual pass in the Databricks
UI, including switching tabs, selecting one store/date, and trying Ask Genie
with another team member's login. API checks do not prove browser rendering or
the other users' effective sessions.
