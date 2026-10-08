# Spec Delta

## Purpose

Permite que el comprador haga todo el resurtido desde un libro de Excel con botones (cargar el inventario, revisar y corregir las excepciones, preparar los pedidos y generar los borradores de correo), sin instalar nada y con los mismos resultados que el programa de Python.

## ADDED Requirements

### Requirement: Libro con botones sin instalación
El repositorio SHALL incluir `excel/Resurtido.xlsm`, con una hoja **Inicio** que muestra en orden los botones **Cargar inventario**, **Revisar datos**, **Preparar pedidos** y **Generar correos**, con una línea de instrucciones por paso. El libro MUST funcionar en Microsoft Excel para Windows y para Mac sin Python ni complementos instalados.

#### Scenario: Abrir el libro
- **WHEN** el comprador abre `Resurtido.xlsm` y habilita las macros
- **THEN** ve la hoja Inicio con los cuatro botones en orden

#### Scenario: Paso fuera de orden
- **WHEN** el comprador da **Preparar pedidos** sin haber cargado un inventario
- **THEN** el libro le dice que primero cargue el inventario y no cambia nada

### Requirement: Cargar inventario sin tocar el original
**Cargar inventario** SHALL pedir el archivo con el diálogo de abrir de Excel y copiar al libro las hojas `Existencias`, `Minimos`, `Producto_Proveedor` y `Proveedores` con sus mismas filas (título en la fila 1, encabezado en la fila 2) y el mismo tipo en cada celda. El archivo elegido MUST quedar sin cambios. Si le falta una hoja o una columna, o no se puede abrir como Excel, el libro MUST decir cuál falta y conservar la carga anterior. Si ya hay datos cargados, MUST pedir confirmación antes de reemplazarlos, porque se pierden las correcciones hechas.

#### Scenario: Excel real
- **WHEN** el comprador carga `data/inventario_ferreteria_garza.xlsx`
- **THEN** el libro tiene 52 renglones de datos en Existencias, 49 en Minimos, 50 en Producto_Proveedor y 8 en Proveedores
- **AND** la celda de existencia de `FTR-0003` contiene el texto `1,250`
- **AND** el archivo de entrada no cambió

#### Scenario: Hoja faltante
- **WHEN** el archivo elegido no tiene la hoja `Minimos`
- **THEN** el libro avisa que falta la hoja `Minimos`
- **AND** los datos cargados antes siguen igual

### Requirement: Revisar datos con las mismas reglas
**Revisar datos** SHALL validar las hojas del libro con las mismas reglas y decisiones de la capacidad `validacion-datos` y reescribir la hoja **Excepciones** con un renglón por excepción y las columnas hoja, fila, código, tipo, detalle, valor original, decisión y grupo, en el mismo orden que `excepciones.csv`. El grupo MUST ser *Se corrigió*, *Advertencia* (existencia negativa o unidad distinta a la descripción), *No se procesó* (toda excepción que excluye al producto) o *Compra* (pedido mínimo no alcanzado), y cada grupo MUST tener su propio color. Cada renglón MUST tener un enlace que lleva a la celda del problema. La hoja Inicio SHALL mostrar el resumen de la revisión: renglones leídos, repetidos, procesables, no procesables y excepciones por grupo.

#### Scenario: Excel real
- **WHEN** el comprador revisa los datos del Excel real recién cargado
- **THEN** la hoja Excepciones tiene las mismas 27 excepciones de validación que Python, con los mismos campos
- **AND** el resumen dice 52 renglones leídos, 1 repetido, 43 procesables y 8 no procesables

#### Scenario: Ir a la celda
- **WHEN** el comprador da clic en el enlace de la excepción "Existencia negativa" de `FTR-0007`
- **THEN** Excel selecciona la celda de existencia de la fila 9 en la hoja Existencias

### Requirement: Correcciones a mano rastreables
El comprador SHALL poder corregir valores en las celdas de datos y agregar renglones al final de cada hoja; las hojas de datos MUST impedir que se inserten o borren renglones. Cada **Revisar datos** MUST reescribir la hoja **Correcciones** con un renglón por celda cuyo valor difiere del cargado: hoja, celda, código del renglón, valor cargado y valor actual. La validación MUST usar los valores actuales.

