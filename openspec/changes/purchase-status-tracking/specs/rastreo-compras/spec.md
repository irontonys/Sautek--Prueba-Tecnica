# Spec Delta

## Purpose

Da a cada compra en Odoo un estatus de seguimiento, desde la RFQ hasta la recepción de la mercancía, que se actualiza solo con lo que pasa en Odoo y deja historial, para que el comprador sepa en qué va cada pedido sin buscar en su correo.

## ADDED Requirements

### Requirement: Estatus de seguimiento
Cada compra SHALL tener un estatus de seguimiento con uno de estos valores: "Pedido preparado", "Esperando cotización", "Cotización recibida", "Aprobada", "PO enviada", "Recibido parcial", "Recibido" o "Cancelado". El estatus MUST calcularse solo a partir del estado de la compra, de la recepción y de los eventos de esta capacidad; el usuario MUST NOT poder editarlo a mano. Cuando aplican varios, MUST ganar el más avanzado, en este orden: Cancelado, Recibido, Recibido parcial, PO enviada, Aprobada, Cotización recibida, Esperando cotización, Pedido preparado.

#### Scenario: RFQ recién generada
- **WHEN** Odoo genera una RFQ en borrador
- **THEN** su estatus es "Pedido preparado"

#### Scenario: RFQ enviada
- **WHEN** el comprador envía la RFQ por correo desde Odoo
- **THEN** su estatus es "Esperando cotización"

#### Scenario: Compra cancelada
- **WHEN** una compra se cancela, en cualquier estatus
- **THEN** su estatus es "Cancelado"

### Requirement: Cotización recibida
Cuando a una RFQ que no está confirmada ni cancelada le llega un correo cuyo autor es el proveedor de la compra (o un contacto de esa empresa), el sistema SHALL marcar la fecha de cotización recibida y el estatus MUST pasar a "Cotización recibida". Un mensaje interno, una nota o un correo de otra persona MUST NOT cambiar el estatus.

#### Scenario: El proveedor contesta la RFQ
- **WHEN** llega a la RFQ un correo del proveedor en respuesta a la RFQ enviada
- **THEN** el estatus pasa a "Cotización recibida"
- **AND** el correo queda en el historial de la compra

#### Scenario: Nota interna del comprador
- **WHEN** el comprador deja una nota interna en una RFQ en "Esperando cotización"
- **THEN** el estatus sigue en "Esperando cotización"

### Requirement: Aviso para aprobar
Cuando una compra pasa a "Cotización recibida", el sistema SHALL asignar una actividad "Revisar cotización y aprobar" al comprador de la compra, o, si no tiene comprador, a los usuarios internos que la siguen. Al confirmar la compra, esa actividad MUST marcarse como hecha.

#### Scenario: Llega la cotización
- **WHEN** una RFQ seguida por el comprador pasa a "Cotización recibida"
- **THEN** el comprador tiene una actividad "Revisar cotización y aprobar" en esa compra

#### Scenario: El comprador aprueba
- **WHEN** el comprador confirma la compra
- **THEN** el estatus pasa a "Aprobada"
- **AND** la actividad "Revisar cotización y aprobar" queda hecha

### Requirement: PO enviada
Cuando una compra confirmada se envía por correo al proveedor desde Odoo, el sistema SHALL marcar la fecha de envío de la orden de compra y el estatus MUST pasar a "PO enviada".

#### Scenario: Envío de la orden de compra
- **WHEN** el comprador envía por correo una compra confirmada
- **THEN** el estatus pasa a "PO enviada"

### Requirement: Recepción
El estatus SHALL seguir la recepción de la mercancía de la compra: "Recibido parcial" cuando se validó una parte, "Recibido" cuando se validó todo.

#### Scenario: Llega una parte
- **WHEN** se valida una recepción parcial de una compra
- **THEN** el estatus pasa a "Recibido parcial"

#### Scenario: Llega todo
- **WHEN** se valida la recepción completa de una compra
- **THEN** el estatus pasa a "Recibido"

### Requirement: Historial y vista
Cada cambio de estatus SHALL quedar en el historial de la compra con fecha y usuario. El estatus SHALL verse en la pantalla de la compra como barra de avance y en la lista de compras como columna, con filtros y agrupación por estatus.

#### Scenario: Historial de una compra completa
- **WHEN** una compra recorre del envío de la RFQ a la recepción completa
- **THEN** su historial muestra cada cambio de estatus en orden, con su fecha

### Requirement: Correo de pruebas sin salida a internet
El entorno Odoo del repositorio SHALL entregar todos los correos que Odoo envía a un buzón de pruebas local que se consulta en el navegador. MUST NOT enviar correos a direcciones reales.

#### Scenario: Envío de una RFQ en el entorno local
- **WHEN** el comprador envía una RFQ desde el Odoo del repositorio
- **THEN** el correo aparece en el buzón de pruebas local
- **AND** no se envía a la dirección del proveedor

### Requirement: Simulación de la respuesta del proveedor
El sistema SHALL ofrecer el comando `python -m resurtido.odoo.proveedor <Proveedor_ID>` que mete en Odoo un correo del proveedor contestando a su RFQ enviada, por la misma entrada que usa Odoo para el correo entrante. Si el proveedor no tiene una RFQ en "Esperando cotización", el comando MUST decirlo en español y terminar con código distinto de cero sin crear nada.

#### Scenario: Proveedor con RFQ enviada
- **WHEN** el usuario corre el comando con un proveedor cuya RFQ está en "Esperando cotización"
- **THEN** la RFQ recibe un correo de la dirección del proveedor
- **AND** su estatus pasa a "Cotización recibida"

#### Scenario: Proveedor sin RFQ enviada
- **WHEN** el usuario corre el comando con un proveedor cuya RFQ no se ha enviado
- **THEN** el comando indica que no hay RFQ esperando cotización para ese proveedor
- **AND** termina con código de salida distinto de cero
