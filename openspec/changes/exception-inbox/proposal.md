# Proposal

## Why

Cada importación entrega las excepciones como un CSV para descargar. Sirve para ver qué venía mal, pero no lleva control: nadie sabe cuáles ya se atendieron, cuáles llevan semanas abiertas ni a quién le tocan, y como la importación es diaria, las mismas excepciones vuelven a salir todos los días hasta que alguien corrige el dato en el sistema de origen. El comprador necesita una lista de pendientes dentro de Odoo que se mantenga sola.

## What Changes

- **Bandeja de excepciones** en Compras → Orders → "Excepciones de inventario": cada excepción de la importación es un pendiente con su hoja, fila, código, tipo, detalle, valor original, decisión, un grupo para leerla rápido (Se corrigió, Advertencia, No se procesó, Compra), el responsable, cuántas veces ha salido y cuántos días lleva abierta.
- **Todas se asignan al comprador**: el usuario que hace la importación (en la demostración, el admin).
- **Estatus que se mantiene solo** entre importaciones:
  - **Pendiente**: apareció y nadie la ha cerrado.
  - **Resuelta**: una importación ya no la reportó (se corrigió el dato en el origen). Si vuelve a aparecer, se reabre como Pendiente.
  - **Aceptada**: el comprador la revisó y no hay que corregir nada (por ejemplo, confirmó la unidad). Aunque siga apareciendo, no vuelve a Pendiente.
  - Una misma excepción se reconoce entre importaciones por su tipo, su hoja y su código (o su fila cuando no hay código): no se duplica.
- **Un aviso por importación**: cada importación le deja al comprador **una** tarea "Revisar excepciones" con cuántas son nuevas, cuántas siguen abiertas y cuántas se resolvieron, y el enlace a la bandeja. La tarea de la importación anterior se cierra sola.
- Para colgar esa tarea, cada importación deja un **registro mínimo** (fecha, quién importó, archivo y los conteos). Es un historial de importaciones pequeño, necesario para la tarea; antes se había decidido no guardar historial, así que se limita a eso.
- El resumen de la importación agrega una línea con los conteos de la bandeja. El CSV para descargar se queda.

## Capabilities

### New Capabilities
- `bandeja-excepciones`: pendientes de excepciones de inventario en Odoo, asignados al comprador, con estatus que se actualiza en cada importación y un aviso por importación.

### Modified Capabilities

## Impact

- Código nuevo en el módulo `purchase_excel_replenishment`: modelos de excepción y de registro de importación, la sincronización al importar, vistas (bandeja, formulario con historial, menú), tipo de actividad y pruebas de Odoo.
- `resurtido/validation.py` no cambia; el grupo de cada tipo se define en el módulo a partir de las decisiones (`DECISIONS`).
- El comando de terminal no alimenta la bandeja (es el camino técnico); la bandeja se llena desde la importación en Odoo.
- README y `SUPUESTOS.md`: cómo se trabaja la bandeja y quién responde por qué.
