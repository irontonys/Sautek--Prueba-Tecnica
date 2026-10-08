# Tasks

## 1. Lectura sin Odoo

- [x] 1.1 Guardar las dos cotizaciones de prueba en `docs/demo/cotizaciones/` y verificar que abren
- [x] 1.2 Crear `resurtido/cotizacion.py` con `extract_text` (PDF con `pdftotext -layout`, `.xlsx`, `.csv`), `parse_quote` y `compare`; verificar con pytest las dos cotizaciones (incluido el párrafo de aviso), Excel, CSV, códigos mal escritos, cantidad que no cuadra con el importe y cada estatus de la comparación

## 2. Imagen y módulo

- [x] 2.1 Agregar `poppler-utils` a `odoo/Dockerfile`, el módulo al compose, y verificar con `up -d --build` que `pdftotext` funciona dentro del contenedor
- [x] 2.2 Crear `purchase_quote_reader` (modelo de líneas de lectura, campos en la compra, `action_read_quote`, `action_apply_quote`, botones y pestaña) e instalarlo; verificar que actualiza sin errores
- [x] 2.3 Pruebas de Odoo: leer y aplicar la cotización parcial adjunta como correo del proveedor (12 de 24, sin existencia, total igual al subtotal, nota, sin confirmar), archivo sin códigos sin cambios, botón oculto fuera de "Cotización recibida"; verificar que pasan junto con las de los otros módulos

## 3. Verificación de punta a punta

- [x] 3.1 Base limpia: importar, enviar la RFQ de P01, responderla desde el webmail con la cotización parcial, dar "Leer cotización" y verificar la tabla; "Aplicar a la RFQ" y verificar líneas, total ($155,631.89) y nota. *Hecho sobre la base de demo sin reiniciarla, con la RFQ P00003 de Pinturas Industriales Regias (P00001 ya estaba aprobada por el recorrido del autor): cotización con surtido parcial (60 → 40) y cambio de precio ($469.92 → $489.90), respondida desde el webmail; al aplicar, total $42,128.14 = subtotal de la cotización, RFQ sin confirmar y nota con los cambios.*

## 4. Documentación

- [x] 4.1 README: lectura de cotización (botones, estatus, formatos que lee y límites) y las cotizaciones de prueba
- [x] 4.2 `SUPUESTOS.md`: lectura por códigos sin IA, límites (escaneados, sin códigos, códigos propios del proveedor) y actualizar el supuesto 22
