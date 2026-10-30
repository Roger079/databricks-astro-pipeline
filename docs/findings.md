# Hallazgos de la ejecución real normalizada

Fuente: dos días reales, 31 dic 2025 y 1 ene 2026; 114 tiendas.
Destino: workspace.astro_taco_main_real. La evidencia verificable está en
evidence/normalized-real-verification.json y las consultas en
../validation/final_analysis.sql. Importes en unidades monetarias fuente; el
extracto no especifica moneda ni prueba liquidación de pagos.

## 1. La estandarización financiera cambia la comparación de tiendas

Hay 78 tiendas cuyo Total es posterior al descuento e incluye impuesto, y 36
cuyo Total es anterior al descuento y no incluye impuesto. Sumar Total sin
normalizar mezcla dos métricas. El contrato inferido reconcilia 40,267 de 40,306
tickets; además se aplican controles de estado y registros no interpretados.

Acción: utilizar customer_total o merchandise_after_discount según la pregunta,
y mantener reported_total solo como trazabilidad de origen. No interpretar
diferencias entre los grupos como desempeño antes de estandarizar.

## 2. La cobertura es alta, pero las excepciones siguen visibles

Se ingirieron las 284,428 filas sin pérdida estructural. Los 40,306 tickets se
separan en 40,257 publicados (99.8784%) y 49 bajo revisión. Hay 39 excepciones
de ecuación, 22 tickets con Total cero y Tax positivo y dos con registros
financieros no interpretados. Esos indicadores se solapan: no sumarlos.

La cuarentena estructural real está vacía; la demo demuestra el rechazo de una
fecha inválida. Revisión financiera y cuarentena cumplen funciones diferentes.
Acción: resolver primero los 49 tickets sin ocultarlos ni corregir importes a mano.

## 3. Mayor volumen de tickets el segundo día, con ticket promedio menor

| Fecha | Tiendas | Tickets publicados | Importe cliente normalizado | Mercancía después de descuento, sin impuesto | Ticket promedio |
|---|---:|---:|---:|---:|---:|
| 2025-12-31 | 114 | 16,017 | 261,359.34 | 242,847.26 | 16.32 |
| 2026-01-01 | 114 | 24,240 | 354,487.34 | 329,026.90 | 14.62 |

El volumen observado sube 51.34%, mientras el ticket promedio baja. Son dos
fechas festivas: no prueban crecimiento sostenido, estacionalidad ni causalidad
de promociones. Acción: separar volumen y valor de ticket al explicar la diferencia;
no atribuirla a campañas con esta ventana temporal.

## 4. Las tiendas líderes combinan cobertura de ambas fechas y volumen

Por importe cliente normalizado, las primeras cinco son 7277 (13,093.62;
775 tickets), 6463 (12,533.26; 759), 7577 (10,784.26; 719), 7276
(10,264.81; 656) y 9050 (9,924.31; 564). Todas tienen datos publicados en
las dos fechas. Esto es una clasificación de la ventana observada, no de rentabilidad.
Acción: comparar también ticket promedio, canal y cobertura antes de recomendar
replicar prácticas de una tienda.

## 5. Los registros de componentes y ajustes no son todos errores de ingesta

La fuente contiene 13,047 filas de cantidad cero, 1,713 filas de artículos con
descuento, 1,323 filas identificadas como artículos anulados y 254 ajustes Item
Promo. Las cantidades cero no añaden unidades; anulaciones y promos no inflan
unidades vendidas. No se eliminan filas idénticas por defecto: la conciliación
conserva repeticiones legítimas y señala diferencias que podrían indicar cargas
duplicadas u otros problemas. No se afirma que una diferencia pruebe su causa.

Acción: presentar los roles de registro y la conciliación como parte del valor
del pipeline. Mantener los precios por producto separados del total de ticket;
no inventar margen sin costos ni repartir arbitrariamente descuentos globales.

## Próximos entregables

Construir el dashboard real con estas métricas, filtros de tienda/fecha y
visibilidad de cobertura. Preparar la presentación y una demostración reproducible
del job, las expectativas y los tickets bajo revisión. Ver delivery_checklist.md.
