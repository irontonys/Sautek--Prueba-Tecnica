# Nota sobre la IA

## Qué usé

**Claude Code**, con **OpenSpec** para ordenar el trabajo. Cada fase empezó como un *change* de OpenSpec (propuesta, diseño, specs y tareas), y el código se escribió tarea por tarea contra esas tareas. Los changes ya terminados están archivados en [`openspec/`](../openspec/).

## Para qué

- **Organizar ideas y decisiones.** Me ayudó a poner por escrito, de forma clara, lo que ya tenía en la cabeza: el análisis, los supuestos y qué hacer con cada tipo de error en los datos.
- **Código repetitivo.** Lectura de las hojas, reglas de validación parecidas entre sí, escritura de archivos y, en el libro de Excel, pasar la misma lógica de Python a VBA.
- **Pruebas automáticas.** Los escenarios de cada regla y la prueba que compara el libro de Excel contra el programa de Python.
- **Redacción.** README, supuestos y textos de las partes 1 y 3.

## Qué le pedí y cómo

Trabajé con un esquema de **proponer, revisar y aplicar**: la IA proponía qué iba a hacer, yo lo revisaba y solo entonces se aplicaba. Así siempre supe qué se estaba moviendo en el proyecto. El avance se ve en los commits y PRs del repositorio, una fase a la vez.

## Qué le corregí

- **La prioridad.** La IA iba avanzando con Odoo, que es un extra. La regresé a lo que pide la prueba: que alguien de Compras use el programa desde Excel, sin terminal.
- **El correo de prueba en Odoo.** Para simular las respuestas de los proveedores la IA propuso Mailpit. Lo cambié por un webmail para las sesiones ficticias.

## Qué no le dejé

- **El stack y la estructura** del proyecto.
- **Las decisiones de dinero**: mínimos, máximos y qué hacer cuando un pedido no llega al mínimo del proveedor.
- **La información sensible**, como las contraseñas de Odoo.
