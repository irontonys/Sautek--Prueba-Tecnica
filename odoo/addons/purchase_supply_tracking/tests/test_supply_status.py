"""Escenarios de la capacidad `rastreo-compras` dentro de Odoo."""

from odoo.tests import TransactionCase, tagged

from odoo.addons.purchase_supply_tracking.models.purchase_order import REVIEW_ACTIVITY


@tagged("post_install", "-at_install")
class TestSupplyStatus(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Proveedor de Prueba", "email": "ventas@proveedor.test", "is_company": True}
        )
        cls.vendor_contact = cls.env["res.partner"].create(
            {"name": "Ejecutiva del Proveedor", "email": "ejecutiva@proveedor.test", "parent_id": cls.vendor.id}
        )
        cls.stranger = cls.env["res.partner"].create({"name": "Otra Empresa", "email": "otra@empresa.test"})
        cls.buyer = cls.env["res.users"].create({
            "name": "Comprador de Prueba",
            "login": "comprador_prueba",
            "email": "comprador@ferretera.test",
            "groups_id": [(6, 0, [cls.env.ref("purchase.group_purchase_user").id])],
        })
        cls.manager = cls.env["res.users"].create({
            "name": "Jefa de Compras",
            "login": "jefa_compras_prueba",
            "email": "jefa@ferretera.test",
            "groups_id": [(6, 0, [cls.env.ref("purchase.group_purchase_user").id])],
        })
        cls.product = cls.env["product.product"].create(
            {"name": "Martillo de prueba", "detailed_type": "product", "standard_price": 10.0}
        )

    def _rfq(self, qty=10):
        # Como las que genera el reabastecimiento: sin comprador responsable.
        order = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "user_id": False,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_qty": qty, "price_unit": 10.0})],
        })
        order.message_subscribe(partner_ids=[self.buyer.partner_id.id])
        return order

    def _send(self, order):
        """Lo mismo que hace el asistente de "Enviar por correo"."""
        order.with_context(mark_rfq_as_sent=True).message_post(body="Pedido", message_type="comment")

    def _vendor_email(self, order, author=None):
        order.message_post(
            body="Les confirmamos precios y disponibilidad.",
            message_type="email",
            author_id=(author or self.vendor).id,
        )

    def _flush_tracking(self):
        """El historial se escribe al cerrar la transacción; en pruebas se fuerza aquí."""
        self.env.flush_all()
        self.env.cr.precommit.run()

    def _review_activities(self, order):
        activity_type = self.env.ref(REVIEW_ACTIVITY)
        return order.activity_ids.filtered(lambda a: a.activity_type_id == activity_type)

    def _receive(self, order, qty):
        picking = order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
        for move in picking.move_ids:
            move.quantity = qty
            move.picked = True
        picking.with_context(cancel_backorder=False)._action_done()

    # Estatus de seguimiento

    def test_rfq_recien_generada_y_enviada(self):
        order = self._rfq()
        self.assertEqual(order.supply_status, "prepared")

        self._send(order)

        self.assertEqual(order.state, "sent")
        self.assertEqual(order.supply_status, "waiting_quote")

    def test_compra_cancelada(self):
        order = self._rfq()
        self._send(order)

        order.button_cancel()

        self.assertEqual(order.supply_status, "cancelled")

    # Cotización recibida y aviso para aprobar

    def test_el_proveedor_contesta_la_rfq(self):
        order = self._rfq()
        self._send(order)

        self._vendor_email(order)

        self.assertEqual(order.supply_status, "quote_received")
        self.assertTrue(order.quote_received_at)
        activities = self._review_activities(order)
        self.assertEqual(activities.user_id, self.buyer)
        self.assertEqual(activities.summary, "Revisar cotización y aprobar")

    def test_el_aviso_le_llega_al_comprador_aunque_el_sea_quien_procesa(self):
        order = self._rfq()
        self._send(order)

        order.with_user(self.buyer).sudo().message_post(
            body="Cotización", message_type="email", author_id=self.vendor.id,
        )

        notice = self.env["mail.message"].search([
            ("model", "=", "purchase.order"), ("res_id", "=", order.id),
            ("message_type", "=", "user_notification"),
        ])
        self.assertIn(self.buyer.partner_id, notice.notification_ids.res_partner_id)

    def test_contacto_del_proveedor_tambien_cuenta(self):
        order = self._rfq()
        self._send(order)

        self._vendor_email(order, author=self.vendor_contact)

        self.assertEqual(order.supply_status, "quote_received")

    def test_nota_interna_o_correo_ajeno_no_cambian_el_estatus(self):
        order = self._rfq()
        self._send(order)

        order.message_post(body="Nota interna", message_type="comment", subtype_xmlid="mail.mt_note")
        self._vendor_email(order, author=self.stranger)

        self.assertEqual(order.supply_status, "waiting_quote")
        self.assertFalse(self._review_activities(order))

    def test_comprador_responsable_recibe_la_actividad(self):
        order = self._rfq()
        order.user_id = self.manager
        self._send(order)

        self._vendor_email(order)

        self.assertEqual(self._review_activities(order).user_id, self.manager)

    # Aprobada y PO enviada

    def test_aprobar_cierra_la_actividad_y_enviar_la_po(self):
        order = self._rfq()
        self._send(order)
        self._vendor_email(order)

        order.button_confirm()

        self.assertEqual(order.supply_status, "approved")
        self.assertFalse(self._review_activities(order))

        self._send(order)

        self.assertEqual(order.supply_status, "po_sent")
        self.assertTrue(order.po_sent_at)

    def test_correo_del_proveedor_despues_de_aprobar_no_regresa_el_estatus(self):
        order = self._rfq()
        order.button_confirm()

        self._vendor_email(order)

        self.assertEqual(order.supply_status, "approved")
        self.assertFalse(order.quote_received_at)

    # Recepción e historial

    def test_recepcion_parcial_y_completa_con_historial(self):
        order = self._rfq(qty=10)
        self._flush_tracking()
        for step in (self._send, self._vendor_email, lambda o: o.button_confirm(), self._send):
            step(order)
            self._flush_tracking()

        self._receive(order, 4)
        self._flush_tracking()
        self.assertEqual(order.supply_status, "partial")

        self._receive(order, 6)
        self._flush_tracking()
        self.assertEqual(order.supply_status, "received")

        tracked = self.env["mail.tracking.value"].search([
            ("mail_message_id.model", "=", "purchase.order"),
            ("mail_message_id.res_id", "=", order.id),
            ("field_id.name", "=", "supply_status"),
        ], order="id")
        self.assertEqual(
            [t.new_value_char for t in tracked],
            ["Esperando cotización", "Cotización recibida", "Aprobada", "PO enviada",
             "Recibido parcial", "Recibido"],
        )

    # Correo real del proveedor (lo que trae el servidor de entrada)

    def test_respuesta_por_correo_con_cotizacion_adjunta(self):
        from email.message import EmailMessage

        order = self._rfq()
        self._send(order)
        sent = order.message_ids.filtered(lambda m: m.message_type == "comment" and m.body)[:1]

        reply = EmailMessage()
        reply["From"] = "Proveedor de Prueba <ventas@proveedor.test>"
        reply["To"] = "compras@ferretera.test"
        reply["Subject"] = f"Re: Solicitud de cotización {order.name}"
        reply["Message-ID"] = "<cotizacion-1@proveedor.test>"
        reply["In-Reply-To"] = sent.message_id
        reply["References"] = sent.message_id
        reply.set_content("Adjunto nuestra cotización.")
        reply.add_attachment(b"%PDF-1.4 cotizacion", maintype="application", subtype="pdf",
                             filename="cotizacion.pdf")

        # Sin modelo ni registro: la RFQ se ubica solo por los encabezados de respuesta.
        self.env["mail.thread"].message_process(False, reply.as_string())

        self.assertEqual(order.supply_status, "quote_received")
        email = order.message_ids.filtered(lambda m: m.message_type == "email")
        self.assertEqual(email.author_id, self.vendor)
        self.assertEqual(email.attachment_ids.mapped("name"), ["cotizacion.pdf"])
