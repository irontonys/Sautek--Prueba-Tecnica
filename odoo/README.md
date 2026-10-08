# Odoo 17: el resurtido como extra

El mismo Excel se puede llevar a un Odoo 17 local. Ahí las compras ya no las calcula el programa: las calcula el reabastecimiento nativo de Odoo. Esta parte es opcional y necesita [Docker](https://www.docker.com/products/docker-desktop/); el programa principal y las pruebas no dependen de ella.

Levanta Odoo desde la raíz del repositorio:

```bash
docker compose -f odoo/docker-compose.yml up -d --build
```

La primera vez construye la imagen de Odoo con las librerías del programa (necesita internet para bajarlas), crea la base `sautek` e instala Compras, Inventario y los cuatro módulos del repo (`odoo/addons/`); tarda unos minutos. Está lista cuando `http://localhost:8070` muestra el inicio de sesión (usuario `admin`, contraseña `admin`; es una base local de prueba). Las siguientes veces basta `docker compose -f odoo/docker-compose.yml up -d`.

## Desde Odoo, sin terminal

1. Entra a `http://localhost:8070` y ve a **Purchase → Orders → Importar inventario (Excel)** (solo lo ven los administradores de Compras).
2. Elige el Excel de inventario y da **Importar**. Odoo corre por dentro el mismo programa: valida con las mismas reglas y decisiones, carga lo procesable (proveedores, productos con su costo, existencias y una regla de reabastecimiento por producto con su mínimo, máximo y múltiplo de empaque) y dispara el reabastecimiento de Odoo.
3. La ventana muestra el resumen (renglones leídos, excepciones por tipo, RFQ generadas, proveedores que no llegan a su mínimo y la comprobación contra el cálculo del programa), el botón para descargar **excepciones.csv** y **Ver RFQ**.
4. Las RFQ quedan en borrador, una por proveedor, en **Purchase → Orders → Requests for Quotation** (la base arranca en inglés). La del proveedor que no llega a su pedido mínimo trae la nota "No enviar"; las que tienen productos a revisar (existencias negativas), otra nota con sus códigos. Nada se confirma ni se envía solo.

**Bandeja de excepciones.** Cada importación también deja sus excepciones en **Purchase → Orders → Excepciones de inventario**, como pendientes del comprador (quien importa). Cada una dice qué venía mal, qué se decidió y en qué grupo cae: *Se corrigió*, *Advertencia* (se procesó pero hay que revisarla, como una existencia negativa), *No se procesó* (el producto no entró al pedido) o *Compra* (pedido mínimo no alcanzado). El estatus se mantiene solo: *Pendiente* al aparecer; *Resuelta* cuando una importación ya no la reporta porque se corrigió el dato en el sistema de origen (si vuelve, se reabre); y *Aceptada* cuando el comprador la revisó y no hay nada que corregir. La misma excepción no se duplica entre importaciones: lleva la cuenta de cuántas veces ha salido y cuántos días lleva abierta. Cada importación le deja al comprador una sola tarea, "Revisar excepciones: N nuevas, M abiertas, K resueltas", con el aviso en su correo; la de la importación anterior se cierra sola.

Si el archivo no es un Excel o le falta una hoja o columna, la ventana lo dice y no cambia nada. Se puede importar varias veces: actualiza en vez de duplicar y cancela solo las RFQ en borrador que dejó la importación anterior.

## Desde la terminal (alternativa técnica)

El mismo proceso, para desarrollo y pruebas:

```bash
# macOS / Linux
ODOO_PASSWORD=admin python -m resurtido.odoo

# Windows (PowerShell)
$env:ODOO_PASSWORD = "admin"; python -m resurtido.odoo
```

`ODOO_URL` (`http://localhost:8070`), `ODOO_DB` (`sautek`) y `ODOO_USER` (`admin`) se pueden cambiar con variables del mismo nombre; acepta `--input` y `--output` igual que el programa principal. Además de lo que hace el asistente, escribe:

| Archivo | Contenido |
|---|---|
| `output/odoo/conciliacion.csv` | Un renglón por proveedor: RFQ en Odoo, total del programa, total de Odoo, diferencia y si cuadra. |
| `output/odoo/excepciones.csv` | El mismo reporte de excepciones, con el pedido mínimo calculado sobre las RFQ de Odoo. |

## Seguimiento de compras

El módulo `odoo/addons/purchase_supply_tracking` (se instala solo al levantar Odoo) le da a cada compra un estatus de seguimiento que se mueve con lo que pasa en Odoo:

| Estatus | Qué lo mueve |
|---|---|
| Pedido preparado | Odoo generó la RFQ |
| Esperando cotización | El comprador la envió con "Send by Email" |
| Cotización recibida | Llegó un correo del proveedor contestando la RFQ; el comprador recibe la actividad "Revisar cotización y aprobar" con el aviso por correo |
| Aprobada | El comprador la confirmó ("Confirm Order"); la actividad se cierra sola |
| PO enviada | La orden de compra confirmada se envió al proveedor |
| Recibido parcial / Recibido | Almacén validó la recepción de una parte o de todo |
| Cancelado | La compra se canceló |

Se ve como barra en cada compra y como columna en las listas de **Purchase**, con filtros ("Esperando cotización", "Cotización por aprobar", "PO enviada, sin recibir completo") y agrupación por **Seguimiento**. Cada cambio queda en el historial de la compra con fecha y usuario. Quien importa el Excel (o el usuario de la conexión, desde la terminal) queda como seguidor de las RFQ, para que le lleguen los avisos.

**Correo de prueba con webmail.** El entorno trae un servidor de correo de prueba y un webmail en `http://localhost:8000`. Ahí se entra con **cualquier dirección del caso y cualquier contraseña**; ningún correo sale a internet:

| Entra como | Para qué |
|---|---|
| `ventas@truper-norte.mx` (o el correo de cualquier proveedor del Excel) | Ver la RFQ que le mandó Odoo, con su PDF, y **responderla adjuntando la cotización** |
| `comprador@ferretera.test` | Ver los avisos de Odoo: la respuesta del proveedor y "Revisar cotización y aprobar", con el enlace a la compra |

Odoo está configurado como lo estaría en producción: las RFQ salen a nombre de "Ferretera Garza" con respuesta a `compras@ferretera.test`, y Odoo revisa ese buzón cada minuto. La respuesta del proveedor entra sola a su RFQ, con el archivo adjunto en el historial, y el estatus pasa a "Cotización recibida". Esa configuración vive en el módulo de demostración `odoo/addons/sautek_demo_mail`, que solo instala este entorno.

Flujo completo, sin terminal:

1. **Purchase → Orders → Importar inventario (Excel)** (o el botón del mismo nombre arriba de la lista de RFQ) → elige el Excel → **Importar**.
2. Abre la RFQ de Distribuidora Truper Norte → **Send by Email** → **Send**. Estatus: "Esperando cotización".
3. En el webmail entra como `ventas@truper-norte.mx` → abre el correo → **Reply** → adjunta un archivo de cotización → **Send**.
4. En un minuto, la RFQ en Odoo muestra la respuesta con el archivo y pasa a "Cotización recibida".
5. En el webmail entra como `comprador@ferretera.test` → abre "Revisar cotización y aprobar" → el enlace abre la compra → ajusta precios o cantidades si el proveedor cambió algo → **Confirm Order**.
6. **Send PO by Email** → en **Receipt**, valida una parte (crea el pendiente) y luego el resto.

**Leer la cotización del proveedor.** En una RFQ en "Cotización recibida", el botón **Leer cotización** toma el último archivo que mandó el proveedor (PDF, Excel o CSV), busca los renglones con código de producto (`FTR-…`), cantidad y precio, y los compara contra la RFQ en la pestaña **Lectura de cotización**: *Igual*, *Cambio de precio*, *Surtido parcial*, *Cambio de cantidad*, *Sin existencia*, *No viene en la cotización* o *No está en la RFQ*. **Aplicar a la RFQ** pone en las líneas lo cotizado (quita las que no surte) y deja una nota con cada cambio; la compra se sigue confirmando a mano. No usa IA ni servicios externos: el texto del PDF se saca en el propio servidor con `pdftotext`. No lee PDFs escaneados ni cotizaciones sin códigos; en esos casos lo dice y se compara a mano. Para probarlo, `docs/demo/cotizaciones/` trae dos cotizaciones de Distribuidora Truper Norte para la RFQ P00001 de una importación limpia: una completa y una con surtido parcial y una partida sin existencia; respóndela desde el webmail adjuntando una de ellas.

**Simular la respuesta del proveedor (atajo).** Para no pasar por el webmail, en **Purchase → Configuration → Settings** enciende **Modo demostración**: cada RFQ en "Esperando cotización" muestra el botón **Simular respuesta del proveedor**, que mete la respuesta por la misma entrada que el correo real. Apágalo en producción. Desde la terminal hace lo mismo `ODOO_PASSWORD=admin python -m resurtido.odoo.proveedor P01`.

**Con correo real.** En una implementación se configura lo mismo que hace `sautek_demo_mail`, con los servidores de la empresa: correo de salida en *Settings → Technical → Outgoing Mail Servers*; el dominio de alias de la compañía con su buzón de compras (*Settings → General Settings → Alias Domain*); y ese buzón como servidor de entrada en *Settings → Technical → Incoming Mail Servers*. Sin el dominio de alias, las respuestas de los proveedores llegan al correo personal del comprador y Odoo nunca se entera.

## Pruebas de los módulos

Corren dentro de Odoo, en una base de prueba aparte:

```bash
docker compose -f odoo/docker-compose.yml run --rm web odoo -d sautek_test \
  -i purchase_supply_tracking,purchase_excel_replenishment,purchase_quote_reader \
  --test-tags /purchase_supply_tracking,/purchase_excel_replenishment,/purchase_quote_reader \
  --stop-after-init --db-filter=^sautek_test$ --http-port 8071
```

Si cambias el código de un módulo, actualízalo en la base y reinicia Odoo (los cambios en `resurtido/` solo necesitan el reinicio):

```bash
docker compose -f odoo/docker-compose.yml run --rm web odoo -d sautek -u purchase_supply_tracking,purchase_excel_replenishment,purchase_quote_reader \
  --stop-after-init --db-filter=^sautek$ --http-port 8071
docker compose -f odoo/docker-compose.yml restart web
```

## Apagar Odoo

Para apagar Odoo: `docker compose -f odoo/docker-compose.yml down` (agrega `-v` para borrar también la base).
