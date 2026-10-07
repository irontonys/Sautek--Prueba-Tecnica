# calculo-pedidos Specification

## Purpose
Calcula los pedidos de la semana a partir de los productos procesables: qué pedir, cuánto, agrupado por proveedor con su total, y respetando el pedido mínimo de cada proveedor.

## Requirements

### Requirement: Selección de productos a pedir
El programa SHALL pedir un producto procesable solo cuando su existencia sea estrictamente menor que su mínimo. Para una existencia negativa MUST usar la existencia ya ajustada a 0 por la validación.

#### Scenario: Existencia bajo el mínimo
- **WHEN** un producto tiene existencia 3 y mínimo 30
- **THEN** el producto se incluye en el pedido de su proveedor

#### Scenario: Existencia igual al mínimo
- **WHEN** un producto tiene existencia 30 y mínimo 30
- **THEN** el producto no se pide

#### Scenario: Producto no procesable
- **WHEN** un producto está bajo el mínimo pero la validación lo marcó como no procesable
- **THEN** el producto no aparece en ningún pedido

### Requirement: Cantidad con múltiplo de empaque
La cantidad SHALL ser lo necesario para llegar al máximo (máximo menos existencia), redondeado hacia arriba al siguiente múltiplo del empaque. El resultado MAY pasar del máximo por efecto del redondeo.

#### Scenario: Redondeo al múltiplo
- **WHEN** un producto tiene existencia 3, máximo 60 y múltiplo 6
- **THEN** la cantidad pedida es 60, porque faltan 57 y el siguiente múltiplo de 6 es 60

#### Scenario: Cantidad exacta
- **WHEN** un producto tiene existencia 0, máximo 20 y múltiplo 1
- **THEN** la cantidad pedida es 20

### Requirement: Agrupación por proveedor con total
Los productos a pedir SHALL agruparse por proveedor. Cada renglón MUST llevar su importe (cantidad por costo unitario) y cada proveedor MUST llevar su total en pesos, redondeado a centavos.

#### Scenario: Total del proveedor
- **WHEN** un proveedor tiene dos productos a pedir con importes de $1,000.50 y $2,000.25
- **THEN** el total del proveedor es $3,000.75

### Requirement: Pedido mínimo del proveedor
Cuando el total de un proveedor sea menor que su pedido mínimo, su pedido SHALL quedar con estado "No se envía" y MUST NOT completarse automáticamente. El programa MUST agregar una excepción de pedido mínimo no alcanzado al reporte de excepciones, con el total, el mínimo y la diferencia. Un proveedor con pedido mínimo 0 siempre alcanza.

#### Scenario: No alcanza el mínimo
- **WHEN** un proveedor con pedido mínimo $15,000 tiene un total de $12,664.05
- **THEN** su pedido queda con estado "No se envía"
- **AND** `excepciones.csv` incluye una excepción de pedido mínimo no alcanzado que menciona la diferencia de $2,335.95

#### Scenario: Alcanza el mínimo
- **WHEN** un proveedor con pedido mínimo $5,000 tiene un total de $168,209.93
- **THEN** su pedido queda con estado "Se envía"

### Requirement: Archivo de pedidos
El programa SHALL escribir `pedidos.xlsx` en la carpeta de salida con dos hojas:
- `Resumen`: un renglón por proveedor del catálogo, con proveedor, correo, número de productos, total, pedido mínimo y estado ("Se envía", "No se envía" o "Sin productos por pedir").
- `Detalle`: un renglón por producto a pedir, con proveedor, código, descripción, existencia, mínimo, máximo, múltiplo, cantidad, costo unitario, importe, estado del pedido y una columna "Revisar" que diga "Sí" en los productos marcados para revisión por la validación.

#### Scenario: Excel real
- **WHEN** el programa corre sobre el Excel real
- **THEN** `pedidos.xlsx` tiene 8 renglones en Resumen, uno por proveedor
- **AND** el proveedor P08 aparece como "Sin productos por pedir"

#### Scenario: Producto marcado para revisión
- **WHEN** la segueta `FTR-0007` tiene existencia negativa
- **THEN** su renglón en Detalle dice "Sí" en la columna Revisar

### Requirement: Resumen de pedidos en consola
Al terminar, el programa SHALL imprimir cuántos pedidos se envían, cuántos no se envían y el total a comprar de los pedidos que se envían.

#### Scenario: Resumen
- **WHEN** el programa termina sobre el Excel real
- **THEN** la consola muestra 6 pedidos que se envían y 1 que no se envía