#### Scenario: Agregar un mínimo que falta
- **WHEN** el comprador agrega en Minimos un renglón para `FTR-0024` con mínimo 10 y máximo 40 y vuelve a revisar los datos
- **THEN** ya no aparece la excepción "Producto sin mínimo" de `FTR-0024`
- **AND** la hoja Correcciones tiene renglones para las celdas nuevas, con valor cargado vacío

#### Scenario: Corregir una existencia
- **WHEN** el comprador cambia la existencia de `FTR-0007` de -4 a 2 y vuelve a revisar los datos
- **THEN** ya no aparece la excepción "Existencia negativa" de `FTR-0007`
- **AND** la hoja Correcciones muestra Existencias, la celda de esa existencia, `FTR-0007`, -4 y 2

### Requirement: Preparar pedidos con el mismo cálculo
**Preparar pedidos** SHALL validar los datos actuales y escribir las hojas **Resumen** y **Detalle** con las mismas columnas, cantidades, importes, totales y estados que `pedidos.xlsx` (capacidad `calculo-pedidos`), y agregar a Excepciones las de pedido mínimo no alcanzado. En Detalle, la cantidad MUST ser editable y el importe, el total del proveedor en Resumen y su estado MUST recalcularse al cambiarla. Una cantidad que no es múltiplo del empaque MUST quedar resaltada. Las demás celdas de Resumen y Detalle MUST estar protegidas.

#### Scenario: Excel real
- **WHEN** el comprador prepara los pedidos del Excel real sin corregir nada
- **THEN** Resumen tiene 6 proveedores con estado "Se envía" y P05 con "No se envía"
- **AND** el total de los pedidos que se envían es $311,129.60
- **AND** Excepciones tiene 28 renglones, con "Pedido mínimo no alcanzado" de P05 en el grupo *Compra*

#### Scenario: Completar un pedido mínimo
- **WHEN** el comprador sube cantidades de P05 en Detalle hasta que su total llega a $15,000.00
- **THEN** el estado de P05 en Resumen cambia a "Se envía"

### Requirement: Generar correos sin enviarlos
**Generar correos** SHALL escribir en la carpeta `correos/`, junto al libro, un borrador `.eml` por cada proveedor con estado "Se envía" en Resumen y el `indice.csv`, con el mismo formato y contenido que la capacidad `borradores-correo` y usando las cantidades y totales actuales de Resumen y Detalle. MUST borrar antes los `.eml` de esa carpeta y MUST NOT enviar correos ni conectarse a ningún servidor. Si las hojas de datos cambiaron desde **Preparar pedidos**, MUST pedir que se preparen los pedidos de nuevo y no escribir nada.

#### Scenario: Excel real
- **WHEN** el comprador genera los correos del Excel real
- **THEN** `correos/` tiene 6 archivos `.eml`, sin P05 ni P08
- **AND** cada borrador es igual al de Python para la misma fecha

#### Scenario: Datos cambiados después de preparar
- **WHEN** el comprador corrige una existencia después de preparar los pedidos y da **Generar correos**
- **THEN** el libro le pide preparar los pedidos de nuevo
- **AND** no escribe ni borra ningún archivo

### Requirement: Paridad con el programa de Python
El libro SHALL exponer una macro sin diálogos que recibe la ruta del inventario, una carpeta de salida y la fecha, y escribe `excepciones.csv`, los pedidos y `correos/`. Para el mismo inventario y la misma fecha, sus resultados MUST ser iguales a los de `python -m resurtido`. Una prueba automatizada MUST comparar los dos, y se omite si en la computadora no hay Microsoft Excel.

#### Scenario: Excel real
- **WHEN** la prueba corre el Excel real por los dos caminos
- **THEN** las excepciones, los pedidos (cantidades, importes, totales y estados) y los borradores coinciden

#### Scenario: Tipos de excepción que el Excel real no trae
- **WHEN** la prueba corre libros de prueba con existencia no numérica, código vacío o no normalizable, costo, múltiplo, correo o pedido mínimo inválidos, proveedor inexistente y códigos repetidos en hojas de referencia
- **THEN** las excepciones y los pedidos coinciden en cada libro
