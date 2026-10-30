# Contrato y definiciones

Fuente esperada: tabla POS con un registro por renglón de ticket. La clave del
ticket es Store # + fecha + Check Number; no es clave única del renglón.
No existe identificador de renglón confirmado: los duplicados exactos se marcan,
se preservan y bloquean el ticket para revisión; no se eliminan automáticamente.

| Campos originales | Tratamiento |
|---|---|
| Store # | BIGINT; obligatorio |
| Date | Texto M/d/yyyy a DATE; errores a cuarentena |
| Check Number | Identificador de texto no vacío |
| Total, Tax, Total Discount | DECIMAL(20,4); obligatorios; grano configurable común |
| Menu Price, Item Discount, Item Voided, Order Voided, Quantity | DECIMAL(20,4); obligatorios |
| Menu Item | Texto limpio; faltantes conservados como NULL |
| Report Group, Tender Type | Vacío/NULL a Unknown, sin imputación de negocio |
| Begin Time, End Time | TIME(6) o texto HH:mm:ss con fracciones opcionales de hasta 6 dígitos; errores quedan NULL y se cuentan |
| Transaction Type | Texto normalizado; no se infieren ventas/reembolsos por etiqueta |
| Otros campos | Conservados en Bronze, incluidos los vacíos del PDF |

Los metadatos de `workspace.default.tb_daily_tld_01_01_2026_m` coinciden con los
nombres requeridos: Date es STRING y Begin/End Time son TIME(6). Bronze normaliza
nombres a snake_case (Store # → store_id) y serializa las horas a texto preservando
fracciones. Así se evitan nombres inválidos de Delta y dependencia de TIME en las
tablas destino. Date acepta M/d/yyyy e ISO/DATE mediante conversión segura.
El parseo exacto aún debe probarse en Spark; no se han consultado filas reales.
No se soportan Excel GRC ni horarios de entrada que ya contengan fecha completa.

## Métricas

- `reported_total`: Total del POS sin restar impuestos/descuentos nuevamente.
  `line`: sumar renglones; `check`: usar un importe por ticket solo si todos sus
  renglones coinciden en Total, Tax y Total Discount.
- `transactions`: tickets distintos por tienda y fecha, después de controles.
- `average_ticket`: importe publicado / tickets publicados.
- Categorías: unidades e Item Discount; importe solo con `line`. Con `check` es
  NULL porque no hay asignación defendible del importe a los productos.
- Duración: diferencia de reloj módulo 24 horas; supone duración menor a 24 h y
  relojes locales comparables. No es una medición fiable si el POS cambia zona/fecha.
- Hora de ticket: menor hora de inicio de sus líneas; revisar tickets que crucen
  medianoche si el POS tiene horas distintas por renglón.
- `gold_quality_summary`: cuentas sobre todas las filas de origen, antes de filtrar.
  Los indicadores pueden solaparse; no se suman como total de errores únicos.

## Política de calidad

Errores estructurales → `silver_pos_quarantine`. Si una línea con clave válida
es inválida, el ticket entero se manda a `silver_checks_review`.
Una línea sin clave completa no puede asociarse a un ticket: se conserva en cuarentena.

Valores negativos, cantidades <=0 o >100, Total >1000, Menu Price >500 y voids
distintos de cero → revisión financiera del ticket. Son umbrales iniciales tomados
del diagnóstico anterior, no reglas definitivas del negocio. Revisarlos con el dueño.
No se convierten negativos a positivos ni nulos a cero. Los tickets excluidos se
reportan junto con la cobertura; estas métricas no equivalen a ventas contables netas.

La fuente y destino deben ser distintos. El snapshot reemplaza únicamente
`bronze_pos` del esquema elegido y las vistas del pipeline reemplazan sus resultados.
Se usa un esquema exclusivo: no reutilizar nombres de tablas ajenos al proyecto.
