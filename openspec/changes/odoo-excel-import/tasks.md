# Tasks

## 1. Motor compartido

- [x] 1.1 Extraer `run_import` e `import_summary_lines` en `resurtido/odoo/cli.py` y hacer que `main` los use; verificar que las pruebas de la CLI de Odoo siguen pasando sin cambios en la salida
- [x] 1.2 Separar `reply_to_order(client, order_id)` en `proveedor.py` y usarla desde `reply_as_vendor`; verificar con pruebas que el comando sigue igual y que la función sola entrega el correo a esa compra

## 2. Imagen de Odoo

- [x] 2.1 Crear `odoo/Dockerfile` (pandas y openpyxl de `requirements.txt`) y ajustar el compose (build, montaje de `resurtido/` en solo lectura, `PYTHONPATH`, instalar el módulo nuevo); verificar con `up -d --build` que dentro del contenedor `import resurtido.validation` funciona

## 3. Módulo `purchase_excel_replenishment`

- [x] 3.1 Crear el módulo con `OrmClient`, el asistente, su vista, el menú en Compras → Orders y los permisos (solo administradores de Compras); verificar que se instala sin errores
- [x] 3.2 Implementar `action_import` (validación con los mensajes de la CLI, `run_import` con `sudo`, CSV de excepciones, resumen, RFQ); verificar con una prueba de Odoo con un Excel pequeño que crea la RFQ, la nota y el CSV
- [x] 3.3 Verificar con pruebas de Odoo que un archivo que no es Excel y uno sin la hoja `Minimos` muestran el mensaje y no cambian registros
- [x] 3.4 Agregar "Modo demostración" a la configuración de Compras y el botón "Simular respuesta del proveedor" con `show_demo_reply`; verificar con pruebas que aparece solo encendido y que lleva la RFQ a "Cotización recibida"
- [x] 3.5 Correr todas las pruebas de los dos módulos en una base de prueba y `pytest`; verificar que pasan

## 3b. Ajustes pedidos en la revisión

- [x] 3.6 Conciliación: estatus "Compra en proceso" cuando el proveedor ya tiene una compra enviada, por aprobar o confirmada sin recibir completa, y título "Comprobación del cálculo"; verificar con pruebas de pytest (cuadra, compra en proceso, no cuadra) y contra Odoo reimportando con una RFQ enviada
- [x] 3.7 Botón "Importar inventario (Excel)" en la lista de RFQ, solo para administradores de Compras; verificar que el módulo actualiza sin errores y que aparece junto a "New"

## 4. Verificación en la interfaz

- [ ] 4.1 Base limpia: importar desde Compras el Excel del caso y verificar el resumen (7 RFQ, 28 excepciones, 8 de 8 cuadran), la descarga del CSV y "Ver RFQ"
- [ ] 4.2 Recorrer sin terminal el flujo completo de una RFQ (enviar, simular respuesta con el botón, aprobar desde el aviso en Mailpit, enviar PO, recibir parcial y completo) y verificar cada estatus

## 5. Documentación

- [ ] 5.1 Reescribir la sección de Odoo del README con el camino desde la interfaz como principal (incluido el primer `--build`) y los comandos como alternativa técnica; verificar siguiendo los pasos
- [x] 5.2 Agregar a `SUPUESTOS.md` los supuestos nuevos (solo administradores de Compras importan, modo demo apagado por omisión)
