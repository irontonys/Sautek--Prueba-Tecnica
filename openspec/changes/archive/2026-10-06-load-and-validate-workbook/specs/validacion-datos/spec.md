# Spec Delta

## Purpose

Lee las cuatro hojas del Excel de inventario, detecta los problemas de calidad de datos, aplica la decisión de negocio de cada caso y los reporta en un archivo de excepciones, garantizando que ningún registro se omita en silencio.

## ADDED Requirements

### Requirement: Lectura de hojas con encabezado en la fila 2
El programa SHALL leer las hojas `Existencias`, `Minimos`, `Producto_Proveedor` y `Proveedores` usando la fila 2 como encabezado y la fila 3 en adelante como datos. Cuando falte una columna esperada, MUST terminar con un mensaje que nombre la hoja y la columna, con código de salida distinto de cero y sin traceback.

#### Scenario: Excel real
- **WHEN** el programa lee `data/inventario_ferreteria_garza.xlsx`
- **THEN** obtiene 52 renglones de Existencias, 49 de Minimos, 50 de Producto_Proveedor y 8 de Proveedores

#### Scenario: Columna faltante
- **WHEN** a la hoja `Minimos` le falta la columna `Maximo`
- **THEN** el programa informa que en la hoja `Minimos` falta la columna `Maximo`
- **AND** termina con código de salida distinto de cero

### Requirement: Existencias inválidas
El programa SHALL reportar como excepción toda existencia que sea texto, esté vacía o sea negativa, y aplicar estas decisiones:
- Texto que representa un número (como `1,250`): se convierte al número y el producto sigue siendo procesable.
- Texto que no representa un número, o existencia vacía: el producto no es procesable.
- Negativa: el producto sigue siendo procesable con existencia 0 para el cálculo, y queda marcado para revisión del comprador.

#### Scenario: Existencia como texto numérico
- **WHEN** un producto tiene existencia `"1,250"`
- **THEN** el reporte incluye una excepción de existencia como texto, con valor original `1,250`
- **AND** el producto es procesable con existencia 1250

#### Scenario: Existencia vacía
- **WHEN** un producto no tiene existencia
- **THEN** el reporte incluye una excepción de existencia vacía
- **AND** el producto no es procesable

#### Scenario: Existencia negativa
- **WHEN** un producto tiene existencia `-4`
- **THEN** el reporte incluye una excepción de existencia negativa, con valor original `-4`
- **AND** el producto es procesable con existencia 0 y marcado para revisión

### Requirement: Códigos repetidos y con formato distinto
El programa SHALL normalizar los códigos de las cuatro hojas a formato estándar (`FTR-` y 4 dígitos, en mayúsculas y sin espacios) antes de cruzarlas, y reportar como excepción cada código que haya necesitado normalización. Cuando un código se repite en Existencias, MUST conservar la primera aparición y reportar las demás.

#### Scenario: Código con formato distinto
- **WHEN** la hoja Minimos contiene el código `" ftr-0004 "`
- **THEN** el reporte incluye una excepción de formato de código cuyo detalle menciona `FTR-0004`
- **AND** el mínimo y máximo de ese renglón se asignan a `FTR-0004`

#### Scenario: Código corto
- **WHEN** la hoja Minimos contiene `FTR-27` y Existencias contiene `FTR-0027`
- **THEN** `FTR-0027` tiene el mínimo y máximo de ese renglón

#### Scenario: Código repetido
- **WHEN** `FTR-0027` aparece dos veces en Existencias
- **THEN** el reporte incluye una excepción de código repetido para la segunda aparición, con su fila de Excel
- **AND** el producto se procesa una sola vez, con los datos de la primera aparición

### Requirement: Referencias cruzadas faltantes
Ya con códigos normalizados, el programa SHALL reportar cada producto de Existencias sin renglón en Minimos o sin renglón en Producto_Proveedor, que MUST quedar no procesable. También SHALL reportar cada código de Minimos o Producto_Proveedor que no exista en Existencias, y cada proveedor referenciado que no exista en Proveedores.

#### Scenario: Producto sin proveedor
- **WHEN** `FTR-0033` está en Existencias pero no en Producto_Proveedor
- **THEN** el reporte incluye una excepción de producto sin proveedor para `FTR-0033`
- **AND** `FTR-0033` no es procesable

#### Scenario: Código ausente de Existencias
- **WHEN** `FTR-0021` está en Minimos pero no en Existencias
- **THEN** el reporte incluye una excepción de código ausente de Existencias para `FTR-0021`
- **AND** no se genera ningún pedido para `FTR-0021`

