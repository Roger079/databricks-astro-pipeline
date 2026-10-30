> Estado actual: ejecución real, rerun, demo normalizada, 28 tests y evidencia
> completados. Ver delivery_checklist.md para pendientes actuales. El dashboard
> estratégico sigue dashboard_plan.md y requiere validar el histórico.

> Alcance acordado: dos días reales, no la fuente histórica completa. Estado y pendientes actuales en delivery_checklist.md. Las tablas se definen en src/transformations.

# Entrega y presentación · Phase 2

| Criterio | Implementación | Evidencia pendiente en workspace |
|---|---|---|
| GitHub y documentación | README, contrato, runbook, bundle, notebooks y pruebas | Confirmar acceso al repo y ejecución por otro compañero |
| Job y pipeline | 01 → src/transformations → 03 → 04; dependencias, timeouts y reintento | Captura del DAG y Run ID exitoso |
| Transformaciones y tablas | Fechas, decimales, categorías Unknown, líneas/tickets, Gold | Mostrar perfiles A/B, conciliación y ejemplos de roles de registro |
| Streaming, MV, liquid clustering, expectations | MV y expectations reales; clustering explícito; evaluación de batch/streaming | Mostrar configuración, event log y rendimiento observado |
| Calidad | Cuarentena, revisión, duplicados candidatos, reconciliación | Mostrar normalized-real-verification.json y normalized-demo-verification.json |
| Análisis y valor | Dos días, tiendas, categorías, canales, horarios, cobertura y gráficas | Presentar docs/findings.md; completar análisis estratégico histórico |
| Comunicación técnica | Contrato, límites y guía de presentación | Explicar decisiones y responder preguntas del equipo evaluador |

## Secuencia sugerida de presentación

1. Objetivo: entender ventas y demanda por tienda, fecha y categoría, con controles
   que eviten confundir renglones con tickets.
2. Fuente y arquitectura: explicar contrato, grano y recorrido Bronze/Silver/Gold.
3. Transformaciones: mostrar fecha string convertida, tipos y ticket multi-item.
4. Calidad: mostrar un caso válido, uno en cuarentena, duplicado candidato y void.
5. Análisis: mostrar comparación de las dos fechas, tiendas, categorías y horarios con cobertura.
6. Conclusión: hallazgo más fuerte, acción sugerida, limitaciones y próximo paso.

No afirmar crecimiento causal por promociones, fraude por valores extremos ni
ingresos netos si no se han validado esas definiciones. Los valores del PDF previo
no son resultados confirmados de este pipeline. La implementación no garantiza
la calificación: hace falta ejecutar, analizar datos reales y presentar evidencia.

Las tablas Silver, Gold y cuarentena existentes en workspace.default son evidencia
de trabajo previo, pero no de su proceso reproducible: faltan los notebooks que
las generaron. El pipeline nuevo se prepara en un esquema separado y las métricas
de dashboards deben migrarse con las definiciones de docs/workspace_compatibility.md.

Rúbrica consultada: https://sunholdings-shared-services-bi.atlassian.net/wiki/external/MTAzZDI5NzhmYjM4NGZmNzkwYTg3ZWQyODM5NWI5ZGI
