# Spec Delta

## Purpose

Deja listo un borrador de correo por proveedor con su pedido de la semana, sin enviarlo, más un índice interno para que el comprador sepa qué revisar antes de mandarlo.

## ADDED Requirements

### Requirement: Un borrador por pedido que se envía
El programa SHALL generar un archivo `.eml` en `correos/`, dentro de la carpeta de salida, por cada pedido con estado "Se envía". Los pedidos con estado "No se envía" o "Sin productos por pedir" MUST NOT generar borrador.

#### Scenario: Excel real
- **WHEN** el programa corre sobre el Excel real
- **THEN** `output/correos/` contiene 6 archivos `.eml`, uno por proveedor de P01, P02, P03, P04, P06 y P07
- **AND** no hay borrador para P05 ni para P08

#### Scenario: Borradores viejos
- **WHEN** `output/correos/` contiene un `.eml` de una corrida anterior para un proveedor que ya no tiene pedido
- **THEN** ese archivo se elimina antes de escribir los borradores nuevos

### Requirement: Borrador listo para enviar, sin enviar
Cada borrador SHALL ser un mensaje de correo válido en UTF-8 con el correo del proveedor como destinatario, un asunto que identifica el pedido y la fecha, y la marca `X-Unsent: 1` para que el cliente de correo lo abra como borrador. El programa MUST NOT enviar correos ni conectarse a ningún servidor.

#### Scenario: Encabezados
- **WHEN** se genera el borrador de Distribuidora Truper Norte con fecha 2026-10-09
- **THEN** el destinatario es `ventas@truper-norte.mx`
- **AND** el asunto contiene "Pedido de resurtido" y "2026-10-09"
- **AND** el mensaje tiene el encabezado `X-Unsent: 1`

### Requirement: Contenido del pedido
El cuerpo del borrador SHALL incluir un saludo al proveedor por su nombre, un renglón por producto con código, descripción, cantidad, costo unitario e importe, el total del pedido en pesos y la petición de confirmar cantidades y fecha de entrega. El total MUST coincidir con el total del pedido en `pedidos.xlsx`.

#### Scenario: Productos y total
- **WHEN** se genera el borrador de un proveedor con dos productos
- **THEN** el cuerpo contiene los dos códigos con sus cantidades
- **AND** contiene el total del pedido con formato `$#,##0.00`

### Requirement: Marca de revisión solo interna
La marca de revisión de un producto (existencia negativa) MUST NOT aparecer en el correo al proveedor. El programa SHALL escribir `correos/indice.csv` con un renglón por pedido que se envía o no se envía, con proveedor, estado, archivo del borrador (vacío si no hay), número de productos, total y una columna `revisar_antes_de_enviar` con los códigos marcados para revisión.

#### Scenario: Segueta marcada
- **WHEN** el pedido de P01 incluye `FTR-0007` marcado para revisión
- **THEN** el borrador de P01 no menciona revisión ni existencia negativa
- **AND** el renglón de P01 en `indice.csv` tiene `FTR-0007` en `revisar_antes_de_enviar`

#### Scenario: Pedido que no se envía
- **WHEN** P05 no alcanza su pedido mínimo
- **THEN** `indice.csv` tiene un renglón de P05 con estado "No se envía" y archivo vacío
