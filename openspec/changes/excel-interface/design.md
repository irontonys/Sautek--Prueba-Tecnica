# Design

## Context

El motor de Python ya está dividido en piezas chicas: `loader.py` lee las hojas, `validation.py` detecta los problemas y aplica la tabla `DECISIONS`, `orders.py` calcula cantidades y estados, y `report.py` y `emails.py` escriben las salidas. Sus specs son `validacion-datos`, `calculo-pedidos` y `borradores-correo`. La motivación del libro de Excel está en `proposal.md`. El comprador trabaja con Excel para Windows o para Mac y no tiene Python. El autor desarrolla en una Mac con Microsoft Excel instalado.

## Goals / Non-Goals

**Goals:**
- Mismos resultados que Python para el mismo inventario: excepciones (hoja, fila, código, tipo, detalle, valor original y decisión), cantidades, importes, totales, estados y contenido de los borradores.
- Que el comprador nunca tenga que saber qué es una macro: abre el libro, habilita macros una vez y sigue los botones.
- Que una corrección hecha a mano en el libro quede visible y se pueda rastrear.

**Non-Goals:**
- Crear borradores directo en Outlook o enviar correos. Lo primero solo funciona en Windows; lo segundo lo descarta el supuesto 11.
- Excel en la web y Excel para iPad: no ejecutan VBA.
- Cambiar las reglas o las decisiones de la validación. El libro las replica tal como están.
- Conectarse a Odoo desde el libro.

## Decisions

- **Toda la lógica en VBA dentro del libro**, replicando el motor de Python módulo por módulo. Alternativas descartadas:
  - *Botones que llaman a Python empaquetado como `.exe`* (PyInstaller): el `.exe` hay que compilarlo en Windows, los antivirus suelen bloquear ejecutables sin firma, en Mac VBA casi no puede ejecutar programas externos y el comprador tendría que mantener dos archivos juntos.
  - *xlwings*: necesita Python instalado.
  - *Office Scripts*: solo existen en Excel en la web con licencia empresarial.

  El costo es tener la lógica duplicada. La mitiga la prueba de paridad (abajo), y Python sigue siendo la referencia: si una regla cambia, se cambia en los dos y la prueba lo confirma.
