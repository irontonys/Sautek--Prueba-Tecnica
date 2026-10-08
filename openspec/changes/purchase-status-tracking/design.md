# Design

## Context

- La fase anterior (`carga-odoo`, `reabastecimiento-odoo`) deja RFQ en borrador generadas por reglas de reabastecimiento, sin comprador asignado (supuesto 19) y sin enviar.
- Odoo 17 ya tiene casi todo el ciclo, pero repartido: `purchase.order.state` (`draft`, `sent`, `to approve`, `purchase`, `done`, `cancel`) y, con `purchase_stock`, `receipt_status` (`pending`, `partial`, `full`). Lo que no existe es la cotización recibida ni la orden de compra enviada: enviar una RFQ y enviar una PO usan el mismo `action_rfq_send` con `mark_rfq_as_sent`, y `message_post` solo lo aprovecha para pasar `draft` → `sent` (`purchase/models/purchase_order.py` de 17.0).
- El correo entrante de Odoo entra por `mail.thread.message_process`, que ubica la compra por los encabezados `In-Reply-To`/`References` (o por un `thread_id` explícito) y publica el correo con `message_type='email'` y como autor el contacto cuyo correo coincide con el remitente. Es lo mismo que usa el `mailgate` de Odoo por XML-RPC.
- Sin Studio (Enterprise), agregar un campo y una barra de estatus requiere un módulo.

## Goals / Non-Goals

**Goals:**
- Un estatus único, calculado y con historial, que el comprador vea en la compra y en la lista.
- Que cada paso lo dispare algo que ya pasa en Odoo (enviar, recibir correo, confirmar, recibir mercancía), sin botones nuevos.
- Una demo completa sin que salga un solo correo a internet.

**Non-Goals:**
- Factura del proveedor (fuera por decisión de esta fase).
- Configurar un servidor de correo real (IMAP/SMTP): se documenta cómo, no se hace.
- Leer precios del correo del proveedor y cambiar la RFQ sola: el comprador ajusta precios a mano antes de aprobar.
- Flujo de doble aprobación de Odoo (`to approve`): se trata como "Cotización recibida" si llegó cotización, o el estatus previo si no.

## Decisions

### 1. Módulo `purchase_supply_tracking` en `odoo/addons/`
Depende de `purchase_stock` y `mail`. Agrega a `purchase.order`:
- `quote_received_at` y `po_sent_at` (Datetime, solo lectura): los dos eventos que Odoo no guarda.
- `supply_status` (Selection, calculado y guardado, `tracking=True`): depende de `state`, `receipt_status`, `quote_received_at` y `po_sent_at`. Al ser guardado con `tracking`, cada cambio queda en el chatter con fecha y usuario sin código extra.

Valores (clave técnica → etiqueta): `prepared` Pedido preparado, `waiting_quote` Esperando cotización, `quote_received` Cotización recibida, `approved` Aprobada, `po_sent` PO enviada, `partial` Recibido parcial, `received` Recibido, `cancelled` Cancelado. Prioridad: `cancel` → `received` (`receipt_status='full'`) → `partial` → `po_sent` (confirmada con `po_sent_at`) → `approved` (`state` en `purchase`/`done`) → `quote_received` → `waiting_quote` (`state` en `sent`/`to approve`) → `prepared`.
- *Alternativa:* reutilizar `state` agregando valores. Se descartó: `state` lo usan reglas internas de Odoo (reabastecimiento, recepciones, facturación) y meter valores nuevos rompe esas comparaciones.

### 2. Cotización recibida: `_message_post_after_hook`
En `purchase.order._message_post_after_hook(message, msg_vals)`: si el mensaje es `email`, su autor pertenece a la misma empresa que el proveedor (`commercial_partner_id`) y la compra está en `draft`/`sent`/`to approve`, se escribe `quote_received_at` (si aún no tiene) y se crea la actividad. Se usa el hook posterior y no `message_post` porque ahí el autor ya está resuelto desde el remitente.
- Un correo del proveedor que llega después de confirmar no cambia nada.

### 3. PO enviada: el mismo contexto que ya usa Odoo
Se extiende `purchase.order.message_post`: si el contexto trae `mark_rfq_as_sent` y la compra está en `purchase`/`done`, se escribe `po_sent_at`. Es el mismo mecanismo con el que Odoo marca la RFQ como enviada, aplicado a la PO.

