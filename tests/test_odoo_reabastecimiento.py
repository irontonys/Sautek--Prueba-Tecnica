"""Escenarios de la capacidad `reabastecimiento-odoo`, contra un Odoo simulado."""

import csv
from decimal import Decimal

from resurtido import cli as resurtido_cli
from resurtido.loader import load_sheets
from resurtido.odoo import cli
from resurtido.odoo.reconcile import CUADRA, EN_PROCESO, NO_CUADRA, reconcile, reconciliation_lines
from resurtido.odoo.replenish import (
    Rfq, cancel_previous, post_notes, read_rfqs, run_replenishment, subscribe_buyer,
)
from resurtido.odoo.sync import load
from resurtido.orders import build_orders
from resurtido.validation import PEDIDO_MINIMO_NO_ALCANZADO, validate
from tests.conftest import write_workbook
from tests.fake_odoo import ADMIN_PARTNER_ID, FakeOdooClient

ENV = {"ODOO_PASSWORD": "prueba"}
FORBIDDEN = {"button_confirm", "button_approve", "action_rfq_send", "print_quotation"}

TWO_SUPPLIERS = {
    "Existencias": [
        ["FTR-0001", "Martillo uña 16 oz", 3, "PZA", "ACTIVO"],
        ["FTR-0002", "Desarmador plano 1/4", 50, "PZA", "ACTIVO"],
        ["FTR-0003", "Pinza de presión", -2, "PZA", "ACTIVO"],
    ],
    "Minimos": [["FTR-0001", 30, 60], ["FTR-0002", 12, 36], ["FTR-0003", 10, 20]],
    "Producto_Proveedor": [
        ["FTR-0001", "P01", 559.58, 6],
        ["FTR-0002", "P01", 66.26, 12],
        ["FTR-0003", "P02", 10.0, 5],
    ],
    "Proveedores": [
        ["P01", "Distribuidora Truper Norte", "ventas@truper-norte.mx", 5000],
        ["P02", "Herramientas Chicas", "chicas@prueba.mx", 1000],
    ],
}


def validated(tmp_path, overrides=TWO_SUPPLIERS):
    return validate(load_sheets(write_workbook(tmp_path / "inv.xlsx", overrides=overrides)))


def replenish(odoo, result):
    loaded = load(odoo, result)
    cancel_previous(odoo, loaded.partner_ids.values())
    run_replenishment(odoo, loaded.orderpoint_ids.values())
    return loaded, read_rfqs(odoo, loaded)


def methods(odoo):
    return {method for _, method, _ in odoo.calls}


# RFQ por reabastecimiento nativo

def test_una_rfq_por_proveedor_con_productos_bajo_el_minimo(tmp_path):
    odoo = FakeOdooClient()

    loaded, rfqs = replenish(odoo, validated(tmp_path))

    assert sorted(rfqs) == ["P01", "P02"]
    assert rfqs["P01"].codes == {"FTR-0001"}
    assert len(odoo.by("purchase.order", partner_id=loaded.partner_ids["P01"])) == 1


def test_proveedor_sin_productos_por_pedir_no_tiene_rfq(tmp_path):
    overrides = dict(TWO_SUPPLIERS, Existencias=[
        ["FTR-0001", "Martillo uña 16 oz", 3, "PZA", "ACTIVO"],
        ["FTR-0002", "Desarmador plano 1/4", 50, "PZA", "ACTIVO"],
        ["FTR-0003", "Pinza de presión", 15, "PZA", "ACTIVO"],
    ])
    odoo = FakeOdooClient()

    _, rfqs = replenish(odoo, validated(tmp_path, overrides))

    assert sorted(rfqs) == ["P01"]


def test_el_reabastecimiento_pide_recalcular(tmp_path):
    odoo = FakeOdooClient()
    calls = []
    original = odoo.call
    odoo.call = lambda model, method, ids, context=None, **kw: (
        calls.append((method, context)), original(model, method, ids, context, **kw)
    )[1]

    replenish(odoo, validated(tmp_path))

    assert ("action_replenish", {"recompute_qty_to_order": True}) in calls


# Ningún pedido sale solo

def test_todo_queda_en_borrador_y_nada_se_envia(tmp_path):
    odoo = FakeOdooClient()

    replenish(odoo, validated(tmp_path))

    assert {o["state"] for o in odoo.by("purchase.order")} == {"draft"}
    assert not methods(odoo) & FORBIDDEN


# RFQ vigentes en cada corrida

