# Cierre de Phase 2

## Implementado

- Merge de magda a main conservando el commit original y su evidencia.
- Orquestación en resources y tablas en src/transformations/silver y gold.
- Snapshot, tipos decimales, claves de ticket y separación ticket/artículo.
- Repeticiones preservadas sin bloquear automáticamente la publicación.
- Duraciones inválidas fuera de promedios, cruce nocturno supuesto marcado.
- Tipos de transacción ambiguos/voids enviados a revisión.
- Calidad, cuarentena, review_reason, cobertura y conciliación diaria/horaria/canales.
- Acceso compartido al esquema nuevo mediante team_principals en la ingesta.
- Pruebas locales y bundle; evidencia de runtime separada de la demo original.

## Pendientes para la entrega real

1. Confirmar con recibos/documentación el grano de Total, Tax y Total Discount,
   la clave del ticket y la política de descuentos/voids. Revisar umbrales
   financieros y calidad de relojes. No configurar check solo para quitar un bloqueo.
2. Ejecutar la ingesta y el pipeline con la fuente real de los dos días.
3. Guardar Run ID, origen/versión, parámetros, DAG, expectativas, conciliación,
   cobertura y ejemplos de filas. Comparar con tablas anteriores explicando
   diferencias sin intentar reproducir métricas que duplicaban importes.
4. Reejecutar sin cambios; probar corrección/borrado de fuente en una copia demo.
5. Completar dashboard real de desempeño, productos/demanda y calidad, con
   filtros por fecha/tienda, etiqueta de importe POS y tasas de exclusión.
6. Escribir tres a cinco hallazgos de los dos días, con cifras verificables y
   acciones. No afirmar crecimiento anual, estacionalidad ni margen sin costos.
7. Medir duración/costo y evaluar clustering; configurar avisos de fallas y un
   umbral acordado de cobertura. Activar schedule solo si aporta a la demostración.
8. Preparar presentación y ensayo: objetivo, fuente, DAG, transformaciones,
   calidad, análisis, valor y límites. Otro compañero debe reproducir el runbook.

La rúbrica pide evidencia de ejecución y razonamiento, no solo archivos.
Demo sintética, demostración real y evidencia histórica deben etiquetarse por separado.
