# Proposal

## Why

Cuando el proveedor contesta, su cotización queda adjunta en la RFQ, pero el comprador tiene que abrir el PDF y comparar renglón por renglón contra la RFQ: qué precio cambió, qué surte incompleto, qué no tiene. Es el mismo trabajo manual que el programa quitó del resurtido, ahora del lado de la respuesta. Se busca la opción de costo cero: sin modelos de IA ni servicios externos, leyendo la cotización por los códigos de producto.

## What Changes

- En la RFQ con la cotización recibida aparece el botón **"Leer cotización"**. Toma el último archivo que mandó el proveedor (PDF, Excel o CSV), saca su texto en el propio servidor y busca los renglones que traen un código de producto (`FTR-…`) con su cantidad y su precio.
- Odoo compara lo leído contra la RFQ y muestra, en una pestaña **"Lectura de cotización"**, cada producto con su estatus: **Igual**, **Cambio de precio**, **Surtido parcial**, **Sin existencia**, **No viene en la cotización** o **No está en la RFQ**, con la cantidad y el precio de cada lado.
- El botón **"Aplicar a la RFQ"** ajusta las líneas con lo cotizado (cantidad, precio; quita las que el proveedor no surte) y deja una nota con cada cambio. Nada cambia sin que el comprador lo apruebe; después confirma la compra como siempre.
- Si el archivo no se puede leer o no trae ningún código de la RFQ, Odoo lo dice y la RFQ queda igual.
- Las dos cotizaciones de prueba (completa y con surtido parcial) se guardan en el repo para la demo y las pruebas.

## Capabilities

### New Capabilities
- `lectura-cotizacion`: lectura de la cotización adjunta del proveedor por códigos de producto, comparación contra la RFQ y aplicación de las diferencias aprobada por el comprador.

### Modified Capabilities

## Impact

- Código nuevo: `resurtido/cotizacion.py` (lectura y comparación, sin Odoo; reusa la normalización de códigos de la validación) y el módulo `odoo/addons/purchase_quote_reader` (botones, pestaña, aplicación, pruebas de Odoo).
- `odoo/Dockerfile`: instala `poppler-utils` (`pdftotext`, gratuito) para sacar el texto de los PDF; la imagen de Odoo no trae una herramienta que sirva (PyPDF2 1.26 no extrae texto de estos PDF).
- `odoo/docker-compose.yml`: instala el módulo nuevo.
- Archivos nuevos: `docs/demo/cotizaciones/` con las dos cotizaciones de prueba.
- Sin costo por uso, sin API keys y sin enviar datos fuera del servidor.
