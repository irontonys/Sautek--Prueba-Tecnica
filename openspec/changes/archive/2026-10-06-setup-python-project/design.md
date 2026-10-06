# Design

## Context

El repo es greenfield: solo contiene `data/inventario_ferreteria_garza.xlsx` y la estructura de OpenSpec. El revisor va a clonar el repositorio y correrlo en su propia máquina siguiendo el README, así que la instalación tiene que ser corta y no depender de nada propio de esta computadora. Python local: 3.13.

## Goals / Non-Goals

**Goals:**
- Que alguien instale y corra el programa en otra computadora con unos 3 comandos.
- Un punto de entrada único sobre el que las fases siguientes agreguen validación, cálculo y salidas.

**Non-Goals:**
- Leer el contenido de las hojas, validar datos o calcular pedidos (eso va en las fases siguientes).
- Empaquetar para PyPI, armar una imagen Docker o configurar CI.

## Decisions

- **Ejecución con `python -m resurtido`** en lugar de un script suelto o un paquete instalable con `pyproject.toml` y entry points. No requiere `pip install -e .` y funciona igual en macOS, Windows y Linux. Alternativa descartada: un `main.py` en la raíz, que con varios módulos queda desordenado.
- **`argparse` de la biblioteca estándar** para los argumentos, en lugar de click o typer: son dos argumentos y no hace falta otra dependencia.
- **pandas + openpyxl con versiones fijadas** en `requirements.txt`. pandas facilita los cruces entre hojas que vienen en las fases siguientes, y openpyxl es el motor que pandas usa para leer y escribir `.xlsx`. Fijar versiones evita que el programa se comporte distinto en la máquina del revisor.
- **Python mínimo 3.10**, documentado en el README. Es lo bastante reciente para la sintaxis moderna de tipos y lo bastante viejo para que la mayoría de las máquinas ya lo tenga.
- **Errores de entrada como mensajes, no como excepciones.** El punto de entrada atrapa los errores de archivo y de formato, imprime el mensaje en español a stderr y regresa un código de salida distinto de cero. Así se cumple desde ahora la regla de "no tronar" que aplica a todo el programa.
- **`output/` sí se versiona.** La prueba pide entregar los archivos que generó el programa, así que no va en `.gitignore`. Mientras esta fase no genere archivos, solo se crea la carpeta.
- **Pruebas con pytest** (dependencia de desarrollo en `requirements-dev.txt`) para los escenarios de la spec. Mantiene `requirements.txt` limpio para quien solo quiere correr el programa.

## Risks / Trade-offs

- [Versiones fijadas que no tengan wheel para la versión de Python del revisor] → fijar versiones recientes con soporte de 3.10 a 3.13 y probar la instalación en un venv limpio antes de cerrar la fase.
- [Windows con rutas o codificación distintas] → usar `pathlib` para las rutas y escribir los archivos en UTF-8 de forma explícita.
