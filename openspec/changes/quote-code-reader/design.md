# Design

## Context

- La respuesta del proveedor ya entra a la RFQ con su archivo adjunto y la RFQ pasa a "Cotización recibida" (`rastreo-compras`, `correo-demo`). Odoo no lee el contenido (supuesto 22).
- Decisiones del autor: sin IA ni servicios externos (costo cero), lectura con un botón, y la lectura solo propone: el comprador aplica.
- Prueba hecha al proponer, con la cotización de surtido parcial: PyPDF2 1.26 (el que trae la imagen de Odoo) regresa texto vacío; `pdftotext -layout` (poppler) conserva cada partida en su renglón con código, solicitada, surtible, precio, importe y existencia. La cotización también trae un párrafo de aviso que menciona códigos sin montos.
- La normalización de códigos ya existe en `resurtido/validation.py` (`normalize_code`: `ftr-4` → `FTR-0004`).

## Goals / Non-Goals

**Goals:**
- Que el comprador vea en segundos qué cambió en la cotización contra su RFQ, y lo aplique con un clic.
- Lógica de lectura probada con pytest, fuera de Odoo, como el resto del motor.

**Non-Goals:**
- PDFs escaneados (imágenes sin texto): se reporta que no se encontraron partidas.
- Cotizaciones sin códigos de producto (solo descripciones): mismo caso. Es el límite conocido de la opción sin IA.
- Leer condiciones comerciales (crédito, vigencia, tiempos de entrega).
- Aplicar sin intervención del comprador o confirmar la compra.

## Decisions

### 1. Lectura en `resurtido/cotizacion.py`, sin Odoo
- `extract_text(path)`: PDF con `pdftotext -layout` (subproceso), `.xlsx` con openpyxl (cada fila como renglón separado por tabulador), `.csv` con el módulo `csv`. Otro tipo → error en español.
- `parse_quote(text) -> {código: QuotedLine}`: un renglón es partida si contiene un código (`FTR-?\d{1,4}`, normalizado con `normalize_code`) **y** al menos un monto con `$` o dos decimales. En ese renglón:
  - Los montos (con `$` o `,`/`.` decimal) son precio e importe: precio = el primero, importe = el último.
  - Los enteros entre el código y el primer monto son cantidades; la cantidad surtible es la que cumple `cantidad × precio ≈ importe` (±$0.01). Si ninguna cumple, se toma la última antes del precio.
  - Si el renglón dice "sin existencia", "agotado" o "no disponible", la cantidad surtible es 0.
  - Si un código aparece en varias partidas, se conserva la primera.
- `compare(rfq_lines, quoted) -> [ComparisonRow]` con los estatus del spec. El precio se compara a centavos con `Decimal`.
- *Alternativa:* un modelo de IA local (Ollama) o Gemini gratuito. Descartadas por decisión del autor: costo cero sin modelo. Se documenta como siguiente paso para formatos libres.

### 2. `poppler-utils` en la imagen
`odoo/Dockerfile` agrega `apt-get install -y --no-install-recommends poppler-utils`. Gratuito, estándar en Debian/Ubuntu y solo agrega `pdftotext` y similares.

### 3. Módulo `purchase_quote_reader`
- Depende de `purchase_supply_tracking` (estatus "Cotización recibida").
- Modelo `purchase.quote.reading.line` (`order_id`, `product_id`, `code`, `rfq_qty`, `rfq_price`, `quoted_qty`, `quoted_price`, `status`). En `purchase.order`: `quote_reading_line_ids`, `quote_reading_attachment_id`, `quote_read_at`, y `has_quote_differences` (calculado).
- `action_read_quote`: busca el adjunto más reciente de un mensaje `email` cuyo autor es de la empresa del proveedor (el mismo criterio que la cotización recibida), lo escribe en un temporal, corre `extract_text` → `parse_quote` → `compare`, reemplaza la lectura anterior y la muestra en la pestaña "Lectura de cotización". Si no hay partidas de la RFQ, `UserError` sin guardar nada.
- `action_apply_quote`: solo en `draft`/`sent`/`to approve`; escribe `product_qty`/`price_unit`, borra las líneas "Sin existencia", deja nota interna con los cambios (`message_post`, nota) y marca la lectura como aplicada (los botones se ocultan hasta una nueva lectura).
- Vistas: botón "Leer cotización" en el encabezado (visible con `supply_status == 'quote_received'`), botón "Aplicar a la RFQ" (visible con diferencias y no aplicada), pestaña con la lista y colores por estatus.

### 4. Archivos de prueba en el repo
`docs/demo/cotizaciones/` guarda las dos cotizaciones (completa y surtido parcial) en PDF. Las pruebas de Odoo y de pytest las usan como entrada real.

### 5. Pruebas
- pytest: `parse_quote` con el texto de las dos cotizaciones (párrafo de aviso incluido), con Excel y CSV, con códigos mal escritos y con cantidad que no cuadra; `compare` con cada estatus; `extract_text` del PDF real (se salta si la máquina no tiene `pdftotext`).
- Odoo: leer y aplicar sobre una RFQ con la cotización parcial adjunta como correo del proveedor; archivo sin códigos; botón oculto fuera de "Cotización recibida".

## Risks / Trade-offs

- [Formatos de proveedor muy distintos (sin códigos, columnas raras, PDF escaneado)] → Se reporta que no hay partidas y el comprador compara a mano como hoy. Es la limitación aceptada de la opción sin IA; la lectura con IA queda como mejora.
- [Confundir cantidad solicitada con surtible] → Se elige la cantidad que cuadra con el importe; el comprador revisa la tabla antes de aplicar.
- [El proveedor usa sus propios códigos, distintos a los de la ferretería] → No se reconocen; en producción se resolvería con los códigos de proveedor de Odoo (`product.supplierinfo.product_code`), fuera de esta fase.

## Migration Plan

`docker compose -f odoo/docker-compose.yml up -d --build` reconstruye la imagen con poppler e instala el módulo. Revertir: desinstalar el módulo.
