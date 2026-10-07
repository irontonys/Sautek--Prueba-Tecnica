# Proposal

## Why

La prueba pide "para cada proveedor, deja un borrador del correo listo para mandar (no lo envíes)". Hoy el comprador redacta un correo por proveedor a mano. Con los pedidos ya calculados, el programa puede dejar cada correo armado, de modo que al comprador solo le quede revisarlo y darle "Enviar".

## What Changes

- Un borrador `.eml` por cada pedido con estado "Se envía", en `output/correos/`. Se abre con doble clic en Outlook o Apple Mail, ya con destinatario, asunto y cuerpo, como borrador sin enviar.
- El cuerpo trae un saludo, la tabla de productos (código, descripción, cantidad, costo unitario e importe), el total y la petición de confirmar cantidades y fecha de entrega.
- Los pedidos "No se envía" (pedido mínimo no alcanzado, decisión 12b) no generan borrador.
- Un índice interno `output/correos/indice.csv`, con un renglón por pedido: proveedor, estado, archivo del borrador, número de productos, total y "Revisar antes de enviar" con los códigos marcados (existencias negativas). Esa marca es interna y nunca aparece en el correo al proveedor.
- El programa nunca envía correos: no abre conexiones ni usa servidores de correo.

## Capabilities

### New Capabilities
- `borradores-correo`: generación de un borrador de correo por proveedor a partir de los pedidos que se envían, más el índice interno de revisión.

### Modified Capabilities

## Impact

- Código nuevo: módulo de borradores dentro de `resurtido/`, que usa la biblioteca estándar `email`.
- Salida nueva: `output/correos/` con los `.eml` y el índice, versionados como entregables.
- Sin dependencias nuevas.
