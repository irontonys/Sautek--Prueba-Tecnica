from odoo import api, fields, models
from odoo.exceptions import UserError

from resurtido.cli import InputError
from resurtido.odoo.client import OdooError
from resurtido.odoo.proveedor import WAITING_QUOTE, reply_to_order

from .orm_client import OrmClient

DEMO_MODE_PARAM = "purchase_excel_replenishment.demo_mode"


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    show_demo_reply = fields.Boolean(compute="_compute_show_demo_reply")

    def _demo_mode(self):
        return bool(self.env["ir.config_parameter"].sudo().get_param(DEMO_MODE_PARAM))

    @api.depends("supply_status")
    def _compute_show_demo_reply(self):
        demo = self._demo_mode()
        for order in self:
            order.show_demo_reply = demo and order.supply_status == WAITING_QUOTE

    def action_simulate_vendor_reply(self):
        """Lo mismo que `python -m resurtido.odoo.proveedor`, desde un botón (solo en modo demo)."""
        if not self._demo_mode():
            raise UserError("El modo demostración está apagado (Compras → Configuración → Ajustes).")
        for order in self:
            if order.supply_status != WAITING_QUOTE:
                raise UserError(f"La RFQ {order.name} no está esperando cotización.")
            try:
                reply_to_order(OrmClient(self.env), order.id)
            except (InputError, OdooError) as exc:
                raise UserError(str(exc)) from exc
        return True
