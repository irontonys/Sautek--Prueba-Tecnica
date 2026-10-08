# Proposal

## Why

Hoy, para llevar el Excel a Odoo y simular la respuesta del proveedor hay que abrir una terminal y escribir comandos. El comprador y el personal de la ferretería no usan terminal: todo el flujo tiene que poder hacerse desde Odoo, con botones, para que la solución sirva en la operación diaria y no solo en manos de quien la programó.

## What Changes

- En **Compras → Orders** aparece **"Importar inventario (Excel)"**: el usuario elige el Excel exportado del sistema actual y da **Importar**. Odoo corre por dentro el mismo motor de la CLI (las 12 reglas de limpieza, la carga, el reabastecimiento nativo, las notas de pedido mínimo y de revisión, la suscripción del comprador).
- Al terminar, la misma ventana muestra un **aviso con el resumen**: renglones leídos, procesables, no procesables, excepciones por tipo, RFQ generadas y RFQ anteriores canceladas, y la comprobación contra el cálculo de la CLI. Trae el **reporte de excepciones en CSV para descargar** y un botón **"Ver RFQ"** que abre las solicitudes generadas.
- Si el archivo no es un Excel válido o le faltan hojas o columnas, la ventana lo dice en español con el mismo mensaje que la CLI y no cambia nada en Odoo.
- **Modo demostración**: una opción en la configuración de Compras que, encendida, muestra en cada RFQ enviada el botón **"Simular respuesta del proveedor"**. Hace lo mismo que el comando `resurtido.odoo.proveedor`. En producción se apaga y la respuesta llega sola por correo.
- La imagen de Odoo del repo instala las dependencias del motor (pandas y openpyxl, las mismas versiones de `requirements.txt`) y monta el paquete `resurtido`, para que Odoo y la CLI usen exactamente el mismo código.
- Los comandos de terminal se quedan para desarrollo y pruebas; dejan de ser el camino principal.

## Capabilities

### New Capabilities
- `importacion-odoo`: importación del Excel desde la interfaz de Odoo con el mismo motor de la CLI, aviso de resultado con excepciones descargables, y botón de simulación del proveedor en modo demostración.

### Modified Capabilities

## Impact

- Código nuevo: módulo `odoo/addons/purchase_excel_replenishment/` (asistente, adaptador del motor al ORM, ajuste de configuración, botón de demo, pruebas de Odoo) y `odoo/Dockerfile`.
- `odoo/docker-compose.yml`: construye la imagen propia, monta `resurtido/` en solo lectura e instala el módulo nuevo.
- `resurtido/odoo/cli.py`: la secuencia carga → cancelación → reabastecimiento → notas pasa a una función que comparten la CLI y Odoo; la salida de la CLI no cambia.
- `resurtido/odoo/proveedor.py`: la simulación se separa en una función por compra, que usan el comando y el botón.
- README: "Odoo desde la interfaz" pasa a ser el camino principal; los comandos quedan como alternativa técnica.
