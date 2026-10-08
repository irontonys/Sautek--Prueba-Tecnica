"""Lectura de la cotización adjunta del proveedor y aplicación de las diferencias a la RFQ.

La lectura y la comparación viven en `resurtido.cotizacion` (sin Odoo, probadas con
pytest); aquí solo se toma el adjunto, se guarda el resultado y se aplica a las líneas.
"""

import base64
import tempfile
from pathlib import Path

from odoo import api, fields, models
from odoo.exceptions import UserError

from resurtido.cotizacion import (
    CAMBIO_CANTIDAD, CAMBIO_PRECIO, IGUAL, NO_COTIZADO, NO_EN_RFQ, PARCIAL, SIN_EXISTENCIA,
    QuoteReadError, compare, extract_text, parse_quote,
)

STATUS_KEYS = {
    IGUAL: "same",
    CAMBIO_PRECIO: "price",
    PARCIAL: "partial",
    CAMBIO_CANTIDAD: "quantity",
    SIN_EXISTENCIA: "out_of_stock",
    NO_COTIZADO: "not_quoted",
    NO_EN_RFQ: "not_in_rfq",
}
READ_STATUS = [(key, label) for label, key in STATUS_KEYS.items()]
APPLICABLE = ("price", "partial", "quantity", "out_of_stock")
OPEN_RFQ_STATES = ("draft", "sent", "to approve")
MIMETYPE_SUFFIX = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/csv": ".csv",
}


class PurchaseQuoteReadingLine(models.Model):
    _name = "purchase.quote.reading.line"
    _description = "Renglón de la lectura de cotización"
    _order = "sequence, id"

    order_id = fields.Many2one("purchase.order", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer()
    code = fields.Char("Código", required=True)
    description = fields.Char("Descripción")
    rfq_qty = fields.Float("Cantidad RFQ", digits="Product Unit of Measure")
    rfq_price = fields.Float("Precio RFQ", digits="Product Price")
    quoted_qty = fields.Float("Cantidad cotizada", digits="Product Unit of Measure")
    quoted_price = fields.Float("Precio cotizado", digits="Product Price")
    status = fields.Selection(READ_STATUS, string="Estatus", required=True)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    quote_reading_line_ids = fields.One2many(
        "purchase.quote.reading.line", "order_id", string="Lectura de cotización", readonly=True
    )
    quote_reading_attachment_id = fields.Many2one("ir.attachment", "Cotización leída", readonly=True, copy=False)
    quote_read_at = fields.Datetime("Leída el", readonly=True, copy=False)
    quote_applied = fields.Boolean("Aplicada a la RFQ", readonly=True, copy=False)
    has_quote_differences = fields.Boolean(compute="_compute_has_quote_differences")

    @api.depends("quote_reading_line_ids.status", "quote_applied")
    def _compute_has_quote_differences(self):
        for order in self:
            order.has_quote_differences = not order.quote_applied and any(
                line.status in APPLICABLE for line in order.quote_reading_line_ids
            )

    def _vendor_quote_attachment(self):
        """El adjunto legible más reciente de un correo del proveedor en esta RFQ."""
        self.ensure_one()
        vendor = self.partner_id.commercial_partner_id
        emails = self.message_ids.filtered(
            lambda m: m.message_type == "email" and m.author_id.commercial_partner_id == vendor
        ).sorted(lambda m: (m.date, m.id), reverse=True)
        for message in emails:
            for attachment in message.attachment_ids.sorted("id", reverse=True):
                if self._attachment_suffix(attachment):
                    return attachment
        return self.env["ir.attachment"]

    @staticmethod
    def _attachment_suffix(attachment):
        suffix = Path(attachment.name or "").suffix.lower()
        if suffix in (".pdf", ".xlsx", ".csv"):
            return suffix
        return MIMETYPE_SUFFIX.get(attachment.mimetype)

    def _rfq_lines_by_code(self):
        lines = {}
        for line in self.order_line.filtered(lambda l: not l.display_type and l.product_id.default_code):
            lines.setdefault(line.product_id.default_code, line)
        return lines

    def action_read_quote(self):
        self.ensure_one()
        attachment = self._vendor_quote_attachment()
        if not attachment:
            raise UserError(
                "El proveedor no ha adjuntado una cotización en PDF, Excel (.xlsx) o CSV en esta RFQ."
            )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"cotizacion{self._attachment_suffix(attachment)}"
            path.write_bytes(base64.b64decode(attachment.datas))
            try:
                quoted = parse_quote(extract_text(path))
            except QuoteReadError as exc:
                raise UserError(f"No se pudo leer {attachment.name}: {exc}") from exc

        lines = self._rfq_lines_by_code()
        if not set(quoted) & set(lines):
            raise UserError(
                f"No encontré partidas de esta RFQ en {attachment.name}: la lectura busca los códigos "
                "de producto (por ejemplo FTR-0001) con su cantidad y precio. Compárala a mano."
            )
        rows = compare(
            [(code, line.product_id.name, line.product_qty, line.price_unit) for code, line in lines.items()],
            quoted,
        )
        self.quote_reading_line_ids.unlink()
        self.write({
            "quote_reading_line_ids": [
                (0, 0, {
                    "sequence": index,
                    "code": row.codigo,
                    "description": row.descripcion,
                    "rfq_qty": float(row.cantidad_rfq),
                    "rfq_price": float(row.precio_rfq),
                    "quoted_qty": float(row.cantidad_cotizada),
                    "quoted_price": float(row.precio_cotizado),
                    "status": STATUS_KEYS[row.estatus],
                })
                for index, row in enumerate(rows)
            ],
            "quote_reading_attachment_id": attachment.id,
            "quote_read_at": fields.Datetime.now(),
            "quote_applied": False,
        })
        return True

    def action_apply_quote(self):
        """Pone en la RFQ lo cotizado. No confirma la compra: eso lo hace el comprador."""
        self.ensure_one()
        if self.state not in OPEN_RFQ_STATES:
            raise UserError("Solo se puede aplicar la cotización a una RFQ sin confirmar.")
        if not self.has_quote_differences:
            raise UserError("No hay diferencias por aplicar: lee primero la cotización.")
        lines = self._rfq_lines_by_code()
        changes = []
        for reading in self.quote_reading_line_ids.filtered(lambda r: r.status in APPLICABLE):
            line = lines.get(reading.code)
            if not line:
                continue
            if reading.status == "out_of_stock":
                changes.append(f"{reading.code}: sin existencia, se quitó la línea de {line.product_qty:g} pzas")
                line.unlink()
                continue
            changes.append(
                f"{reading.code}: {line.product_qty:g} → {reading.quoted_qty:g} pzas, "
                f"${line.price_unit:,.2f} → ${reading.quoted_price:,.2f}"
            )
            line.write({"product_qty": reading.quoted_qty, "price_unit": reading.quoted_price})
        self.message_post(
            body=f"Cotización aplicada desde {self.quote_reading_attachment_id.name}: " + "; ".join(changes),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        self.quote_applied = True
        return True
