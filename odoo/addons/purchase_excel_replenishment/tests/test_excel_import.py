"""Escenarios de la capacidad `importacion-odoo` dentro de Odoo."""

import base64
import io
from unittest.mock import patch

from openpyxl import Workbook

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

from resurtido.loader import SHEET_COLUMNS

from odoo.addons.base.models.res_company import Company
from odoo.addons.purchase_excel_replenishment.models.purchase_order import DEMO_MODE_PARAM

ROWS = {
    "Existencias": [
        ["FTR-0901", "Martillo de prueba", 3, "PZA", "ACTIVO"],
        ["FTR-0902", "Pinza de prueba", 50, "PZA", "INACTIVO"],
    ],
    "Minimos": [["FTR-0901", 30, 60], ["FTR-0902", 12, 36]],
    "Producto_Proveedor": [["FTR-0901", "P91", 100.0, 6], ["FTR-0902", "P91", 50.0, 12]],
    "Proveedores": [["P91", "Proveedor de Prueba", "ventas@proveedor-prueba.test", 1000]],
}


def workbook_bytes(rows=ROWS, sheets=None):
    """Mismo formato que el Excel del caso: título en la fila 1, encabezados en la 2."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name in sheets or SHEET_COLUMNS:
        sheet = workbook.create_sheet(name)
        sheet.append([f"Hoja {name} de prueba"])
        sheet.append(SHEET_COLUMNS[name])
        for row in rows[name]:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@tagged("post_install", "-at_install")
class TestExcelImport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env["res.users"].create({
            "name": "Jefa de Compras",
            "login": "jefa_compras_import",
            "email": "jefa@ferretera.test",
            "groups_id": [(6, 0, [cls.env.ref("purchase.group_purchase_manager").id])],
        })
        cls.purchase_user = cls.env["res.users"].create({
            "name": "Auxiliar de Compras",
            "login": "auxiliar_compras_import",
            "groups_id": [(6, 0, [cls.env.ref("purchase.group_purchase_user").id])],
        })

    def _import(self, content=None, filename="inventario.xlsx", user=None):
        wizard = self.env["purchase.excel.replenishment.wizard"].with_user(user or self.manager).create({
            "file": base64.b64encode(content if content is not None else workbook_bytes()),
            "filename": filename,
        })
        wizard.action_import()
        return wizard

    def _vendor_products(self):
        return self.env["product.template"].search([("default_code", "in", ["FTR-0901", "FTR-0902"])])

    # Importar el Excel desde Compras

    def test_importacion_crea_la_rfq_con_sus_notas(self):
        wizard = self._import()

        self.assertEqual(wizard.state, "done")
        self.assertEqual(self._vendor_products().mapped("default_code"), ["FTR-0901"])
        rfq = wizard.rfq_ids
        self.assertEqual(len(rfq), 1)
        self.assertEqual(rfq.partner_id.ref, "P91")
        self.assertEqual(rfq.state, "draft")
        self.assertEqual(rfq.order_line.product_qty, 60)  # 60 - 3 = 57 → múltiplo de 6
        self.assertIn(self.manager.partner_id, rfq.message_partner_ids)
        # 60 x $100 = $6,000 alcanza el mínimo de $1,000: sin nota "No enviar".
        self.assertFalse(rfq.message_ids.filtered(lambda m: "No enviar" in (m.body or "")))

    def test_nota_de_pedido_minimo(self):
        rows = dict(ROWS, Proveedores=[["P91", "Proveedor de Prueba", "ventas@proveedor-prueba.test", 999999]])

        wizard = self._import(workbook_bytes(rows))

        notes = wizard.rfq_ids.message_ids.mapped("body")
        self.assertTrue(any("No enviar" in (body or "") for body in notes))

    def test_menu_solo_para_administradores_de_compras(self):
        menu = self.env.ref("purchase_excel_replenishment.menu_excel_replenishment_wizard")
        self.assertEqual(menu.groups_id, self.env.ref("purchase.group_purchase_manager"))
        with self.assertRaises(AccessError):
            self.env["purchase.excel.replenishment.wizard"].with_user(self.purchase_user).create({})

    def test_boton_en_la_lista_de_rfq(self):
        arch = self.env["purchase.order"].with_user(self.manager).get_views(
            [(self.env.ref("purchase.purchase_order_kpis_tree").id, "list")]
        )["views"]["list"]["arch"]
        self.assertIn("Importar inventario (Excel)", arch)
        arch_user = self.env["purchase.order"].with_user(self.purchase_user).get_views(
            [(self.env.ref("purchase.purchase_order_kpis_tree").id, "list")]
        )["views"]["list"]["arch"]
        self.assertNotIn("Importar inventario (Excel)", arch_user)

    def test_compania_con_asientos_contables_no_detiene_la_importacion(self):
        # Odoo no deja cambiar la moneda si ya hay asientos: el motor avisa y sigue.

        def refuse(records, vals):
            if "currency_id" in vals:
                raise UserError("You cannot change the currency of the company since some journal items already exist")
            return original_write(records, vals)

        original_write = Company.write
        with patch.object(Company, "write", refuse):
            wizard = self._import()

        self.assertEqual(wizard.state, "done")
        self.assertIn("no se pudo poner la compañía en MXN", wizard.summary)
        self.assertEqual(len(wizard.rfq_ids), 1)

    # Aviso de resultado

    def test_resumen_y_csv_de_excepciones(self):
        wizard = self._import()

        self.assertIn("Archivo: inventario.xlsx", wizard.summary)
        self.assertIn("Procesables: 1", wizard.summary)
        self.assertIn("RFQ en borrador generadas por Odoo (sin enviar): 1", wizard.summary)
        self.assertIn("Comprobación del cálculo: 1 de 1 proveedores cuadran", wizard.summary)
        csv = base64.b64decode(wizard.exceptions_file).decode("utf-8-sig")
        self.assertTrue(csv.startswith("hoja,fila_excel,codigo,tipo,detalle,valor_original,decision"))
        self.assertIn("Producto inactivo", csv)
        self.assertEqual(wizard.exceptions_filename, "excepciones.csv")

        action = wizard.action_view_rfqs()
        self.assertEqual(action["domain"], [("id", "in", wizard.rfq_ids.ids)])

    # Archivo inválido

    def test_archivo_que_no_es_excel(self):
        with self.assertRaisesRegex(UserError, r"No se pudo leer como Excel.*mi_archivo\.xlsx"):
            self._import(b"esto no es un Excel", filename="mi_archivo.xlsx")
        self.assertFalse(self._vendor_products())

    def test_falta_la_hoja_minimos(self):
        content = workbook_bytes(sheets=["Existencias", "Producto_Proveedor", "Proveedores"])

        with self.assertRaisesRegex(UserError, "Minimos"):
            self._import(content)
        self.assertFalse(self._vendor_products())

    # Modo demostración

    def _sent_rfq(self):
        wizard = self._import()
        rfq = wizard.rfq_ids
        rfq.with_context(mark_rfq_as_sent=True).message_post(body="Pedido", message_type="comment")
        return rfq

    def test_boton_de_demo_encendido(self):
        self.env["ir.config_parameter"].sudo().set_param(DEMO_MODE_PARAM, "True")
        rfq = self._sent_rfq()
        self.assertTrue(rfq.show_demo_reply)

        rfq.with_user(self.manager).action_simulate_vendor_reply()

        self.assertEqual(rfq.supply_status, "quote_received")
        vendor_email = rfq.message_ids.filtered(lambda m: m.message_type == "email")
        self.assertEqual(vendor_email.author_id.ref, "P91")

    def test_boton_de_demo_apagado(self):
        self.env["ir.config_parameter"].sudo().set_param(DEMO_MODE_PARAM, False)
        rfq = self._sent_rfq()

        self.assertFalse(rfq.show_demo_reply)
        with self.assertRaisesRegex(UserError, "modo demostración está apagado"):
            rfq.action_simulate_vendor_reply()
