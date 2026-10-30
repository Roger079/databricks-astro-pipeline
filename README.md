# Astro · Taco Bueno

Demostración de ingesta y procesamiento de **dos días de datos POS reales**:
31 de diciembre de 2025 y 1 de enero de 2026, desde
`workspace.default.tb_daily_tld_01_01_2026_m`. No se requiere procesar la fuente
histórica de 85 millones de filas para esta entrega.

El snapshot Bronze lee una tabla que ya existe en Databricks. Esto demuestra
ingesta tabla-a-tabla del extracto real entregado al equipo. El job conserva
la versión Delta leída y demuestra el recorrido reproducible hasta Gold.

## Objetivo comercial

Taco Bueno - Pricing & Promotion Analytics: investigar qué ofertas conviene
mantener, reconsiderar o volver a probar. La ingesta real de dos días demuestra
el pipeline; lift, estacionalidad y posible canibalización requieren ampliar el
análisis a la historia disponible. Ver [plan del dashboard](docs/dashboard_plan.md).

## Estado

La ejecución real y su rerun ya pasaron: 284,428 filas, 40,257 tickets publicados
y 49 en revisión, con iguales importes en ambas ejecuciones. Hay 28 pruebas
locales. Ver [hallazgos](docs/findings.md) y evidencia normalizada.

El trabajo original de Magda está preservado en `magda` (commit `4d2aef2`) y fue
integrado en `main` con un merge. Su demo original y evidencia se conservan.
Las correcciones de main se prueban en `workspace.astro_taco_main_demo`, separado
de `workspace.astro_taco_demo` y de las tablas reales del equipo.
Consultar [evidencia](docs/execution_evidence.md) y [pendientes](docs/delivery_checklist.md).

Dashboard real AI/BI y espacio Genie conectados: seis páginas de indicadores,
descuentos, demanda, mezcla de menú, decisiones y confianza del pipeline.
Ver [configuración y verificación](docs/promotion_dashboard_setup.md),
[prompt para Genie Code](docs/genie_dashboard_prompt.md) y
[enlaces y evidencia API/SQL](docs/evidence/promotion-bi-deployment.json).
El análisis histórico de lift, estacionalidad y canibalización sigue pendiente.
`dev` usa `amount_grain=check`, verificado en los 40,306 tickets reales.
Los perfiles financieros por tienda son inferidos, versionados y comprobados por ecuaciones; ver [análisis](docs/financial_definition_analysis.md).

## Estructura requerida

```text
databricks.yml
resources/
  jobs/daily_orchestration_job.yml
  pipelines/lakeflow_pipeline.yml
src/transformations/
  silver/
    mv_store_financial_profiles.py
    mv_pos_typed.py
    mv_pos_classified.py
    mv_pos_checks.py
  gold/
    mv_store_daily.py
    mv_channel_hourly.py
    mv_item_daily.py
    mv_data_quality.py
notebooks/
  00_demo_source.py
  01_ingest.py
  03_validate.py
  04_analysis.py
  05_source_diagnostics.py
config/store_financial_profiles.json
tests/test_pipeline.py
dashboards/astro_demo.lvdash.json
docs/
```

Orquestación en `resources`; lógica de tablas Silver/Gold en
`src/transformations`, siguiendo la plantilla del reto. Los notebooks restantes
son herramientas de ingesta, diagnóstico, validación y presentación.

## Flujo y reglas

Fuente → snapshot Bronze → tipado/clasificación Silver → tickets y artículos →
Gold diario, horario, canales, categorías y calidad → validación → análisis.

- Clave de ticket: tienda + fecha de negocio + número de cheque, pendiente de
  confirmar si el POS requiere otra columna de identidad.
- Total, Tax y Total Discount se cuentan una vez por ticket. Los perfiles A/B
  se normalizan a `customer_total` y `merchandise_after_discount`; el Total fuente
  no se interpreta como una definición uniforme de ventas entre tiendas.
- Repeticiones idénticas se preservan y cuentan como candidatos. No se elimina
  el artículo ni se excluye automáticamente el ticket. La fuente debe ser un
  snapshot sin cargas duplicadas; si existen, resolverlas por procedencia/ID real.
