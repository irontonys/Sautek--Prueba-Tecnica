# Design

## Context

- La CLI (`resurtido/cli.py`) ya separa las etapas: `load_sheets` → `validate` → `build_orders` → reportes. `validate` regresa un `ValidationResult` con productos procesables (`Product`, con `revisar` y la existencia ya ajustada a 0 si venía negativa), proveedores (`Supplier`, con `pedido_minimo`) y excepciones. Esa es la entrada natural para Odoo: los datos ya vienen limpios y las decisiones del caso ya están aplicadas.
- En `~/Desktop/odoo-local` hay un Odoo 17 Community con Docker (imagen `odoo:17.0` y `postgres:15`, puerto 8069). Sirve de referencia, pero el entregable no puede depender de una carpeta fuera del repo.
- El revisor debe poder correr la prueba sin Docker. La parte de Odoo es opcional y no puede romper `python -m resurtido` ni `pytest`.

## Goals / Non-Goals

**Goals:**
- Que las cantidades las calcule Odoo (regla de reabastecimiento + ruta Comprar), no el script. El script solo carga datos, dispara y revisa.
- Que la conciliación demuestre que Odoo y la CLI llegan a lo mismo, o que señale dónde no.
- Pruebas automáticas sin Odoo real.

**Non-Goals:**
- Un addon de Odoo con modelos o vistas propias. Todo se hace con modelos estándar vía XML-RPC.
- Enviar correos, confirmar compras o recibir mercancía.
- Localización mexicana (impuestos, CFDI) y multi-almacén.
- Sustituir la CLI.

## Decisions

### 1. XML-RPC con la biblioteca estándar, sin addon
`xmlrpc.client` (`/xmlrpc/2/common` para autenticar y `/xmlrpc/2/object` para `execute_kw`), con `allow_none=True`. Botones como `button_cancel` regresan `None`, y el servidor XML-RPC de Odoo 17 no puede enviarlo: responde con un `Fault` "cannot marshal None" *después* de hacer el cambio. El cliente trata ese `Fault` como respuesta vacía; cualquier otro `Fault` sigue siendo error. Lo encontró la segunda corrida contra el contenedor; el simulador no lo reproducía.
- *Alternativa:* un addon con un wizard para subir el Excel. Se descartó porque obliga a meter pandas dentro del contenedor de Odoo y a duplicar o empaquetar el motor de validación.
- *Alternativa:* OdooRPC o `odoo-client-lib`. Se descartaron porque agregan una dependencia para lo que resuelven 40 líneas.

### 2. Estructura del subpaquete `resurtido/odoo/`
- `client.py`: `OdooClient` envuelve la conexión (`search_read`, `create`, `write`, `call`) y traduce `ConnectionRefusedError`, `OSError` y `xmlrpc.client.Fault` a `OdooError`, con un mensaje en español.
- `sync.py`: carga de proveedores, productos, tarifas, existencias y reglas (`carga-odoo`).
- `replenish.py`: cancela las RFQ anteriores, dispara el reabastecimiento, lee las RFQ y deja las notas (`reabastecimiento-odoo`).
- `reconcile.py`: funciones puras que comparan los `SupplierOrder` de `build_orders` contra los totales de Odoo y escriben `conciliacion.csv`.
- `cli.py` y `__main__.py`: argumentos, variables de entorno y orquestación. Se reusan `read_sheet_names`, `check_sheets` e `InputError` de `resurtido/cli.py` para que los mensajes de entrada sean idénticos.
- Las pruebas usan un `FakeOdooClient` en memoria con la misma interfaz que `OdooClient`. `sync`, `replenish` y `reconcile` reciben el cliente como parámetro.

### 3. Modelo de datos en Odoo
| Excel | Odoo 17 | Llave para actualizar |
|---|---|---|
| Proveedor | `res.partner` (`is_company`, `email`, `ref` = `Proveedor_ID`) | `ref` |
| Producto | `product.template` (`detailed_type='product'`, `default_code`, `name`, `route_ids` = ruta Comprar, `supplier_taxes_id` vacío, UdM Unidades) | `default_code` |
| Costo con proveedor | `product.supplierinfo` (`partner_id`, `product_tmpl_id`, `price`) | producto + proveedor |
| Existencia | `stock.quant` en la ubicación de stock del almacén principal, creado en modo inventario con `inventory_quantity_auto_apply` | producto + ubicación (Odoo reusa el quant) |
| Mínimo, máximo, múltiplo | `stock.warehouse.orderpoint` (`product_min_qty`, `product_max_qty`, `qty_multiple`, `trigger='manual'`) | producto + almacén |

- Todas las cantidades van en Unidades, por la decisión 7a: misma unidad en existencia, mínimo y máximo.
- La ruta Comprar se obtiene por su XML ID `purchase_stock.route_warehouse0_buy`, no por su nombre, que depende del idioma.
- `trigger='manual'` evita que el scheduler nocturno de Odoo genere compras por su cuenta. Solo el comando dispara.
- Existencia por ajuste de inventario: `create` de `stock.quant` con `context={'inventory_mode': True}` e `inventory_quantity_auto_apply` (lo mismo que hace la importación de existencias de Odoo). Si el quant ya existe, Odoo lo reusa y fija el valor absoluto, así que es idempotente; el movimiento queda en el historial. Confirmado en `stock_quant.py` de 17.0 (`create` con `_gather`).
- Las tarifas se crean con la moneda de la compañía ya cambiada a MXN, para que Odoo no convierta precios al armar la RFQ. Si un producto cambia de proveedor, se borra la tarifa anterior: Odoo elige proveedor por tarifa y no debe quedar una vieja.

