"""Bandeja de excepciones: cada excepción de la importación es un pendiente del comprador.

Una excepción se reconoce entre importaciones por su tipo, hoja y código (o fila si no
tiene código). En cada importación se crean las nuevas, se reabren las que vuelven, se
resuelven las que ya no salen y se respetan las que el comprador aceptó.
"""

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import UserError

from resurtido.validation import EXISTENCIA_NEGATIVA, PEDIDO_MINIMO_NO_ALCANZADO, UNIDAD_INCONSISTENTE

GROUPS = [
    ("corrected", "Se corrigió"),
    ("warning", "Advertencia"),
    ("excluded", "No se procesó"),
    ("purchase", "Compra"),
]
STATES = [("pending", "Pendiente"), ("resolved", "Resuelta"), ("accepted", "Aceptada")]
# Se procesan, pero alguien debe revisarlas; el resto de las que no excluyen ya se corrigieron.
WARNING_TYPES = {EXISTENCIA_NEGATIVA, UNIDAD_INCONSISTENTE}
REVIEW_ACTIVITY = "purchase_excel_replenishment.mail_act_review_exceptions"


def exception_key(item):
    reference = item.codigo or f"fila {item.fila_excel}"
    return f"{item.tipo}|{item.hoja}|{reference}"


def exception_group(item):
    if item.tipo == PEDIDO_MINIMO_NO_ALCANZADO:
        return "purchase"
    if item.excludes:
        return "excluded"
    if item.tipo in WARNING_TYPES:
        return "warning"
    return "corrected"


class ReplenishmentException(models.Model):
    _name = "purchase.replenishment.exception"
    _description = "Excepción de inventario"
    _inherit = ["mail.thread"]
    _order = "state, group, code, id"
    _rec_name = "display_label"

    key = fields.Char(required=True, index=True, readonly=True)
    sheet = fields.Char("Hoja", readonly=True)
    excel_row = fields.Integer("Fila", readonly=True)
    code = fields.Char("Código", readonly=True)
    exception_type = fields.Char("Tipo", readonly=True)
    detail = fields.Char("Detalle", readonly=True)
    original_value = fields.Char("Valor original", readonly=True)
    decision = fields.Char("Decisión", readonly=True)
    group = fields.Selection(GROUPS, string="Grupo", readonly=True)
    user_id = fields.Many2one("res.users", "Responsable", tracking=True)
    state = fields.Selection(STATES, string="Estatus", default="pending", required=True, tracking=True)
    first_seen = fields.Datetime("Primera vez", readonly=True)
    last_seen = fields.Datetime("Última vez", readonly=True)
    times_seen = fields.Integer("Veces vista", readonly=True, default=1)
    reopen_count = fields.Integer("Reaperturas", readonly=True)
    resolved_at = fields.Datetime("Resuelta el", readonly=True)
    accepted_by = fields.Many2one("res.users", "Aceptada por", readonly=True)
    accepted_at = fields.Datetime("Aceptada el", readonly=True)
    last_import_id = fields.Many2one("purchase.replenishment.import", "Última importación", readonly=True)
    days_open = fields.Integer("Días abierta", compute="_compute_days_open")
    display_label = fields.Char(compute="_compute_display_label")

    _sql_constraints = [("key_unique", "unique(key)", "La excepción ya existe en la bandeja.")]

    @api.depends("first_seen", "state")
    def _compute_days_open(self):
        now = fields.Datetime.now()
        for record in self:
            open_ = record.state != "resolved" and record.first_seen
            record.days_open = (now - record.first_seen).days if open_ else 0

    @api.depends("code", "exception_type", "excel_row")
    def _compute_display_label(self):
        for record in self:
            record.display_label = f"{record.code or f'Fila {record.excel_row}'} · {record.exception_type}"

    def action_accept(self):
        to_accept = self.filtered(lambda r: r.state == "pending")
        if not to_accept:
            raise UserError("Solo se pueden aceptar excepciones pendientes.")
        to_accept.write({
            "state": "accepted", "accepted_by": self.env.user.id, "accepted_at": fields.Datetime.now(),
        })
        return True

    def action_reopen(self):
        to_reopen = self.filtered(lambda r: r.state == "accepted")
        if not to_reopen:
            raise UserError("Solo se pueden reabrir excepciones aceptadas.")
        to_reopen.write({"state": "pending", "accepted_by": False, "accepted_at": False})
        return True


