# Tasks

## 1. Proyecto y dependencias

- [x] 1.1 Crear `.gitignore` de Python (venv, `__pycache__`, `.pytest_cache`, `.DS_Store`) y verificar con `git status` que un venv local no aparece como archivo sin seguimiento
- [x] 1.2 Crear `requirements.txt` (pandas, openpyxl fijados) y `requirements-dev.txt` (pytest) y verificar que `pip install -r requirements-dev.txt` termina sin errores en un venv limpio

## 2. Punto de entrada

- [ ] 2.1 Crear el paquete `resurtido/` con `__main__.py` y argumentos `--input`/`--output` con sus valores por omisión, y verificar que `python -m resurtido --help` muestra ambos
- [ ] 2.2 Manejar archivo inexistente o no legible como Excel con un mensaje en español y código de salida distinto de cero, y verificar ambos casos sin que aparezca traceback
- [ ] 2.3 Verificar la presencia de las cuatro hojas esperadas, reportando por nombre las faltantes, y verificar que `python -m resurtido` sobre el Excel real termina con código 0 e informa las cuatro hojas
- [ ] 2.4 Crear la carpeta de salida si no existe y verificar que tras la ejecución existe `output/`

## 3. Pruebas

- [ ] 3.1 Escribir pruebas pytest para cada escenario de `ejecucion-cli` (sin argumentos, rutas personalizadas, archivo inexistente, archivo no Excel, hoja faltante) y verificar que `pytest` pasa

## 4. Documentación

- [ ] 4.1 Reescribir `README.md` con requisitos (Python 3.10 o superior), instalación en venv y comando de ejecución, y verificar siguiendo sus pasos al pie de la letra en un clon limpio
- [ ] 4.2 Crear `SUPUESTOS.md` con los supuestos iniciales (muestra de 52 productos y 8 proveedores, encabezado en la fila 2, los correos no se envían) y verificar que el README lo enlaza
