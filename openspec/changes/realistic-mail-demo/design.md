# Design

## Context

- Hoy Odoo envía a Mailpit (`--smtp mailpit`), que solo muestra correos; la respuesta del proveedor entra con `message_process` desde un comando o el botón de demostración.
- En Odoo 17 la dirección de respuesta de los correos de un documento sin alias propio es el *catchall* del dominio de alias de la compañía (`mail.alias.domain`, nuevo en 17). Si no hay dominio de alias, la respuesta va al autor, es decir, al buzón personal del comprador: Odoo nunca se entera.
- El correo entrante en Odoo lo trae `fetchmail.server` (en Odoo 17, parte de `mail`) con un cron, y lo enruta con `message_process` por `In-Reply-To`/`References`: es la misma entrada que ya prueba el seguimiento.
- Prueba aislada hecha al proponer: GreenMail (`greenmail/standalone`, autenticación apagada) entrega a cualquier dirección y deja entrar a cualquier buzón por IMAP; Roundcube (`roundcube/roundcubemail`) contra GreenMail entra como `ventas@truper-norte.mx`, crea su identidad y envía a `compras@ferretera.test`, que lo recibe. Roundcube necesita `smtp_user`/`smtp_pass` vacíos para no intentar autenticarse en SMTP.

## Goals / Non-Goals

**Goals:**
- Que la demostración recorra el camino real del correo: Odoo → buzón del proveedor → respuesta con adjunto → buzón de compras → Odoo.
- Que la configuración de Odoo sea la misma que se haría en producción, solo cambiando servidores y dominio.

**Non-Goals:**
- Leer precios del archivo de cotización (sigue siendo manual, supuesto 22).
- Contraseñas o TLS en el correo de prueba.
- Quitar el botón de simulación: se queda como atajo.

## Decisions

### 1. GreenMail + Roundcube en lugar de Mailpit
- `greenmail` con `-Dgreenmail.setup.test.all -Dgreenmail.hostname=0.0.0.0 -Dgreenmail.auth.disabled`: SMTP 3025, IMAP 3143, solo dentro de la red de Docker.
- `roundcube` con `ROUNDCUBEMAIL_DEFAULT_HOST=greenmail`, puerto IMAP 3143, SMTP `greenmail:3025`, SQLite, publicado en `8000:80`, y `odoo/roundcube/smtp.php` montado con `smtp_user`/`smtp_pass` vacíos.
- Odoo envía con `--smtp greenmail --smtp-port 3025`.
- *Alternativa:* Mailpit con su servidor POP3 como entrada de Odoo. Se descartó: Mailpit no permite responder, y Odoo se llevaría también sus propios correos salientes del mismo buzón.

### 2. Módulo `sautek_demo_mail` solo con datos
Depende de `mail` (en Odoo 17 el recolector `fetchmail.server` vive ahí, no en un módulo aparte) y `purchase_supply_tracking`. Datos (`noupdate`):
- `mail.alias.domain` `ferretera.test` con catchall `compras`, asignado a la compañía principal, que pasa a llamarse "Ferretera Garza".
- El usuario admin con correo `comprador@ferretera.test`.
- `fetchmail.server` IMAP `greenmail:3143`, usuario `compras@ferretera.test`, sin SSL, sin modelo destino (enruta por encabezados), confirmado (`state='done'`).
- El cron de recolección (`mail.ir_cron_mail_gateway_action`, que Odoo activa solo al crear un servidor confirmado) cada minuto.
- `report.url` = `http://localhost:8069`: para el PDF de la RFQ, wkhtmltopdf pide los estilos a Odoo en `web.base.url` (8070, el puerto publicado), que dentro del contenedor no existe. Se encontró en el recorrido: el PDF salía sin formato. Se fija con `<function model="ir.config_parameter" name="set_param">` y no como registro: el compose vuelve a cargar los datos del módulo en cada arranque, y un registro nuevo chocaba con un parámetro que ya existía en la base (Odoo no arrancó).
- La cola de envío (`mail.ir_cron_mail_scheduler_action`) cada minuto. Los avisos que genera un correo entrante no se envían en el momento: quedan en la cola, que Odoo vacía cada hora. Se encontró en la verificación (con la simulación salían al instante porque se procesaban dentro de una petición).
Lo instala solo el compose del repo; la ferretería configuraría lo mismo con sus servidores reales (README).

### 3. Prueba del correo entrante con adjunto
En `purchase_supply_tracking` se agrega una prueba que envía la RFQ, arma un correo crudo del proveedor con `In-Reply-To` = el `message_id` del envío y un archivo adjunto, y lo pasa por `mail.thread.message_process` sin `thread_id`: debe ubicar la RFQ solo por encabezados, guardar el adjunto y pasar a "Cotización recibida". Es lo que hará el servidor de entrada.

## Risks / Trade-offs

- [El cron revisa cada minuto: la respuesta no aparece al instante] → En la demo se dice; si urge, la RFQ también se puede recargar tras un minuto. El botón de simulación sigue disponible.
- [Si el proveedor contesta a otra dirección o desde una cuenta que no es la suya, Odoo no lo reconoce como del proveedor] → Mismo comportamiento que en producción (supuesto 23); el correo igual queda en la RFQ.
- [Dos contenedores más] → Solo en el entorno opcional de Odoo; la prueba principal sigue sin Docker.

## Migration Plan

Reiniciar el entorno con base limpia (`down -v`, `up -d --build`): instala el módulo de demostración en la base nueva. Revertir: volver al compose con Mailpit y no instalar `sautek_demo_mail`.
