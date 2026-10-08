"""Escenarios de la capacidad `validacion-datos`."""

import csv
import subprocess
import sys

import pytest

from resurtido import validation as v
from resurtido.cli import DEFAULT_INPUT, REPO_ROOT
from resurtido.loader import ColumnError, load_sheets
from resurtido.report import write_exceptions
from tests.conftest import CLEAN_ROWS, write_workbook


def run(tmp_path, **overrides):
    path = write_workbook(tmp_path / "prueba.xlsx", overrides=overrides)
    return v.validate(load_sheets(path))


def of_type(result, tipo):
    return [e for e in result.exceptions if e.tipo == tipo]


def product(result, code):
    return next((p for p in result.products if p.codigo == code), None)


def with_stock(row_2):
    return [CLEAN_ROWS["Existencias"][0], row_2]


# Lectura


def test_excel_real_cantidad_de_renglones():
    sheets = load_sheets(DEFAULT_INPUT)

    assert {name: len(frame) for name, frame in sheets.items()} == {
        "Existencias": 52, "Minimos": 49, "Producto_Proveedor": 50, "Proveedores": 8,
    }


def test_columna_faltante_nombra_hoja_y_columna(tmp_path):
    path = write_workbook(tmp_path / "x.xlsx", columns={"Minimos": ["Codigo", "Minimo"]})

    with pytest.raises(ColumnError, match="Minimos.*Maximo"):
        load_sheets(path)


