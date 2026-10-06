# Spec Delta

## Purpose

Lee las cuatro hojas del Excel de inventario, detecta los problemas de calidad de datos y los reporta en un archivo de excepciones, garantizando que ningún registro se omita en silencio.

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

### Requirement: Detección de existencias inválidas
El programa SHALL reportar como excepción toda existencia que esté vacía, sea texto (aunque represente un número, como `1,250`) o sea negativa.

#### Scenario: Existencia como texto
- **WHEN** un producto tiene existencia `"1,250"`
- **THEN** el reporte incluye una excepción de tipo existencia como texto, con valor original `1,250`

#### Scenario: Existencia vacía
- **WHEN** un producto no tiene existencia
- **THEN** el reporte incluye una excepción de tipo existencia vacía

#### Scenario: Existencia negativa
- **WHEN** un producto tiene existencia `-4`
- **THEN** el reporte incluye una excepción de tipo existencia negativa, con valor original `-4`

### Requirement: Detección de códigos problemáticos
El programa SHALL reportar los códigos que se repiten dentro de una misma hoja y los códigos que no siguen el formato estándar `FTR-` seguido de 4 dígitos, incluyendo minúsculas, espacios alrededor o ceros faltantes. Para un código con formato distinto, el detalle MUST indicar a qué código estándar correspondería.

#### Scenario: Código repetido
- **WHEN** `FTR-0027` aparece dos veces en Existencias
- **THEN** el reporte incluye una excepción de código repetido para cada aparición, con su fila de Excel

#### Scenario: Código con formato distinto
- **WHEN** la hoja Minimos contiene el código `" ftr-0004 "`
- **THEN** el reporte incluye una excepción de formato de código cuyo detalle menciona `FTR-0004`

### Requirement: Detección de referencias cruzadas faltantes
El programa SHALL reportar cada producto de Existencias sin renglón en Minimos o sin renglón en Producto_Proveedor, cada código de Minimos o Producto_Proveedor que no exista en Existencias y cada proveedor referenciado que no exista en Proveedores. La comparación de códigos MUST ser exacta; cuando un código no coincide pero sí coincidiría con formato estándar, el detalle MUST mencionar esa posible coincidencia.

#### Scenario: Producto sin proveedor
- **WHEN** `FTR-0033` está en Existencias pero no en Producto_Proveedor
- **THEN** el reporte incluye una excepción de producto sin proveedor para `FTR-0033`

#### Scenario: Código ausente de Existencias
- **WHEN** `FTR-0021` está en Minimos pero no en Existencias
- **THEN** el reporte incluye una excepción de código ausente de Existencias para `FTR-0021`

#### Scenario: Posible coincidencia por formato
- **WHEN** `FTR-0027` está en Existencias y la hoja Minimos solo tiene `FTR-27`
- **THEN** la excepción de producto sin mínimo para `FTR-0027` menciona `FTR-27` como posible coincidencia

### Requirement: Detección de mínimos y máximos inválidos
El programa SHALL reportar los mínimos o máximos vacíos, no numéricos o negativos, y los casos donde el mínimo es mayor que el máximo.

#### Scenario: Mínimo mayor que máximo
- **WHEN** un producto tiene mínimo 60 y máximo 40
- **THEN** el reporte incluye una excepción de mínimo mayor que máximo con ambos valores en el detalle

### Requirement: Detección de datos de compra inválidos
El programa SHALL reportar costos unitarios o múltiplos de empaque vacíos, no numéricos o menores o iguales a cero, pedidos mínimos de proveedor vacíos, no numéricos o negativos, y correos de proveedor sin formato de correo válido.

#### Scenario: Múltiplo de empaque en cero
- **WHEN** un producto tiene múltiplo de empaque `0`
- **THEN** el reporte incluye una excepción de múltiplo de empaque inválido

#### Scenario: Correo inválido
- **WHEN** un proveedor tiene correo `ventas.truper.mx`
- **THEN** el reporte incluye una excepción de correo inválido para ese proveedor

### Requirement: Detección de productos sospechosos
El programa SHALL reportar los productos con estatus distinto de `ACTIVO`, los productos de Existencias con códigos distintos cuya descripción coincide al ignorar mayúsculas, comillas y espacios repetidos, y los productos cuya descripción indica entre paréntesis una unidad de compra (caja, bolsa, kg, m, par) distinta de la columna Unidad.

#### Scenario: Producto inactivo
- **WHEN** un producto tiene estatus `INACTIVO`
- **THEN** el reporte incluye una excepción de producto inactivo

#### Scenario: Mismo producto con dos códigos
- **WHEN** `FTR-0009` se describe como `Tornillo 1/4 x 2" (caja)` y `FTR-0051` como `Tornillo 1/4 x 2 (caja)`
- **THEN** el reporte incluye una excepción de posible duplicado para cada código, mencionando al otro

#### Scenario: Unidad distinta a la descripción
- **WHEN** un producto se describe como `Clavo 2" (kg)` y su unidad es `PZA`
- **THEN** el reporte incluye una excepción de unidad inconsistente

### Requirement: Reporte de excepciones
El programa SHALL escribir `excepciones.csv` en la carpeta de salida, en UTF-8 con BOM para que Excel muestre bien los acentos, con las columnas `hoja`, `fila_excel`, `codigo`, `tipo`, `detalle`, `valor_original` y `decision`. Mientras no exista una decisión de negocio registrada para un tipo de excepción, su columna `decision` MUST decir `Pendiente de decisión`.

#### Scenario: Reporte generado
- **WHEN** el programa termina de validar el Excel real
- **THEN** existe `output/excepciones.csv` con un renglón por cada excepción detectada
- **AND** cada renglón indica la fila del Excel donde está el dato, contando el título y el encabezado

#### Scenario: Excel sin problemas
- **WHEN** el Excel no tiene ningún problema de datos
- **THEN** `excepciones.csv` existe y contiene solo el encabezado

### Requirement: Ningún producto se omite en silencio
Cada renglón de Existencias SHALL quedar clasificado como procesable o no procesable. Es no procesable si tiene al menos una excepción asociada. El programa MUST imprimir un resumen donde productos leídos = procesables + no procesables, junto con el conteo de excepciones por tipo.

#### Scenario: Conciliación de conteos
- **WHEN** el programa termina de validar el Excel real
- **THEN** el resumen muestra 52 productos leídos
- **AND** la suma de procesables y no procesables es 52
