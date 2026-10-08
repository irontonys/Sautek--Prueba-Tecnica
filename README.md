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
docker compose -f odoo/docker-compose.yml up -d
```

El primer arranque crea la base `sautek` e instala Compras e Inventario, y tarda unos minutos. Está lista cuando `http://localhost:8070` muestra el inicio de sesión (usuario `admin`, contraseña `admin`; es una base local de prueba).

Corre la carga con la contraseña en una variable de entorno:

```bash
# macOS / Linux
ODOO_PASSWORD=admin python -m resurtido.odoo

# Windows (PowerShell)
$env:ODOO_PASSWORD = "admin"; python -m resurtido.odoo
```

`ODOO_URL` (`http://localhost:8070`), `ODOO_DB` (`sautek`) y `ODOO_USER` (`admin`) se pueden cambiar con variables del mismo nombre; acepta `--input` y `--output` igual que el programa principal.

Qué hace:

1. Valida el Excel con las mismas reglas y decisiones que el programa principal y carga solo lo procesable: proveedores, productos (con su costo con el proveedor), existencias y una regla de reabastecimiento por producto con su mínimo, máximo y múltiplo de empaque.
2. Dispara el reabastecimiento de Odoo, que deja una solicitud de cotización (RFQ) en borrador por proveedor, en **Purchase → Orders → Requests for Quotation** (la base arranca en inglés). Ninguna se confirma ni se envía: el comprador la revisa y usa "Send by Email".
3. Deja una nota interna "No enviar" en la RFQ del proveedor que no llega a su pedido mínimo, y otra con los productos a revisar (existencias negativas).
4. Compara el total de cada RFQ contra el que calcula el programa principal.

Se puede correr varias veces: actualiza en vez de duplicar y cancela solo las RFQ en borrador que dejó la corrida anterior.

| Archivo | Contenido |
|---|---|
| `output/odoo/conciliacion.csv` | Un renglón por proveedor: RFQ en Odoo, total del programa, total de Odoo, diferencia y si cuadra. |
| `output/odoo/excepciones.csv` | El mismo reporte de excepciones, con el pedido mínimo calculado sobre las RFQ de Odoo. |

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
| `odoo/` | Odoo 17 local con Docker (opcional) |
| `tests/` | Pruebas automatizadas |
| `output/` | Archivos generados por el programa |
| `openspec/` | Propuestas, specs y tareas de cada fase (OpenSpec) |

## Supuestos

Lo que el caso no especifica y decidí asumir está en [SUPUESTOS.md](SUPUESTOS.md).
