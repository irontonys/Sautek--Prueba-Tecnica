# Tasks

## 1. Entorno de correo

- [x] 1.1 Cambiar Mailpit por GreenMail y Roundcube en el compose (con `odoo/roundcube/smtp.php`) y Odoo por `--smtp greenmail --smtp-port 3025`; verificar que `http://localhost:8000` abre y que se entra como `ventas@truper-norte.mx`
- [x] 1.2 Crear `sautek_demo_mail` (dominio de alias `ferretera.test` con catchall `compras`, compañía "Ferretera Garza", admin con `comprador@ferretera.test`, servidor IMAP confirmado, cron cada minuto) e instalarlo desde el compose; verificar en la base cada valor

## 2. Pruebas

- [x] 2.1 Agregar a `purchase_supply_tracking` la prueba del correo entrante crudo con adjunto enrutado solo por `In-Reply-To`; verificar que pasa junto con las demás pruebas de los módulos
- [x] 2.2 Verificar que `purchase_supply_tracking` y `purchase_excel_replenishment` siguen instalando y pasando sus pruebas en una base sin `sautek_demo_mail`

## 3. Verificación de punta a punta

- [x] 3.1 Base limpia: importar el Excel, enviar la RFQ de P01 y verificar que llega al buzón del proveedor con `Reply-To` `compras@ferretera.test`
- [x] 3.2 Responderla desde el webmail como el proveedor con un archivo adjunto y verificar que en menos de dos minutos queda en la RFQ con el adjunto, en "Cotización recibida", y que el aviso llega al buzón del comprador con el enlace al 8070

## 4. Documentación

- [x] 4.1 Actualizar el README (webmail en lugar de Mailpit, cómo entrar como proveedor y como comprador, flujo completo, configuración equivalente en producción)
- [x] 4.2 Actualizar `SUPUESTOS.md` (supuesto 24 y el nuevo de la configuración de demostración separada)
