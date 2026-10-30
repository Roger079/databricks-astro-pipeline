# Astro · Taco Bueno

Demostración de ingesta y procesamiento de **dos días de datos POS reales**:
31 de diciembre de 2025 y 1 de enero de 2026, desde
`workspace.default.tb_daily_tld_01_01_2026_m`. No se requiere procesar la fuente
histórica de 85 millones de filas para esta entrega.

El snapshot Bronze lee una tabla que ya existe en Databricks. Esto demuestra
ingesta tabla-a-tabla; no afirma cargar archivos externos. Confirmar con el
enunciado si se necesita demostrar también el paso original de archivo a tabla.

## Estado

El trabajo original de Magda está preservado en `magda` (commit `4d2aef2`) y fue
integrado en `main` con un merge. Su demo original y evidencia se conservan.
Las correcciones de main se prueban en `workspace.astro_taco_main_demo`, separado
de `workspace.astro_taco_demo` y de las tablas reales del equipo.
Consultar [evidencia](docs/execution_evidence.md) y [pendientes](docs/delivery_checklist.md).
`dev` conserva `amount_grain=unconfirmed`: una prueba sintética no confirma la
definición financiera de la fuente real.

## Estructura requerida

```text
databricks.yml
resources/
  jobs/daily_orchestration_job.yml
  pipelines/lakeflow_pipeline.yml
src/transformations/
  silver/
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
- Con grano `check`, Total/Tax/Total Discount se cuentan una vez por ticket si
  son consistentes; no se publican como ingreso neto auditado.
- Repeticiones idénticas se preservan y cuentan como candidatos. No se elimina
  el artículo ni se excluye automáticamente el ticket. La fuente debe ser un
  snapshot sin cargas duplicadas; si existen, resolverlas por procedencia/ID real.
- Errores de tipos van a cuarentena; tickets financieros ambiguos van a revisión.
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

Ejecutar secuencialmente. Esperado: **8 Bronze, 7 Silver, 1 cuarentena,
3 tickets publicados, 2 en revisión e importe sintético 28**. No son ventas reales.
El ticket repetido conserva ambos tacos y su importe de ticket se cuenta una vez.
El horario 23:59 a 00:02 se marca como cruce nocturno supuesto de 180 segundos.
No mezclar estos resultados con la evidencia histórica de Magda (importe 18).

## Demostración con los dos días reales

1. Ejecutar `notebooks/05_source_diagnostics.py` y documentar el contrato.
2. Confirmar grano común de Total/Tax/Total Discount. Si difieren, adaptar el
   código antes de ejecutar. Revisar voids, descuentos y umbrales de exclusión.
3. Registrar overrides locales ignorados por Git en
   `.databricks/bundle/dev/variable-overrides.json` con `amount_grain: check`
   únicamente si ese contrato ha sido confirmado.
4. Validar, desplegar y ejecutar:

```powershell
databricks bundle validate -t dev -p datathon --strict
databricks bundle deploy -t dev -p datathon
databricks bundle run daily_orchestration -t dev -p datathon
```

El destino es `workspace.astro_taco_dev`; no se sobrescriben las tablas de
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
crecimiento interanual. Falta completar el dashboard real y conclusiones.

Ver [arquitectura](docs/architecture.md), [diccionario](docs/data_dictionary.md),
[contrato](docs/data_contract.md), [operación](docs/runbook.md) y
[rúbrica](docs/rubric.md).
