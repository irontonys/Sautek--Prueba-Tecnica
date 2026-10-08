# Spec Delta

## Purpose

Convierte las excepciones de cada importación del Excel en una lista de pendientes dentro de Odoo, asignada al comprador, que se mantiene sola entre importaciones y le avisa una vez por importación.

## ADDED Requirements

### Requirement: Bandeja de excepciones
Odoo SHALL tener en el menú de Compras la "bandeja de excepciones de inventario", con un renglón por excepción: hoja, fila, código, tipo, detalle, valor original, decisión, grupo, responsable, estatus, cuántas importaciones la han reportado y días abierta. El grupo MUST ser "Se corrigió" para las excepciones que se corrigieron y se procesaron, "Advertencia" para las que se procesaron marcadas para revisión, "No se procesó" para las que excluyeron el producto o el proveedor, y "Compra" para el pedido mínimo no alcanzado. La bandeja MUST abrir mostrando las pendientes y permitir agrupar por grupo, tipo y estatus.

#### Scenario: Primera importación
- **WHEN** el comprador importa el Excel del caso en una base sin excepciones
- **THEN** la bandeja tiene 28 excepciones pendientes asignadas a él
- **AND** la existencia negativa de FTR-0007 aparece en el grupo "Advertencia"
- **AND** el producto sin mínimo FTR-0024 aparece en el grupo "No se procesó"

### Requirement: Responsable
Toda excepción nueva o reabierta SHALL quedar asignada al usuario que hizo la importación.

#### Scenario: Importa el admin
- **WHEN** el admin importa el Excel
- **THEN** todas las excepciones pendientes tienen al admin como responsable

### Requirement: Una excepción por problema entre importaciones
Una excepción SHALL reconocerse entre importaciones por su tipo, su hoja y su código, o por su fila cuando no tiene código. Si una importación vuelve a reportar una excepción existente, Odoo MUST actualizar su fila, detalle y valor, sumar una vez más a su conteo y su fecha de última vez vista, sin crear otra.

#### Scenario: Segunda importación del mismo Excel
- **WHEN** el comprador importa dos veces el mismo Excel
- **THEN** la bandeja sigue teniendo 28 excepciones, cada una reportada 2 veces

### Requirement: Estatus que se mantiene solo
Cada excepción SHALL tener uno de estos estatus: "Pendiente", "Resuelta" o "Aceptada". Al importar, Odoo MUST:
- crear como "Pendiente" cada excepción que no existía;
- pasar a "Resuelta", con su fecha, cada excepción "Pendiente" o "Aceptada" que la importación ya no reporta;
- regresar a "Pendiente" una excepción "Resuelta" que la importación vuelve a reportar, y contar la reapertura;
- dejar en "Aceptada" una excepción aceptada que la importación sigue reportando.
El comprador SHALL poder marcar una excepción pendiente como "Aceptada" (quedan su usuario y la fecha) y regresar una aceptada a "Pendiente".

#### Scenario: Se corrige el dato en el origen
- **WHEN** el producto FTR-0024 recibe su mínimo y se importa el Excel corregido
- **THEN** su excepción "Producto sin mínimo" pasa a "Resuelta"

#### Scenario: El problema vuelve
- **WHEN** una excepción resuelta vuelve a aparecer en una importación posterior
- **THEN** regresa a "Pendiente" y su conteo de reaperturas sube a 1

#### Scenario: Excepción aceptada
- **WHEN** el comprador acepta la excepción de unidad de FTR-0009 y se vuelve a importar el mismo Excel
- **THEN** la excepción sigue "Aceptada" y no cuenta entre las pendientes

### Requirement: Aviso por importación
Cada importación SHALL dejar un registro con la fecha, el usuario, el archivo y cuántas excepciones quedaron nuevas, abiertas (pendientes) y resueltas, y una tarea "Revisar excepciones" para el comprador sobre ese registro, con esos conteos y un botón que abra la bandeja en las pendientes. Al crear la tarea de una importación, Odoo MUST marcar como hecha la tarea abierta de la importación anterior. Si no hay excepciones pendientes, MUST NOT crear la tarea. El resumen de la importación SHALL incluir los mismos conteos.

#### Scenario: Dos importaciones seguidas
- **WHEN** el comprador importa el Excel dos veces
- **THEN** tiene una sola tarea "Revisar excepciones" abierta, la de la segunda importación
- **AND** el resumen de la segunda dice 0 nuevas y 28 abiertas
