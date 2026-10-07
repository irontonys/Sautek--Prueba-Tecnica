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