### Requirement: Mínimos y máximos inválidos
El programa SHALL reportar los mínimos o máximos vacíos, no numéricos o negativos, y los casos donde el mínimo es mayor que el máximo. En todos esos casos el producto MUST quedar no procesable.

#### Scenario: Mínimo mayor que máximo
- **WHEN** un producto tiene mínimo 60 y máximo 40
- **THEN** el reporte incluye una excepción de mínimo mayor que máximo con ambos valores en el detalle
- **AND** el producto no es procesable

### Requirement: Datos de compra inválidos
El programa SHALL reportar los costos unitarios o múltiplos de empaque vacíos, no numéricos o menores o iguales a cero; los pedidos mínimos de proveedor vacíos, no numéricos o negativos; y los correos de proveedor sin formato válido. Estos tipos no tienen decisión del autor todavía, así que el producto afectado (o todos los productos del proveedor afectado) MUST quedar no procesable.

#### Scenario: Múltiplo de empaque en cero
- **WHEN** un producto tiene múltiplo de empaque `0`
- **THEN** el reporte incluye una excepción de múltiplo de empaque inválido
- **AND** el producto no es procesable

#### Scenario: Correo inválido
- **WHEN** un proveedor tiene correo `ventas.truper.mx`
- **THEN** el reporte incluye una excepción de correo inválido para ese proveedor
- **AND** los productos de ese proveedor no son procesables

### Requirement: Productos sospechosos
El programa SHALL reportar:
- Los productos con estatus distinto de `ACTIVO`, que MUST quedar no procesables.
- Los productos de Existencias con códigos distintos cuya descripción coincide al ignorar mayúsculas, comillas y espacios repetidos. Todos los códigos del grupo MUST quedar no procesables hasta que alguien defina cuál es el bueno.
- Los productos cuya descripción indica entre paréntesis una unidad de compra (caja, bolsa, kg, m, par) distinta de la columna Unidad. Siguen siendo procesables, bajo el supuesto de que mínimo, máximo y existencia están en la misma unidad.

#### Scenario: Producto inactivo
- **WHEN** un producto tiene estatus `INACTIVO`
- **THEN** el reporte incluye una excepción de producto inactivo
- **AND** el producto no es procesable

#### Scenario: Mismo producto con dos códigos
- **WHEN** `FTR-0009` se describe como `Tornillo 1/4 x 2" (caja)` y `FTR-0051` como `Tornillo 1/4 x 2 (caja)`
- **THEN** el reporte incluye una excepción de posible duplicado para cada código, mencionando al otro
- **AND** ninguno de los dos es procesable

#### Scenario: Unidad distinta a la descripción
- **WHEN** un producto se describe como `Clavo 2" (kg)` y su unidad es `PZA`
- **THEN** el reporte incluye una excepción de unidad inconsistente
- **AND** el producto sigue siendo procesable

### Requirement: Reporte de excepciones
El programa SHALL escribir `excepciones.csv` en la carpeta de salida, en UTF-8 con BOM para que Excel muestre bien los acentos, con las columnas `hoja`, `fila_excel`, `codigo`, `tipo`, `detalle`, `valor_original` y `decision`. La columna `decision` MUST describir en español la decisión aplicada a ese tipo de excepción, o decir `Pendiente de decisión` cuando el tipo no tiene una registrada.

#### Scenario: Reporte generado
- **WHEN** el programa termina de validar el Excel real
- **THEN** existe `output/excepciones.csv` con un renglón por cada excepción detectada
- **AND** cada renglón indica la fila del Excel donde está el dato, contando el título y el encabezado

#### Scenario: Decisión visible
- **WHEN** se reporta una existencia negativa
- **THEN** su columna `decision` explica que se pide tomando existencia 0 y se marca para revisión

#### Scenario: Excel sin problemas
- **WHEN** el Excel no tiene ningún problema de datos
- **THEN** `excepciones.csv` existe y contiene solo el encabezado

### Requirement: Ningún producto se omite en silencio
Cada producto de Existencias (sin contar las apariciones repetidas de un mismo código) SHALL quedar clasificado como procesable o no procesable, según las decisiones de los requisitos anteriores. El programa MUST imprimir un resumen con los renglones leídos, los repetidos, los productos procesables y no procesables, y el conteo de excepciones por tipo, donde renglones leídos = repetidos + procesables + no procesables.

#### Scenario: Conciliación de conteos
- **WHEN** el programa termina de validar el Excel real
- **THEN** el resumen muestra 52 renglones leídos
- **AND** repetidos + procesables + no procesables suman 52
