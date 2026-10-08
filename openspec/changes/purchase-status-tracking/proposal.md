# Proposal

## Why

Con la fase anterior, Odoo deja las RFQ listas, pero en cuanto el comprador las envía el seguimiento se pierde: la cotización del proveedor llega al correo de alguien, la aprobación queda en una conversación y nadie ve de un vistazo en qué va cada compra. El comprador necesita saber, por pedido, si ya contestó el proveedor, si ya se aprobó, si ya salió la orden de compra y si ya llegó la mercancía, y que cada cambio quede registrado con su fecha.

## What Changes

- Un módulo de Odoo propio dentro del repo (`odoo/addons/purchase_supply_tracking`) que agrega a cada compra un **estatus de seguimiento** que se mueve solo:
  1. **Pedido preparado**: RFQ en borrador.
  2. **Esperando cotización**: RFQ enviada al proveedor.
  3. **Cotización recibida**: llegó un correo del proveedor en respuesta a la RFQ.
  4. **Aprobada**: el comprador confirmó la compra.
  5. **PO enviada**: la orden de compra confirmada se envió al proveedor.
  6. **Recibido parcial**: llegó parte de la mercancía.
  7. **Recibido**: llegó todo.
  Más **Cancelado**, fuera del flujo. La factura del proveedor queda fuera de esta fase.
- Cada cambio de estatus queda en el historial de la compra con fecha y usuario. El estatus se ve como barra en la compra y como columna, filtro y agrupación en la lista.
- Cuando llega la cotización del proveedor, se le asigna al comprador una actividad "Revisar cotización y aprobar"; el aviso le llega por correo con el enlace a la compra, y aprueba con el botón nativo de confirmar.
- Un buzón de pruebas local (Mailpit) en el `docker-compose`: Odoo "envía" ahí los correos y se ven en el navegador; nada sale a internet.
- Un comando, `python -m resurtido.odoo.proveedor <Proveedor_ID>`, que simula la respuesta del proveedor: mete en Odoo un correo de su dirección contestando a la RFQ enviada, por la misma entrada que usa Odoo para el correo real.
- El comando de carga (`python -m resurtido.odoo`) agrega al usuario de la conexión (el comprador) como seguidor de las RFQ que genera, para que le lleguen los avisos.

## Capabilities

### New Capabilities
- `rastreo-compras`: estatus de seguimiento de cada compra en Odoo, desde la RFQ hasta la recepción, con su historial, la actividad de aprobación y la simulación de la respuesta del proveedor.

### Modified Capabilities
- `reabastecimiento-odoo`: el comando suscribe al comprador a las RFQ que genera.

## Impact

- Código nuevo: `odoo/addons/purchase_supply_tracking/` (modelo, vistas, pruebas de Odoo) y `resurtido/odoo/proveedor.py`.
- `odoo/docker-compose.yml`: monta los addons, instala el módulo y agrega Mailpit (puertos 8025 para ver correos, SMTP interno). Para aplicar el cambio la base de Odoo se actualiza al reiniciar el contenedor.
- `resurtido/odoo/replenish.py`: suscripción del comprador.
- README y `SUPUESTOS.md`: flujo de seguimiento y cómo se conectaría a un correo real.
- Sin dependencias nuevas de Python.