class ReplenishmentImport(models.Model):
    _name = "purchase.replenishment.import"
    _description = "Importación de inventario"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    date = fields.Datetime("Fecha", default=fields.Datetime.now, readonly=True)
    user_id = fields.Many2one("res.users", "Importó", readonly=True)
    filename = fields.Char("Archivo", readonly=True)
    new_count = fields.Integer("Nuevas", readonly=True)
    open_count = fields.Integer("Abiertas", readonly=True)
    resolved_count = fields.Integer("Resueltas", readonly=True)

    @api.depends("date")
    def _compute_name(self):
        for record in self:
            record.name = f"Importación del {fields.Datetime.to_string(record.date)[:16]}" if record.date else "Importación"

    def summary_text(self):
        self.ensure_one()
        return f"{self.new_count} nuevas, {self.open_count} abiertas, {self.resolved_count} resueltas"

    @api.model
    def register(self, user, filename, exceptions):
        """Sincroniza la bandeja con las excepciones de una importación. Regresa el registro."""
        Exception_ = self.env["purchase.replenishment.exception"]
        now = fields.Datetime.now()
        log = self.create({"user_id": user.id, "filename": filename, "date": now})
        existing = {record.key: record for record in Exception_.search([])}
        reported, new_count = set(), 0
        for item in exceptions:
            key = exception_key(item)
            if key in reported:
                continue  # el mismo problema dos veces en una importación cuenta una vez
            reported.add(key)
            values = {
                "sheet": item.hoja, "excel_row": item.fila_excel, "code": item.codigo,
                "exception_type": item.tipo, "detail": item.detalle,
                "original_value": str(item.valor_original or ""), "decision": item.decision,
                "group": exception_group(item), "last_seen": now, "last_import_id": log.id,
            }
            record = existing.get(key)
            if record is None:
                Exception_.create({**values, "key": key, "first_seen": now, "user_id": user.id})
                new_count += 1
            elif record.state == "resolved":
                record.write({
                    **values, "state": "pending", "user_id": user.id, "resolved_at": False,
                    "first_seen": now, "times_seen": record.times_seen + 1,
                    "reopen_count": record.reopen_count + 1,
                })
            else:
                record.write({**values, "times_seen": record.times_seen + 1})
        gone = Exception_.browse([r.id for k, r in existing.items() if k not in reported and r.state != "resolved"])
        gone.write({"state": "resolved", "resolved_at": now})
        log.write({
            "new_count": new_count,
            "open_count": Exception_.search_count([("state", "=", "pending")]),
            "resolved_count": len(gone),
        })
        log._notify_buyer(user)
        return log

    def _notify_buyer(self, user):
        """Una sola tarea abierta: se cierra la de la importación anterior y se crea la nueva."""
        self.ensure_one()
        previous = self.search([("id", "!=", self.id)]).filtered(lambda r: r.activity_ids)
        previous.activity_feedback([REVIEW_ACTIVITY], feedback="Reemplazada por una importación más reciente")
        if self.open_count:
            # Quien importa suele ser el mismo comprador. Odoo no avisa a quien se asigna una tarea a
            # sí mismo, ni manda un aviso a su propio autor: se avisa siempre, a nombre de OdooBot.
            activity = self.with_context(mail_activity_quick_update=True).activity_schedule(
                REVIEW_ACTIVITY, user_id=user.id,
                summary=f"Revisar excepciones: {self.summary_text()}",
            )
            activity.with_user(SUPERUSER_ID).action_notify()

    def action_open_pending(self):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "purchase_excel_replenishment.action_replenishment_exceptions"
        )
        action["context"] = {"search_default_pending": 1}
        return action
