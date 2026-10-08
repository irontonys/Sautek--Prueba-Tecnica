"""Paridad entre `excel/Resurtido.xlsm` y el programa de Python (capacidad `interfaz-excel`).

Corre el mismo inventario con la misma fecha por los dos caminos y compara las
excepciones, los pedidos y los borradores de correo. Del lado del libro usa la macro
sin diálogos `modUI.RunHeadless`, controlada con AppleScript, así que solo corre en
una Mac con Microsoft Excel; si no lo hay, se omite. Con RESURTIDO_SKIP_EXCEL=1 también
se omite, para quien no quiera que la prueba tome el control de Excel.
"""

import csv
import filecmp
import os
import shutil
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path

import pytest

from resurtido.cli import check_sheets, load_sheets, read_sheet_names
from resurtido.emails import EMAILS_DIR, write_drafts
from resurtido.orders import build_orders
from resurtido.report import write_exceptions
from resurtido.validation import sort_exceptions, validate
from tests.conftest import write_workbook

ROOT = Path(__file__).resolve().parent.parent
WORKBOOK = ROOT / "excel" / "Resurtido.xlsm"
EXCEL_APP = Path("/Applications/Microsoft Excel.app")
# Excel para Mac corre en sandbox: en su propia carpeta lee y escribe sin pedir permiso.
EXCEL_TMP = Path.home() / "Library" / "Containers" / "com.microsoft.Excel" / "Data" / "tmp"
DAY = date(2026, 3, 5)

SCRIPT = """
on run {workbookPath, workbookName, inputPath, outputDir, isoDate}
    set workbookFile to (POSIX file workbookPath) as alias
    tell application "Microsoft Excel"
        with timeout of 600 seconds
            open workbookFile
            set outcome to run VB macro ("'" & workbookName & "'!modUI.RunHeadless") ¬
                arg1 inputPath arg2 outputDir arg3 isoDate
            close workbook workbookName saving no
        end timeout
        return outcome
    end tell
end run
"""


def excel_unavailable():
    if os.environ.get("RESURTIDO_SKIP_EXCEL"):
        return "RESURTIDO_SKIP_EXCEL está definida"
    if sys.platform != "darwin" or not EXCEL_APP.exists():
        return "Microsoft Excel para Mac no está instalado"
    if not WORKBOOK.exists():
        return f"no existe {WORKBOOK}; ver excel/README.md"
    return None


pytestmark = pytest.mark.skipif(excel_unavailable() is not None, reason=str(excel_unavailable()))


@pytest.fixture
def excel_dir():
    folder = EXCEL_TMP / f"resurtido-paridad-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True)
    yield folder
    shutil.rmtree(folder, ignore_errors=True)


def run_python(source, output):
    """La secuencia de `python -m resurtido`, con la fecha fija de la prueba."""
    check_sheets(read_sheet_names(source))
    result = validate(load_sheets(source))
    orders, order_exceptions = build_orders(result.products, result.suppliers)
    result.exceptions = sort_exceptions(result.exceptions + order_exceptions)
    output.mkdir(parents=True, exist_ok=True)
    write_exceptions(result.exceptions, output)
    write_drafts(orders, output, DAY)
    return orders


def run_excel(source, folder):
    """Copia el libro y el inventario a la carpeta de Excel y corre RunHeadless."""
    workbook = folder / f"paridad-{folder.name[-8:]}.xlsm"
    shutil.copy(WORKBOOK, workbook)
    source_copy = folder / source.name
    shutil.copy(source, source_copy)
    output = folder / "salida"
    output.mkdir()
    completed = subprocess.run(
        ["osascript", "-e", SCRIPT, str(workbook), workbook.name, str(source_copy),
         str(output), DAY.isoformat()],
        capture_output=True, text=True, timeout=660,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("OK "), completed.stdout
    return output


def number_text(value):
    """Como escribe el libro un número del inventario: entero sin decimales o repr."""
    return str(int(value)) if value == int(value) else repr(float(value))


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))[1:]


def expected_summary(orders):
    return [
        [o.supplier.proveedor_id, o.supplier.nombre, o.supplier.correo, str(len(o.lines)),
         f"{o.total:.2f}", number_text(o.supplier.pedido_minimo), o.estado]
        for o in orders
    ]


def expected_detail(orders):
    return [
        [o.supplier.proveedor_id, o.supplier.nombre, line.product.codigo,
         line.product.descripcion, number_text(line.product.existencia),
         number_text(line.product.minimo), number_text(line.product.maximo),
         str(int(line.product.empaque_multiplo)), str(line.cantidad),
         number_text(line.product.costo_unitario), f"{line.importe:.2f}", o.estado,
         "Sí" if line.product.revisar else ""]
        for o in orders
        for line in o.lines
    ]


def file_lines(path):
    """Los bytes del archivo partidos en renglones, para que pytest muestre cuál difiere."""
    return path.read_bytes().decode("utf-8").splitlines(keepends=True)


def assert_same_folder(left, right):
    comparison = filecmp.dircmp(left, right)
    assert sorted(comparison.left_list) == sorted(comparison.right_list)
    for name in comparison.left_list:
        assert file_lines(left / name) == file_lines(right / name), name


def real_workbook(_tmp_path):
    return ROOT / "data" / "inventario_ferreteria_garza.xlsx"


