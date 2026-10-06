# Design

## Context

Ya existe el punto de entrada `python -m resurtido`, que valida que el archivo exista y que tenga las cuatro hojas (spec `ejecucion-cli`). Esta fase agrega la lectura del contenido y la detección de problemas. El autor revisó el Excel a mano y encontró 16 problemas; las decisiones de negocio sobre cada uno siguen pendientes (ver Open Questions).

## Goals / Non-Goals

**Goals:**
- Detectar cada problema del Excel real y cualquier problema del mismo tipo en un Excel distinto, sin reglas atadas a códigos específicos.
- Que cada excepción se pueda rastrear a su celda: hoja y fila del Excel tal como se ve al abrirlo.

**Non-Goals:**
- Corregir datos o decidir qué hacer con cada caso. Eso entra en la fase de cálculo, una vez que el autor tome las decisiones.
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
- **Las decisiones viven en un diccionario `tipo → decisión`**, hoy vacío, así que todo sale "Pendiente de decisión". Cuando el autor decida, se llena ese diccionario y la lógica correspondiente sin reescribir la detección.
- **Comparación exacta de códigos, con pista de normalización.** Normalizar en silencio sería tomar la decisión 9/10 por el autor. Se compara exacto, y el detalle de la excepción menciona la posible coincidencia (`FTR-27` → `FTR-0027`).
- **Duplicado por descripción con normalización ligera:** minúsculas, sin comillas y con espacios colapsados. Detecta `FTR-0009` / `FTR-0051` sin falsos positivos en el archivo real. Se descarta la similitud difusa: en 800 productos daría ruido.
- **Unidad contra descripción:** solo se revisa un paréntesis final con una palabra del catálogo (caja, bolsa, kg, m, par). Es conservador: marca la duda y no adivina conversiones.
- **CSV en UTF-8 con BOM (`utf-8-sig`).** Sin BOM, Excel en Windows muestra mal los acentos.

## Risks / Trade-offs

- [Reglas heurísticas (duplicados por descripción, unidades) con falsos positivos en un Excel más grande] → son avisos para revisión, no descartes automáticos, y el detalle explica por qué se marcó.
- [Un producto con varias excepciones aparece en varios renglones del reporte] → es intencional: cada problema necesita su propia decisión. El resumen cuenta productos y excepciones por separado.
- [Mientras no haya decisiones, casi un tercio de los productos queda no procesable] → es el comportamiento correcto para esta fase; la fase de cálculo lo resuelve con las decisiones del autor.

## Open Questions

Decisiones de negocio pendientes del autor, una por tipo de excepción. No cambian la detección ni el reporte de esta fase; definen qué hará la fase de cálculo con cada caso:

1. Existencia como texto (`1,250`)
2. Existencia vacía
3. Existencia negativa
4. Código repetido en Existencias
5. Producto inactivo
6. Mismo producto con dos códigos
7. Unidad de la descripción distinta a la columna Unidad
8. Código en Minimos o Producto_Proveedor ausente de Existencias
9. Código con formato no estándar
10. Mínimo mayor que máximo
11. Producto sin mínimo o sin proveedor
12. Proveedor con pedido mínimo no alcanzado (regla de la fase de cálculo; el autor ya propuso un criterio en la Parte 1, pregunta 5)
