"""Escenarios de `rastreo-compras` que viven en Python: la simulación del proveedor.

El estatus en sí lo calcula el módulo de Odoo y se prueba dentro de Odoo
(odoo/addons/purchase_supply_tracking/tests).
"""

from email import message_from_string

from resurtido.odoo import proveedor
from tests.fake_odoo import FakeOdooClient

ENV = {"ODOO_PASSWORD": "prueba"}


def odoo_with_rfq(supply_status="waiting_quote", email="ventas@truper-norte.mx"):
    odoo = FakeOdooClient()
    vendor = odoo.create("res.partner", [{"name": "Distribuidora Truper Norte", "email": email, "ref": "P01"}])[0]
    order = odoo.create("purchase.order", [{
        "partner_id": vendor, "state": "sent", "name": "P00001", "supply_status": supply_status,
    }])[0]
    odoo.create("mail.message", [{
        "model": "purchase.order", "res_id": order, "message_type": "comment", "author_id": 3,
        "message_id": "<rfq-p00001@sautek>", "subject": "Ferretera Garza Request for Quotation (Ref P00001)",
        "email_from": "Administrator <admin@example.com>",
    }])
    return odoo, order


def run(odoo, *argv):
    return proveedor.main(list(argv), environ=ENV, connect=lambda settings: odoo)


def test_el_correo_del_proveedor_contesta_a_la_rfq(capsys):
    odoo, order = odoo_with_rfq()

    assert run(odoo, "p01") == 0

    [delivered] = odoo.processed_emails
    assert (delivered["model"], delivered["thread_id"]) == ("purchase.order", order)
    email = message_from_string(delivered["raw"])
    assert email["From"] == "Distribuidora Truper Norte <ventas@truper-norte.mx>"
    assert email["In-Reply-To"] == "<rfq-p00001@sautek>"
    assert email["Subject"] == "Re: Ferretera Garza Request for Quotation (Ref P00001)"
    assert email["To"] == "Administrator <admin@example.com>"
    assert email["Message-ID"].endswith("@truper-norte.mx>")
    assert "P00001" in email.get_payload(decode=True).decode("utf-8")
    assert "contestó la RFQ P00001" in capsys.readouterr().out


def test_sin_rfq_esperando_cotizacion(capsys):
    odoo, _ = odoo_with_rfq(supply_status="prepared")

    assert run(odoo, "P01") == 1

    assert "no tiene una RFQ esperando cotización" in capsys.readouterr().err
    assert odoo.processed_emails == []


def test_proveedor_que_no_existe(capsys):
    odoo, _ = odoo_with_rfq()

    assert run(odoo, "P99") == 1

    assert "No existe en Odoo el proveedor P99" in capsys.readouterr().err
    assert odoo.processed_emails == []


def test_proveedor_sin_correo(capsys):
    odoo, _ = odoo_with_rfq(email=False)

    assert run(odoo, "P01") == 1

    assert "no tiene correo" in capsys.readouterr().err


def test_falta_la_contrasena(capsys):
    def never_connect(settings):
        raise AssertionError("No debía conectarse a Odoo")

    assert proveedor.main(["P01"], environ={}, connect=never_connect) == 1

    assert "ODOO_PASSWORD" in capsys.readouterr().err


def test_contestar_una_compra_concreta():
    odoo, order = odoo_with_rfq()

    proveedor.reply_to_order(odoo, order)

    [delivered] = odoo.processed_emails
    assert delivered["thread_id"] == order
    assert message_from_string(delivered["raw"])["In-Reply-To"] == "<rfq-p00001@sautek>"
