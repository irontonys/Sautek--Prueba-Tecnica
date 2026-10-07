"""Escritura del reporte de excepciones."""

import csv
from collections import Counter

EXCEPTIONS_FILE = "excepciones.csv"
EXCEPTION_COLUMNS = ["hoja", "fila_excel", "codigo", "tipo", "detalle", "valor_original", "decision"]


def write_exceptions(exceptions, output_dir):
    path = output_dir / EXCEPTIONS_FILE
    # utf-8-sig agrega el BOM para que Excel en Windows muestre bien los acentos.
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(EXCEPTION_COLUMNS)
        for item in exceptions:
            writer.writerow([getattr(item, column) for column in EXCEPTION_COLUMNS])
    return path


def summary_lines(result):
    lines = [
        f"Renglones leídos en Existencias: {result.rows_read}",
        f"  Repetidos (se conserva el primero): {result.repeated}",
        f"  Procesables: {len(result.products)}",
        f"  No procesables: {len(result.excluded)}",
        f"Excepciones: {len(result.exceptions)}",
    ]
    for tipo, count in sorted(Counter(e.tipo for e in result.exceptions).items()):
        lines.append(f"  {tipo}: {count}")
    return lines
