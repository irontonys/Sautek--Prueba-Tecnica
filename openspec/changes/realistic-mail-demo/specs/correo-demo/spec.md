# Spec Delta

## Purpose

Da al entorno de demostración un correo de prueba completo, con webmail, para que el proveedor conteste la RFQ desde un buzón con su cotización adjunta y Odoo la recoja sola, como pasaría en producción, sin que ningún correo salga a internet.

## ADDED Requirements

### Requirement: Webmail de prueba
El entorno de Odoo del repositorio SHALL incluir un servidor de correo de prueba y un webmail en `http://localhost:8000`. En el webmail MUST poderse entrar con cualquier dirección de correo, sin contraseña real, para leer los correos que recibió esa dirección y enviar correos. Ningún correo MUST salir a internet.

#### Scenario: El proveedor lee la RFQ
- **WHEN** el comprador envía desde Odoo la RFQ de Distribuidora Truper Norte
- **THEN** al entrar al webmail como `ventas@truper-norte.mx` se ve el correo con la RFQ en PDF

### Requirement: Respuesta del proveedor por correo
Los correos de RFQ que envía Odoo SHALL llevar como dirección de respuesta el buzón de compras (`compras@ferretera.test`). Odoo MUST revisar ese buzón al menos cada minuto y meter cada respuesta en la RFQ a la que contesta, con sus archivos adjuntos en el historial, sin intervención del usuario.

#### Scenario: El proveedor responde con su cotización adjunta
- **WHEN** desde el webmail, como `ventas@truper-norte.mx`, se responde el correo de la RFQ adjuntando un archivo de cotización
- **THEN** en menos de dos minutos la respuesta aparece en el historial de esa RFQ en Odoo, con el archivo adjunto
- **AND** el estatus de la RFQ pasa a "Cotización recibida"
- **AND** el comprador recibe el aviso "Revisar cotización y aprobar"

### Requirement: Buzón del comprador
El usuario comprador del entorno de demostración SHALL tener el correo `comprador@ferretera.test`, y los avisos de Odoo para él MUST llegar a ese buzón del webmail. Los correos de Odoo SHALL salir a nombre de la compañía "Ferretera Garza".

#### Scenario: Aviso en el buzón del comprador
- **WHEN** una RFQ pasa a "Cotización recibida"
- **THEN** al entrar al webmail como `comprador@ferretera.test` se ve el aviso con el enlace para abrir la compra

### Requirement: Configuración de demostración separada
La configuración del correo de prueba (servidores, buzón de compras, correo del comprador, nombre de la compañía) SHALL vivir en un módulo de demostración propio, instalado solo por el entorno del repositorio. Los módulos de seguimiento e importación MUST NOT depender de él.

#### Scenario: Módulos de producción sin la demostración
- **WHEN** se instalan `purchase_supply_tracking` y `purchase_excel_replenishment` en una base sin el módulo de demostración
- **THEN** se instalan y funcionan sin servidores de correo de prueba configurados