# Los tipos de excepción que el Excel real no trae, más valores de borde de la lectura
# (texto con miles y signo, booleano, espacios, renglón vacío, códigos en minúsculas).
EDGE_ROWS = {
    "Existencias": [
        ["FTR-0001", "Martillo uña 16 oz", "abc", "PZA", "ACTIVO"],
        [None, "Sin código", 5, "PZA", "ACTIVO"],
        ["XYZ-9", "Raro", 5, "PZA", "ACTIVO"],
        ["FTR-0002", "Desarmador", "-1,250.5", "PZA", "ACTIVO"],
        ["FTR-0003", "Pinza", 12.5, "PZA", None],
        ["FTR-0004", "Llave", True, "PZA", "activo"],
        ["ftr4", "Llave repetida", 3, "PZA", "ACTIVO"],
        ["FTR-0005", 'Cinta "aislante"  negra (M)', 2, None, "ACTIVO"],
        ["FTR-0006", "cinta aislante negra (m)", 2, "M", "ACTIVO"],
        ["FTR-0007", "Foco", "  ", "PZA", "ACTIVO"],
        ["FTR-0008", "Clavo", -1e-05, "PZA", "ACTIVO"],
        [None, None, None, None, None],
        ["FTR-0009", "Tubo", 1234567, "PZA", "ACTIVO"],
        ["FTR-0010", "Rondana", 1, "PZA", "ACTIVO"],
    ],
    "Minimos": [
        ["FTR-0001", 30, 60],
        ["FTR-0001", 1, 2],
        ["FTR-0002", "x", 5],
        ["FTR-0003", -1, 10],
        ["FTR-0005", 10.5, 20],
        ["FTR-0006", 5, 5],
        ["FTR-0007", 1, 2],
        ["FTR-0008", 1, 2],
        [None, 1, 2],
        ["ABC", 1, 2],
        ["FTR-0009", 2000000, 3000000],
        ["FTR-0010", 20, 10],
    ],
    "Producto_Proveedor": [
        ["FTR-0001", "P01", 559.58, 6],
        ["FTR-0002", "P09", 0, 2.5],
        ["FTR-0003", "P02", 10, "6"],
        ["FTR-0005", "p03", 5, 1],
        ["FTR-0006", "P04", 1, 1],
        ["FTR-0007", "P01", 1, 1],
        ["FTR-0007", "P01", 2, 2],
        ["FTR-0008", "P01", 1, 1],
        ["FTR-0009", "P05", 1.5, 10],
        ["FTR-0010", "P01", 3, 1],
    ],
    "Proveedores": [
        ["P01", "Distribuidora Truper Norte", "ventas@truper-norte.mx", 5000],
        ["P02", "Dos", "ventas@@x.mx", 100],
        ["P03", "Tres", "a@b.c", "1000"],
        ["P04", "Cuatro", "c@d.com", -5],
        ["P01", "Repetido", "r@r.com", 1],
        [None, "Sin id", "s@s.com", 1],
        [" p05 ", " Cinco ", "x @y.com", 0],
    ],
}

# Cálculo de pedidos: máximo con decimales, costos de 3 y 4 decimales que redondean
# distinto en el importe y en el texto del correo, existencia negativa y un proveedor
# que no llega a su mínimo.
ORDER_ROWS = {
    "Existencias": [
        ["FTR-0001", "Clavo (kg)", 2.4, "KG", "ACTIVO"],
        ["FTR-0002", "Cable", 0, "M", "ACTIVO"],
        ["FTR-0003", "Taquete", 10, "PZA", "ACTIVO"],
        ["FTR-0004", "Lija", 5, "PZA", "ACTIVO"],
        ["FTR-0005", "Broca", -3, "PZA", "ACTIVO"],
        ["FTR-0006", "Cinta", 99, "PZA", "ACTIVO"],
    ],
    "Minimos": [
        ["FTR-0001", 10, 25.5],
        ["FTR-0002", 100, 333],
        ["FTR-0003", 10, 40],
        ["FTR-0004", 6, 6],
        ["FTR-0005", 1, 7],
        ["FTR-0006", 5, 10],
    ],
    "Producto_Proveedor": [
        ["FTR-0001", "P01", 66.255, 4],
        ["FTR-0002", "P02", 12.345, 50],
        ["FTR-0003", "P01", 1, 1],
        ["FTR-0004", "P03", 0.105, 3],
        ["FTR-0005", "P03", 1234.5678, 2],
        ["FTR-0006", "P04", 1, 1],
    ],
    "Proveedores": [
        ["P01", "Uno", "a@b.mx", 1590.12],
        ["P02", "Dos", "c@d.mx", 4500],
        ["P03", "Tres", "e@f.mx", 0],
        ["P04", "Cuatro", "g@h.mx", 10],
    ],
}


def edge_workbook(tmp_path):
    return write_workbook(tmp_path / "bordes.xlsx", overrides=EDGE_ROWS)


def order_workbook(tmp_path):
    return write_workbook(tmp_path / "pedidos_bordes.xlsx", overrides=ORDER_ROWS)


def clean_workbook(tmp_path):
    return write_workbook(tmp_path / "limpio.xlsx")


CASES = {
    "excel_real": real_workbook,
    "tipos_de_excepcion": edge_workbook,
    "calculo_de_pedidos": order_workbook,
    "libro_limpio": clean_workbook,
}


@pytest.mark.parametrize("case", CASES)
def test_libro_y_python_coinciden(case, tmp_path, excel_dir):
    source = CASES[case](tmp_path)
    python_output = tmp_path / "python"
    orders = run_python(source, python_output)

    excel_output = run_excel(source, excel_dir)

    assert file_lines(excel_output / "excepciones.csv") == \
        file_lines(python_output / "excepciones.csv")
    assert read_csv(excel_output / "resumen.csv") == expected_summary(orders)
    assert read_csv(excel_output / "detalle.csv") == expected_detail(orders)
    assert_same_folder(python_output / EMAILS_DIR, excel_output / EMAILS_DIR)
