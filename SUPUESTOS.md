# Supuestos

El PDF de la prueba pide: "Si algo del caso no queda claro, asume lo que te parezca razonable y anótalo". Aquí quedan esos supuestos. Se agregan conforme avanzan las fases.

## Datos de entrada

1. **El Excel es una muestra.** El caso habla de unos 800 productos y 25 proveedores; el archivo trae 52 productos en `Existencias` y 8 proveedores. El programa no depende del tamaño, así que se asume que el real tiene la misma estructura con más filas.
2. **El encabezado está en la fila 2.** Cada hoja trae en la fila 1 un título descriptivo (por ejemplo, "Reporte de existencias exportado del ERP actual"). Se asume que así sale siempre del sistema y el programa lee los encabezados de la fila 2.
3. **El Excel no se modifica.** El archivo en `data/` se queda tal como llegó; cualquier corrección se hace dentro del programa y queda registrada en el reporte de excepciones.

## Calidad de datos

Qué se hace con cada tipo de problema está en [`excepciones.csv`](output/excepciones.csv) (columna `decision`) y en el diseño de la fase de validación. Supuestos detrás de esas decisiones:

4. **Mismas unidades.** Varias descripciones dicen caja, bolsa, kg, m o par mientras la columna Unidad dice PZA. Se supone que existencia, mínimo y máximo están en la misma unidad, sea cual sea; esos productos se procesan y quedan marcados en el reporte.
5. **Existencia negativa = 0.** Una existencia negativa probablemente es un error de captura (salidas sin su entrada). Se pide como si no hubiera piezas, y el producto queda marcado para que el comprador lo revise antes de mandar el pedido.
6. **Códigos normalizados.** `ftr-0004`, ` FTR-27 ` y similares se llevan a `FTR-0004` / `FTR-0027` antes de cruzar las hojas. Cada caso se reporta.
7. **Tipos sin decisión.** Costos o múltiplos inválidos, pedido mínimo inválido, correo inválido y proveedor inexistente no aparecen en este Excel. Si aparecen, el producto (o el proveedor) no se procesa y el reporte dice "Pendiente de decisión".

## Cálculo de pedidos

8. **"Por debajo del mínimo" es estrictamente menor.** Si la existencia es igual al mínimo, no se pide.
9. **El redondeo puede pasar el máximo.** El enunciado pide redondear hacia arriba al múltiplo de empaque, así que el inventario resultante puede quedar arriba del máximo (por ejemplo, FTR-0001: 3 + 60 = 63 con máximo 60). Se respeta el múltiplo porque el proveedor no vende piezas sueltas.
10. **Pedido mínimo no alcanzado: no se envía.** Si el total de un proveedor no llega a su pedido mínimo, el pedido no se manda ni se completa automáticamente; aparece como "No se envía" en `pedidos.xlsx` y en `excepciones.csv`, y el comprador decide si lo completa. Completarlo solo llevaría a subir cantidades por encima del máximo sin que nadie lo apruebe.

## Operación

11. **Los correos no se envían.** El programa deja borradores `.eml`; mandarlos sigue siendo decisión del comprador. No tienen remitente: el cliente de correo pone la cuenta de quien los abre. Los pedidos que no llegan al pedido mínimo no generan borrador.
12. **Corrida diaria.** El programa se corre al menos una vez al día, después de exportar el reporte de existencias, como propone el análisis de la Parte 1 (pregunta 3): revisar solo los lunes es una de las causas de los faltantes.
13. **Moneda.** Todos los importes están en pesos mexicanos (MXN), como lo indican los nombres de columna.
14. **Fecha del pedido.** El asunto y el cuerpo del correo usan la fecha del día en que se corre el programa.

## Odoo (opcional)

