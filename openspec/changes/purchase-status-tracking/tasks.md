# Tasks

## 1. Entorno

- [x] 1.1 Agregar Mailpit al `odoo/docker-compose.yml`, montar `odoo/addons` y arrancar Odoo con `--smtp mailpit --smtp-port 1025`; verificar que `http://localhost:8025` abre y que la base `sautek` sigue intacta tras reiniciar
- [x] 1.2 Confirmar contra el código de 17.0 los XML ID de las vistas a heredar (formulario, listas de RFQ y de compras, búsqueda) y anotarlos en `design.md`

## 2. Módulo `purchase_supply_tracking`

- [x] 2.1 Crear el esqueleto (`__manifest__.py`, `__init__.py`, `models/`, `views/`, `data/`) e instalarlo en la base; verificar que aparece instalado en `ir.module.module`
- [x] 2.2 Agregar `quote_received_at`, `po_sent_at` y `supply_status` (calculado, guardado, con `tracking`) con la prioridad del design; verificar con una prueba del módulo cada estatus, incluido Cancelado
- [x] 2.3 Implementar la cotización recibida en `_message_post_after_hook` y la actividad "Revisar cotización y aprobar"; verificar con pruebas que un correo del proveedor la dispara y que una nota interna o un correo de otro contacto no
- [x] 2.4 Extender `button_confirm` para cerrar la actividad y `message_post` para marcar `po_sent_at`; verificar con pruebas Aprobada → PO enviada
- [x] 2.5 Verificar con pruebas la recepción parcial y completa (Recibido parcial → Recibido) y que el historial registra cada cambio
- [ ] 2.6 Heredar las vistas (barra de estatus en el formulario, columna con colores, filtros y agrupación); verificar que el módulo se actualiza sin errores y que la barra se ve en una RFQ
- [x] 2.7 Correr las pruebas del módulo en una base de prueba con `--test-tags /purchase_supply_tracking` y verificar que pasan

## 3. Comandos de Python

- [x] 3.1 Suscribir al usuario de la conexión a las RFQ vigentes en `replenish.py` sin asignar `user_id`; verificar con `FakeOdooClient` que queda como seguidor y que `user_id` sigue vacío
- [x] 3.2 Crear `resurtido/odoo/proveedor.py` (`python -m resurtido.odoo.proveedor <Proveedor_ID>`) que arma y entrega el correo del proveedor; verificar con pruebas el correo armado (remitente, `In-Reply-To`, asunto) y el error en español cuando no hay RFQ esperando cotización
- [x] 3.3 Correr `.venv/bin/python -m pytest` y verificar que pasan todas sin Docker
- [x] 3.4 Fijar `web.base.url` = `ODOO_URL` al cargar (los avisos apuntaban a otro Odoo en el 8069); verificar con una prueba y contra la base que los enlaces nuevos usan el 8070

## 4. Verificación contra Odoo real

- [x] 4.1 Reiniciar la base limpia, correr `python -m resurtido.odoo`, enviar desde Odoo la RFQ de P01 y verificar el correo en Mailpit y el estatus "Esperando cotización"
- [x] 4.2 Correr `python -m resurtido.odoo.proveedor P01` y verificar "Cotización recibida", el correo en el historial y la actividad del comprador con su aviso en Mailpit
- [x] 4.3 Confirmar la compra, enviar la PO, validar una recepción parcial y luego la completa; verificar cada estatus y el historial completo en la compra
- [ ] 4.4 Verificar en la lista de compras la columna de estatus, el filtro y la agrupación, y tomar capturas para el PR

## 5. Documentación

- [ ] 5.1 Agregar al README el flujo de seguimiento (estatus, Mailpit, simulación del proveedor, pruebas del módulo) y cómo se conectaría a un correo real; verificar siguiendo los pasos
- [x] 5.2 Agregar a `SUPUESTOS.md` los supuestos nuevos (admin como comprador, factura fuera, precios ajustados a mano, Mailpit) y actualizar el 19
