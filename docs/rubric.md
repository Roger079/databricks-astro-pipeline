# Entrega y presentación · Phase 2

| Criterio | Implementación | Evidencia pendiente en workspace |
|---|---|---|
| GitHub y documentación | README, contrato, runbook, bundle, notebooks y pruebas | Confirmar acceso al repo y ejecución por otro compañero |
| Job y pipeline | 01 → pipeline 02 → 03 → 04; dependencias, timeouts y reintento | Captura del DAG y Run ID exitoso |
| Transformaciones y tablas | Fechas, decimales, categorías Unknown, líneas/tickets, Gold | Comparar ejemplos de entrada/salida y definir grano real |
| Streaming, MV, liquid clustering, expectations | MV y expectations reales; clustering explícito; evaluación de batch/streaming | Mostrar configuración, event log y rendimiento observado |
| Calidad | Cuarentena, revisión, duplicados candidatos, reconciliación | Ejecutar casos demo y presentar conteos reales |
| Análisis y valor | Diario, categorías, horarios, tendencias, cobertura y gráficas | Formular hallazgos basados en ejecución real |
| Comunicación técnica | Contrato, límites y guía de presentación | Explicar decisiones y responder preguntas del equipo evaluador |

## Secuencia sugerida de presentación

1. Objetivo: entender ventas y demanda por tienda, fecha y categoría, con controles
   que eviten confundir renglones con tickets.
2. Fuente y arquitectura: explicar contrato, grano y recorrido Bronze/Silver/Gold.
3. Transformaciones: mostrar fecha string convertida, tipos y ticket multi-item.
4. Calidad: mostrar un caso válido, uno en cuarentena, duplicado candidato y void.
5. Análisis: mostrar evolución mensual, categorías y horarios con cobertura.
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