15. **Sin impuestos en Odoo.** Los productos se cargan sin impuestos de compra para que el total de cada RFQ sea comparable con el del programa, que trabaja sin IVA. La localización mexicana (IVA, CFDI) queda fuera.
16. **Todo en Unidades.** Por el supuesto 4, existencia, mínimo, máximo y cantidades se cargan en la unidad de medida Unidades de Odoo.
17. **Solo el comando dispara compras.** Las reglas de reabastecimiento quedan en modo manual: el scheduler nocturno de Odoo no genera compras por su cuenta. Las cantidades sí las calcula Odoo.
18. **Moneda MXN.** La base nueva de Odoo arranca en USD; el comando pone la compañía en pesos mexicanos. Si Odoo no lo permite (por ejemplo, porque ya hay asientos contables), avisa y sigue: la moneda no cambia ningún total.
19. **Odoo sin comprador asignado al proveedor.** Odoo junta compras nuevas en una RFQ en borrador del mismo proveedor solo si esa RFQ no tiene comprador. Las RFQ hechas a mano desde la interfaz siempre lo tienen, así que no se mezclan con las del comando. Por eso el comprador de las RFQ del comando no se asigna como responsable sino como seguidor (supuesto 20).

## Seguimiento de compras en Odoo (opcional)

20. **El comprador es el usuario de la conexión.** En la prueba, `admin` hace de comprador: sigue las RFQ, recibe los avisos y aprueba. En una implementación sería un usuario de Compras por persona, y las RFQ manuales llevarían su nombre como responsable.
21. **La factura queda fuera.** El seguimiento termina cuando la mercancía se recibe completa. Registrar la factura del proveedor necesita el módulo de Facturación y queda para una fase siguiente.
22. **La cotización se lee por códigos y el comprador aplica.** Cuando el proveedor contesta, el botón "Leer cotización" compara su archivo contra la RFQ y "Aplicar a la RFQ" ajusta cantidades y precios; nada cambia sin que el comprador lo apruebe, y la confirmación sigue siendo manual.
23. **Cotización recibida = correo del proveedor.** Cuenta cualquier correo que llegue a la RFQ desde la dirección del proveedor o de un contacto dado de alta bajo su empresa. Un correo de otra dirección o una nota interna no cambian el estatus.
24. **Correos solo de prueba.** El Odoo del repositorio envía y recibe por un servidor de correo de prueba con webmail; ningún correo sale a internet, aunque las direcciones de los proveedores sean las del caso.
25. **Solo los administradores de Compras importan.** La importación crea productos, ajusta existencias y cambia reglas de reabastecimiento, así que la opción solo aparece para administradores de Compras y corre con permisos completos durante el proceso. Quien importa queda como seguidor de las RFQ.
26. **Modo demostración apagado por omisión.** El botón para simular la respuesta del proveedor solo existe para demostraciones; en producción la respuesta llega por correo.
27. **La configuración del correo de prueba es solo de la demostración.** El buzón de compras, el servidor de entrada, el correo del comprador y el nombre "Ferretera Garza" viven en el módulo `sautek_demo_mail`. Los módulos de seguimiento e importación no dependen de él; en producción se configura lo mismo con los servidores de la empresa.
28. **En la demo, Odoo revisa el correo y envía sus avisos cada minuto.** Odoo trae por omisión la recolección cada 5 minutos y la cola de envío cada hora; el módulo de demostración baja ambas a un minuto para que el flujo se vea en el momento.
29. **Lectura de cotización sin IA.** Por costo, la lectura no usa modelos de IA ni servicios externos: saca el texto del archivo en el servidor y busca los códigos de producto de la ferretería (`FTR-…`) con su cantidad y precio. Toma como cantidad la que cuadra con el importe (cantidad × precio), para no confundirla con la solicitada. No lee PDFs escaneados, cotizaciones sin códigos ni códigos propios del proveedor; en esos casos avisa y el comprador compara a mano. Leer formatos libres con IA (local o en la nube) queda como mejora.
30. **Las excepciones se corrigen en el origen y las da seguimiento el comprador.** La bandeja de excepciones no corrige el catálogo: los datos se arreglan en el sistema que exporta el Excel, y la excepción se resuelve sola en la siguiente importación. Todas se asignan a quien importa (el comprador); él revisa las advertencias antes de enviar las RFQ y pasa las demás a quien mantiene el catálogo. Las que revisó y no requieren cambio (como una unidad confirmada) las marca como aceptadas.
31. **Historial mínimo de importaciones.** Para colgar la tarea de "Revisar excepciones", cada importación deja un registro con fecha, usuario, archivo y conteos. No guarda el Excel ni el resumen completo.
