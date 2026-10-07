# Tasks

## 1. Borradores

- [ ] 1.1 Crear `resurtido/emails.py` con la construcción del mensaje (destinatario, asunto con fecha, `X-Unsent: 1`, cuerpo con productos, total y petición de confirmación); verificar con pytest los escenarios de encabezados y contenido
- [ ] 1.2 Escribir la carpeta `correos/` (borrar los `.eml` viejos, un archivo por pedido que se envía, nombre `ID_nombre.eml`) y el `indice.csv` con la columna de revisión; verificar con pytest los escenarios de borradores viejos, segueta marcada y pedido que no se envía

## 2. Integración

- [ ] 2.1 Conectar los borradores al punto de entrada y agregarlos al resumen en consola; verificar con `python -m resurtido` que se generan 6 borradores y que el `.eml` de P01 abre en el cliente de correo
- [ ] 2.2 Prueba de regresión sobre el Excel real: 6 borradores, sin P05 ni P08, y totales iguales a `pedidos.xlsx`; verificar con pytest

## 3. Documentación y entregables

- [ ] 3.1 Generar y versionar `output/correos/`; actualizar el README (cómo abrir los borradores) y `SUPUESTOS.md` (sin remitente, la fecha del pedido es la de la corrida); verificar leyendo un `.eml` generado
