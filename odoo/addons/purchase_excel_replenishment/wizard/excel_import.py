"""Asistente "Importar inventario (Excel)": el flujo del comando de terminal, desde Compras."""

import base64
import tempfile
from pathlib import Path

from odoo import fields, models
from odoo.exceptions import UserError

from resurtido.cli import InputError, check_sheets, read_sheet_names
from resurtido.loader import ColumnError, load_sheets
from resurtido.odoo.cli import import_summary_lines, run_import
from resurtido.odoo.client import OdooError
from resurtido.report import write_exceptions
from resurtido.validation import validate

from ..models.orm_client import OrmClient


class ExcelReplenishmentWizard(models.TransientModel):
    _name = "purchase.excel.replenishment.wizard"
    _description = "Importar inventario (Excel)"

    file = fields.Binary("Excel de inventario", attachment=False)
    filename = fields.Char("Archivo")
    state = fields.Selection([("upload", "Subir"), ("done", "Listo")], default="upload")
    summary = fields.Text("Resumen", readonly=True)
    exceptions_file = fields.Binary("Reporte de excepciones", readonly=True, attachment=False)
    exceptions_filename = fields.Char()
    rfq_ids = fields.Many2many("purchase.order", string="RFQ generadas", readonly=True)

    def _read_workbook(self, path):
        """Mismos mensajes que la CLI, con el nombre del archivo en lugar de la ruta temporal."""
        try:
            check_sheets(read_sheet_names(path))
            return load_sheets(path)
        except (InputError, ColumnError) as exc:
            raise UserError(str(exc).replace(str(path), self.filename or "el archivo")) from exc
        except Exception as exc:  # pandas u openpyxl con un archivo dañado a medias
            raise UserError(f"No se pudo leer {self.filename or 'el archivo'} como Excel: {exc}") from exc

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError("Elige el Excel de inventario.")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventario.xlsx"
            path.write_bytes(base64.b64decode(self.file))
            result = validate(self._read_workbook(path))
            try:
                # sudo: crea productos, ajustes de inventario y reglas; `uid` sigue siendo
                # quien importa, así que él queda como seguidor y autor de las notas.
                imported = run_import(OrmClient(self.env(su=True)), result)
            except OdooError as exc:
                raise UserError(str(exc)) from exc
            # La bandeja de excepciones: todas al comprador que importa.
            log = self.env(su=True)["purchase.replenishment.import"].register(
                self.env.user, self.filename or "inventario.xlsx", result.exceptions
            )
            report = write_exceptions(result.exceptions, Path(tmp))
            exceptions_csv = report.read_bytes()

        lines = [f"Archivo: {self.filename or 'inventario.xlsx'}"] + import_summary_lines(result, imported)
        lines.append(f"Bandeja de excepciones: {log.summary_text()}")
        self.write({
            "state": "done",
            "summary": "\n".join(lines),
            "exceptions_file": base64.b64encode(exceptions_csv),
            "exceptions_filename": "excepciones.csv",
            "rfq_ids": [(6, 0, [i for rfq in imported.rfqs.values() for i in rfq.order_ids])],
            "file": False,
        })
        return {
            "type": "ir.actions.act_window",
            "name": "Importar inventario (Excel)",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_view_rfqs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "RFQ generadas",
            "res_model": "purchase.order",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.rfq_ids.ids)],
            "target": "current",
        }
