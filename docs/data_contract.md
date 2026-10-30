# Contrato analítico inferido de los dos días reales

## Evidencia y alcance

Fuente: workspace.default.tb_daily_tld_01_01_2026_m; 284,428 filas, 40,306 tickets,
114 tiendas, 2025-12-31 y 2026-01-01. No hay variaciones de Total, Tax o Total
Discount dentro de ninguna clave tienda/fecha/check: el grano común es check.
El perfil completo y las ecuaciones están en financial_definition_analysis.md.
No se exige documentación externa que el equipo no tiene.

El contrato es una inferencia reproducible, no prueba de liquidación de pagos,
moneda, margen ni reconocimiento contable. Las etiquetas dicen importe cliente
normalizado y mercancía después de descuentos, no ingresos netos auditados.

## Perfiles versionados

config/store_financial_profiles.json contiene 114 tiendas y ventanas de fechas.
Cada perfil se eligió por la ecuación de mejor ajuste, con mínimo 95% de tickets
reconciliados por tienda. No se usa el tamaño del número de ticket en el runtime.
scripts/build_financial_profiles.py genera la tabla de lookup del pipeline.
Una tienda, fecha o población demo/real desconocida va a revisión, sin adivinar.

| Perfil | Ecuación de control | Mercancía después de descuentos | Importe cliente incluyendo impuesto |
|---|---|---|---|
| A_TAX_INCLUSIVE | Total = SUM(Menu Price) - SUM(Item Voided) - Total Discount + Tax | Total - Tax | Total |
| B_PRE_DISCOUNT | Total = SUM(Menu Price * Quantity) | Total - Total Discount | Total - Total Discount + Tax |

Los importes fuente se conservan en reported_total, reported_tax y
reported_discount. reported_total mezcla definiciones entre perfiles y solo se
usa para trazabilidad/reconciliación; no es la métrica principal del dashboard.
Se requiere abs(residual) <= 0.011 y consistencia de los tres campos del ticket.
Para B, SUM(Item Discount) debe coincidir con Total Discount.

## Tipado y roles

Se conservan todas las ocurrencias en Bronze. Silver convierte fechas M/d/yyyy
o ISO a DATE, importes a DECIMAL(20,4), horas con fracciones a timestamps de
reloj y nombres a snake_case. Claves y campos numéricos obligatorios inválidos
van a cuarentena con motivo. Una fila inválida con clave completa bloquea el
ticket entero para impedir publicar un ticket parcial.

- sale_item / discounted_item: se preservan; Discount no invalida un ticket.
- zero_quantity_component: cantidad cero no suma unidades y no bloquea B.
- zero_price_component: componente sin cargo; puede conservar unidades reportadas.
- promo_adjustment: Item Promo de precio negativo; conserva el ajuste monetario,
  aporta cero unidades de producto. Otros negativos sin interpretación van a revisión.
- voided_item: excluye sus unidades; el ticket puede publicarse si reconcilia.
  No restar una anulación otra vez cuando el precio fuente ya es cero.

Cantidad negativa, impuesto/descuento negativo, Order Voided no cero, tipos
de transacción desconocidos, negativos no clasificados y cantidades distintas
de uno en A (no observadas en la fuente analizada) requieren revisión.
No hay rechazo por umbrales arbitrarios de Total >1000 o precio >500.

Los tickets también van a revisión por perfil desconocido, ecuación fallida,
normalización negativa o Total cero con Tax positivo. La ecuación por sí sola
no identifica con certeza todos los estados cancelados del POS.

## Repeticiones e ingesta

Las filas idénticas se cuentan como candidatos; no se borran ni excluyen por
ser idénticas. La prueba contable puede detectar la sobrecarga de un ticket al
agregar copias sin cambiar su Total. Si una carga duplicara además toda la
identidad de tickets, la prueba no prueba procedencia: resolver con fuente/ID.
El snapshot se reemplaza atómicamente y el rerun no añade filas al snapshot.

## Duraciones y métricas

Tiempo normal válido entre 0 y 4 horas. Cruce nocturno supuesto solo con inicio
>=20:00, fin <=04:59 y duración <=4 h. Lo demás queda NULL con motivo, sin
eliminar importes financieros. Si una línea del ticket carece de duración
válida, el ticket no participa en el promedio. La regla es provisional.

Ticket promedio = SUM(customer_total) / SUM(transactions).
Duración global = SUM(duration_seconds_sum) / SUM(duration_observations).
Cobertura = SUM(published_checks) / SUM(identifiable_checks).
Las incidencias de calidad se pueden solapar. Los importes por producto no se
reparten arbitrariamente: reported_line_total sigue NULL y se muestran unidades.
