# Spec Delta

## Purpose

Permite que el personal de compras haga todo el flujo desde Odoo, sin terminal: subir el Excel de inventario, obtener las RFQ calculadas por el reabastecimiento nativo con el mismo motor de la CLI, ver el resultado y, en demostraciones, simular la respuesta del proveedor con un botón.

## ADDED Requirements

### Requirement: Importar el Excel desde Compras
Odoo SHALL ofrecer la opción "Importar inventario (Excel)" en el menú de Compras y como botón arriba de la lista de solicitudes de cotización, disponible para los administradores de Compras. Al subir el Excel y confirmar, Odoo MUST validarlo con las mismas reglas y decisiones que la CLI y ejecutar la misma carga, cancelación de RFQ anteriores, reabastecimiento, notas y suscripción del comprador que el comando `python -m resurtido.odoo`, sin usar la terminal.

#### Scenario: Importación del Excel del caso
- **WHEN** un administrador de Compras sube `inventario_ferreteria_garza.xlsx` y da Importar
- **THEN** Odoo queda con las mismas RFQ en borrador que genera el comando de terminal
- **AND** la RFQ del proveedor que no llega a su pedido mínimo tiene la nota "No enviar"
- **AND** quien importó sigue las RFQ generadas

#### Scenario: Botón en la lista de RFQ
- **WHEN** un administrador de Compras abre la lista de solicitudes de cotización
- **THEN** ve el botón "Importar inventario (Excel)" junto a "New", sin seleccionar registros

#### Scenario: Usuario sin permiso
- **WHEN** un usuario de Compras que no es administrador busca la opción
- **THEN** la opción no aparece en su menú ni como botón en la lista

### Requirement: Aviso de resultado
Al terminar, la ventana de importación SHALL mostrar un resumen con: renglones leídos, repetidos, procesables y no procesables; excepciones por tipo; proveedores y productos cargados; RFQ generadas y RFQ anteriores canceladas; proveedores que no alcanzan su pedido mínimo; y la comprobación del cálculo (proveedores que cuadran, con compra en proceso y que no cuadran). MUST ofrecer el reporte de excepciones en CSV para descargar, con las mismas columnas que el de la CLI, y un botón que abra las RFQ generadas.

#### Scenario: Resumen y descarga
- **WHEN** termina una importación
- **THEN** la ventana muestra el resumen con 7 RFQ generadas para el Excel del caso
- **AND** se puede descargar el CSV de excepciones con 28 renglones para el Excel del caso
- **AND** el botón "Ver RFQ" abre la lista con esas 7 RFQ

### Requirement: Archivo inválido
Cuando el archivo subido no es un Excel válido o le faltan hojas o columnas, la ventana SHALL mostrar en español el mismo mensaje que la CLI y MUST NOT crear ni modificar registros en Odoo.

#### Scenario: Archivo que no es Excel
- **WHEN** el usuario sube un archivo de texto con extensión `.xlsx`
- **THEN** la ventana indica que no se pudo leer como Excel
- **AND** no se crea ni cambia ningún proveedor, producto o RFQ

#### Scenario: Falta una hoja
- **WHEN** el usuario sube un Excel sin la hoja `Minimos`
- **THEN** la ventana indica que falta la hoja `Minimos`

### Requirement: Simulación del proveedor en modo demostración
La configuración de Compras SHALL tener la opción "Modo demostración", apagada por omisión. Con la opción encendida, cada RFQ en "Esperando cotización" MUST mostrar el botón "Simular respuesta del proveedor", que mete en Odoo un correo del proveedor contestando esa RFQ por la misma entrada que usa el correo real, igual que el comando `python -m resurtido.odoo.proveedor`. Con la opción apagada, el botón MUST NOT aparecer.

#### Scenario: Demostración encendida
- **WHEN** el modo demostración está encendido y el usuario da "Simular respuesta del proveedor" en una RFQ en "Esperando cotización"
- **THEN** la RFQ recibe un correo de la dirección del proveedor
- **AND** su estatus pasa a "Cotización recibida"

#### Scenario: Demostración apagada
- **WHEN** el modo demostración está apagado
- **THEN** ninguna RFQ muestra el botón "Simular respuesta del proveedor"