- **Módulos VBA espejo de los de Python:** `modLoader`, `modValidation` (con su propia tabla de decisiones `tipo → texto, ¿excluye?, grupo`), `modOrders`, `modEmails`, `modWorkbook` (hojas, formatos y botones) y `modUI` (lo que hace cada botón). Las reglas no saben de la interfaz, igual que en Python, y la comparación entre los dos lados se hace función por función.
- **Las hojas se copian con su misma forma:** título en la fila 1, encabezado en la fila 2 y datos desde la fila 3. Así la fila que reporta una excepción es la misma en el archivo exportado y en la copia, y el enlace "Ir a la celda" apunta al lugar correcto. Se copia con `Range.Value`, que conserva el tipo de cada celda (el texto `"1,250"` sigue siendo texto y `" ftr-0004 "` conserva sus espacios), y se leen los rangos completos a arreglos en memoria en vez de celda por celda.
- **Grupos de excepción iguales a los de la bandeja de Odoo:** *Se corrigió*, *Advertencia* (existencia negativa y unidad distinta), *No se procesó* (toda excepción que excluye) y *Compra* (pedido mínimo no alcanzado). El comprador ve las mismas palabras en las dos interfaces.
- **Correcciones por comparación contra una copia oculta, no por eventos.** Al cargar, cada hoja se copia también a una hoja oculta y protegida. **Revisar datos** compara celda por celda y reescribe la hoja **Correcciones**: hoja, celda, código del renglón, valor cargado y valor actual. Se descartó registrar cada edición con `Worksheet_Change`: no ve bien lo que se pega, se desactiva si una macro falla y no guarda el valor anterior sin trucos extra. Para que comparar por posición sea válido, las hojas de datos se protegen contra insertar y borrar renglones; las celdas de datos y un bloque de renglones vacíos al final quedan editables para agregar registros (por ejemplo, el mínimo que falta).
- **Revisar datos siempre valida desde cero** sobre lo que hay en las hojas. Repetir la validación no acumula estado y da lo mismo que daría Python con un Excel que ya trajera esas correcciones.
- **Pedidos con fórmulas para lo editable.** **Preparar pedidos** escribe en **Detalle** la cantidad calculada como valor y el importe como fórmula (`cantidad × costo`). En **Resumen**, el total (`SUMIFS` sobre Detalle) y el estado (comparación contra el pedido mínimo) también son fórmulas. Si el comprador completa el pedido de P05 subiendo cantidades, el total y el estado cambian al momento. Un formato condicional marca la cantidad que no es múltiplo del empaque. La columna "Revisar" se conserva.
- **Generar correos lee el estado actual de Resumen y Detalle**, ediciones incluidas, y antes revisa que los datos no hayan cambiado desde **Preparar pedidos**. **Preparar pedidos** guarda una firma (una suma de verificación del contenido de las cuatro hojas). Si al generar ya no coincide, avisa que hay que preparar los pedidos de nuevo y no escribe nada. Así no sale un correo con cantidades de datos viejos. Se eligió la firma en vez de eventos por la misma razón de arriba.
- **Los `.eml` se escriben byte por byte en UTF-8 con E/S binaria de VBA**, con un codificador propio. `ADODB.Stream` es lo usual, pero no existe en Mac. Mismo formato que Python: `To`, `Subject`, `X-Unsent: 1`, `Content-Type: text/plain; charset="utf-8"`, `Content-Transfer-Encoding: 8bit`, sin `From`; mismo cuerpo, mismos nombres de archivo (`P01_distribuidora-truper-norte.eml`, con los acentos quitados por una tabla) y mismo `indice.csv` con BOM. Se borran los `.eml` viejos de la carpeta antes de escribir.
- **Importes con el tipo `Currency`** (punto fijo, 4 decimales) y redondeo a centavos hacia arriba en el medio, igual que `money()` en Python. Con `Double` aparecerían diferencias de un centavo en los totales.
- **El repo guarda el código como texto y el libro armado.** `excel/vba/*.bas` se revisa en los commits. `excel/build.py` controla Excel en Mac con AppleScript: crea un libro, importa los módulos, ejecuta `modWorkbook.BuildWorkbook` (hojas, formatos, protección y botones) y guarda `excel/Resurtido.xlsm`. El `.xlsm` también se versiona, porque es lo que el comprador descarga. Para armarlo hay que activar una vez en Excel *Confiar en el acceso al modelo de objetos de proyectos de VBA*; no hace falta para usar el libro.
- **Prueba de paridad con una macro sin diálogos.** `modUI.RunHeadless(entrada, salida, fecha)` hace la misma secuencia que los botones (cargar, revisar, preparar y generar), pero recibe las rutas como parámetros y escribe `excepciones.csv`, `pedidos.csv` y `correos/` en el formato de Python. `tests/test_excel_paridad.py` corre Python y el libro sobre el mismo inventario y la misma fecha, y compara:
  - el Excel real;
  - libros armados con `write_workbook` de `conftest.py` que cubren los tipos de excepción que el Excel real no trae (existencia no numérica, código vacío o no normalizable, costo, múltiplo, correo y pedido mínimo inválidos, proveedor inexistente y repetidos en hojas de referencia).

  La prueba se omite si no hay Microsoft Excel en la computadora.

## Risks / Trade-offs

- [Lógica duplicada que se desfasa con el tiempo] → la prueba de paridad cubre todos los tipos de excepción y el cálculo; el README y `SUPUESTOS.md` dicen que una regla se cambia en los dos lados.
- [Windows bloquea las macros de un archivo descargado de internet (Marca de la Web)] → el README explica cómo desbloquearlo: clic derecho → Propiedades → "Desbloquear". En una implementación real se firmaría la macro o se pondría el libro en una ubicación de confianza.
- [Excel para Mac pide permiso para escribir fuera de la carpeta del libro (sandbox)] → los correos se escriben junto al libro y se pide el permiso con `GrantAccessToMultipleFiles` antes de escribir. Si el comprador lo niega, el libro avisa y no queda a medias.
- [El comprador edita las hojas de pedidos más allá de la cantidad] → Resumen y Detalle se protegen con solo la columna Cantidad editable.
- [La prueba de paridad solo corre en la Mac del autor] → la parte sin Excel (Python) sigue corriendo en cualquier lado. La paridad se corre antes de cada commit que toque `excel/vba/` y el resultado queda anotado en las tareas.
- [Diferencias de redondeo o de formato de número entre VBA y Python] → los importes usan `Currency` y los textos con números (`{value:g}`, `$#,##0.00`) se arman con funciones propias, no con `Format` regional, para no depender de la configuración del equipo (coma o punto decimal).

## Migration Plan

No hay migración: el libro es una salida nueva y no cambia el programa de Python ni sus salidas. Para volver atrás basta con no usar el libro.
