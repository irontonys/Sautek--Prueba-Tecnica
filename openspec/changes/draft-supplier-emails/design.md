# Design

## Context

`build_orders` entrega una lista de `SupplierOrder` con proveedor, renglones, total y estado. Los proveedores solo reciben pedidos por correo. Decisiones del autor para esta fase: `.eml` (1a), sin borrador para pedidos que no se envían (2a) y marca de revisión solo en un índice interno (3).

## Goals / Non-Goals

**Goals:**
- Que abrir el borrador y darle "Enviar" sea lo único que le quede al comprador.
- Que el contenido sea determinista para la misma fecha, para poder probarlo y versionarlo.

**Non-Goals:**
- Enviar correos, adjuntar PDFs o leer las respuestas del proveedor (la Parte 1, pregunta 6, describe cómo se haría).
- Plantillas configurables por proveedor.

## Decisions

- **`email.message.EmailMessage` de la biblioteca estándar**, en lugar de armar el texto a mano o de usar una plantilla externa. Codifica bien los acentos y los encabezados en UTF-8 y produce un `.eml` que abre cualquier cliente. No agrega dependencias.
- **Encabezado `X-Unsent: 1` y sin `From`.** Outlook abre así el mensaje como borrador editable y le pone el remitente de la cuenta de quien lo abre. Inventar un remitente sería un dato falso en el archivo.
- **Cuerpo en texto plano con tabla alineada**, no HTML. Se lee igual en cualquier cliente, no se rompe si el proveedor lo reenvía y se prueba con comparaciones de texto simples.
- **La fecha del pedido entra como parámetro** (por omisión, la del día). Las pruebas fijan la fecha y el asunto sale idéntico en cada corrida.
- **Nombres de archivo `P01_distribuidora-truper-norte.eml`**: el ID garantiza que sean únicos y el nombre los hace legibles. Se quitan acentos y símbolos para que funcionen en Windows.
- **Se borran los `.eml` anteriores de `output/correos/` antes de escribir.** Si un proveedor ya no tiene pedido, su borrador viejo no se queda ahí, donde podría enviarse por error. Solo se borran archivos `.eml` de esa carpeta, nunca otra cosa.
- **Módulo `emails.py`** con la construcción del mensaje y la escritura de la carpeta, separado de `report.py`: es una salida distinta, con su propia lógica de texto.

## Risks / Trade-offs

- [Un cliente de correo que no respeta `X-Unsent` abre el `.eml` como mensaje recibido] → el README explica cómo usarlo; en el peor caso se usa "Reenviar", o se copia y pega el cuerpo, que es texto plano.
- [La tabla alineada con espacios se desalinea en clientes con fuente proporcional] → cada renglón trae la etiqueta del dato (código, cantidad, importe), así que se lee aunque no quede alineado.