def test_columna_faltante_sin_traceback(tmp_path):
    path = write_workbook(tmp_path / "x.xlsx", columns={"Minimos": ["Codigo", "Minimo"]})

    result = subprocess.run(
        [sys.executable, "-m", "resurtido", "--input", str(path), "--output", str(tmp_path / "o")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_lectura_conserva_el_tipo_de_cada_celda(tmp_path):
    # pd.read_excel convertía el 1 en True cuando la columna también trae un booleano.
    path = write_workbook(tmp_path / "x.xlsx", overrides={"Existencias": [
        ["FTR-0001", "Martillo uña 16 oz", True, "PZA", "ACTIVO"],
        ["FTR-0002", "Desarmador plano 1/4", 1, "PZA", "ACTIVO"],
    ]})

    values = list(load_sheets(path)["Existencias"]["Existencia"])

    assert [(value, type(value)) for value in values] == [(True, bool), (1, int)]


# Existencias


def test_excel_limpio_sin_excepciones(tmp_path):
    result = run(tmp_path)

    assert result.exceptions == []
    assert [p.codigo for p in result.products] == ["FTR-0001", "FTR-0002"]


def test_existencia_texto_numerico_se_convierte(tmp_path):
    result = run(tmp_path, Existencias=with_stock(["FTR-0002", "Desarmador", "1,250", "PZA", "ACTIVO"]))

    [found] = of_type(result, v.EXISTENCIA_TEXTO)
    assert found.valor_original == "1,250"
    assert product(result, "FTR-0002").existencia == 1250


def test_existencia_texto_no_numerico_excluye(tmp_path):
    result = run(tmp_path, Existencias=with_stock(["FTR-0002", "Desarmador", "N/D", "PZA", "ACTIVO"]))

    assert of_type(result, v.EXISTENCIA_NO_NUMERICA)
    assert "FTR-0002" in result.excluded


def test_existencia_vacia_excluye(tmp_path):
    result = run(tmp_path, Existencias=with_stock(["FTR-0002", "Desarmador", None, "PZA", "ACTIVO"]))

    assert of_type(result, v.EXISTENCIA_VACIA)
    assert "FTR-0002" in result.excluded


def test_existencia_negativa_se_toma_como_cero_y_se_marca(tmp_path):
    result = run(tmp_path, Existencias=with_stock(["FTR-0002", "Desarmador", -4, "PZA", "ACTIVO"]))

    [found] = of_type(result, v.EXISTENCIA_NEGATIVA)
    assert found.valor_original == "-4"
    assert "existencia 0" in found.decision
    assert product(result, "FTR-0002").existencia == 0
    assert product(result, "FTR-0002").revisar


# Códigos


def test_codigo_con_formato_distinto_se_normaliza(tmp_path):
    result = run(tmp_path, Minimos=[["FTR-0001", 30, 60], [" ftr-0002 ", 12, 36]])

    [found] = of_type(result, v.CODIGO_FORMATO)
    assert "FTR-0002" in found.detalle
    assert product(result, "FTR-0002").minimo == 12


def test_codigo_corto_se_normaliza(tmp_path):
    result = run(tmp_path, Minimos=[["FTR-0001", 30, 60], ["FTR-2", 12, 36]])

    assert product(result, "FTR-0002").maximo == 36


def test_codigo_repetido_conserva_el_primero(tmp_path):
    rows = CLEAN_ROWS["Existencias"] + [["FTR-0002", "Desarmador", 999, "PZA", "ACTIVO"]]
    result = run(tmp_path, Existencias=rows)

    [found] = of_type(result, v.CODIGO_REPETIDO)
    assert found.fila_excel == 5
    assert product(result, "FTR-0002").existencia == 50
    assert result.repeated == 1


# Referencias cruzadas


def test_producto_sin_proveedor(tmp_path):
    result = run(tmp_path, Producto_Proveedor=[CLEAN_ROWS["Producto_Proveedor"][0]])

    [found] = of_type(result, v.SIN_PROVEEDOR)
    assert found.codigo == "FTR-0002"
    assert "FTR-0002" in result.excluded


def test_producto_sin_minimo(tmp_path):
    result = run(tmp_path, Minimos=[CLEAN_ROWS["Minimos"][0]])

    assert [e.codigo for e in of_type(result, v.SIN_MINIMO)] == ["FTR-0002"]
    assert "FTR-0002" in result.excluded


def test_codigo_ausente_de_existencias(tmp_path):
    result = run(tmp_path, Minimos=CLEAN_ROWS["Minimos"] + [["FTR-0021", 10, 30]])

    [found] = of_type(result, v.CODIGO_SIN_EXISTENCIA)
    assert found.codigo == "FTR-0021"
    assert product(result, "FTR-0021") is None


def test_proveedor_inexistente_pendiente(tmp_path):
    result = run(tmp_path, Producto_Proveedor=[CLEAN_ROWS["Producto_Proveedor"][0], ["FTR-0002", "P99", 66.26, 12]])

    [found] = of_type(result, v.PROVEEDOR_INEXISTENTE)
    assert found.decision == v.PENDING
    assert "FTR-0002" in result.excluded


# Mínimos y datos de compra


def test_minimo_mayor_que_maximo(tmp_path):
    result = run(tmp_path, Minimos=[CLEAN_ROWS["Minimos"][0], ["FTR-0002", 60, 40]])

    [found] = of_type(result, v.MINIMO_MAYOR_MAXIMO)
    assert "60" in found.detalle and "40" in found.detalle
    assert "FTR-0002" in result.excluded


def test_minimo_vacio(tmp_path):
    result = run(tmp_path, Minimos=[CLEAN_ROWS["Minimos"][0], ["FTR-0002", None, 40]])

    assert of_type(result, v.MINIMO_INVALIDO)
    assert "FTR-0002" in result.excluded


def test_multiplo_en_cero(tmp_path):
    result = run(tmp_path, Producto_Proveedor=[CLEAN_ROWS["Producto_Proveedor"][0], ["FTR-0002", "P01", 66.26, 0]])

    [found] = of_type(result, v.MULTIPLO_INVALIDO)
    assert found.decision == v.PENDING
    assert "FTR-0002" in result.excluded


def test_costo_no_numerico(tmp_path):
    result = run(tmp_path, Producto_Proveedor=[CLEAN_ROWS["Producto_Proveedor"][0], ["FTR-0002", "P01", "N/D", 12]])

    assert of_type(result, v.COSTO_INVALIDO)
    assert "FTR-0002" in result.excluded


def test_correo_invalido_excluye_productos_del_proveedor(tmp_path):
    result = run(tmp_path, Proveedores=[["P01", "Truper", "ventas.truper.mx", 5000]])

    [found] = of_type(result, v.CORREO_INVALIDO)
    assert found.codigo == "P01"
    assert result.products == []
    assert sorted(result.excluded) == ["FTR-0001", "FTR-0002"]


# Productos sospechosos


def test_producto_inactivo(tmp_path):
    result = run(tmp_path, Existencias=with_stock(["FTR-0002", "Desarmador", 50, "PZA", "INACTIVO"]))

    assert of_type(result, v.PRODUCTO_INACTIVO)
    assert "FTR-0002" in result.excluded


def test_mismo_producto_con_dos_codigos(tmp_path):
    result = run(
        tmp_path,
        Existencias=[
            ["FTR-0001", 'Tornillo 1/4 x 2" (caja)', 3, "CAJA", "ACTIVO"],
            ["FTR-0002", "Tornillo 1/4 x 2 (caja)", 50, "CAJA", "ACTIVO"],
        ],
    )

    found = of_type(result, v.POSIBLE_DUPLICADO)
    assert {e.codigo for e in found} == {"FTR-0001", "FTR-0002"}
    assert "FTR-0002" in found[0].detalle
    assert result.products == []


def test_unidad_distinta_a_la_descripcion_sigue_procesable(tmp_path):
    result = run(tmp_path, Existencias=with_stock(["FTR-0002", 'Clavo 2" (kg)', 50, "PZA", "ACTIVO"]))

    [found] = of_type(result, v.UNIDAD_INCONSISTENTE)
    assert "kg" in found.detalle
    assert product(result, "FTR-0002") is not None


# Reporte y conciliación


def test_reporte_utf8_con_bom_y_decisiones(tmp_path):
    result = run(tmp_path, Existencias=with_stock(["FTR-0002", "Desarmador", -4, "PZA", "ACTIVO"]))

    path = write_exceptions(result.exceptions, tmp_path)

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        [row] = list(csv.DictReader(handle))
    assert row["tipo"] == "Existencia negativa"
    assert row["fila_excel"] == "4"
    assert "revisión" in row["decision"]


def test_reporte_vacio_solo_encabezado(tmp_path):
    path = write_exceptions(run(tmp_path).exceptions, tmp_path)

    assert path.read_text(encoding="utf-8-sig").strip() == (
        "hoja,fila_excel,codigo,tipo,detalle,valor_original,decision"
    )


def test_tipo_sin_decision_sale_pendiente():
    item = v.DataException("Proveedores", 3, "P01", v.CORREO_INVALIDO, "x")

    assert item.decision == v.PENDING
    assert item.excludes


# Regresión sobre el Excel real: los 16 problemas de la revisión manual.


@pytest.fixture(scope="module")
def real():
    return v.validate(load_sheets(DEFAULT_INPUT))


def test_conciliacion_excel_real(real):
    assert real.rows_read == 52
    assert real.repeated + len(real.products) + len(real.excluded) == 52
    assert (real.repeated, len(real.products), len(real.excluded)) == (1, 43, 8)


@pytest.mark.parametrize(
    "hoja, codigo, tipo",
    [
        ("Existencias", "FTR-0003", v.EXISTENCIA_TEXTO),
        ("Existencias", "FTR-0016", v.EXISTENCIA_VACIA),
        ("Existencias", "FTR-0007", v.EXISTENCIA_NEGATIVA),
        ("Existencias", "FTR-0027", v.CODIGO_REPETIDO),
        ("Existencias", "FTR-0011", v.PRODUCTO_INACTIVO),
        ("Existencias", "FTR-0009", v.POSIBLE_DUPLICADO),
        ("Existencias", "FTR-0051", v.POSIBLE_DUPLICADO),
        ("Existencias", "FTR-0012", v.UNIDAD_INCONSISTENTE),
        ("Minimos", "FTR-0021", v.CODIGO_SIN_EXISTENCIA),
        ("Minimos", "FTR-0004", v.CODIGO_FORMATO),
        ("Minimos", "FTR-0013", v.CODIGO_FORMATO),
        ("Minimos", "FTR-0027", v.CODIGO_FORMATO),
        ("Minimos", "FTR-0019", v.MINIMO_MAYOR_MAXIMO),
        ("Existencias", "FTR-0024", v.SIN_MINIMO),
        ("Existencias", "FTR-0051", v.SIN_MINIMO),
        ("Existencias", "FTR-0052", v.SIN_MINIMO),
        ("Existencias", "FTR-0033", v.SIN_PROVEEDOR),
        ("Existencias", "FTR-0052", v.SIN_PROVEEDOR),
    ],
)
def test_problema_detectado_en_excel_real(real, hoja, codigo, tipo):
    assert any(
        e.hoja == hoja and e.codigo == codigo and e.tipo == tipo for e in real.exceptions
    )


def test_unidades_marcadas_en_excel_real(real):
    marked = {e.codigo for e in of_type(real, v.UNIDAD_INCONSISTENTE)}

    assert marked == {
        "FTR-0009", "FTR-0010", "FTR-0011", "FTR-0012", "FTR-0013",
        "FTR-0014", "FTR-0020", "FTR-0045", "FTR-0051",
    }


def test_sin_falsos_positivos_de_duplicado_en_excel_real(real):
    assert {e.codigo for e in of_type(real, v.POSIBLE_DUPLICADO)} == {"FTR-0009", "FTR-0051"}
