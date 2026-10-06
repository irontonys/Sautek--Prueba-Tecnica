# Proposal

## Why

El Excel viene "tal como sale de los sistemas, con errores", y la prueba pide que el programa no truene ni se brinque registros sin avisar. Antes de calcular un solo pedido hace falta leer las cuatro hojas, detectar cada problema de los datos y dejarlo por escrito. La revisión manual del archivo encontró 16 problemas de 12 tipos distintos.

## What Changes

- El programa lee las cuatro hojas tomando el encabezado de la fila 2 y verifica que existan las columnas esperadas.
- Detecta los problemas de datos por tipo, sin depender de códigos específicos: existencias como texto, vacías o negativas; códigos repetidos o con formato distinto; productos inactivos; el mismo producto con dos códigos; unidades que no coinciden con la descripción; mínimos ausentes o mayores que el máximo; productos sin proveedor; códigos que no existen en Existencias; costos, múltiplos o correos inválidos.
- Genera `output/excepciones.csv` con un renglón por problema: hoja, fila del Excel, código, tipo, detalle, valor original y decisión.
- **En esta fase la decisión de cada caso queda como "Pendiente de decisión".** El programa detecta y reporta, pero no corrige ni descarta nada por su cuenta. Las decisiones de negocio las toma el autor antes de la fase de cálculo.
- Cada producto de Existencias queda marcado como procesable o no procesable. Ninguno se pierde: leídos = procesables + no procesables.
- Al terminar, el programa imprime un resumen: productos leídos, procesables y con excepciones, y cuántas excepciones hay por tipo.

## Capabilities

### New Capabilities
- `validacion-datos`: lectura de las cuatro hojas del Excel, detección de problemas de datos por tipo y reporte de excepciones, con la garantía de que ningún registro se omite en silencio.

### Modified Capabilities

## Impact

- Código nuevo: módulos de carga y validación dentro de `resurtido/`; el punto de entrada los invoca después de verificar las hojas.
- Salida nueva: `output/excepciones.csv`, que se versiona como archivo entregable.
- Sin dependencias nuevas.
- La fase de cálculo de pedidos consumirá los productos procesables y aplicará las decisiones que hoy quedan pendientes.
