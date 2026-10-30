> Alcance acordado: dos días reales, no la fuente histórica completa. Estado y pendientes actuales en delivery_checklist.md. Las tablas se definen en src/transformations.

# Operación y validación en Databricks

## Primera ejecución

1. Confirmar contrato y privilegios: USE CATALOG/SCHEMA, SELECT fuente,
   CREATE SCHEMA/TABLE/MATERIALIZED VIEW según el workspace y permiso de compute.
   La fuente predeterminada es workspace.default.tb_daily_tld_01_01_2026_m.
   No crear recursos en default. El bundle usa serverless Jobs/notebooks además
   de Lakeflow serverless; confirmar que ambos estén habilitados.
2. Ejecutar demo en esquema exclusivo y confirmar los resultados del README.
3. Revisar que el pipeline haya publicado las tablas y el event log muestre expectations.
4. Abrir 03: debe reconciliar Bronze = Silver + cuarentena, tickets clasificados
   = publicados + revisión y agregados diarios/horarios con tickets.
5. Reejecutar el Job: mismas cuentas/importes de negocio si no cambió la fuente.
6. Probar cambio/borrado en la fuente demo y verificar que el refresh lo refleje.
7. Ejecutar con fuente real y revisar todos los tickets excluidos antes de interpretar.

## Fallos y reejecuciones

El Job permite una ejecución concurrente. Ingesta reintenta una vez; timeout 2 h.
Transformación tiene timeout 4 h. Validación/análisis tienen timeout 1 h cada una.
Las dependencias impiden análisis si falla una etapa anterior.

Si falla 01, Bronze anterior permanece si el fallo fue antes del overwrite Delta.
Si falla el pipeline, algunas tablas pueden estar en versiones de refresh diferentes:
no presentar resultados hasta refrescar exitosamente y validar. Reparar el Job
desde la tarea fallida con Repair run; si cambió fuente/contrato, ejecutar el Job
completo. No ejecutar otra escritura a Bronze mientras esté refrescando Lakeflow.

03 falla si no hay tickets publicables, pérdida de filas o diferencias de importes.
Revisar cuarentena, perfiles y tickets bajo revisión; no vaciar tablas para lograr
una validación verde. No hay alerta por porcentaje de exclusión aún: acordar un
umbral de negocio con el dueño y configurar notificaciones del Job a responsables.

## Diseño y límites

- Batch diario: la entrada conocida es una tabla/snapshot, sin contrato de eventos
  append-only ni ID estable. Un readStream append duplicaría snapshots o ignoraría
  correcciones/borrados; por eso se evaluó y no se usa streaming ahora.
- Materialized views Lakeflow: manejan dependencias y refresh; el motor decide
  si puede actualizar incrementalmente o necesita recomputar.
- Liquid clustering explícito por fecha/tienda en tablas principales; comprobar
  patrón de consultas, tamaños y costo antes de ampliarlo. No se particiona por fecha.
- Expectations registran fechas/importes inválidos y fallan ante claves inválidas
  en Silver publicado. Cuarentena y revisión dan evidencia consultable.
- Un snapshot completo facilita correcciones e idempotencia, pero puede ser caro
  para decenas de millones de filas. Medir duración/costo antes de fijar frecuencia.
- Bronze conserva solo el snapshot vigente. El historial Delta y el run history
  dependen de retención del workspace; no se promete un historial de negocio permanente.
- Un ticket podría agrupar varios POS si el número no es único dentro de tienda/fecha.
  Confirmar si POS Code debe agregarse a la clave antes de uso real.
- Los dashboards existentes no se cambian automáticamente. Consultar el plan de
  compatibilidad y usar copias nuevas una vez validadas las tablas; no equiparar
  importe POS con gross_sales/net_sales ni promediar promedios sin ponderación.

## Evidencia que guardar

Run ID y fecha, nombre/versión de fuente, parámetros de grano, DAG exitoso,
resumen de calidad, muestras de cuarentena/revisión, métricas de expectations,
tablas Gold y gráficas. Exportar los resultados del notebook 04 tras ejecutar;
no versionar ventas sensibles ni credenciales en el repositorio.

## Referencias técnicas

- https://docs.databricks.com/aws/en/ldp/developer/ldp-python-ref-materialized-view
- https://docs.databricks.com/aws/en/ldp/developer/python-ref
- https://docs.databricks.com/aws/en/dev-tools/bundles/resources
