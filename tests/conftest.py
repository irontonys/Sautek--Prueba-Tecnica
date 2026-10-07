"""Generador de libros de Excel de prueba con la misma forma que el real."""

from openpyxl import Workbook

from resurtido.loader import SHEET_COLUMNS

CLEAN_ROWS = {
    "Existencias": [
        ["FTR-0001", "Martillo uña 16 oz", 3, "PZA", "ACTIVO"],
        ["FTR-0002", "Desarmador plano 1/4", 50, "PZA", "ACTIVO"],
    ],
    "Minimos": [
        ["FTR-0001", 30, 60],
        ["FTR-0002", 12, 36],
    ],
    "Producto_Proveedor": [
        ["FTR-0001", "P01", 559.58, 6],
        ["FTR-0002", "P01", 66.26, 12],
    ],
    "Proveedores": [
        ["P01", "Distribuidora Truper Norte", "ventas@truper-norte.mx", 5000],
    ],
}


def write_workbook(path, sheets=None, overrides=None, columns=None):
    """Escribe un libro con título en la fila 1, encabezado en la 2 y datos desde la 3.

    `overrides` reemplaza los renglones de una hoja; `columns` sus encabezados;
    `sheets` limita qué hojas se crean.
    """
    overrides = overrides or {}
    columns = columns or {}
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name in sheets or SHEET_COLUMNS:
        sheet = workbook.create_sheet(name)
        sheet.append([f"Hoja {name} de prueba"])
        sheet.append(columns.get(name, SHEET_COLUMNS[name]))
        for row in overrides.get(name, CLEAN_ROWS[name]):
            sheet.append(row)
    workbook.save(path)
    return path
