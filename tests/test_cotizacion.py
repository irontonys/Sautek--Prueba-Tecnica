"""Escenarios de la capacidad `lectura-cotizacion` que viven en Python (lectura y comparación)."""

import shutil
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from resurtido.cotizacion import (
    CAMBIO_CANTIDAD, CAMBIO_PRECIO, IGUAL, NO_COTIZADO, NO_EN_RFQ, PARCIAL, SIN_EXISTENCIA,
    QuoteReadError, compare, extract_text, parse_line, parse_quote,
)

DEMO = Path(__file__).resolve().parent.parent / "docs" / "demo" / "cotizaciones"
COMPLETA = DEMO / "cotizacion_truper_P00001_completa.pdf"
PARCIAL_PDF = DEMO / "cotizacion_truper_P00001_surtido_parcial.pdf"
needs_pdftotext = pytest.mark.skipif(shutil.which("pdftotext") is None, reason="sin pdftotext")

RFQ = [
    ("FTR-0001", "Martillo uña 16 oz", 60, 559.58),
    ("FTR-0006", "Llave ajustable 10\"", 72, 116.00),
    ("FTR-0018", "Rodillo 9\"", 24, 352.17),
]


# Partidas

def test_renglon_de_tabla():
    line = '  1     FTR-0001     Martillo uña 16 oz     60     60     $559.58     $33,574.80     Disponible'

    item = parse_line(line)

    assert (item.codigo, item.cantidad, item.precio) == ("FTR-0001", 60, Decimal("559.58"))


def test_cantidad_surtible_es_la_que_cuadra_con_el_importe():
    # La descripción trae un 24 y la solicitada es 80: la surtible es la que da el importe.
    line = '3   FTR-0005   Nivel aluminio 24"   80   40   $56.76   $2,270.40   Parcial'

    assert parse_line(line).cantidad == 40


def test_sin_existencia_es_cero():
    line = '4   FTR-0006   Llave ajustable 10"   72   0   $116.00   $0.00   Sin existencia'

    assert parse_line(line).cantidad == 0


def test_agotado_es_cero_aunque_no_haya_importe():
    assert parse_line("FTR-0006 Llave ajustable 72 pzas $116.00 AGOTADO").cantidad == 0


def test_parrafo_con_codigos_sin_montos_no_es_partida():
    line = 'Aviso: solo podemos surtir 12 de 24 piezas de Rodillo 9" (FTR-0018) y nada de FTR-0006.'

    assert parse_line(line) is None


def test_codigo_mal_escrito_se_normaliza():
    assert parse_line("ftr-18   Rodillo   24   $352.17   $8,452.08").codigo == "FTR-0018"


def test_si_nada_cuadra_se_toma_la_ultima_cantidad_antes_del_precio():
    assert parse_line("FTR-0001 Martillo 60 50 $559.58 $1.00").cantidad == 50


def test_codigo_repetido_se_queda_la_primera():
    text = "FTR-0001 Martillo 60 $559.58 $33,574.80\nFTR-0001 Martillo 10 $1.00 $10.00"

    assert parse_quote(text)["FTR-0001"].cantidad == 60


# Archivos

@needs_pdftotext
def test_pdf_cotizacion_completa():
    quoted = parse_quote(extract_text(COMPLETA))

    assert len(quoted) == 11
    assert quoted["FTR-0018"].cantidad == 24
    assert quoted["FTR-0006"].precio == Decimal("116.00")


@needs_pdftotext
def test_pdf_cotizacion_parcial_con_parrafo_de_aviso():
    quoted = parse_quote(extract_text(PARCIAL_PDF))

    assert len(quoted) == 11
    assert quoted["FTR-0018"].cantidad == 12
    assert quoted["FTR-0006"].cantidad == 0
    assert quoted["FTR-0001"].cantidad == 60


def test_excel(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Código", "Descripción", "Cantidad", "Precio", "Importe"])
    sheet.append(["FTR-0001", "Martillo", 60, 559.58, 33574.8])
    sheet.append(["FTR-0018", "Rodillo", 12, 352.17, 4226.04])
    path = tmp_path / "cotizacion.xlsx"
    workbook.save(path)

    quoted = parse_quote(extract_text(path))

    assert quoted["FTR-0001"].cantidad == 60
    assert quoted["FTR-0018"].cantidad == 12


def test_csv(tmp_path):
    path = tmp_path / "cotizacion.csv"
    path.write_text("codigo,cantidad,precio,importe\nFTR-0001,60,559.58,33574.80\n", encoding="utf-8")

    assert parse_quote(extract_text(path))["FTR-0001"].precio == Decimal("559.58")


def test_tipo_de_archivo_no_soportado(tmp_path):
    path = tmp_path / "cotizacion.docx"
    path.write_bytes(b"x")

    with pytest.raises(QuoteReadError, match="solo PDF, Excel"):
        extract_text(path)


# Comparación

def _status(rows):
    return {row.codigo: row.estatus for row in rows}


def test_comparacion_surtido_parcial_y_sin_existencia():
    quoted = parse_quote(
        "FTR-0001 Martillo 60 60 $559.58 $33,574.80\n"
        "FTR-0006 Llave 72 0 $116.00 $0.00 Sin existencia\n"
        "FTR-0018 Rodillo 24 12 $352.17 $4,226.04 Parcial: 12 de 24"
    )

    rows = compare(RFQ, quoted)

    assert _status(rows) == {"FTR-0001": IGUAL, "FTR-0006": SIN_EXISTENCIA, "FTR-0018": PARCIAL}
    rodillo = next(r for r in rows if r.codigo == "FTR-0018")
    assert (rodillo.cantidad_rfq, rodillo.cantidad_cotizada) == (24, 12)


def test_comparacion_precio_cantidad_mayor_faltante_y_extra():
    quoted = parse_quote(
        "FTR-0001 Martillo 60 $600.00 $36,000.00\n"
        "FTR-0018 Rodillo 30 $352.17 $10,565.10\n"
        "FTR-0099 Producto nuevo 5 $10.00 $50.00"
    )

    rows = compare(RFQ, quoted)

    assert _status(rows) == {
        "FTR-0001": CAMBIO_PRECIO, "FTR-0006": NO_COTIZADO, "FTR-0018": CAMBIO_CANTIDAD,
        "FTR-0099": NO_EN_RFQ,
    }


def test_cambio_de_cantidad_prevalece_y_conserva_el_precio_nuevo():
    rows = compare(RFQ, parse_quote("FTR-0018 Rodillo 12 $400.00 $4,800.00"))

    rodillo = next(r for r in rows if r.codigo == "FTR-0018")
    assert (rodillo.estatus, rodillo.precio_cotizado) == (PARCIAL, Decimal("400.00"))
