# Proposal

## Why

Ya hay 43 productos limpios y procesables. Falta la parte central de la prueba: decidir qué pedir, cuánto y a quién, y respetar el pedido mínimo de cada proveedor. Hoy eso le cuesta al comprador la mayor parte de sus 6 horas semanales.

## What Changes

- Se pide un producto procesable cuando su existencia está estrictamente por debajo del mínimo.
- La cantidad es lo necesario para llegar al máximo, redondeada hacia arriba al múltiplo de empaque. Puede pasar el máximo por el redondeo.
- Los pedidos se agrupan por proveedor con su total en pesos.
- Si el total de un proveedor no alcanza su pedido mínimo, ese pedido queda como **"No se envía"** y se avisa al comprador. Esto aplica la decisión 12b del autor: no se completa automáticamente.
- Nueva salida `output/pedidos.xlsx`, con una hoja de detalle por producto (incluida la marca "Revisar" de existencias negativas) y una hoja de resumen por proveedor con su estado.
- Cada pedido que no alcanza el mínimo se agrega también a `excepciones.csv`.
- El resumen en consola agrega los pedidos a enviar, los no enviados y el total a comprar.

## Capabilities

### New Capabilities
- `calculo-pedidos`: selección de productos a pedir, cálculo de cantidades con múltiplo de empaque, agrupación por proveedor con totales, regla de pedido mínimo y archivo de pedidos.

### Modified Capabilities

## Impact

- Código nuevo: módulo de cálculo de pedidos dentro de `resurtido/` y escritura del Excel de pedidos.
- Salida nueva: `output/pedidos.xlsx`, que se versiona como entregable.
- `excepciones.csv` gana un tipo nuevo: pedido mínimo no alcanzado.
- Sin dependencias nuevas; openpyxl ya está instalado.
- La fase de correos usará los pedidos con estado "Se envía".
