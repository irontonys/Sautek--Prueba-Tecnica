# Tasks

## 1. Cálculo

- [x] 1.1 Crear `resurtido/orders.py` con `OrderLine` y `SupplierOrder`, la selección (existencia < mínimo) y la cantidad con redondeo al múltiplo; verificar con pytest los escenarios de selección y cantidad, incluidos igual al mínimo y existencia con decimales
- [x] 1.2 Agrupar por proveedor con importes y total en `Decimal`; verificar con pytest que el total coincide con la suma de importes al centavo
- [x] 1.3 Aplicar el pedido mínimo (estados "Se envía", "No se envía" y "Sin productos por pedir") y registrar la excepción con su decisión en `DECISIONS`; verificar con pytest los escenarios de alcanza y no alcanza

## 2. Salidas

- [x] 2.1 Escribir `pedidos.xlsx` (Resumen y Detalle, con moneda y la columna Revisar) en `report.py`; verificar con pytest leyendo el archivo generado
- [x] 2.2 Conectar el cálculo al punto de entrada, agregar las excepciones de pedido mínimo al CSV y el resumen de pedidos en consola; verificar con `python -m resurtido` sobre el Excel real (6 se envían, 1 no)
- [x] 2.3 Prueba de regresión sobre el Excel real: totales por proveedor de la simulación, P05 "No se envía", P08 "Sin productos por pedir" y FTR-0007 con Revisar = Sí; verificar con pytest

## 3. Documentación y entregables

- [x] 3.1 Generar y versionar `output/pedidos.xlsx` y el `excepciones.csv` actualizado; actualizar el README (salidas) y `SUPUESTOS.md` (estrictamente menor, redondeo sobre el máximo, decisión 12b); verificar abriendo el Excel generado
