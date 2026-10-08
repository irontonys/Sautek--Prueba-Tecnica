"""Escenarios de la capacidad `lectura-cotizacion` dentro de Odoo."""

from pathlib import Path

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

PARTIAL_QUOTE = Path(__file__).parent / "data" / "cotizacion_truper_P00001_surtido_parcial.pdf"


@tagged("post_install", "-at_install")
class TestQuoteReader(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Distribuidora Truper Norte", "email": "ventas@truper-norte.test", "is_company": True}
        )
        cls.products = {
            code: cls.env["product.product"].create({"name": name, "default_code": code, "detailed_type": "product"})
            for code, name in [("FTR-0001", "Martillo uña 16 oz"), ("FTR-0006", "Llave ajustable 10\""),
                               ("FTR-0018", "Rodillo 9\"")]
        }

    def _rfq(self):
        lines = [("FTR-0001", 60, 559.58), ("FTR-0006", 72, 116.00), ("FTR-0018", 24, 352.17)]
        order = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "user_id": False,
            "order_line": [
                (0, 0, {"product_id": self.products[code].id, "product_qty": qty, "price_unit": price})
                for code, qty, price in lines
            ],
        })
        order.with_context(mark_rfq_as_sent=True).message_post(body="Pedido", message_type="comment")
        return order

    def _vendor_reply(self, order, name, content):
        order.message_post(
            body="Adjunto nuestra cotización.", message_type="email", author_id=self.vendor.id,
            attachments=[(name, content)],
        )

    def _status(self, order):
        return {line.code: line.status for line in order.quote_reading_line_ids}

    def test_leer_y_aplicar_la_cotizacion_parcial(self):
        order = self._rfq()
        self._vendor_reply(order, "cotizacion.pdf", PARTIAL_QUOTE.read_bytes())
        self.assertEqual(order.supply_status, "quote_received")

        order.action_read_quote()

        status = self._status(order)
        self.assertEqual(
            {code: status[code] for code in ("FTR-0001", "FTR-0006", "FTR-0018")},
            {"FTR-0001": "same", "FTR-0006": "out_of_stock", "FTR-0018": "partial"},
        )
        # El PDF trae 8 partidas más que esta RFQ de prueba no pidió.
        self.assertEqual(list(status.values()).count("not_in_rfq"), 8)
        rodillo = order.quote_reading_line_ids.filtered(lambda l: l.code == "FTR-0018")
        self.assertEqual((rodillo.rfq_qty, rodillo.quoted_qty), (24, 12))
        self.assertTrue(order.has_quote_differences)

        order.action_apply_quote()

        by_code = {line.product_id.default_code: line for line in order.order_line}
        self.assertNotIn("FTR-0006", by_code)
        self.assertEqual(by_code["FTR-0018"].product_qty, 12)
        self.assertAlmostEqual(order.amount_untaxed, 33574.80 + 4226.04, places=2)
        self.assertIn(order.state, ("draft", "sent"))
        note = order.message_ids.filtered(lambda m: "Cotización aplicada" in (m.body or ""))
        self.assertIn("FTR-0006", note.body)
        self.assertIn("FTR-0018", note.body)
        self.assertFalse(order.has_quote_differences)

    def test_csv_con_cambio_de_precio(self):
        order = self._rfq()
        csv = b"codigo,cantidad,precio,importe\nFTR-0001,60,600.00,36000.00\nFTR-0006,72,116.00,8352.00\nFTR-0018,24,352.17,8452.08\n"
        self._vendor_reply(order, "cotizacion.csv", csv)

        order.action_read_quote()
        order.action_apply_quote()

        martillo = order.order_line.filtered(lambda l: l.product_id.default_code == "FTR-0001")
        self.assertEqual(martillo.price_unit, 600.00)

    def test_archivo_sin_codigos_no_cambia_nada(self):
        order = self._rfq()
        self._vendor_reply(order, "cotizacion.csv", b"producto,precio\nMartillo,559.58\n")

        with self.assertRaisesRegex(UserError, "No encontré partidas de esta RFQ"):
            order.action_read_quote()
        self.assertFalse(order.quote_reading_line_ids)
        self.assertEqual(len(order.order_line), 3)

    def test_sin_adjunto(self):
        order = self._rfq()
        order.message_post(body="Les confirmo por aquí.", message_type="email", author_id=self.vendor.id)

        with self.assertRaisesRegex(UserError, "no ha adjuntado una cotización"):
            order.action_read_quote()

    def test_boton_solo_con_cotizacion_recibida(self):
        arch = self.env["purchase.order"].get_views([(False, "form")])["views"]["form"]["arch"]
        self.assertIn('name="action_read_quote"', arch)
        self.assertIn("supply_status != 'quote_received'", arch)

    def test_no_se_aplica_a_una_compra_confirmada(self):
        order = self._rfq()
        self._vendor_reply(order, "cotizacion.pdf", PARTIAL_QUOTE.read_bytes())
        order.action_read_quote()
        order.button_confirm()

        with self.assertRaisesRegex(UserError, "RFQ sin confirmar"):
            order.action_apply_quote()
