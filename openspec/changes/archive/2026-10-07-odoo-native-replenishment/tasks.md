# Tasks

## 1. Entorno Odoo en el repo

- [x] 1.1 Crear `odoo/docker-compose.yml` (Odoo 17 + Postgres 15, `name: sautek-odoo`, puerto 8070, `-d sautek -i purchase_stock --without-demo=all`) y verificar con `docker compose -f odoo/docker-compose.yml up -d` que `http://localhost:8070` abre la base `sautek` con Compras e Inventario instalados
- [x] 1.2 Confirmar por XML-RPC contra ese Odoo que existen `action_replenish` y `qty_to_order`/`qty_multiple` en `stock.warehouse.orderpoint`, `orderpoint_id` en `purchase.order.line` y el XML ID `purchase_stock.route_warehouse0_buy`, y anotar en `design.md` cualquier diferencia antes de seguir. *Confirmado contra el código fuente de 17.0 y contra el contenedor: los tres módulos instalados, `qty_to_order` guardado, `orderpoint_id` y la ruta Comprar existen.*

## 2. Cliente y comando

- [x] 2.1 Crear `resurtido/odoo/client.py` con `OdooClient` y `OdooError` (conexión rechazada, credenciales inválidas, `Fault`) y verificar con pruebas que cada caso produce un mensaje en español con la URL y la base
- [x] 2.2 Crear `tests/fake_odoo.py` con `FakeOdooClient` en memoria (search_read, create, write, call de los métodos usados) y verificar que lo usan las pruebas de las secciones 3 a 5
- [x] 2.3 Crear `resurtido/odoo/cli.py` y `__main__.py`: `--input`/`--output`, variables `ODOO_*` sin contraseña por omisión, y la reutilización de `read_sheet_names`/`check_sheets`. Verificar con pruebas que un Excel inexistente o la falta de `ODOO_PASSWORD` salen con código 1, sin traceback y sin crear el cliente

## 3. Carga de datos (`carga-odoo`)

- [x] 3.1 Implementar en `sync.py` la carga de proveedores por `ref` y verificar con `FakeOdooClient` que solo se cargan los proveedores con productos procesables y que una segunda carga no duplica
- [x] 3.2 Implementar la carga de productos (almacenables, ruta Comprar, sin impuestos de compra) y tarifas de proveedor por `default_code`, y verificar con pruebas que los excluidos (inactivo, duplicado, sin mínimo) no llegan al cliente
- [x] 3.3 Implementar el ajuste de inventario y las reglas de reabastecimiento (`trigger='manual'`, mín, máx, múltiplo) y verificar con pruebas que una existencia negativa llega como 0 y que dos cargas dejan una sola regla por producto
- [x] 3.4 Cambiar la moneda de la compañía a MXN cuando se pueda, con aviso si Odoo lo rechaza, y verificar con una prueba que el rechazo no detiene la carga

## 4. Reabastecimiento (`reabastecimiento-odoo`)

- [x] 4.1 Implementar en `replenish.py` la cancelación de las RFQ en borrador propias (de un proveedor cargado y con todos sus renglones con `orderpoint_id`) y verificar con pruebas que una RFQ sin `orderpoint_id` o confirmada no se cancela
- [x] 4.2 Implementar el disparo de `action_replenish` sobre las reglas cargadas con el contexto `recompute_qty_to_order` y la lectura de las RFQ resultantes por proveedor; verificar con pruebas que no se llama a ningún método de confirmación ni de envío
- [x] 4.3 Implementar las notas internas (pedido mínimo no alcanzado y productos a revisar) y la excepción de pedido mínimo, y verificar con pruebas el texto de la nota con total, mínimo y faltante

## 5. Conciliación y salidas

- [x] 5.1 Implementar `reconcile.py` (CLI contra `amount_untaxed`, tolerancia de un centavo) y verificar con pruebas los casos "Cuadra", "No cuadra" y "sin productos en ambos lados"
- [x] 5.2 Escribir `output/odoo/excepciones.csv` y `output/odoo/conciliacion.csv` e imprimir el resumen, y verificar con una prueba de punta a punta con `FakeOdooClient` sobre `data/inventario_ferreteria_garza.xlsx` que no cambia nada en `output/` fuera de `output/odoo/`
- [x] 5.3 Correr `.venv/bin/python -m pytest` y verificar que las 81 pruebas existentes y las nuevas pasan sin Docker (111 en total)

## 6. Verificación contra Odoo real

- [x] 6.1 Con el contenedor arriba, correr `python -m resurtido.odoo` y verificar en Odoo que hay una RFQ en borrador por cada proveedor con productos por pedir, que la de P05 trae la nota "No enviar" y que `conciliacion.csv` cuadra (o documentar cada "No cuadra" con su causa en `SUPUESTOS.md`)
- [x] 6.2 Correr el comando una segunda vez y verificar que no hay contactos, productos ni reglas duplicados, que las RFQ anteriores quedaron canceladas y que hay el mismo número de RFQ vigentes
- [x] 6.3 Tomar capturas de las RFQ y de la nota de P05 para el PR

## 7. Documentación

- [x] 7.1 Agregar al README la sección "Odoo (opcional)": levantar el contenedor, primer arranque lento, variables `ODOO_*`, comando y salidas. Verificar siguiendo el README desde un clon en el scratchpad. *Hecho con una copia del árbol de trabajo (aún sin commit); `pip install` no pudo llegar a pypi.org desde este entorno, así que se usó el `.venv` del proyecto con las mismas dependencias.*
- [x] 7.2 Agregar a `SUPUESTOS.md` los supuestos de Odoo (impuestos fuera, UdM Unidades, trigger manual, moneda) y verificar que cada decisión del design que afecta al usuario quedó anotada
