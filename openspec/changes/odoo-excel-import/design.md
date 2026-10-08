# Design

## Context

- `resurtido/odoo/` habla con Odoo solo a través de una interfaz mínima de cliente: `search_read`, `create`, `write`, `unlink`, `call`, `execute`, `xmlid`, más los atributos `uid` y `url` (`client.py`). `sync`, `replenish` y `proveedor` no saben si del otro lado hay XML-RPC o no; las pruebas ya lo aprovechan con `FakeOdooClient`.
- La secuencia completa vive hoy dentro de `resurtido/odoo/cli.py:main`, mezclada con la impresión.
- La imagen `odoo:17.0` trae Python 3.10 y `pip`, pero no pandas ni openpyxl, que usan `loader.py` y `validation.py`. pandas 2.3.3 corre en 3.10 (por eso se eligió en la fase 1).
- Depende del change `purchase-status-tracking` (módulo `purchase_supply_tracking` y estatus `waiting_quote`), que se archiva antes que este.

## Goals / Non-Goals

**Goals:**
- Cero terminal para el usuario de compras: importar, revisar, enviar, aprobar y recibir desde Odoo.
- Un solo motor: las reglas, la carga y las notas son el mismo código para la CLI y para Odoo.

**Non-Goals:**
- Historial de importaciones dentro de Odoo (se decidió un aviso al terminar).
- Importar en segundo plano o por programación (cron): la importación es al dar el botón.
- Cambiar el formato del Excel o las 12 decisiones.

## Decisions

### 1. Adaptador `OrmClient` en lugar de reescribir
El módulo `purchase_excel_replenishment` trae `OrmClient(env)`, que implementa la misma interfaz que `OdooClient` sobre el ORM: `search_read` → `env[model].with_context(ctx).search_read(...)`, `create` → ids, `call` → método sobre `browse(ids)`, `execute` → método de modelo, `xmlid` → `env.ref(...).id`, `uid` → `env.uid`, `url` → `None`: dentro de Odoo la dirección pública la mantiene Odoo (se actualiza cuando el admin entra), así que `set_base_url` no la toca; si la fijara, en una base nueva podría congelar el puerto equivocado. Los many2one del ORM llegan como `(id, nombre)`, que `m2o_id` ya acepta. Con esto `load`, `cancel_previous`, `run_replenishment`, `read_rfqs`, `subscribe_buyer`, `post_notes` y la simulación del proveedor corren igual dentro de Odoo.
- *Alternativa:* copiar la lógica al módulo. Se descartó por decisión del autor: dos versiones de las mismas reglas.

### 2. Una función compartida para la secuencia
`resurtido/odoo/cli.py` gana `run_import(client, result)` que hace carga → cancelación → reabastecimiento → lectura de RFQ → suscripción → notas → conciliación y regresa un resultado (`ImportResult`: `loaded`, `cancelled`, `rfqs`, `minimum_exceptions`, `rows`) más `import_summary_lines(...)` con las líneas del resumen. `main` la usa e imprime lo mismo que hoy; el asistente de Odoo la usa y muestra las mismas líneas. Igual con `proveedor.py`: `reply_to_order(client, order_id)` para una compra concreta, y `reply_as_vendor` la usa tras ubicar la RFQ por `Proveedor_ID`.

### 3. Imagen propia y paquete montado
- `odoo/Dockerfile`: `FROM odoo:17.0`, instala `requirements.txt` del repo con `pip3` como root y regresa al usuario `odoo`.
- `docker-compose`: `build` con contexto en la raíz del repo; monta `../resurtido` en `/mnt/resurtido/resurtido` (solo lectura) y define `PYTHONPATH=/mnt/resurtido`. El código del motor se edita en un solo lugar; reiniciar Odoo basta para tomar cambios.
- *Alternativa:* copiar `resurtido/` dentro de la imagen. Obligaría a reconstruirla con cada cambio del motor.

