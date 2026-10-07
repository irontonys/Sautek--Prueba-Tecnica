# reabastecimiento-odoo Specification

## Purpose
Usa el reabastecimiento nativo de Odoo para generar las solicitudes de cotización a proveedores, cubre las decisiones del caso que Odoo no maneja solo y comprueba que el resultado cuadra con el de la CLI.

## Requirements

### Requirement: RFQ por reabastecimiento nativo
Después de la carga, el comando SHALL disparar el reabastecimiento nativo de Odoo sobre las reglas cargadas, de modo que Odoo genere una solicitud de cotización (RFQ) en borrador por proveedor con los productos cuya existencia sea menor que su mínimo. Las cantidades MUST ser las que calcula Odoo con su regla, sin que el comando las reescriba.

#### Scenario: Proveedor con productos bajo el mínimo
- **WHEN** un proveedor tiene productos cuya existencia es menor que su mínimo
- **THEN** Odoo tiene una RFQ en borrador para ese proveedor con esos productos

#### Scenario: Proveedor sin productos por pedir
- **WHEN** ningún producto de un proveedor está debajo de su mínimo
- **THEN** no hay RFQ en borrador para ese proveedor

### Requirement: Ningún pedido sale solo
El comando MUST NOT confirmar RFQ ni enviar correos. Todas las RFQ que genere SHALL quedar en estado borrador, para que el comprador las revise y las envíe desde Odoo.

#### Scenario: Estado al terminar
- **WHEN** el comando termina
- **THEN** todas las RFQ generadas están en borrador y ninguna se ha enviado al proveedor

### Requirement: RFQ vigentes en cada corrida
Antes de reabastecer, el comando SHALL cancelar las RFQ en borrador de los proveedores cargados que haya dejado una corrida anterior, para que las RFQ reflejen el Excel actual. MUST NOT tocar RFQ confirmadas, enviadas ni creadas a mano.

#### Scenario: Segunda corrida con otro Excel
- **WHEN** el comando se corre con un Excel y luego con otro que trae existencias distintas
- **THEN** las RFQ en borrador de la primera corrida quedan canceladas
- **AND** las RFQ vigentes corresponden al segundo Excel

#### Scenario: RFQ creada a mano
- **WHEN** existe una RFQ en borrador que no generó el comando
- **THEN** el comando no la cancela ni la modifica

### Requirement: Aviso de pedido mínimo
Cuando el total sin impuestos de la RFQ de un proveedor sea menor que su pedido mínimo del Excel, el comando SHALL dejar en el chatter de esa RFQ una nota que diga que no debe enviarse, el total, el mínimo y cuánto falta. La RFQ MUST quedar en borrador, sin completarse ni cancelarse, y la excepción "Pedido mínimo no alcanzado" MUST aparecer en el reporte de excepciones.

#### Scenario: Proveedor P05 debajo de su mínimo
- **WHEN** el total de la RFQ de `P05` es menor que su pedido mínimo
- **THEN** la RFQ de `P05` tiene una nota de "No enviar" con el total, el mínimo y la diferencia
- **AND** la RFQ sigue en borrador con las mismas cantidades

### Requirement: Aviso de productos a revisar
Cuando una RFQ incluya productos marcados para revisión, el comando SHALL dejar en su chatter una nota con los códigos que el comprador debe revisar antes de enviarla.

#### Scenario: Producto con existencia negativa
- **WHEN** una RFQ incluye un producto cuya existencia venía negativa en el Excel
- **THEN** la RFQ tiene una nota que lista ese código para revisión

### Requirement: Conciliación con la CLI
El comando SHALL escribir `conciliacion.csv` en la subcarpeta `odoo/` de la carpeta de salida, con un renglón por proveedor cargado: proveedor, total según la CLI, total sin impuestos de la RFQ en Odoo, diferencia y si cuadra. Una diferencia mayor a un centavo MUST marcarse como "No cuadra". Al terminar, el comando SHALL imprimir cuántos proveedores cuadran y cuáles no.

#### Scenario: Totales iguales
- **WHEN** el total de la RFQ en Odoo de un proveedor es igual al total que calcula la CLI
- **THEN** su renglón dice "Cuadra"

#### Scenario: Totales distintos
- **WHEN** el total de la RFQ en Odoo de un proveedor difiere del de la CLI en más de un centavo
- **THEN** su renglón dice "No cuadra" con la diferencia
- **AND** el resumen impreso nombra a ese proveedor