- Errores de tipos van a cuarentena. Descuentos, cantidades cero y ajustes Item Promo reconocidos se conservan; ecuaciones fallidas y estados ambiguos van a revisión.
- Relojes invertidos no se convierten automáticamente en servicios de casi 24 h.
  La ventana nocturna documentada permite un supuesto marcado; duraciones
  inválidas no eliminan ventas y no entran en promedios.
- Se publica cobertura de tickets para explicar las exclusiones del análisis.

## Requisitos

Unity Catalog, serverless Jobs y Lakeflow habilitados. CLI autenticada con perfil
`datathon` o el perfil propio del equipo; no guardar tokens en Git. La identidad
que ejecuta necesita leer la fuente y crear/administrar su esquema destino.
La ingesta concede ALL PRIVILEGES y MANAGE a `team_principals` en el esquema
proyecto; todos necesitan USE CATALOG en workspace (ya heredado por los usuarios).

## Prueba sintética del código de main

```powershell
databricks bundle validate -t demo -p datathon --strict
databricks bundle deploy -t demo -p datathon
databricks bundle run seed_demo -t demo -p datathon
databricks bundle run daily_orchestration -t demo -p datathon
```

Ejecutar secuencialmente. Esperado: **12 Bronze, 11 Silver, 1 cuarentena,
5 tickets publicados, 2 en revisión, importe cliente normalizado 37.96 y mercancía
después de descuentos 35**. El Total fuente suma 38.76 y se conserva para rastreo.
La demo cubre ambos perfiles, artículos repetidos, descuentos, componentes de
cantidad cero, promo negativa, anulación parcial, fecha inválida, perfil desconocido
y una diferencia contable. No son ventas reales ni se mezclan con demos históricas.

## Demostración con los dos días reales

1. Revisar las reglas inferidas en docs/data_contract.md y los 114 perfiles
   versionados en config/store_financial_profiles.json.
2. El grano check ya se verificó en toda la fuente real. No necesita confirmación
   externa; los tickets se publican solo si cumplen su ecuación y controles.
3. Eliminar overrides locales antiguos `amount_grain=unconfirmed`, si existen.
4. Validar, desplegar y ejecutar:

```powershell
databricks bundle validate -t dev -p datathon --strict
databricks bundle deploy -t dev -p datathon
databricks bundle run daily_orchestration -t dev -p datathon
```

El destino es `workspace.astro_taco_main_real`; no se sobrescriben las tablas de
`workspace.default`. El horario de las 06:00 sigue pausado. Un miembro designado
debe administrar el despliegue compartido: desplegar desde otra identidad crea
recursos diferentes y no debe apuntarlos simultáneamente al mismo esquema.

## Verificación y presentación

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

Las pruebas DuckDB ejecutan el SQL real de los archivos; no sustituyen a Spark,
Delta, Lakeflow ni a la validación con datos reales. El job comprueba conciliación
de filas, unicidad de tickets, agregados diarios/horarios/canales y cobertura.

Dos fechas permiten explicar el pipeline y comparar tiendas/categorías con
cobertura explícita. No permiten afirmar tendencias mensuales, estacionalidad ni
crecimiento interanual. Consultar docs/delivery_checklist.md para el estado de ejecución real, dashboard y conclusiones.

Ver [arquitectura](docs/architecture.md), [diccionario](docs/data_dictionary.md),
[contrato](docs/data_contract.md), [operación](docs/runbook.md) y
[rúbrica](docs/rubric.md).

## Evidencia de ejecución normalizada

Usar `python scripts/capture_run_evidence.py --run-id ID --pipeline-id ID --schema astro_taco_main_real --kind real`
(o `--schema astro_taco_main_demo --kind demo`). Captura conciliación, perfiles,
razones de revisión y expectations únicamente dentro de la ventana de ese run.
Los archivos normalized-*-verification.json están separados de la evidencia histórica.

## Aislamiento entre despliegues

El destino real de main es workspace.astro_taco_main_real. El esquema
workspace.astro_taco_dev pertenece al pipeline de Magda y no debe reutilizarse
para este despliegue. La ingesta verifica pipelines.pipelineId antes de escribir
Bronze; el job pasa expected_pipeline_id automáticamente. El modo manual debe
proporcionar ese ID cuando ya existen tablas Silver/Gold.
