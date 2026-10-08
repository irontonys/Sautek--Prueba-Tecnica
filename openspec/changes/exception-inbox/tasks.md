# Tasks

## 1. Modelos y sincronización

- [x] 1.1 Crear `purchase.replenishment.exception` (llave única, grupo, estatus con historial, responsable, conteos, días abierta) y `purchase.replenishment.import` (conteos, actividades) con sus permisos; verificar que el módulo actualiza sin errores
- [x] 1.2 Implementar `register` (crear, actualizar, reabrir, resolver, mantener aceptadas, conteos) y llamarlo desde el asistente, con la línea de conteos en el resumen; verificar con pruebas de Odoo cada transición de estatus
- [x] 1.3 Tipo de actividad "Revisar excepciones", una tarea por importación para quien importa, cierre de la tarea anterior y sin tarea cuando no hay pendientes; verificar con pruebas de Odoo

## 2. Bandeja

- [x] 2.1 Vistas: lista con filtros y agrupaciones (abre en pendientes), formulario con historial, botones Aceptar/Reabrir, menú en Compras y formulario del registro de importación con el botón a la bandeja; verificar con pruebas de Odoo que aceptar y reabrir guardan usuario y fecha
- [x] 2.2 Correr las pruebas de los cuatro módulos juntos y pytest; verificar que pasan

## 3. Verificación

- [x] 3.1 En la base de demostración: importar el Excel del caso y verificar 28 pendientes asignadas al admin con sus grupos, la tarea con el aviso en el buzón del comprador, aceptar una, reimportar y verificar conteos (0 nuevas) y una sola tarea abierta. *En la verificación salió que el aviso de la tarea no tenía destinatario cuando quien importa es el mismo comprador (Odoo no le manda un aviso a su propio autor); se manda a nombre de OdooBot, en este módulo y en el de seguimiento, con prueba de que el aviso llega.*

## 4. Documentación

- [x] 4.1 README y `SUPUESTOS.md`: la bandeja, los estatus, quién la trabaja y cómo se cierran las excepciones
