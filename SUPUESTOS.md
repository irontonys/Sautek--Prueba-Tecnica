# Supuestos

El PDF de la prueba pide: "Si algo del caso no queda claro, asume lo que te parezca razonable y anótalo". Aquí quedan esos supuestos. Se agregan conforme avanzan las fases.

## Datos de entrada

1. **El Excel es una muestra.** El caso habla de unos 800 productos y 25 proveedores; el archivo trae 52 productos en `Existencias` y 8 proveedores. El programa no depende del tamaño, así que se asume que el real tiene la misma estructura con más filas.
2. **El encabezado está en la fila 2.** Cada hoja trae en la fila 1 un título descriptivo (por ejemplo, "Reporte de existencias exportado del ERP actual"). Se asume que así sale siempre del sistema y el programa lee los encabezados de la fila 2.
3. **El Excel no se modifica.** El archivo en `data/` se queda tal como llegó; cualquier corrección se hace dentro del programa y queda registrada en el reporte de excepciones.

## Operación

4. **Los correos no se envían.** El programa deja borradores; mandarlos sigue siendo decisión del comprador.
5. **Corrida semanal.** El programa se corre una vez por semana, después de exportar el reporte de existencias del lunes.
6. **Moneda.** Todos los importes están en pesos mexicanos (MXN), como lo indican los nombres de columna.
