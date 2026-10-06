# Spec Delta

## Purpose

Define cómo se ejecuta el programa de resurtido desde la línea de comandos: qué archivo lee, dónde escribe sus salidas y cómo reporta los problemas con la entrada sin tronar.

## ADDED Requirements

### Requirement: Ejecución con valores por omisión
El programa SHALL poder ejecutarse sin argumentos. En ese caso MUST leer `data/inventario_ferreteria_garza.xlsx` y escribir sus salidas en `output/`, relativo a la raíz del repositorio.

#### Scenario: Ejecución sin argumentos
- **WHEN** el usuario ejecuta el programa sin argumentos desde la raíz del repositorio
- **THEN** el programa lee `data/inventario_ferreteria_garza.xlsx`
- **AND** crea la carpeta `output/` si no existe

### Requirement: Rutas configurables
El programa SHALL aceptar argumentos para indicar otra ruta del Excel de entrada y otra carpeta de salida.

#### Scenario: Entrada y salida personalizadas
- **WHEN** el usuario ejecuta el programa con `--input otro.xlsx --output resultados/`
- **THEN** el programa lee `otro.xlsx` y escribe sus salidas en `resultados/`

### Requirement: Entrada inexistente o ilegible
Cuando el Excel de entrada no existe o no se puede abrir como libro de Excel, el programa MUST terminar con un código de salida distinto de cero y un mensaje en español que diga qué archivo falló y por qué. MUST NOT mostrar un traceback de Python.

#### Scenario: Archivo inexistente
- **WHEN** el usuario indica una ruta de entrada que no existe
- **THEN** el programa imprime un mensaje que incluye esa ruta
- **AND** termina con código de salida distinto de cero

#### Scenario: Archivo que no es Excel
- **WHEN** el usuario indica un archivo que no es un libro de Excel válido
- **THEN** el programa imprime un mensaje indicando que no pudo leerlo como Excel
- **AND** termina con código de salida distinto de cero

### Requirement: Verificación de hojas esperadas
Al abrir el Excel, el programa SHALL verificar que existan las hojas `Existencias`, `Minimos`, `Producto_Proveedor` y `Proveedores`, y MUST reportar por nombre cada hoja faltante.

#### Scenario: Libro completo
- **WHEN** el Excel contiene las cuatro hojas esperadas
- **THEN** el programa informa que encontró las cuatro hojas y termina con código de salida cero

#### Scenario: Hoja faltante
- **WHEN** al Excel le falta la hoja `Minimos`
- **THEN** el programa informa que falta la hoja `Minimos`
- **AND** termina con código de salida distinto de cero
