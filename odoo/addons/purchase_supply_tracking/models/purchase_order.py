"""Estatus de seguimiento de una compra, de la RFQ a la recepción.

Odoo ya guarda el estado de la compra (`state`) y de la recepción (`receipt_status`).
Lo que no guarda son dos eventos: que el proveedor contestó la RFQ y que la orden de
compra confirmada se le envió. Este módulo los registra y combina todo en un solo
estatus calculado, con historial en el chatter (`tracking`).
"""

from odoo import SUPERUSER_ID, api, fields, models

SUPPLY_STATUS = [
    ("prepared", "Pedido preparado"),
    ("waiting_quote", "Esperando cotización"),
    ("quote_received", "Cotización recibida"),
    ("approved", "Aprobada"),
    ("po_sent", "PO enviada"),
    ("partial", "Recibido parcial"),
    ("received", "Recibido"),
    ("cancelled", "Cancelado"),
]

OPEN_RFQ_STATES = ("draft", "sent", "to approve")
CONFIRMED_STATES = ("purchase", "done")
REVIEW_ACTIVITY = "purchase_supply_tracking.mail_act_review_quote"


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    quote_received_at = fields.Datetime("Cotización recibida el", readonly=True, copy=False)
    po_sent_at = fields.Datetime("PO enviada el", readonly=True, copy=False)
    supply_status = fields.Selection(
        SUPPLY_STATUS,
        string="Seguimiento",
        compute="_compute_supply_status",
        store=True,
        index=True,
        tracking=True,
    )

    @api.depends("state", "receipt_status", "quote_received_at", "po_sent_at")
    def _compute_supply_status(self):
        for order in self:
            order.supply_status = order._get_supply_status()

    def _get_supply_status(self):
        """Gana el estatus más avanzado (ver design.md, decisión 1)."""
        self.ensure_one()
        if self.state == "cancel":
            return "cancelled"
        if self.receipt_status == "full":
            return "received"
        if self.receipt_status == "partial":
            return "partial"
        if self.state in CONFIRMED_STATES:
            return "po_sent" if self.po_sent_at else "approved"
        if self.quote_received_at:
            return "quote_received"
        if self.state in ("sent", "to approve"):
            return "waiting_quote"
        return "prepared"

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, **kwargs):
        # Enviar la RFQ y enviar la PO usan el mismo asistente con `mark_rfq_as_sent`;
        # Odoo solo lo aprovecha para pasar la RFQ a "enviada". Aquí se marca la PO.
        if self.env.context.get("mark_rfq_as_sent"):
            self.filtered(
                lambda o: o.state in CONFIRMED_STATES and not o.po_sent_at
            ).write({"po_sent_at": fields.Datetime.now()})
        return super().message_post(**kwargs)

    def _message_post_after_hook(self, message, msg_vals):
        result = super()._message_post_after_hook(message, msg_vals)
        if message.message_type == "email" and message.author_id:
            vendor_replies = self.filtered(
                lambda o: o.state in OPEN_RFQ_STATES
                and not o.quote_received_at
                and message.author_id.commercial_partner_id == o.partner_id.commercial_partner_id
            )
            for order in vendor_replies:
                order.quote_received_at = message.date or fields.Datetime.now()
                order._schedule_quote_review()
        return result

    def _quote_reviewers(self):
        """El comprador de la compra o, si no tiene, los usuarios internos que la siguen."""
        self.ensure_one()
        if self.user_id:
            return self.user_id
        return self.message_partner_ids.user_ids.filtered(
            lambda user: not user.share and not user._is_superuser()
        )

    def _schedule_quote_review(self):
        self.ensure_one()
        activities = self.env["mail.activity"]
        for user in self._quote_reviewers():
            activities |= self.with_context(mail_activity_quick_update=True).activity_schedule(
                REVIEW_ACTIVITY, user_id=user.id
            )
        # Odoo solo avisa por correo cuando quien asigna no es el asignado, y no le manda un aviso a
        # su propio autor; el correo del proveedor puede procesarse con la sesión del propio
        # comprador, así que se avisa siempre y a nombre de OdooBot.
        activities.with_user(SUPERUSER_ID).action_notify()

    def button_confirm(self):
        result = super().button_confirm()
        self.filtered(lambda o: o.state in CONFIRMED_STATES).activity_feedback([REVIEW_ACTIVITY])
        return result
