# Design

## Context

Ya existe el punto de entrada `python -m resurtido`, que valida que el archivo exista y que tenga las cuatro hojas (spec `ejecucion-cli`). Esta fase agrega la lectura del contenido y la detección de problemas. El autor revisó el Excel a mano, encontró 16 problemas y decidió qué hacer con cada tipo (ver Decisiones del autor).

## Goals / Non-Goals

**Goals:**
- Detectar cada problema del Excel real y cualquier problema del mismo tipo en un Excel distinto, sin reglas atadas a códigos específicos.
- Que cada excepción se pueda rastrear a su celda: hoja y fila del Excel tal como se ve al abrirlo.

**Non-Goals:**
- La regla de pedido mínimo de proveedor (decisión 12): se aplica al calcular pedidos.
- Calcular pedidos, agrupar por proveedor o escribir correos.

## Decisions

- **Leer todo como texto (`dtype=object`) y convertir después.** Si pandas infiere tipos, `"1,250"` y un número se mezclan en silencio o la columna cambia de tipo. Leyendo el valor crudo se puede reportar el valor original exacto. Alternativa descartada: `dtype=float`, que trona o convierte sin avisar.
- **Fila de Excel = índice del DataFrame + 3** (fila 1 título, fila 2 encabezado). Se calcula en un solo lugar.
- **Tres módulos con una responsabilidad cada uno:**
  - `loader.py` lee las hojas y verifica columnas.
  - `validation.py` aplica las reglas y devuelve la lista de excepciones y la clasificación de productos.
  - `report.py` escribe el CSV.

  Así cada pieza se prueba sola, y la fase de cálculo reutiliza el loader sin tocar la validación.
- **Una excepción es un registro simple** (`dataclass`) con los mismos campos que las columnas del CSV, y su tipo viene de un catálogo fijo de constantes. Contar por tipo y probar se vuelve directo.
- **Las decisiones viven en un diccionario `tipo → (texto de la decisión, ¿excluye el producto?)`.** La detección no sabe qué se decidió. Si una decisión cambia, se edita una línea del diccionario, no las reglas. Un tipo ausente del diccionario sale "Pendiente de decisión" y excluye el producto.
- **Normalizar los códigos antes de cruzar las hojas** (decisión 9a): mayúsculas, sin espacios y, si el código es `FTR-` más dígitos, rellenado a 4 dígitos. Cada código que cambió se reporta, así que la normalización nunca es silenciosa. Un código que no se puede llevar a formato estándar se queda tal cual y no cruza con nada.
- **Existencia negativa como 0 para el cálculo** (decisión 3c, "pedir pero marcar para revisión"). Usar el negativo pediría de más para cubrir un hueco que probablemente es un error de captura. Partir de 0 asume que físicamente no hay piezas. La marca de revisión viaja con el producto para que la fase de cálculo la muestre en el pedido.
- **Duplicado por descripción con normalización ligera:** minúsculas, sin comillas y con espacios colapsados. Detecta `FTR-0009` / `FTR-0051` sin falsos positivos en el archivo real. Se descarta la similitud difusa: en 800 productos daría ruido.
- **Unidad contra descripción:** solo se revisa un paréntesis final con una palabra del catálogo (caja, bolsa, kg, m, par). Es conservador: marca la duda y no adivina conversiones.
- **CSV en UTF-8 con BOM (`utf-8-sig`).** Sin BOM, Excel en Windows muestra mal los acentos.

## Risks / Trade-offs

- [Reglas heurísticas (duplicados por descripción, unidades) con falsos positivos en un Excel más grande] → son avisos para revisión, no descartes automáticos, y el detalle explica por qué se marcó.
- [Un producto con varias excepciones aparece en varios renglones del reporte] → es intencional: cada problema necesita su propia decisión. El resumen cuenta productos y excepciones por separado.
- [Las decisiones excluyentes (6, 10, 11) dejan productos sin pedir aunque estén bajo el mínimo] → aparecen en el reporte con su decisión, así que el comprador los ve y puede pedirlos a mano.

## Decisiones del autor

Tomadas el 2026-10-06 después de revisar el Excel a mano.

| # | Caso | Decisión | ¿Procesable? |
|---|---|---|---|
| 1 | Existencia como texto (`1,250`) | Convertir a número y avisar | Sí |
| 2 | Existencia vacía | No procesar y avisar | No |
| 3 | Existencia negativa | Pedir tomando existencia 0 y marcar para revisión | Sí, marcado |
| 4 | Código repetido en Existencias | Conservar la primera aparición y avisar | Sí, una vez |
| 5 | Producto inactivo | No pedirlo | No |
| 6 | Mismo producto con dos códigos | No procesar ninguno hasta que alguien defina cuál es el bueno | No |
| 7 | Unidad de la descripción distinta a la columna Unidad | Suponer que todo está en la misma unidad; queda en `SUPUESTOS.md` | Sí |
| 8 | Código ausente de Existencias | No procesar y avisar | No aplica (no hay existencia) |
| 9 | Código con formato no estándar | Normalizar y avisar | Sí |
| 10 | Mínimo mayor que máximo | No procesar y avisar | No |
| 11 | Sin mínimo o sin proveedor | No procesar y avisar | No |
| 12 | Pedido mínimo de proveedor no alcanzado | No mandar el pedido y avisar al comprador | Se aplica en la fase de cálculo |

**Tipos sin decisión** porque no aparecen en el Excel real: costo o múltiplo inválido, pedido mínimo inválido, correo inválido y proveedor inexistente. Quedan como "Pendiente de decisión" y excluyen el producto, criterio conservador coherente con la decisión 11.
