# Sautek — Prueba técnica: Coordinación de procesos y desarrollo

Programa de resurtido semanal para el caso **Ferretera Garza**. Lee el Excel de inventario y arma los pedidos de la semana por proveedor, con un borrador de correo para cada uno y un reporte de los registros que no pudo procesar.

## La entrega

| La prueba pide | Dónde está |
|---|---|
| Parte 1. Análisis | [`docs/parte-1-analisis.md`](docs/parte-1-analisis.md) |
| Parte 2. Programa de resurtido | El libro [`excel/Resurtido.xlsm`](#uso-el-libro-de-excel) para Compras y el mismo programa en Python para la [terminal](#alternativa-técnica-la-terminal) |
| Archivos que generó el programa | [`output/`](output/): `pedidos.xlsx`, `correos/` (borradores `.eml` e `indice.csv`) y `excepciones.csv` |
| Parte 3. Redes sociales | [`docs/parte-3-redes-sociales.md`](docs/parte-3-redes-sociales.md) |
| Nota sobre la IA | [`docs/nota-ia.md`](docs/nota-ia.md) |
| Supuestos | [`SUPUESTOS.md`](SUPUESTOS.md) |

El programa se usa de dos formas, con las mismas reglas:

- **El libro de Excel `excel/Resurtido.xlsm`**: la forma principal, pensada para Compras. Todo se hace con cuatro botones, sin instalar nada.
- **La terminal** (`python -m resurtido`): la misma lógica en Python, para quien la mantiene o la quiere automatizar.

Como extra, el mismo Excel se puede llevar a un **Odoo 17** local (ver [Extra: Odoo 17](#extra-odoo-17-opcional)).

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

## Extra: Odoo 17 (opcional)

La empresa va a migrar a Odoo, así que el mismo Excel también se puede llevar a un Odoo 17 local con Docker. Ahí las compras las calcula el reabastecimiento nativo de Odoo, y el comprador trabaja desde la interfaz: importa el Excel, revisa las excepciones en una bandeja, envía las solicitudes de cotización, recibe la respuesta del proveedor en un webmail de prueba, lee la cotización por códigos y sigue cada compra hasta la recepción. Nada sale a internet.

No es parte de lo que pide la prueba: el programa principal y sus pruebas no dependen de esto. Cómo levantarlo y usarlo: [`odoo/README.md`](odoo/README.md).

## Pruebas

Con el entorno de la terminal activo:

```bash
pip install -r requirements-dev.txt
python -m pytest
```

`tests/test_excel_paridad.py` corre el mismo inventario por el libro de Excel y por Python, con la misma fecha, y compara excepciones, pedidos y borradores byte a byte: con el Excel real y con libros de prueba que cubren todos los tipos de excepción. Toma el control de Excel unos segundos, así que solo corre en una Mac con Microsoft Excel; en otra computadora se omite. Para omitirla a propósito: `RESURTIDO_SKIP_EXCEL=1 python -m pytest`.

Las pruebas de los módulos de Odoo corren dentro de Odoo: ver [`odoo/README.md`](odoo/README.md#pruebas-de-los-módulos).

## Estructura

| Ruta | Contenido |
|---|---|
| `excel/` | Libro `Resurtido.xlsm` para Compras, su código VBA y cómo se arma |
| `data/` | Excel de entrada, tal como llegó |
| `resurtido/` | Código del programa; `resurtido/odoo/` es la carga a Odoo |
| `odoo/` | Odoo 17 local con Docker (opcional, ver su [README](odoo/README.md)): imagen, compose y los módulos `purchase_supply_tracking` (seguimiento), `purchase_excel_replenishment` (importar el Excel desde Compras), `purchase_quote_reader` (leer la cotización del proveedor) y `sautek_demo_mail` (correo de la demostración) |
| `docs/` | Partes 1 y 3, nota sobre la IA, capturas (`img/`) y cotizaciones de prueba para la demostración de Odoo (`demo/`) |
| `tests/` | Pruebas automatizadas |
| `output/` | Archivos generados por el programa |
| `openspec/` | Propuestas, specs y tareas de cada fase (OpenSpec) |

## Supuestos

Lo que el caso no especifica y decidí asumir está en [SUPUESTOS.md](SUPUESTOS.md).
