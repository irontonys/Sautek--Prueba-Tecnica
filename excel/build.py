"""Arma `excel/Resurtido.xlsm` a partir de los módulos de `excel/vba/` con Excel para Mac.

Uso, desde la raíz del repositorio:

    python excel/build.py

Abre `excel/tools/constructor.xlsm` en Excel, ejecuta su macro `Constructor.Build`
(importa cada `.bas` en un libro nuevo, corre `modWorkbook.BuildWorkbook` y lo guarda)
y lo cierra. No toca los demás libros abiertos. Solo hace falta para quien cambia el
código VBA: el comprador usa el `.xlsm` ya armado.
"""

import re
import subprocess
import sys
from pathlib import Path

EXCEL_DIR = Path(__file__).resolve().parent
VBA_DIR = EXCEL_DIR / "vba"
CONSTRUCTOR = EXCEL_DIR / "tools" / "constructor.xlsm"
TARGET = EXCEL_DIR / "Resurtido.xlsm"

SCRIPT = """
on run {constructorPath, excelDir}
    set constructorFile to (POSIX file constructorPath) as alias
    tell application "Microsoft Excel"
        open constructorFile
        -- Margen para que alguien conceda en Excel el acceso a los modulos nuevos.
        with timeout of 600 seconds
            set outcome to run VB macro "'constructor.xlsm'!Constructor.Build" arg1 excelDir
        end timeout
        close workbook "constructor.xlsm" saving no
        return outcome
    end tell
end run
"""


class BuildError(Exception):
    """El libro no se pudo armar; el mensaje dice por qué."""


def check_ascii():
    """El editor de VBA no importa bien UTF-8: los acentos van como \\uXXXX dentro de U()."""
    problems = []
    for path in sorted(VBA_DIR.glob("*.bas")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.isascii():
                problems.append(f"{path.name}:{number}: {line.strip()}")
    if problems:
        raise BuildError("Hay caracteres fuera de ASCII; escríbelos como \\uXXXX:\n" + "\n".join(problems))


PROCEDURE_START = re.compile(r"^(Public |Private |Friend )?(Static )?(Sub|Function|Property) ", re.I)
PROCEDURE_END = re.compile(r"^End (Sub|Function|Property)\b", re.I)
DECLARATION = re.compile(r"^(Public|Private|Global|Dim|Const|Type|Enum)\b", re.I)


def check_declarations():
    """VBA exige las variables, constantes y tipos del modulo antes de la primera funcion.

    Si no, el modulo no compila, y llamado desde AppleScript Excel no muestra el error:
    se queda en "break" esperando y al restablecerlo se cierra.
    """
    problems = []
    for path in sorted(VBA_DIR.glob("*.bas")):
        seen_procedure = inside = False
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            code = line.strip()
            if PROCEDURE_START.match(code):
                seen_procedure = inside = True
            elif PROCEDURE_END.match(code):
                inside = False
            elif seen_procedure and not inside and DECLARATION.match(code):
                problems.append(f"{path.name}:{number}: {code}")
    if problems:
        raise BuildError("Declaraciones despues de una funcion; muevelas al inicio del modulo:\n"
                         + "\n".join(problems))


def build():
    if sys.platform != "darwin":
        raise BuildError("El armado usa AppleScript y solo corre en macOS con Microsoft Excel.")
    if not CONSTRUCTOR.exists():
        raise BuildError(f"No existe {CONSTRUCTOR}; ver excel/README.md para crearlo.")
    check_ascii()
    check_declarations()
    completed = subprocess.run(
        ["osascript", "-e", SCRIPT, str(CONSTRUCTOR), str(EXCEL_DIR)],
        capture_output=True,
        text=True,
        timeout=660,
    )
    outcome = completed.stdout.strip()
    if completed.returncode != 0:
        raise BuildError(f"Excel no respondió: {completed.stderr.strip()}")
    if not outcome.startswith("OK"):
        raise BuildError(outcome or "La macro no regresó resultado.")
    return TARGET


def main():
    try:
        path = build()
    except (BuildError, subprocess.TimeoutExpired) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Libro armado: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
