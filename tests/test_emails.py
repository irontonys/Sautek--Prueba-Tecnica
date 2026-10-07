"""Escenarios de la capacidad `borradores-correo`."""

import csv
from datetime import date
from email import policy
from email.parser import BytesParser

import pytest

from resurtido import cli
from resurtido.emails import build_draft, write_drafts
from resurtido.loader import load_sheets
from resurtido.orders import build_orders
from resurtido.validation import Supplier, validate
from tests.test_orders import make_product

DAY = date(2026, 10, 9)


def make_orders(*products, pedido_minimo=0):
    suppliers = {
        "P01": Supplier("P01", "Distribuidora Truper Norte", "ventas@truper-norte.mx", pedido_minimo, 3),
        "P02": Supplier("P02", "Aceros del Golfo", "pedidos@atgolfo.mx", 0, 4),
    }
    orders, _ = build_orders(list(products), suppliers)
    return orders


def read_eml(path):
    with path.open("rb") as handle:
        return BytesParser(policy=policy.default).parse(handle)


def read_index(folder):
    with (folder / "indice.csv").open(encoding="utf-8-sig", newline="") as handle:
        return {row["proveedor_id"]: row for row in csv.DictReader(handle)}


# Encabezados y contenido


def test_encabezados_del_borrador():
    [order, _] = make_orders(make_product())

    message = build_draft(order, DAY)

    assert message["To"] == "ventas@truper-norte.mx"
    assert "Pedido de resurtido" in message["Subject"] and "2026-10-09" in message["Subject"]
    assert message["X-Unsent"] == "1"
    assert message["From"] is None


def test_contenido_con_productos_y_total():
    [order, _] = make_orders(
        make_product("FTR-0001", existencia=3, maximo=60, multiplo=6, costo=559.58),
        make_product("FTR-0002", existencia=0, maximo=36, multiplo=12, costo=66.26),
    )

    body = build_draft(order, DAY).get_content()

    assert "Estimado equipo de Distribuidora Truper Norte" in body
    assert "FTR-0001" in body and "FTR-0002" in body
    assert "$33,574.80" in body and "$2,385.36" in body
    assert f"Total del pedido: ${order.total:,.2f}" in body
    assert "9 de octubre de 2026" in body
    assert "fecha de entrega" in body


def test_marca_de_revision_no_aparece_en_el_correo():
    [order, _] = make_orders(make_product("FTR-0007", existencia=0, revisar=True))

    body = build_draft(order, DAY).get_content().lower()

    assert "revis" not in body and "negativ" not in body


# Carpeta e índice


def test_un_borrador_por_pedido_que_se_envia(tmp_path):
    orders = make_orders(make_product("FTR-0001"), make_product("FTR-0002", existencia=50))

    folder = write_drafts(orders, tmp_path, DAY)

    assert sorted(p.name for p in folder.glob("*.eml")) == ["P01_distribuidora-truper-norte.eml"]
    message = read_eml(folder / "P01_distribuidora-truper-norte.eml")
    assert message["To"] == "ventas@truper-norte.mx"


def test_pedido_que_no_se_envia_sin_borrador_y_en_indice(tmp_path):
    orders = make_orders(make_product(costo=10), pedido_minimo=15000)

    folder = write_drafts(orders, tmp_path, DAY)

    assert list(folder.glob("*.eml")) == []
    index = read_index(folder)
    assert index["P01"]["estado"] == "No se envía"
    assert index["P01"]["archivo"] == ""
    assert "P02" not in index  # sin productos por pedir


def test_segueta_marcada_en_el_indice(tmp_path):
    orders = make_orders(make_product("FTR-0007", existencia=0, revisar=True), make_product("FTR-0001"))

    index = read_index(write_drafts(orders, tmp_path, DAY))

    assert index["P01"]["revisar_antes_de_enviar"] == "FTR-0007"


def test_borradores_viejos_se_eliminan(tmp_path):
    folder = tmp_path / "correos"
    folder.mkdir()
    (folder / "P09_viejo.eml").write_text("viejo", encoding="utf-8")
    (folder / "notas.txt").write_text("no se toca", encoding="utf-8")

    write_drafts(make_orders(make_product()), tmp_path, DAY)

    assert not (folder / "P09_viejo.eml").exists()
    assert (folder / "notas.txt").exists()


# Regresión sobre el Excel real


@pytest.fixture(scope="module")
def real_drafts(tmp_path_factory):
    result = validate(load_sheets(cli.DEFAULT_INPUT))
    orders, _ = build_orders(result.products, result.suppliers)
    folder = write_drafts(orders, tmp_path_factory.mktemp("salida"), DAY)
    return folder, {o.supplier.proveedor_id: o for o in orders}


def test_seis_borradores_excel_real(real_drafts):
    folder, _ = real_drafts

    ids = sorted(p.name.split("_")[0] for p in folder.glob("*.eml"))
    assert ids == ["P01", "P02", "P03", "P04", "P06", "P07"]


def test_totales_iguales_a_pedidos_excel_real(real_drafts):
    folder, orders = real_drafts

    for path in folder.glob("*.eml"):
        order = orders[path.name.split("_")[0]]
        assert f"Total del pedido: ${order.total:,.2f}" in read_eml(path).get_content()
    assert read_index(folder)["P01"]["revisar_antes_de_enviar"] == "FTR-0007"
