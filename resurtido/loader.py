"""Lectura de las cuatro hojas del Excel de inventario, sin interpretar los valores."""

import pandas as pd

SHEET_COLUMNS = {
    "Existencias": ["Codigo", "Descripcion", "Existencia", "Unidad", "Estatus"],
    "Minimos": ["Codigo", "Minimo", "Maximo"],
    "Producto_Proveedor": ["Codigo", "Proveedor_ID", "Costo_unitario_MXN", "Empaque_multiplo"],
    "Proveedores": ["Proveedor_ID", "Nombre", "Correo", "Pedido_minimo_MXN"],
}

# Fila 1: título descriptivo. Fila 2: encabezados. Fila 3 en adelante: datos.
HEADER_ROW_INDEX = 1
FIRST_DATA_ROW = 3

ROW_COLUMN = "fila_excel"


class ColumnError(Exception):
    """Falta una columna esperada en alguna hoja."""


def load_sheets(path):
    """Regresa {hoja: DataFrame} con valores crudos y la columna `fila_excel`.

    Los valores se leen como objeto (sin inferir tipos) para poder reportar
    exactamente lo que trae cada celda, por ejemplo `"1,250"` guardado como texto.
    """
    raw = pd.read_excel(
        path,
        sheet_name=list(SHEET_COLUMNS),
        header=HEADER_ROW_INDEX,
        dtype=object,
    )
    sheets = {}
    for name, columns in SHEET_COLUMNS.items():
        frame = raw[name]
        frame.columns = [str(column).strip() for column in frame.columns]
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ColumnError(f"En la hoja {name} falta la columna: " + ", ".join(missing))
        frame = frame[columns].copy()
        frame[ROW_COLUMN] = frame.index + FIRST_DATA_ROW
        # Un renglón totalmente vacío no es un registro: es espacio en blanco del Excel.
        frame = frame.dropna(how="all", subset=columns).reset_index(drop=True)
        sheets[name] = frame
    return sheets
