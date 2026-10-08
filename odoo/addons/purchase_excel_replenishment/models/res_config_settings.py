from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    purchase_demo_mode = fields.Boolean(
        "Modo demostración",
        config_parameter="purchase_excel_replenishment.demo_mode",
        help="Muestra en las RFQ enviadas el botón para simular la respuesta del proveedor.",
    )
