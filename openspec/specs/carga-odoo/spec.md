# carga-odoo Specification

## Purpose
Lleva a Odoo los datos del Excel de inventario ya validados (proveedores, productos, existencias y reglas de reabastecimiento) para que Odoo pueda calcular las compras con su lógica nativa.

## Requirements

### Requirement: Ejecución del comando de Odoo
El sistema SHALL ofrecer un comando `python -m resurtido.odoo` que acepte `--input` (Excel de entrada) y `--output` (carpeta de salida) con los mismos valores por omisión que la CLI. Cuando el Excel no existe, no es un Excel o le faltan hojas o columnas, el comando MUST terminar con código de salida distinto de cero y el mismo mensaje en español que la CLI, sin traceback y sin conectarse a Odoo.

#### Scenario: Excel inexistente
- **WHEN** el usuario corre el comando con un `--input` que no existe
- **THEN** el comando imprime un mensaje que incluye esa ruta
- **AND** termina con código de salida distinto de cero sin abrir conexión con Odoo

### Requirement: Configuración de la conexión
El comando SHALL leer la conexión de las variables de entorno `ODOO_URL`, `ODOO_DB`, `ODOO_USER` y `ODOO_PASSWORD`. `ODOO_URL`, `ODOO_DB` y `ODOO_USER` MUST tener valores por omisión que apunten al Odoo del `docker-compose` del repositorio. `ODOO_PASSWORD` MUST NOT tener valor por omisión en el código.

#### Scenario: Falta la contraseña
- **WHEN** el usuario corre el comando sin definir `ODOO_PASSWORD`
- **THEN** el comando indica que falta la variable `ODOO_PASSWORD`
- **AND** termina con código de salida distinto de cero

#### Scenario: Odoo no responde o rechaza las credenciales
- **WHEN** Odoo no está levantado en `ODOO_URL` o el usuario y la contraseña no son válidos
- **THEN** el comando imprime un mensaje en español que dice cuál de los dos casos ocurrió y a qué URL y base de datos intentó conectarse
- **AND** termina con código de salida distinto de cero sin mostrar un traceback

### Requirement: Solo se cargan registros validados
El comando SHALL validar el Excel con las mismas reglas y decisiones que la CLI antes de escribir en Odoo. MUST cargar únicamente los productos procesables y los proveedores que tienen al menos un producto procesable. Los registros excluidos MUST NOT llegar a Odoo y MUST aparecer en el reporte de excepciones con la misma decisión que en la CLI.

#### Scenario: Producto inactivo
- **WHEN** el Excel trae un producto con estatus inactivo
- **THEN** ese producto no se crea ni se actualiza en Odoo
- **AND** aparece en el reporte de excepciones con la decisión "No se pide"

#### Scenario: Existencia negativa
- **WHEN** un producto procesable trae existencia negativa
- **THEN** su existencia en Odoo queda en 0
- **AND** el producto queda marcado para revisión, como en la CLI

### Requirement: Datos maestros en Odoo
Por cada proveedor cargado, Odoo SHALL tener un contacto de empresa con su nombre, su correo y su `Proveedor_ID` como referencia. Por cada producto cargado, Odoo SHALL tener un producto almacenable con el código normalizado como referencia interna, la descripción como nombre, la ruta de compra activa y una tarifa de proveedor con el costo unitario. Los productos MUST NOT llevar impuestos de compra, para que los totales sean comparables con los de la CLI.

#### Scenario: Producto con su proveedor
- **WHEN** se carga un producto procesable con su proveedor y su costo unitario
- **THEN** en Odoo existe un producto con su código normalizado como referencia interna
- **AND** su tarifa de proveedor apunta al contacto con ese `Proveedor_ID` como referencia, con precio igual al costo unitario

### Requirement: Existencias y reglas de reabastecimiento
Por cada producto cargado, el comando SHALL fijar en el almacén principal de Odoo su existencia, ya ajustada por la validación, mediante un ajuste de inventario. También SHALL fijar una regla de reabastecimiento con el mínimo, el máximo y el múltiplo de empaque del Excel.

#### Scenario: Regla del producto
- **WHEN** se carga un producto procesable
- **THEN** su regla de reabastecimiento en Odoo tiene el mínimo, el máximo y el múltiplo de empaque del Excel

### Requirement: Carga repetible
Correr el comando dos veces con el mismo Excel SHALL dejar Odoo en el mismo estado que correrlo una vez. Los proveedores, productos, tarifas y reglas MUST identificarse por su `Proveedor_ID` o su código y actualizarse en lugar de duplicarse. La existencia MUST fijarse al valor del Excel, no sumarse a la anterior.

#### Scenario: Segunda corrida
- **WHEN** el comando se corre dos veces seguidas con el mismo Excel
- **THEN** Odoo tiene un solo contacto por proveedor, un solo producto por código y una sola regla por producto
- **AND** la existencia de cada producto es la del Excel
