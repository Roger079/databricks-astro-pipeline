# Estado de entrega · 30 de octubre de 2026

## Completado y verificado

- Magda preservada en su rama original; main incluye su trabajo y las correcciones.
- Plantilla respetada: orquestación en resources y tablas en src/transformations/silver y gold.
- Contrato financiero inferido de todos los tickets, perfiles por tienda versionados
  y dos métricas normalizadas; no se requieren recibos que el equipo no tiene.
- Repeticiones, componentes de cantidad cero, descuentos, promos negativas y
  anulaciones parciales tratados por rol y conciliación, sin borrar filas idénticas.
- Duraciones inválidas fuera de promedios; cuarentena y revisión separadas.
- Ingesta fija la versión Delta y verifica propiedad del destino antes de escribir.
- Esquemas aislados main_real/main_demo; acceso de los tres miembros configurado.
- 28 pruebas locales, sintaxis Python y bundle validate --strict en dev/demo.
- Demo sintética completa: 12 filas, 5 tickets publicados y 2 en revisión;
  importe cliente 37.96 y mercancía después de descuentos 35.00.
- Dos ejecuciones reales completas sobre Delta versión 1, con iguales conteos e
  importes: 284,428 filas, 40,306 tickets identificables, 40,257 publicados y
  49 en revisión. Cero filas perdidas; 39 diferencias de ecuación dentro de los 49.
- Importe cliente normalizado 615,846.68; mercancía después de descuentos y sin
  impuesto 571,874.16. Son métricas analíticas inferidas, no ingresos auditados.
- Evidencia API/SQL y expectations, falla de propiedad y recuperación, análisis
  real de cinco hallazgos y consultas reproducibles guardados en docs/validation.

## Pendientes de la entrega y del dashboard estratégico

1. Ejecutar la prueba de cambio/borrado en una fuente sintética aislada. El rerun
   sin cambios ya se verificó con los dos días reales.
2. Construir el dashboard real: filtros consistentes, métricas normalizadas,
   cobertura y explicación de excepciones; exportar/versionar su definición.
3. Alinear la estrategia con el reto Pricing & Promotion Analytics: perfilar la
   historia disponible, validar reglas financieras por tienda/periodo e investigar
   si pueden identificarse ofertas. Los dos días solos no permiten estacionalidad.
4. Aplicar docs/dashboard_plan.md: lift con baseline defendible, señales de
   canibalización y decisiones con confianza explícita; no inventar campañas.
5. Medir rendimiento/costo y documentar la evaluación de clustering. Configurar
   avisos de falla y umbrales de cobertura si se acuerdan; horario sigue pausado.
6. Preparar presentación y ensayo según la rúbrica. Otro compañero debe seguir
   el runbook y comprobar acceso al dashboard y a la evidencia.

La tabla histórica existe (85.27 millones de filas, 119 tiendas), pero sus métricas
estratégicas todavía no están normalizadas/publicadas por este pipeline. No
presentar la consulta exploratoria de factibilidad como un análisis de lift acabado.