### 4. Actividad de aprobación
Tipo de actividad propio en datos del módulo (`mail_act_review_quote`, "Revisar cotización y aprobar"). Se asigna a `user_id` de la compra; si no tiene, a los usuarios internos que la siguen (el comprador, por la suscripción de la decisión 6); si no hay ninguno, no se crea. `button_confirm` se extiende para cerrar esa actividad con `activity_feedback`. Odoo solo avisa por correo de una actividad si quien la asigna no es el asignado (`mail_activity.py`, `create`); como el correo del proveedor puede procesarse con la sesión del propio comprador (así pasa con la simulación), la actividad se crea con `mail_activity_quick_update` y se avisa siempre con `action_notify`. La notificación por correo de la actividad es la que lleva el enlace "ver compra" con el que el comprador entra a aprobar.

### 5. Vistas
Se heredan por XML ID, confirmados contra `purchase/views/purchase_views.xml` de 17.0: `purchase_order_form`, `purchase_order_kpis_tree` (lista de RFQ), `purchase_order_view_tree` (lista de compras), `view_purchase_order_filter` y `purchase_order_view_search`. En el formulario, la barra de estatus nativa del encabezado se oculta y se pone `supply_status` con `widget="statusbar"` (sin "Cancelado" visible salvo que aplique); en las listas de RFQ y de compras, columna con `widget="badge"` y colores; en la búsqueda, un filtro por estatus clave y agrupación por estatus.

### 6. Comprador como seguidor, no como responsable
El comando de carga llama `message_subscribe(partner_ids=[partner del ODOO_USER])` sobre las RFQ vigentes. No se usa `user_id`: Odoo junta compras nuevas en RFQ en borrador cuyo `user_id` coincide con el comprador del proveedor, y asignarlo rompería el supuesto 19.

### 7. Mailpit y simulación del proveedor
- `docker-compose`: servicio `mailpit` (`axllent/mailpit`), interfaz en `localhost:8025`, SMTP en `mailpit:1025` solo dentro de la red de Docker. Odoo arranca con `--smtp mailpit --smtp-port 1025`; sin servidor de salida configurado en la base, Odoo usa esos parámetros.
- `python -m resurtido.odoo.proveedor P01`: busca la RFQ del proveedor en `waiting_quote`, toma el `message_id` del último correo enviado en ella, arma un correo con `email.message` (remitente = correo del proveedor, `In-Reply-To`/`References` = ese id, asunto "Re: …", cuerpo con la confirmación de la cotización) y lo entrega con `mail.thread.message_process('purchase.order', raw, thread_id=id)`. El `thread_id` hace la entrega determinista aunque los encabezados no casen.
- *Alternativa:* GreenMail con IMAP y el recolector de correo de Odoo. Más realista pero agrega un servicio y una configuración de servidor entrante por una diferencia que no cambia el comportamiento que se prueba.

### 8. Pruebas
- Del módulo: `TransactionCase` dentro de Odoo (`odoo/addons/purchase_supply_tracking/tests/`), corridas en una base de prueba con `docker compose run --rm web odoo -d sautek_test -i purchase_supply_tracking --test-tags /purchase_supply_tracking --stop-after-init`.
- De Python: el `FakeOdooClient` aprende `message_subscribe` y lo necesario para `proveedor.py`; `pytest` sigue sin Docker.

## Risks / Trade-offs

- [Actualizar la base con el módulo nuevo exige reiniciar Odoo con `-i`/`-u`] → El compose instala el módulo al arrancar; el README da el comando de actualización.
- [Sin seguidores internos ni comprador, la actividad no se asigna] → El comando de carga suscribe al comprador; una RFQ hecha a mano tiene comprador.
- [`message_process` falla si el correo no trae `Message-Id` o el remitente no existe como contacto] → El comando genera `Message-Id` y usa el correo del proveedor cargado; si el contacto no tiene correo, lo dice y sale.
- [Los enlaces de los avisos ("View Purchase Order") apuntaban al puerto 8069, donde corría otro Odoo, porque una base nueva solo corrige `web.base.url` cuando el admin entra por el navegador] → Encontrado en la verificación: el comando de carga fija `web.base.url` = `ODOO_URL` y la congela (`web.base.url.freeze`).
- [Un correo de un empleado del proveedor con otra dirección no se reconoce como del proveedor si no existe como contacto] → Documentado: en producción se dan de alta los contactos del proveedor bajo su empresa.

## Migration Plan

Aditivo. En la base existente: reiniciar con el compose nuevo (instala el módulo; el estatus se calcula para las compras que ya existen). Revertir: desinstalar el módulo desde Apps y volver al compose anterior.
