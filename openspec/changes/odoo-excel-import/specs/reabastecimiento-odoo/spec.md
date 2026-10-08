# Spec Delta

## MODIFIED Requirements

### Requirement: Conciliación con la CLI
El comando SHALL escribir `conciliacion.csv` en la subcarpeta `odoo/` de la carpeta de salida, con un renglón por proveedor cargado: proveedor, total según la CLI, total sin impuestos de la RFQ en Odoo, diferencia y estatus. El estatus MUST ser "Cuadra" si la diferencia es de un centavo o menos; "Compra en proceso" si hay diferencia y el proveedor ya tiene en Odoo una compra enviada, por aprobar o confirmada que aún no se recibe completa (Odoo no vuelve a pedir lo que ya está en camino); y "No cuadra" en cualquier otro caso. Al terminar, el comando SHALL imprimir, bajo el título "Comprobación del cálculo", cuántos proveedores cuadran, cuántos tienen compra en proceso y cuáles no cuadran.

#### Scenario: Totales iguales
- **WHEN** el total de la RFQ en Odoo de un proveedor es igual al total que calcula la CLI
- **THEN** su renglón dice "Cuadra"

#### Scenario: Totales distintos
- **WHEN** el total de la RFQ en Odoo de un proveedor difiere del de la CLI en más de un centavo y el proveedor no tiene compras en proceso
- **THEN** su renglón dice "No cuadra" con la diferencia
- **AND** el resumen impreso nombra a ese proveedor

#### Scenario: Compra ya enviada al proveedor
- **WHEN** un proveedor tiene una RFQ ya enviada y se vuelve a importar el mismo Excel
- **THEN** su renglón dice "Compra en proceso"
- **AND** el resumen lo cuenta como compra en proceso, no como diferencia