def test_segunda_corrida_cancela_las_rfq_anteriores(tmp_path):
    odoo = FakeOdooClient()
    replenish(odoo, validated(tmp_path))
    first = {o["id"] for o in odoo.by("purchase.order")}

    otra = tmp_path / "otra"
    otra.mkdir()
    overrides = dict(TWO_SUPPLIERS, Existencias=[
        ["FTR-0001", "Martillo uña 16 oz", 20, "PZA", "ACTIVO"],
        ["FTR-0002", "Desarmador plano 1/4", 50, "PZA", "ACTIVO"],
        ["FTR-0003", "Pinza de presión", -2, "PZA", "ACTIVO"],
    ])
    _, rfqs = replenish(odoo, validated(otra, overrides))

    assert {odoo.records["purchase.order"][i]["state"] for i in first} == {"cancel"}
    line = odoo.by("purchase.order.line", order_id=rfqs["P01"].order_ids[0])[0]
    assert line["product_qty"] == 42  # 60 - 20 = 40 → múltiplo de 6


def test_misma_cantidad_de_rfq_vigentes_al_repetir(tmp_path):
    odoo = FakeOdooClient()
    _, first = replenish(odoo, validated(tmp_path))

    _, second = replenish(odoo, validated(tmp_path))

    assert {k: v.total for k, v in first.items()} == {k: v.total for k, v in second.items()}
    assert len([o for o in odoo.by("purchase.order") if o["state"] == "draft"]) == 2


def test_rfq_hecha_a_mano_no_se_toca(tmp_path):
    odoo = FakeOdooClient()
    loaded = load(odoo, validated(tmp_path))
    manual = odoo.add_manual_rfq(loaded.partner_ids["P01"], loaded.product_ids["FTR-0002"])

    cancel_previous(odoo, loaded.partner_ids.values())
    run_replenishment(odoo, loaded.orderpoint_ids.values())
    cancel_previous(odoo, loaded.partner_ids.values())

    assert odoo.records["purchase.order"][manual]["state"] == "draft"
    assert len(odoo.by("purchase.order.line", order_id=manual)) == 1


# Avisos

def test_nota_de_pedido_minimo(tmp_path):
    odoo = FakeOdooClient()
    result = validated(tmp_path)
    _, rfqs = replenish(odoo, result)

    exceptions = post_notes(odoo, rfqs, result.suppliers, result.products)

    # P02: (20 - 0) = 20 piezas x $10 = $200 contra mínimo $1,000.
    notes = odoo.notes(rfqs["P02"].order_ids[0])
    assert any(
        n.startswith("No enviar") and "Total $200.00 contra mínimo $1,000.00; faltan $800.00" in n
        for n in notes
    )
    assert odoo.records["purchase.order"][rfqs["P02"].order_ids[0]]["state"] == "draft"
    assert [(e.codigo, e.tipo) for e in exceptions] == [("P02", PEDIDO_MINIMO_NO_ALCANZADO)]
    assert not any(n.startswith("No enviar") for n in odoo.notes(rfqs["P01"].order_ids[0]))


def test_nota_de_productos_a_revisar(tmp_path):
    odoo = FakeOdooClient()
    result = validated(tmp_path)
    _, rfqs = replenish(odoo, result)

    post_notes(odoo, rfqs, result.suppliers, result.products)

    notes = odoo.notes(rfqs["P02"].order_ids[0])
    assert any(n.startswith("Revisar antes de enviar") and "FTR-0003" in n for n in notes)
    assert not any(n.startswith("Revisar") for n in odoo.notes(rfqs["P01"].order_ids[0]))


def test_las_notas_son_internas(tmp_path):
    odoo = FakeOdooClient()
    result = validated(tmp_path)
    _, rfqs = replenish(odoo, result)

    post_notes(odoo, rfqs, result.suppliers, result.products)

    assert {m["subtype_xmlid"] for m in odoo.by("mail.message")} == {"mail.mt_note"}


# Comprador como seguidor

def test_el_comprador_sigue_las_rfq_sin_ser_responsable(tmp_path):
    odoo = FakeOdooClient()
    _, rfqs = replenish(odoo, validated(tmp_path))

    subscribe_buyer(odoo, rfqs)

    followed = {f["res_id"] for f in odoo.by("mail.followers", partner_id=ADMIN_PARTNER_ID)}
    assert followed == {i for rfq in rfqs.values() for i in rfq.order_ids}
    assert not any(o.get("user_id") for o in odoo.by("purchase.order"))


def test_el_comando_suscribe_al_comprador(tmp_path):
    odoo = FakeOdooClient()

    cli.main(["--output", str(tmp_path / "out")], environ=ENV, connect=lambda settings: odoo)

    drafts = {o["id"] for o in odoo.by("purchase.order", state="draft")}
    assert {f["res_id"] for f in odoo.by("mail.followers")} == drafts


# Conciliación

def _orders(tmp_path):
    result = validated(tmp_path)
    orders, _ = build_orders(result.products, result.suppliers)
    return orders


