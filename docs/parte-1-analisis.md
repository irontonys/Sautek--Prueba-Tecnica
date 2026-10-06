# Parte 1. Análisis

## 1. Antes de proponer nada, ¿qué le preguntarías al comprador y a dirección?

**Al comprador:**
- ¿Por qué hace la comparación en Excel y no en el sistema actual? ¿Le falta capacitación, la función no existe o simplemente le es más fácil en Excel?
- ¿Quién definió los mínimos y máximos, y con qué criterio? Si aun con ellos se quedan sin producto, hay que evaluarlos.

**A dirección:**
- ¿Quién es el dueño de este proceso y quién aprobaría los cambios?
- ¿Por qué no se han actualizado los mínimos si las ventas varían? Esto lo llevaría también con ventas, que es quien conoce cómo se mueve cada producto.

## 2. ¿Dónde se pierde el tiempo y por qué crees que hay faltantes?

**El tiempo** se va en tres pasos manuales:
- Exportar el reporte y compararlo contra el Excel de mínimos.
- Armar a mano los pedidos de cada proveedor.
- Escribir un correo por proveedor.

**Los faltantes** tienen tres causas:
- **Mínimos viejos.** Si un producto hoy se vende más que cuando se fijó su mínimo, se compra menos de lo necesario y hay desabasto.
- **Revisión semanal.** Si un producto se acaba el martes, el comprador se entera hasta el lunes siguiente.
- **Comparación a ojo.** Comparar dos archivos a mano deja espacio para errores.

## 3. ¿Qué cambiarías del proceso antes de automatizarlo?

- **Eliminar el Excel personal de mínimos y máximos.** Todo debe vivir en la plataforma para que nunca haya dos versiones de los números.
- **Revisar con más frecuencia.** Al menos a diario, y hasta dos veces al día según qué tanto varíe cada producto; una vez por semana no alcanza.
- **Darle un dueño a los mínimos.** Si hay un área de procesos, ella los actualiza con los KPIs de ventas; idealmente el propio sistema los calcula a partir del módulo de ventas.

## 4. ¿Qué automatizarías primero y cómo sabrías que funcionó?

**Primero la comparación entre existencias y mínimos.** Es donde más tiempo se pierde y donde más errores hay, y es fácil de hacer: basta con tener los datos en orden. Es el mayor impacto por el menor esfuerzo.

**Cómo saber que funcionó:**
- **Productos que se quedan sin stock** por semana: deben bajar.
- **Tiempo del proceso:** hoy son unas 6 horas a la semana; deben bajar.

## 5. Pensando en Odoo, ¿qué ya viene resuelto, qué hay que configurar y qué habría que programar?

| | Qué |
|---|---|
| **Ya viene resuelto** | Mínimos y máximos por producto dentro del módulo de Inventario. |
| **Hay que configurar** | El envío de la solicitud de compra por correo a cada proveedor y la aprobación del comprador antes de mandarla. El sistema ya lo permite. |
| **Habría que programar** | Un addon para el **pedido mínimo del proveedor**. Si lo que falta pedir no llega al mínimo, revisa si completarlo cabe dentro de los máximos. Si no cabe, compara qué cuesta más: quedarse sin stock o tener sobrestock un tiempo mientras se equilibra. |

## 6. ¿Cómo manejarías el PDF de confirmación del proveedor? ¿Qué pasa si se lee mal una cantidad?

1. **Leer el PDF con OCR.**
2. **Compararlo contra el pedido que yo envié**, línea por línea: producto, cantidad y fecha.
3. **Como segunda revisión, compararlo contra el histórico** de lo que se suele pedir, para detectar volúmenes fuera de lo normal.
4. **Lo que no cuadra lo revisa una persona.** Si el pedido decía 10 y el OCR leyó 100, no se captura: se marca y el comprador lo verifica.

**Lo que nunca le dejaría a la IA sola:** el envío final de un pedido al proveedor. Un pedido compromete dinero; en la práctica es una inversión, así que siempre lo aprueba el comprador.
