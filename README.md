# Sautek — Prueba técnica: Coordinación de procesos y desarrollo

Programa de resurtido semanal para el caso **Ferretera Garza**. Lee el Excel de inventario y arma los pedidos de la semana por proveedor, con un borrador de correo para cada uno y un reporte de los registros que no pudo procesar.

Se usa de tres formas:

- **El libro de Excel `excel/Resurtido.xlsm`**: la forma principal, pensada para Compras. Todo se hace con cuatro botones, sin instalar nada.
- **La terminal** (`python -m resurtido`): la misma lógica en Python, para quien la mantiene o la quiere automatizar.
- **Odoo** (opcional): lleva el inventario a un Odoo 17 local y deja las solicitudes de cotización ahí.

## Uso: el libro de Excel

Solo necesitas Microsoft Excel (Windows o Mac) con macros habilitadas. No hace falta Python.

1. Descarga [`excel/Resurtido.xlsm`](excel/Resurtido.xlsm) y guárdalo en una carpeta propia, por ejemplo `Documentos/Resurtido/`. Los correos se escriben junto al libro.
2. **Solo en Windows:** clic derecho en el archivo → **Propiedades** → marca **Desbloquear** → **Aceptar**. Windows bloquea las macros de los archivos descargados de internet.
3. Abre el libro. Si Excel lo pregunta, da **Habilitar contenido** (Windows) o **Habilitar macros** (Mac).
4. En la hoja **Inicio**, sigue los cuatro botones en orden:

| Paso | Botón | Qué hace |
|---|---|---|
| 1 | **Cargar inventario** | Pide el Excel que exporta el sistema y copia sus cuatro hojas al libro. El archivo original no se modifica. |
| 2 | **Revisar datos** | Llena la hoja **Excepciones**: un renglón por problema, con color según su gravedad y un enlace **Ir a la celda**. Corrige en las hojas de datos y vuelve a dar **Revisar datos**; cada cambio a mano queda en la hoja **Correcciones**. |
| 3 | **Preparar pedidos** | Llena **Resumen** (un renglón por proveedor) y **Detalle** (un renglón por producto). En Detalle puedes ajustar la **Cantidad** (celdas amarillas): el importe, el total y el estado se recalculan solos, y una cantidad que no es múltiplo del empaque se pinta de color. |
| 4 | **Generar correos** | Escribe en la carpeta `correos/`, junto al libro, un borrador `.eml` por pedido que se envía y el `indice.csv`. Si cambiaste las hojas de datos después del paso 3, te pide preparar los pedidos de nuevo. **No envía nada.** |

La hoja **Inicio** muestra el estado de cada paso. Los borradores se abren con doble clic. Outlook para Windows los abre como borrador listo para enviar; Apple Mail los muestra como mensaje recibido, y con **Mensaje → Volver a enviar** se abren para editar y enviar.