### 4. Cómo se dispara el reabastecimiento
Se llama `action_replenish` sobre todas las reglas cargadas con `context={'recompute_qty_to_order': True}`. Odoo agrupa por proveedor en una RFQ en borrador y calcula la cantidad: si el pronóstico es estrictamente menor que el mínimo, pide `max(mín, máx) − pronóstico` redondeado hacia arriba al múltiplo (`_compute_qty_to_order` en `stock_orderpoint.py` de 17.0).
- `qty_to_order` es un campo calculado **guardado** que depende del pronóstico, que no se guarda: cambiar la existencia o cancelar RFQ no lo recalcula. Por eso no se filtra por `qty_to_order > 0` desde fuera y se usa el contexto `recompute_qty_to_order`, que `_procure_orderpoint_confirm` atiende recalculando antes de pedir.
- *Alternativa:* `procurement.group.run_scheduler`. Se descartó porque corre todas las reglas de la base, no solo las de la carga.

### 5. Qué RFQ son "nuestras"
Una RFQ es del comando si está en borrador (`state='draft'`), es de un proveedor cargado y todos sus renglones tienen `orderpoint_id`. Las RFQ hechas a mano no tienen `orderpoint_id`, así que nunca se tocan. Antes de reabastecer se cancelan (`button_cancel`) solo las nuestras. No se exige que la regla sea de la carga actual: así también se cancela la RFQ vieja de un producto que dejó de ser procesable.
- *Alternativa:* marcar las RFQ con un texto en `origin` o en `partner_ref`. Se descartó porque Odoo sobrescribe `origin` con el nombre de la regla y `partner_ref` es para el folio del proveedor.

### 6. Notas en el chatter
`message_post` con `message_type='comment'` y `subtype_xmlid='mail.mt_note'`: es nota interna y no notifica al proveedor. El texto de pedido mínimo reusa el formato de la excepción de `build_orders`: total, mínimo y faltante.

### 7. Salidas en `output/odoo/`
`excepciones.csv` (con el mismo escritor de la CLI, incluida la de pedido mínimo calculada contra Odoo) y `conciliacion.csv`. No se tocan las salidas de la CLI en `output/`.

### 8. Conciliación
Total CLI = `SupplierOrder.total` de `build_orders`. Total Odoo = `amount_untaxed` de la RFQ nuestra del proveedor (0 si no hay). Ambos en `Decimal` a centavos; "Cuadra" si `|diferencia| <= 0.01`. Un proveedor que no tiene productos por pedir en ninguno de los dos lados cuadra con 0 = 0.

### 9. Entorno Docker en el repo
`odoo/docker-compose.yml` con `name: sautek-odoo` (volúmenes separados de `odoo-local`), puerto `8070:8069`, y el comando `odoo -d sautek -i purchase_stock --without-demo=all --db-filter=^sautek$`. La base se crea e instala sola en el primer arranque. Valores por omisión del comando: `ODOO_URL=http://localhost:8070`, `ODOO_DB=sautek`, `ODOO_USER=admin`. La contraseña del admin local solo aparece en el README, no en el código.

### 10. Moneda
La compañía de una base nueva arranca en USD. El comando cambia la moneda de la compañía a MXN si aún no tiene asientos contables. Si Odoo lo rechaza, imprime un aviso y sigue: la moneda no cambia ningún total.

## Risks / Trade-offs

- [El cálculo de Odoo difiere del de la CLI en existencias con decimales (kg, m): la CLI sube el faltante al entero antes del múltiplo y Odoo redondea con la precisión de la UdM] → Para eso existe la conciliación: el caso aparece como "No cuadra" con su diferencia, en lugar de ocultarse. Si pasa con los datos reales, se documenta en `SUPUESTOS.md`.
- [El pronóstico de Odoo incluye entradas pendientes y plazos de entrega, y la CLI solo ve la existencia] → En una base limpia, sin otras compras, son iguales. Cancelar nuestras RFQ en borrador antes de reabastecer evita que una corrida anterior cuente como entrada.
- [Nombres de métodos o campos de Odoo 17 que no coincidan con lo esperado (`action_replenish`, `qty_multiple`, `orderpoint_id`)] → La primera tarea de integración los confirma contra el Odoo levantado, antes de escribir la carga completa.
- [El primer arranque del contenedor tarda varios minutos en crear la base] → El README lo advierte, y el error de conexión del comando dice que Odoo no responde en la URL.
- [Odoo junta una compra nueva en una RFQ en borrador del mismo proveedor si esa RFQ no tiene comprador (`_make_po_get_domain` filtra por `user_id = partner.buyer_id`, vacío aquí)] → Una RFQ hecha desde la interfaz lleva al usuario que la creó, así que no se mezcla. Si alguien hace una sin comprador, queda con renglones mixtos: el comando no la cancela (tiene renglones sin regla) y la conciliación la cuenta fuera, lo que aparece como "No cuadra".
- [Las pruebas con `FakeOdooClient` no detectan errores de la API real] → Hay una verificación manual de punta a punta (sección 6 de tasks) con evidencia en el PR.

## Migration Plan

Es aditivo: no hay migración. Para revertir basta con borrar `resurtido/odoo/`, `odoo/` y la sección del README; `docker compose down -v` borra la base.
