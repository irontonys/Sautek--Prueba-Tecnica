# Design

## Context

La validación (`validacion-datos`) entrega una lista de `Product` limpios, con existencia ya ajustada y marca `revisar`, más el catálogo de `Supplier`. Una simulación sobre el Excel real da 7 proveedores con productos por pedir; solo Plomería Express (P05) no llega a su mínimo ($12,664.05 contra $15,000).

## Goals / Non-Goals

**Goals:**
- Que el cálculo sea una función pura (productos y proveedores de entrada, pedidos de salida), fácil de probar con casos de resultado conocido.
- Que el comprador abra un solo Excel y vea qué se manda, qué no y por qué.

**Non-Goals:**
- Completar automáticamente un pedido que no llega al mínimo (decisión 12b).
- Redactar los correos: es la siguiente fase.

## Decisions

- **Módulo `orders.py` con el cálculo, sin entrada ni salida de archivos.** Recibe `products` y `suppliers` y regresa una lista de `SupplierOrder` con sus `OrderLine`. La escritura del Excel va en `report.py`, junto al CSV de excepciones. Así el cálculo se prueba sin archivos y la fase de correos reutiliza `SupplierOrder` directamente.
- **Redondeo con aritmética entera:** `ceil(faltante / múltiplo) * múltiplo` sobre enteros. Con existencias como 1250.0 se convierte a entero solo si no tiene decimales; si los tiene (por ejemplo, kg), el faltante se redondea hacia arriba antes de aplicar el múltiplo. Así no se pide de menos por un decimal.
- **Totales en `Decimal`, redondeados a 2 decimales.** Sumar floats en pesos acumula errores de centavos; con `Decimal` el total del resumen coincide con la suma de importes del detalle.
- **El estado del pedido vive en `SupplierOrder`** ("Se envía", "No se envía", "Sin productos por pedir"), y el texto de la decisión 12b se agrega a `DECISIONS` en `validation.py`, con la excepción nueva. Así todas las decisiones siguen en un solo lugar.
- **Los proveedores sin productos también aparecen en el Resumen.** Que P08 diga "Sin productos por pedir" le confirma al comprador que se revisó y no se olvidó.
- **Excel con openpyxl directo**, con encabezados en negritas, formato de moneda y anchos de columna, en lugar de `DataFrame.to_excel`. El archivo lo abre una persona, y con poco código se lee mucho mejor.
- **Orden estable:** proveedores por ID y productos por código, para que dos corridas con el mismo Excel den el mismo archivo y los diffs de Git sean legibles.

## Risks / Trade-offs

- [El redondeo puede dejar inventario por encima del máximo (9 productos en el Excel real)] → lo pide el enunciado; queda en `SUPUESTOS.md`, y el detalle muestra máximo y cantidad lado a lado para que se vea.
- [Un pedido que no llega al mínimo deja productos bajo el mínimo sin resurtir] → aparece en el Resumen, en el Detalle con su estado y en `excepciones.csv`, así que el comprador decide si lo completa a mano.
- [`pedidos.xlsx` versionado en Git es binario: los diffs no se leen] → es un entregable que pide la prueba. Se regenera completo en cada corrida.