def test_conciliacion_cuadra(tmp_path):
    orders = _orders(tmp_path)
    p01 = next(o for o in orders if o.supplier.proveedor_id == "P01")

    rows = reconcile(orders, {"P01": Rfq("P01", [1], ["P00001"], p01.total)}, ["P01"])

    assert rows[0].estado == CUADRA


def test_conciliacion_no_cuadra(tmp_path):
    orders = _orders(tmp_path)
    p01 = next(o for o in orders if o.supplier.proveedor_id == "P01")

    rows = reconcile(orders, {"P01": Rfq("P01", [1], ["P00001"], p01.total + Decimal("0.02"))}, ["P01"])

    assert rows[0].estado == NO_CUADRA
    assert rows[0].diferencia == Decimal("0.02")


def test_conciliacion_compra_en_proceso(tmp_path):
    orders = _orders(tmp_path)

    rows = reconcile(orders, {}, ["P01"], in_progress={"P01"})

    assert rows[0].estado == EN_PROCESO
    lines = reconciliation_lines(rows)
    assert lines[0] == "Comprobación del cálculo: 0 de 1 proveedores cuadran"
    assert "Con compra en proceso" in lines[1] and "P01" in lines[1]
    assert not any("No cuadra" in line for line in lines)


def test_reimportar_con_rfq_enviada_es_compra_en_proceso(tmp_path):
    from resurtido.odoo.cli import run_import

    odoo = FakeOdooClient()
    first = run_import(odoo, validated(tmp_path))
    sent = first.rfqs["P01"].order_ids[0]
    odoo.records["purchase.order"][sent]["state"] = "sent"

    again = tmp_path / "otra"
    again.mkdir()
    second = run_import(odoo, validated(again))

    row = next(r for r in second.rows if r.proveedor_id == "P01")
    assert row.estado == EN_PROCESO
    assert "P01" not in second.rfqs  # Odoo no lo vuelve a pedir


def test_conciliacion_sin_productos_en_ambos_lados(tmp_path):
    overrides = dict(TWO_SUPPLIERS, Existencias=[
        ["FTR-0001", "Martillo uña 16 oz", 3, "PZA", "ACTIVO"],
        ["FTR-0002", "Desarmador plano 1/4", 50, "PZA", "ACTIVO"],
        ["FTR-0003", "Pinza de presión", 15, "PZA", "ACTIVO"],
    ])
    result = validated(tmp_path, overrides)
    orders, _ = build_orders(result.products, result.suppliers)

    rows = reconcile(orders, {}, ["P02"])

    assert (rows[0].total_cli, rows[0].total_odoo, rows[0].estado) == (Decimal("0.00"), Decimal("0.00"), CUADRA)


# De punta a punta con el Excel del caso

def test_punta_a_punta_con_el_excel_del_caso(tmp_path, capsys):
    odoo = FakeOdooClient()
    output = tmp_path / "output"

    code = cli.main(["--output", str(output)], environ=ENV, connect=lambda settings: odoo)

    assert code == 0
    assert [p.name for p in output.iterdir()] == ["odoo"]
    with (output / "odoo" / "conciliacion.csv").open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 8 and {r["estado"] for r in rows} == {CUADRA}
    with (output / "odoo" / "excepciones.csv").open(encoding="utf-8-sig") as handle:
        exceptions = list(csv.DictReader(handle))
    assert [e["codigo"] for e in exceptions if e["tipo"] == PEDIDO_MINIMO_NO_ALCANZADO] == ["P05"]
    assert len(exceptions) == 28
    out = capsys.readouterr().out
    assert "8 de 8 proveedores cuadran" in out
    assert "RFQ en borrador generadas por Odoo (sin enviar): 7" in out
    assert not methods(odoo) & FORBIDDEN


def test_punta_a_punta_mismas_excepciones_que_la_cli(tmp_path):
    cli.main(["--output", str(tmp_path / "a")], environ=ENV, connect=lambda settings: FakeOdooClient())
    resurtido_cli.main(["--output", str(tmp_path / "b")])

    odoo_report = (tmp_path / "a" / "odoo" / "excepciones.csv").read_text(encoding="utf-8-sig")
    cli_report = (tmp_path / "b" / "excepciones.csv").read_text(encoding="utf-8-sig")
    assert odoo_report == cli_report


def test_run_import_es_la_misma_secuencia_que_el_comando():
    from resurtido.odoo.cli import import_summary_lines, run_import

    result = validate(load_sheets(resurtido_cli.DEFAULT_INPUT))
    odoo = FakeOdooClient()

    imported = run_import(odoo, result)

    assert len(imported.rfqs) == 7
    assert [e.codigo for e in imported.minimum_exceptions] == ["P05"]
    assert len(result.exceptions) == 28
    lines = import_summary_lines(result, imported)
    assert "RFQ en borrador generadas por Odoo (sin enviar): 7" in lines
    assert "Comprobación del cálculo: 8 de 8 proveedores cuadran" in lines
