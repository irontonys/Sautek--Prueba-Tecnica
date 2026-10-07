# Proposal

## Why

El programa de resurtido resuelve el problema con un Excel y un script, pero el caso de Ferretera Garza termina, tarde o temprano, en un ERP. Mostrar que los mismos datos, ya limpios, se cargan a Odoo y que el reabastecimiento nativo de Odoo llega a los mismos pedidos demuestra que la solución no es un script aislado: es el primer paso de una migración. Es la diferencia frente a una entrega que solo cumple el enunciado.

## What Changes

- Un Odoo 17 Community local dentro del repo (`odoo/docker-compose.yml`), con Compras e Inventario instalados al levantarlo y sin datos de demostración. Usa un puerto distinto al de cualquier otro Odoo de la máquina.
- Un comando nuevo, `python -m resurtido.odoo`, que:
  - Lee y valida el Excel con el mismo motor de la CLI. Solo carga a Odoo los productos procesables; lo excluido queda en el reporte de excepciones, igual que hoy.
  - Carga a Odoo por XML-RPC los proveedores (contactos con correo), los productos almacenables con su costo de compra con el proveedor, las existencias como ajuste de inventario y una regla de reabastecimiento por producto (mínimo, máximo y múltiplo de empaque) con la ruta "Comprar".
  - Dispara el reabastecimiento nativo de Odoo, que genera las solicitudes de cotización (RFQ) en borrador, una por proveedor.
  - Cubre lo que Odoo no hace solo: deja un aviso en el chatter de la RFQ del proveedor que no llega a su pedido mínimo (decisión 12b) y otro en las RFQ con productos marcados para revisión (existencia negativa, decisión 3c).
  - Concilia: compara por proveedor el total de la RFQ en Odoo contra el total que calcula la CLI y escribe el resultado en `output/odoo/conciliacion.csv`. Si algo no cuadra, lo dice.
- Ningún correo sale de Odoo: las RFQ quedan en borrador y el comprador las envía con el botón nativo "Enviar por correo".
- El comando se puede correr varias veces: actualiza en lugar de duplicar, y antes de reabastecer cancela solo las RFQ en borrador que dejó una corrida anterior.
- La CLI actual no cambia. Odoo es un complemento opcional: la prueba se sigue corriendo y evaluando sin Docker.

## Capabilities

### New Capabilities
- `carga-odoo`: conexión a Odoo y carga idempotente de proveedores, productos, existencias y reglas de reabastecimiento a partir del Excel ya validado.
- `reabastecimiento-odoo`: generación de RFQ con el reabastecimiento nativo de Odoo, avisos de pedido mínimo y revisión, y conciliación contra los totales de la CLI.

### Modified Capabilities

## Impact

- Código nuevo: subpaquete `resurtido/odoo/`. Usa `xmlrpc.client` de la biblioteca estándar: sin dependencias nuevas en `requirements.txt`.
- Archivos nuevos: `odoo/docker-compose.yml`, una sección "Odoo (opcional)" en el README y supuestos nuevos en `SUPUESTOS.md`.
- Salida nueva: `output/odoo/conciliacion.csv`.
- Requisito solo para esta parte: Docker. La conexión se configura con variables de entorno; ninguna contraseña queda en el código.
- Las pruebas nuevas usan un Odoo simulado: `pytest` sigue corriendo sin Docker.
