# Proposal

## Why

En la vida real el proveedor nunca abre Odoo: recibe la RFQ en su correo, le da Responder y adjunta su cotización. Con Mailpit eso no se puede mostrar, porque Mailpit solo deja ver correos (no responder) y Odoo no puede leer de él; la respuesta del proveedor se simula con un botón dentro de Odoo. Para que la demostración pruebe el camino real (y la configuración de correo que necesitaría la ferretería en producción), el proveedor tiene que poder contestar desde un buzón y Odoo tiene que recoger esa respuesta solo.

## What Changes

- El entorno de Odoo del repo cambia Mailpit por un **servidor de correo de prueba** (GreenMail) y un **webmail** (Roundcube, en `http://localhost:8000`). Acepta cualquier dirección y no entrega nada a internet.
- En el webmail se entra como cualquier dirección del caso, sin contraseña real: como el proveedor (`ventas@truper-norte.mx`) para leer la RFQ y **responderla con su cotización adjunta** (PDF, Excel o lo que mande), o como el comprador para ver sus avisos.
- Odoo queda configurado como lo estaría en producción: correo de salida por ese servidor, un **buzón de compras** (`compras@ferretera.test`) al que apuntan las respuestas de los proveedores, y un **servidor de entrada** que Odoo revisa cada minuto. La respuesta del proveedor entra sola a su RFQ, con el archivo en el historial, y el estatus pasa a "Cotización recibida".
- El comprador (el admin) recibe sus avisos en `comprador@ferretera.test` y la compañía se llama "Ferretera Garza" en los correos.
- Esa configuración vive en un módulo de demostración aparte (`sautek_demo_mail`), para no mezclarla con los módulos que irían a producción.
- El botón "Simular respuesta del proveedor" se queda como atajo para cuando no se quiere usar el webmail.

## Capabilities

### New Capabilities
- `correo-demo`: entorno de correo de prueba con webmail donde el proveedor responde la RFQ con su cotización adjunta, y la configuración de Odoo (alias de compras, servidor de entrada) que la recoge sola.

### Modified Capabilities

## Impact

- `odoo/docker-compose.yml`: sale Mailpit, entran GreenMail y Roundcube (más un archivo de configuración de Roundcube en `odoo/roundcube/`); Odoo envía por GreenMail.
- Código nuevo: módulo `odoo/addons/sautek_demo_mail` (solo datos de configuración del entorno de demostración) y una prueba nueva en `purchase_supply_tracking` con un correo entrante real con adjunto.
- README y `SUPUESTOS.md`: el buzón de pruebas pasa a ser el webmail; se documenta la configuración equivalente para producción.
- Odoo se reinicia con base limpia para tomar la configuración.