### 4. Asistente `purchase.excel.replenishment.wizard` (transitorio)
- Campos: `file`/`filename` (el Excel), `state` (`upload`/`done`), `summary` (texto del resumen), `exceptions_file`/`exceptions_filename` (CSV), `rfq_ids` (many2many a `purchase.order`).
- `action_import`: escribe el archivo en un directorio temporal, usa `read_sheet_names`/`check_sheets`/`load_sheets` de la CLI (los mismos mensajes), `validate`, `build_orders` y `run_import(OrmClient(self.env(su=True)), ...)`; escribe el CSV con `write_exceptions` y lo guarda en el campo; pasa a `done` y regresa la misma ventana. `InputError`/`ColumnError` → `UserError` con el mensaje de la CLI, antes de tocar registros.
- Se ejecuta como superusuario (`env(su=True)`; en Odoo 17 el entorno no tiene `sudo()`) porque crea productos, ajustes de inventario, reglas y cambia parámetros, que un usuario de Compras no puede; `env.uid` sigue siendo el de quien importa, así que él queda como seguidor y como autor de las notas.
- Menú en Compras → Orders, solo para `purchase.group_purchase_manager`; acceso al modelo solo para ese grupo.
- Si el motor falla a la mitad, la transacción de Odoo se revierte completa (una sola petición).

### 5. Modo demostración
- `res.config.settings` gana `purchase_demo_mode` (`config_parameter='purchase_excel_replenishment.demo_mode'`) en la pantalla de configuración de Compras.
- `purchase.order` gana `show_demo_reply` (calculado, no guardado): modo demo encendido y `supply_status == 'waiting_quote'`. El botón "Simular respuesta del proveedor" en el encabezado del formulario se muestra con ese campo y llama `action_simulate_vendor_reply`, que corre `reply_to_order(OrmClient(self.env), self.id)`.
- El servidor también verifica el modo demo en el método, no solo en la vista.

### 6. Ajustes pedidos en la revisión
- **Compra en proceso.** `replenish.in_progress_suppliers(client, partner_ids)` regresa los proveedores con compras en `sent`, `to approve` o `purchase` cuya recepción no está completa (`receipt_status != 'full'`). `reconcile` recibe ese conjunto: si hay diferencia y el proveedor está en él, el estatus es "Compra en proceso" en lugar de "No cuadra". El resumen se titula "Comprobación del cálculo" en lugar de "Conciliación con la CLI", que no le dice nada al comprador.
- **Botón en la lista de RFQ.** Se hereda `purchase.purchase_order_kpis_tree` y se agrega al `<header>` un botón `type="action"` hacia el asistente con `display="always"` (visible sin seleccionar registros) y `groups="purchase.group_purchase_manager"`.

### 7. Pruebas
- pytest: `run_import` y `reply_to_order` con `FakeOdooClient`; la salida de la CLI se mantiene (las pruebas actuales la cubren).
- Odoo (`TransactionCase`): el asistente con un Excel pequeño generado con openpyxl (proveedor, producto bajo el mínimo, un producto inactivo), el archivo inválido y la hoja faltante sin cambios en la base, la descarga del CSV, el menú restringido, y el botón de demo encendido/apagado.

## Risks / Trade-offs

- [`docker compose up` ahora construye una imagen y necesita bajar pandas de PyPI] → Solo la primera vez; el README lo dice. Si no hay red, el resto del repo sigue funcionando sin Docker.
- [El superusuario amplía permisos durante la importación] → Solo para administradores de Compras, y solo dentro de la secuencia del motor, que es la misma ya probada.
- [El motor montado desde el disco: si alguien lo cambia, Odoo usa el cambio al reiniciar] → Es lo buscado (una sola fuente); las pruebas de pytest y de Odoo cubren ambos lados.
- [El aviso no deja historial] → Decisión del autor; las RFQ y sus notas sí quedan, y el CSV se descarga en el momento.

## Migration Plan

`docker compose -f odoo/docker-compose.yml up -d --build`: construye la imagen e instala el módulo en la base existente. Revertir: desinstalar el módulo y volver al compose anterior; los comandos de terminal siguen funcionando.