El libro aplica las mismas reglas que el programa de Python, y una prueba automatizada compara los dos resultados (ver [Pruebas](#pruebas)). Para cambiar el código del libro: [`excel/README.md`](excel/README.md).

## Alternativa técnica: la terminal

### Requisitos

- Python 3.10 o superior
- Git

### Instalación

```bash
git clone https://github.com/irontonys/Sautek--Prueba-Tecnica.git
cd Sautek--Prueba-Tecnica
python3 -m venv .venv
```

Activa el entorno virtual:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```bash
pip install -r requirements.txt
```

### Uso

Desde la raíz del repositorio:

```bash
python -m resurtido
```

Por omisión lee `data/inventario_ferreteria_garza.xlsx` y escribe en `output/`. Para usar otros archivos:

```bash
python -m resurtido --input otro_inventario.xlsx --output resultados/
```

Si el archivo no existe, no es un Excel o le falta alguna de las hojas `Existencias`, `Minimos`, `Producto_Proveedor` o `Proveedores` (o alguna de sus columnas), el programa lo dice y termina con código de salida 1.

### Salidas

| Archivo | Contenido |
|---|---|
| `output/pedidos.xlsx` | Hoja **Resumen**: un renglón por proveedor con productos, total, pedido mínimo y estado (se envía, no se envía o sin productos por pedir). Hoja **Detalle**: un renglón por producto a pedir con cantidad, importe y la marca "Revisar". |
| `output/correos/*.eml` | Un borrador de correo por cada pedido que se envía, con destinatario, asunto, la tabla de productos y el total. **No se envían**: se abren con doble clic en Outlook o Apple Mail, se revisan y se mandan a mano. |
| `output/correos/indice.csv` | Índice interno de los borradores: estado de cada pedido, archivo, total y la columna "revisar_antes_de_enviar" con los productos que el comprador debe checar antes de mandar el correo. |
| `output/excepciones.csv` | Un renglón por cada problema encontrado en el Excel: hoja, fila, código, tipo, detalle, valor original y la decisión que se tomó. Abre directo en Excel. |

Al terminar, el programa imprime un resumen que concilia los renglones leídos (repetidos + procesables + no procesables), así ningún producto se pierde sin aviso. También muestra cuántos pedidos se envían, cuáles no llegan al pedido mínimo y el total a comprar.

## Odoo (opcional)

El mismo Excel se puede llevar a un Odoo 17 local. Ahí las compras ya no las calcula el programa: las calcula el reabastecimiento nativo de Odoo. Esta parte es opcional y necesita [Docker](https://www.docker.com/products/docker-desktop/); el programa principal y las pruebas no dependen de ella.

Levanta Odoo desde la raíz del repositorio:

```bash
docker compose -f odoo/docker-compose.yml up -d --build
```

La primera vez construye la imagen de Odoo con las librerías del programa (necesita internet para bajarlas), crea la base `sautek` e instala Compras, Inventario y los dos módulos del repo; tarda unos minutos. Está lista cuando `http://localhost:8070` muestra el inicio de sesión (usuario `admin`, contraseña `admin`; es una base local de prueba). Las siguientes veces basta `docker compose -f odoo/docker-compose.yml up -d`.

### Desde Odoo, sin terminal

1. Entra a `http://localhost:8070` y ve a **Purchase → Orders → Importar inventario (Excel)** (solo lo ven los administradores de Compras).
2. Elige el Excel de inventario y da **Importar**. Odoo corre por dentro el mismo programa: valida con las mismas reglas y decisiones, carga lo procesable (proveedores, productos con su costo, existencias y una regla de reabastecimiento por producto con su mínimo, máximo y múltiplo de empaque) y dispara el reabastecimiento de Odoo.
3. La ventana muestra el resumen (renglones leídos, excepciones por tipo, RFQ generadas, proveedores que no llegan a su mínimo y la comprobación contra el cálculo del programa), el botón para descargar **excepciones.csv** y **Ver RFQ**.
4. Las RFQ quedan en borrador, una por proveedor, en **Purchase → Orders → Requests for Quotation** (la base arranca en inglés). La del proveedor que no llega a su pedido mínimo trae la nota "No enviar"; las que tienen productos a revisar (existencias negativas), otra nota con sus códigos. Nada se confirma ni se envía solo.

**Bandeja de excepciones.** Cada importación también deja sus excepciones en **Purchase → Orders → Excepciones de inventario**, como pendientes del comprador (quien importa). Cada una dice qué venía mal, qué se decidió y en qué grupo cae: *Se corrigió*, *Advertencia* (se procesó pero hay que revisarla, como una existencia negativa), *No se procesó* (el producto no entró al pedido) o *Compra* (pedido mínimo no alcanzado). El estatus se mantiene solo: *Pendiente* al aparecer; *Resuelta* cuando una importación ya no la reporta porque se corrigió el dato en el sistema de origen (si vuelve, se reabre); y *Aceptada* cuando el comprador la revisó y no hay nada que corregir. La misma excepción no se duplica entre importaciones: lleva la cuenta de cuántas veces ha salido y cuántos días lleva abierta. Cada importación le deja al comprador una sola tarea, "Revisar excepciones: N nuevas, M abiertas, K resueltas", con el aviso en su correo; la de la importación anterior se cierra sola.

Si el archivo no es un Excel o le falta una hoja o columna, la ventana lo dice y no cambia nada. Se puede importar varias veces: actualiza en vez de duplicar y cancela solo las RFQ en borrador que dejó la importación anterior.

### Desde la terminal (alternativa técnica)

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

### Seguimiento de compras

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

**Pruebas de los módulos.** Corren dentro de Odoo, en una base de prueba aparte:

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

Para apagar Odoo: `docker compose -f odoo/docker-compose.yml down` (agrega `-v` para borrar también la base).

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest
```

`tests/test_excel_paridad.py` corre el mismo inventario por el libro de Excel y por Python, con la misma fecha, y compara excepciones, pedidos y borradores byte a byte: con el Excel real y con libros de prueba que cubren todos los tipos de excepción. Toma el control de Excel unos segundos, así que solo corre en una Mac con Microsoft Excel; en otra computadora se omite. Para omitirla a propósito: `RESURTIDO_SKIP_EXCEL=1 python -m pytest`.

## Estructura

| Ruta | Contenido |
|---|---|
| `excel/` | Libro `Resurtido.xlsm` para Compras, su código VBA y cómo se arma |
| `data/` | Excel de entrada, tal como llegó |
| `resurtido/` | Código del programa; `resurtido/odoo/` es la carga a Odoo |
| `odoo/` | Odoo 17 local con Docker (opcional): imagen, compose y los módulos `purchase_supply_tracking` (seguimiento), `purchase_excel_replenishment` (importar el Excel desde Compras), `purchase_quote_reader` (leer la cotización del proveedor) y `sautek_demo_mail` (correo de la demostración) |
| `docs/demo/` | Cotizaciones de prueba para la demostración |
| `tests/` | Pruebas automatizadas |
| `output/` | Archivos generados por el programa |
| `openspec/` | Propuestas, specs y tareas de cada fase (OpenSpec) |

## Supuestos

Lo que el caso no especifica y decidí asumir está en [SUPUESTOS.md](SUPUESTOS.md).
