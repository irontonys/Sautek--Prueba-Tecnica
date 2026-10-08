# Design

## Context

- El asistente "Importar inventario (Excel)" (`purchase_excel_replenishment`) ya corre `validate` + `run_import` y tiene en memoria `result.exceptions`: objetos `DataException` con `hoja`, `fila_excel`, `codigo`, `tipo`, `detalle`, `valor_original` y la propiedad `decision` (de `DECISIONS`), además de la de pedido mínimo calculada contra Odoo.
- Decisiones del autor: todas las excepciones al comprador (quien importa; en la demo el admin), una tarea por importación, y tres estatus con "Aceptada" para lo revisado que no se corrige.
- Las actividades de Odoo cuelgan de un registro; el asistente es transitorio, así que hace falta un registro persistente por importación.

## Goals / Non-Goals

**Goals:**
- Una lista de pendientes que se cierra sola cuando el dato se corrige en el origen, sin trabajo de mantenimiento.
- Un solo aviso por importación, no uno por excepción.

**Non-Goals:**
- Corregir el catálogo desde la bandeja: los datos se corrigen en el sistema de origen (el que exporta el Excel).
- Asignar a distintos responsables por tipo (todas al comprador, por decisión).
- Alimentar la bandeja desde el comando de terminal.

## Decisions

### 1. Modelos en `purchase_excel_replenishment`
- `purchase.replenishment.exception` (hereda `mail.thread` para notas e historial de estatus): `key` (único), `sheet`, `excel_row`, `code`, `exception_type`, `detail`, `original_value`, `decision`, `group` (selección), `user_id`, `state` (`pending`/`resolved`/`accepted`, con `tracking`), `first_seen`, `last_seen`, `times_seen`, `reopen_count`, `resolved_at`, `accepted_by`, `accepted_at`, `days_open` (calculado, no guardado: desde `first_seen` mientras no esté resuelta), `last_import_id`.
- `purchase.replenishment.import` (hereda `mail.thread` y `mail.activity.mixin`): `user_id`, `filename`, `date`, `new_count`, `open_count`, `resolved_count`. Su nombre es "Importación del {fecha}". Sin vistas propias más allá del formulario mínimo que abre la tarea; la tarea lleva el botón a la bandeja.
- *Alternativa:* colgar la tarea del usuario o de una excepción cualquiera. Se descartó: Odoo exige un registro y colgarla de una excepción arbitraria confunde.

### 2. Llave de identidad
`key = "{tipo}|{hoja}|{código}"`, o `"{tipo}|{hoja}|fila {n}"` cuando el código está vacío. La fila no entra en la llave cuando hay código: si el Excel se reordena, el problema sigue siendo el mismo. Restricción SQL de unicidad sobre `key`.

### 3. Grupo a partir del tipo
- "Compra": `PEDIDO_MINIMO_NO_ALCANZADO`.
- "No se procesó": cualquier tipo cuya decisión excluye (`DataException.excludes`), incluidos los "Pendiente de decisión".
- "Advertencia": `EXISTENCIA_NEGATIVA` y `UNIDAD_INCONSISTENTE` (se procesan, pero alguien debe revisarlas).
- "Se corrigió": el resto de los que no excluyen (`EXISTENCIA_TEXTO`, `CODIGO_FORMATO`, `CODIGO_REPETIDO`).
Se calcula en el módulo con las constantes de `resurtido.validation`; un tipo nuevo cae en "No se procesó" o "Se corrigió" según su decisión, sin tocar el módulo.

### 4. Sincronización al importar
`purchase.replenishment.import.register(user, filename, exceptions)`, llamado por el asistente después de `run_import` y dentro de la misma transacción:
1. Crea el registro de importación.
2. Lee todas las excepciones existentes por `key`.
3. Por cada excepción reportada: si no existe → crea `pending` (nueva); si está `resolved` → `pending`, `reopen_count += 1`, responsable = quien importa; si está `pending`/`accepted` → actualiza fila, detalle, valor, `last_seen`, `times_seen += 1`, `last_import_id`.
4. Las `pending`/`accepted` que no se reportaron → `resolved`, `resolved_at`.
5. Guarda los conteos (nuevas, pendientes después de sincronizar, resueltas en esta importación).
6. Marca como hecha la tarea abierta de la importación anterior y, si hay pendientes, crea la nueva con `activity_schedule` (tipo propio "Revisar excepciones", resumen con los conteos) para quien importa.
Se escribe con superusuario, como el resto de la importación (`env(su=True)`). El aviso de la tarea se manda con `action_notify` a nombre de OdooBot: quien importa es el mismo comprador, y Odoo no avisa a quien se asigna una tarea a sí mismo ni le manda un aviso a su propio autor.

### 5. Vistas
- Bandeja: lista con insignias de grupo y estatus, filtro predeterminado "Pendientes", filtros por estatus y grupo, agrupación por grupo, tipo y estatus; botones de lista "Aceptar" y "Reabrir" sobre la selección.
- Formulario: datos de la excepción, botones "Aceptar"/"Reabrir", historial (chatter) para notas del comprador.
- Menú Compras → Orders → "Excepciones de inventario" para usuarios de Compras; la importación y la escritura automática siguen siendo de administradores de Compras.
- El formulario del registro de importación muestra los conteos y el botón "Ver excepciones pendientes".

### 6. Pruebas
Odoo (`TransactionCase`) con Excel pequeños generados con openpyxl: primera importación crea pendientes con responsable y grupo; segunda no duplica y cuenta veces; dato corregido → resuelta; vuelve → reabierta; aceptada se mantiene; una sola tarea abierta tras dos importaciones; sin pendientes no hay tarea. Más la verificación con el Excel del caso (28 pendientes) contra la base de demostración.

## Risks / Trade-offs

- [Cambiar el texto de un tipo de excepción cambia la llave y duplica pendientes] → Los tipos son constantes en `validation.py`; cambiar uno es un cambio de código consciente. Las viejas se resolverían en la siguiente importación.
- [El pedido mínimo cambia de detalle cada día (montos)] → La llave no incluye el detalle; se actualiza el texto en la misma excepción.
- [Se guarda un historial de importaciones, que se había decidido no tener] → Se limita a fecha, usuario, archivo y conteos, lo mínimo para la tarea.

## Migration Plan

Actualizar el módulo (`-u purchase_excel_replenishment`). La bandeja empieza vacía y se llena en la siguiente importación.
