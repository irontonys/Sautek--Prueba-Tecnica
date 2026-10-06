# Proposal

## Why

El repositorio solo tiene el Excel de entrada y la estructura de OpenSpec. Antes de escribir la lógica de resurtido hace falta un esqueleto de proyecto Python que cualquiera pueda instalar y correr en otra computadora (la prueba lo pide explícitamente) y un lugar donde dejar por escrito los supuestos del caso desde el primer día.

## What Changes

- Estructura de paquete Python (`resurtido/`) con un punto de entrada ejecutable por línea de comandos.
- El comando recibe la ruta del Excel de entrada y la carpeta de salida, con valores por omisión que apuntan a `data/inventario_ferreteria_garza.xlsx` y `output/`.
- Si el Excel no existe o no se puede abrir, el comando termina con un mensaje claro en español y un código de salida distinto de cero, sin mostrar un traceback.
- Si el Excel abre, el comando confirma que encontró las cuatro hojas esperadas y avisa cuáles faltan. Todavía no calcula pedidos.
- `requirements.txt` con dependencias fijadas (pandas, openpyxl), `.gitignore` para Python y entornos virtuales, y un README con los pasos de instalación y ejecución.
- `SUPUESTOS.md` con los supuestos iniciales del caso (por ejemplo, que el Excel es una muestra de 52 productos y 8 proveedores aunque el caso habla de unos 800 y 25).

## Capabilities

### New Capabilities
- `ejecucion-cli`: cómo se invoca el programa de resurtido, qué entradas acepta, dónde deja sus salidas y cómo responde cuando la entrada no existe o está incompleta.

### Modified Capabilities

## Impact

- Código nuevo: paquete `resurtido/` y su punto de entrada.
- Dependencias nuevas: pandas y openpyxl, con versiones fijadas en `requirements.txt`.
- Documentación: README reescrito, `SUPUESTOS.md` nuevo.
- Las fases siguientes (validación, cálculo, agrupación y correos) se construyen sobre este punto de entrada.
