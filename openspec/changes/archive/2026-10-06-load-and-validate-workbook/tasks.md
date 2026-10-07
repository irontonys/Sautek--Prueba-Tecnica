# Tasks

## 1. Carga

- [x] 1.1 Crear `resurtido/loader.py`, que lea las cuatro hojas con encabezado en la fila 2 como texto crudo y verifique columnas esperadas; verificar con pytest que el Excel real da 52/49/50/8 renglones y que una columna faltante produce un error que nombra hoja y columna
- [x] 1.2 Conectar el loader al punto de entrada, con columna faltante reportada como mensaje sin traceback y código 1; verificar con la prueba de subprocess existente extendida

## 2. Validación

- [x] 2.1 Crear `resurtido/validation.py` con el registro de excepción, el catálogo de tipos y el diccionario de decisiones del autor; verificar con pytest que cada tipo decidido muestra su decisión y un tipo sin decisión sale como "Pendiente de decisión"
- [x] 2.2 Reglas de existencias (texto, vacía, negativa) y de estatus no activo; verificar con un Excel de prueba por escenario
- [x] 2.3 Normalización de códigos en las cuatro hojas y reglas de códigos (formato no estándar, repetido en Existencias conservando el primero); verificar con un Excel de prueba por escenario
- [x] 2.4 Reglas de referencias cruzadas (sin mínimo, sin proveedor, ausente de Existencias, proveedor inexistente) sobre códigos normalizados; verificar con un Excel de prueba por escenario
- [x] 2.5 Reglas de mínimos/máximos y de datos de compra (costo, múltiplo, pedido mínimo, correo); verificar con un Excel de prueba por escenario
- [x] 2.6 Reglas de productos sospechosos (duplicado por descripción, unidad distinta a la descripción); verificar que en el Excel real marca `FTR-0009`/`FTR-0051` y las unidades caja, bolsa, kg, m y par, sin falsos positivos
- [x] 2.7 Clasificación procesable / no procesable según las decisiones (con existencia limpia y marca de revisión); verificar con pytest que leídos = repetidos + procesables + no procesables

## 3. Reporte y salida

- [x] 3.1 Crear `resurtido/report.py`, que escriba `excepciones.csv` en UTF-8 con BOM con las 7 columnas; verificar con pytest que abre con acentos correctos y que un Excel limpio produce solo el encabezado
- [x] 3.2 Imprimir el resumen (leídos, repetidos, procesables, no procesables, excepciones por tipo) al final de `python -m resurtido`; verificar corriéndolo sobre el Excel real
- [x] 3.3 Prueba de regresión sobre el Excel real que confirme que se detectan los 16 problemas de la revisión manual; verificar con pytest
- [x] 3.4 Generar y versionar `output/excepciones.csv` del Excel real, y actualizar el README (salidas) y `SUPUESTOS.md` (unidades, existencia negativa como 0, tipos sin decisión); verificar leyendo el CSV generado

## 4. Decisiones del autor (bloquea la fase de cálculo, no esta)

- [x] 4.1 Recordar al autor que conteste las 12 decisiones; quedaron registradas en `design.md` → Decisiones del autor
