# Tasks

## 1. Armado del libro

- [x] 1.1 Crear `excel/build.py`, que con AppleScript abre Excel, importa `excel/vba/*.bas`, ejecuta `modWorkbook.BuildWorkbook` y guarda `excel/Resurtido.xlsm`; con un módulo mínimo, verificar que el libro se arma y la macro corre
- [x] 1.2 `modWorkbook.BuildWorkbook`: hoja Inicio con los cuatro botones y sus instrucciones, hojas de datos, Excepciones, Correcciones, Resumen y Detalle con sus encabezados, formatos y protección; verificar abriendo el libro armado y revisando que el orden de los botones y la protección son los del spec

## 2. Carga

- [x] 2.1 `modLoader` y el botón **Cargar inventario**: diálogo de abrir, revisión de hojas y columnas, copia por `Range.Value` con las mismas filas, copia oculta para Correcciones y confirmación antes de reemplazar; verificar con el Excel real (52/49/50/8 renglones, `FTR-0003` como texto `1,250`, el original sin cambios) y con un archivo sin la hoja `Minimos`

## 3. Validación

- [x] 3.1 `modValidation`: reglas de códigos (vacío, formato, no normalizable, repetidos en Existencias y en hojas de referencia), existencias, estatus, unidad, duplicado por descripción, mínimos, proveedores y producto-proveedor, con la tabla de decisiones y grupos, y el orden de `sort_exceptions`; verificar con `RunHeadless` sobre el Excel real que las 27 excepciones de validación coinciden con las de Python
- [x] 3.2 Botón **Revisar datos**: hoja Excepciones con grupo, color y enlace "Ir a la celda", hoja Correcciones por comparación contra la copia oculta y resumen en Inicio; verificar los escenarios "Ir a la celda", "Agregar un mínimo que falta" y "Corregir una existencia"

## 4. Pedidos

- [x] 4.1 `modOrders`: cantidad (faltante al entero siguiente y redondeo al múltiplo), importes en `Currency` con redondeo hacia arriba en el medio, totales, estados y excepción de pedido mínimo; verificar con `RunHeadless` que los pedidos del Excel real coinciden con `pedidos.xlsx` (6 se envían, P05 no, total $311,129.60)
- [x] 4.2 Botón **Preparar pedidos**: Resumen y Detalle con importe, total y estado como fórmulas, Cantidad editable con formato condicional de múltiplo, firma de los datos; verificar el escenario "Completar un pedido mínimo"

## 5. Correos

- [x] 5.1 `modEmails`: codificador UTF-8 en bytes, cuerpo con la tabla alineada, fecha larga en español, nombres de archivo sin acentos, `indice.csv` con BOM y borrado de `.eml` viejos; verificar con `RunHeadless` que los 6 borradores y el índice del Excel real coinciden con los de Python para la misma fecha
- [x] 5.2 Botón **Generar correos**: lee Resumen y Detalle actuales, revisa la firma, pide permiso de escritura en Mac y escribe junto al libro; verificar el escenario "Datos cambiados después de preparar" y abrir un `.eml` generado en el cliente de correo

## 6. Paridad

- [x] 6.1 `tests/test_excel_paridad.py`: corre Python y `RunHeadless` sobre el Excel real y compara excepciones, pedidos y borradores; se omite si no hay Microsoft Excel; verificar con `python -m pytest` en la Mac (pasa) y con Excel no disponible (se omite)
- [x] 6.2 Agregar a la prueba los libros de `write_workbook` con los tipos de excepción que el Excel real no trae; verificar que todos coinciden

## 7. Documentación y entregables

- [x] 7.1 Armar y versionar `excel/Resurtido.xlsm`; README con el libro como forma principal de uso (habilitar macros, desbloquear en Windows, los cuatro pasos), la terminal como alternativa técnica y Odoo como extra; `SUPUESTOS.md` con la lógica duplicada y la regla de cambiar los dos lados; verificar siguiendo el README desde cero con el libro descargado de GitHub
- [ ] 7.2 Recorrido completo en Excel para Mac con capturas en `docs/img/` (cargar, revisar, corregir, preparar, completar P05 y generar correos); verificar que el resultado coincide con el spec
