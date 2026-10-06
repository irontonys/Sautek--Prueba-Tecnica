# Sautek — Prueba técnica: Coordinación de procesos y desarrollo

Programa de resurtido semanal para el caso **Ferretera Garza**. Lee el Excel de inventario y arma los pedidos de la semana por proveedor, con un borrador de correo para cada uno y un reporte de los registros que no pudo procesar.

> Estado: en construcción por fases. Por ahora el programa valida el Excel de entrada; el cálculo de pedidos llega en las siguientes fases.

## Requisitos

- Python 3.10 o superior
- Git

## Instalación

```bash
git clone https://github.com/irontonys/Sautek--Prueba-Tecnica.git
cd Sautek--Prueba-Tecnica
python3 -m venv .venv
```

Activa el entorno virtual:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Uso

Desde la raíz del repositorio:

```bash
python -m resurtido
```

Por omisión lee `data/inventario_ferreteria_garza.xlsx` y escribe en `output/`. Para usar otros archivos:

```bash
python -m resurtido --input otro_inventario.xlsx --output resultados/
```

Si el archivo no existe, no es un Excel o le falta alguna de las hojas `Existencias`, `Minimos`, `Producto_Proveedor` o `Proveedores`, el programa lo dice y termina con código de salida 1.

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Estructura

| Ruta | Contenido |
|---|---|
| `data/` | Excel de entrada, tal como llegó |
| `resurtido/` | Código del programa |
| `tests/` | Pruebas automatizadas |
| `output/` | Archivos generados por el programa |
| `openspec/` | Propuestas, specs y tareas de cada fase (OpenSpec) |

## Supuestos

Lo que el caso no especifica y decidí asumir está en [SUPUESTOS.md](SUPUESTOS.md).
