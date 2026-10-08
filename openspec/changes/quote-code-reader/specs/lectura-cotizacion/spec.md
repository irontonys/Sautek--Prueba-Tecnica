# Spec Delta

## Purpose

Lee la cotización que adjunta el proveedor buscando los códigos de producto, la compara contra la RFQ y deja que el comprador aplique las diferencias, sin modelos de IA ni servicios externos.

## ADDED Requirements

### Requirement: Leer la cotización adjunta
Una RFQ en "Cotización recibida" SHALL mostrar el botón "Leer cotización". Al usarlo, Odoo MUST tomar el archivo más reciente que adjuntó el proveedor en esa RFQ (PDF, Excel `.xlsx` o CSV), extraer su texto en el servidor y reconocer como partida cada renglón que trae un código de producto y al menos un monto. De cada partida MUST obtener el código normalizado, la cantidad que el proveedor puede surtir y el precio unitario. La lectura MUST NOT enviar datos a servicios externos.

#### Scenario: Cotización completa en PDF
- **WHEN** el comprador da "Leer cotización" en una RFQ cuyo proveedor adjuntó una cotización en PDF con las mismas partidas, cantidades y precios
- **THEN** cada producto de la RFQ aparece con estatus "Igual"

#### Scenario: Párrafo que menciona códigos sin montos
- **WHEN** la cotización tiene un párrafo de texto que menciona códigos de producto sin cantidades ni precios
- **THEN** ese párrafo no se toma como partida

### Requirement: Comparación contra la RFQ
Odoo SHALL mostrar, en la RFQ, una lectura con un renglón por producto: código, descripción, cantidad y precio en la RFQ, cantidad y precio cotizados, y uno de estos estatus: "Igual", "Cambio de precio", "Surtido parcial", "Cambio de cantidad", "Sin existencia", "No viene en la cotización" o "No está en la RFQ". Un producto con cantidad cotizada en 0, o marcado como sin existencia o agotado, MUST quedar como "Sin existencia". Una cantidad cotizada menor a la de la RFQ MUST quedar como "Surtido parcial"; una mayor (por ejemplo, el proveedor redondea a su empaque), como "Cambio de cantidad". Una diferencia de precio mayor a un centavo MUST marcarse como "Cambio de precio"; si además cambia la cantidad, MUST prevalecer el estatus de cantidad y el precio nuevo MUST verse en el renglón.

#### Scenario: Cotización con surtido parcial y sin existencia
- **WHEN** el proveedor cotiza 12 de 24 piezas de un producto y 0 de otro, con los demás iguales
- **THEN** el primero aparece como "Surtido parcial" con 24 en la RFQ y 12 cotizadas
- **AND** el segundo aparece como "Sin existencia"
- **AND** los demás aparecen como "Igual"

#### Scenario: Producto que no cotizó
- **WHEN** un producto de la RFQ no aparece en la cotización
- **THEN** aparece como "No viene en la cotización"

### Requirement: Aplicar las diferencias
La RFQ SHALL ofrecer "Aplicar a la RFQ" cuando hay una lectura con diferencias y la RFQ no está confirmada. Al usarlo, Odoo MUST poner en cada línea la cantidad y el precio cotizados, quitar las líneas en "Sin existencia", dejar sin cambio las líneas "No viene en la cotización" y "No está en la RFQ", y dejar una nota interna que liste cada cambio. MUST NOT confirmar la compra.

#### Scenario: Aplicar el surtido parcial
- **WHEN** el comprador aplica una lectura con un producto en "Surtido parcial" (12 de 24) y otro en "Sin existencia"
- **THEN** la línea del primero queda con 12 piezas y la del segundo ya no está
- **AND** el total sin impuestos de la RFQ es igual al subtotal de la cotización
- **AND** la RFQ sigue sin confirmar, con una nota que lista los dos cambios

### Requirement: Archivo que no se puede leer
Cuando el proveedor no adjuntó un archivo legible, o el archivo no trae ningún código de la RFQ, Odoo SHALL decir en español qué pasó y MUST NOT cambiar la RFQ ni guardar una lectura.

#### Scenario: Cotización sin códigos
- **WHEN** el archivo adjunto no contiene ningún código de producto de la RFQ
- **THEN** Odoo indica que no encontró partidas de la RFQ en la cotización
- **AND** la RFQ queda igual
