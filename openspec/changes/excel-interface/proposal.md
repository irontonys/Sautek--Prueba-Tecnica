# Proposal

## Why

El programa resuelve lo que pide la prueba, pero para usarlo hay que instalar Python, abrir una terminal y escribir `python -m resurtido`. Eso no lo va a hacer una persona de Compras, que trabaja todo el día en Excel. Odoo ya trae su propia interfaz, pero es un extra opcional y necesita Docker. Falta una forma de usar el proceso que se pidió (validar, ver y corregir excepciones, preparar pedidos y correos) sin salir de Excel y sin instalar nada.

## What Changes

- Un libro `excel/Resurtido.xlsm` con una hoja **Inicio** y botones que el comprador sigue en orden:
  1. **Cargar inventario**: elige el Excel que exporta el sistema y copia sus cuatro hojas al libro. El archivo original no se toca (supuesto 3).
  2. **Revisar datos**: aplica las mismas reglas y decisiones de la validación de Python y llena la hoja **Excepciones**, con un enlace a la celda de cada problema y un color por grupo (se corrigió solo, revisar, no se procesó).
  3. El comprador corrige directo en las hojas copiadas y vuelve a dar **Revisar datos**. La hoja **Correcciones** muestra cada celda que cambió contra lo que se cargó: hoja, celda, valor cargado y valor actual.
  4. **Preparar pedidos**: arma las hojas **Resumen** y **Detalle**, con las mismas columnas que `pedidos.xlsx`. En **Detalle** el comprador puede ajustar la cantidad; el importe, el total del proveedor y su estado se recalculan solos.
  5. **Generar correos**: escribe un borrador `.eml` por pedido que se envía, más `indice.csv`, en una carpeta `correos/` junto al libro. No envía nada.
- Toda la lógica vive en VBA dentro del libro: no hace falta instalar Python, y funciona en Excel para Windows y para Mac.
- El código VBA se versiona como texto en `excel/vba/` y un script arma el `.xlsm` a partir de él.
- Una prueba de paridad: el mismo inventario pasa por Python y por el libro, y las excepciones, los pedidos y los totales deben salir iguales.
- El README empieza por el libro. La terminal queda como alternativa técnica y Odoo como extra opcional.

## Capabilities

### New Capabilities
- `interfaz-excel`: el proceso de resurtido completo desde un libro de Excel con botones (carga, revisión y corrección de excepciones, pedidos y borradores de correo), con los mismos resultados que el programa de Python.

### Modified Capabilities

## Impact

- Código nuevo: `excel/vba/*.bas` (módulos VBA), `excel/build.py` (arma el libro) y `excel/Resurtido.xlsm` (entregable versionado).
- Pruebas nuevas: `tests/test_excel_paridad.py`. Necesita Microsoft Excel instalado y se omite sola donde no lo hay, así que `python -m pytest` sigue pasando en cualquier computadora.
- Sin cambios en `resurtido/` ni en sus salidas: Python sigue siendo el motor de referencia y el de la línea de comandos y Odoo.
- Sin dependencias nuevas de Python.
