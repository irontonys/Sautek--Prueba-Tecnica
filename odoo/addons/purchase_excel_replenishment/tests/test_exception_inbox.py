"""Escenarios de la capacidad `bandeja-excepciones` dentro de Odoo."""

import base64

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.purchase_excel_replenishment.models.replenishment_exception import REVIEW_ACTIVITY
from odoo.addons.purchase_excel_replenishment.tests.test_excel_import import workbook_bytes

PROVIDER = [["P91", "Proveedor de Prueba", "ventas@proveedor-prueba.test", 1000]]


def rows(minimo_0904=None, stock_0903=-4, inactive=True):
    minimos = [["FTR-0901", 30, 60], ["FTR-0902", 12, 36], ["FTR-0903", 10, 20]]
    if minimo_0904:
        minimos.append(["FTR-0904", minimo_0904, minimo_0904 * 2])
    return {
        "Existencias": [
            ["FTR-0901", "Martillo de prueba", 3, "PZA", "ACTIVO"],
            ["FTR-0902", "Pinza de prueba", 50, "PZA", "INACTIVO" if inactive else "ACTIVO"],
            ["FTR-0903", "Segueta de prueba", stock_0903, "PZA", "ACTIVO"],
            ["FTR-0904", "Brocha de prueba", 5, "PZA", "ACTIVO"],
        ],
        "Minimos": minimos,
        "Producto_Proveedor": [[f"FTR-090{i}", "P91", 100.0, 1] for i in range(1, 5)],
        "Proveedores": PROVIDER,
    }


@tagged("post_install", "-at_install")
class TestExceptionInbox(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.buyer = cls.env["res.users"].create({
            "name": "Comprador Bandeja", "login": "comprador_bandeja", "email": "comprador@ferretera.test",
            "groups_id": [(6, 0, [cls.env.ref("purchase.group_purchase_manager").id])],
        })
        cls.Exception_ = cls.env["purchase.replenishment.exception"]

    def _import(self, data):
        wizard = self.env["purchase.excel.replenishment.wizard"].with_user(self.buyer).create({
            "file": base64.b64encode(workbook_bytes(data)), "filename": "inventario.xlsx",
        })
        wizard.action_import()
        return wizard

    def _by_code(self, tipo_fragment):
        return {e.code: e for e in self.Exception_.search([]) if tipo_fragment in e.exception_type}

    def _open_tasks(self):
        activity_type = self.env.ref(REVIEW_ACTIVITY)
        return self.env["mail.activity"].search([
            ("res_model", "=", "purchase.replenishment.import"), ("activity_type_id", "=", activity_type.id),
        ])

    def test_primera_importacion_asigna_al_comprador_con_su_grupo(self):
        wizard = self._import(rows())

        pending = self.Exception_.search([("state", "=", "pending")])
        self.assertEqual(len(pending), 3)
        self.assertEqual(pending.user_id, self.buyer)
        self.assertEqual(self._by_code("negativa")["FTR-0903"].group, "warning")
        self.assertEqual(self._by_code("inactivo")["FTR-0902"].group, "excluded")
        self.assertEqual(self._by_code("sin mínimo")["FTR-0904"].group, "excluded")
        self.assertIn("Bandeja de excepciones: 3 nuevas, 3 abiertas, 0 resueltas", wizard.summary)

    def test_segunda_importacion_no_duplica(self):
        self._import(rows())
        wizard = self._import(rows())

        self.assertEqual(self.Exception_.search_count([]), 3)
        self.assertEqual(set(self.Exception_.search([]).mapped("times_seen")), {2})
        self.assertIn("0 nuevas, 3 abiertas, 0 resueltas", wizard.summary)

    def test_dato_corregido_se_resuelve(self):
        self._import(rows())
        wizard = self._import(rows(minimo_0904=10))

        brocha = self._by_code("sin mínimo")["FTR-0904"]
        self.assertEqual(brocha.state, "resolved")
        self.assertTrue(brocha.resolved_at)
        self.assertIn("0 nuevas, 2 abiertas, 1 resueltas", wizard.summary)

    def test_el_problema_vuelve_y_se_reabre(self):
        self._import(rows())
        self._import(rows(minimo_0904=10))
        self._import(rows())

        brocha = self._by_code("sin mínimo")["FTR-0904"]
        self.assertEqual((brocha.state, brocha.reopen_count), ("pending", 1))

    def test_aceptada_se_mantiene_y_no_cuenta(self):
        self._import(rows())
        negativa = self._by_code("negativa")["FTR-0903"]
        negativa.with_user(self.buyer).action_accept()
        self.assertEqual((negativa.accepted_by, negativa.state), (self.buyer, "accepted"))
        self.assertTrue(negativa.accepted_at)

        wizard = self._import(rows())

        self.assertEqual(negativa.state, "accepted")
        self.assertIn("0 nuevas, 2 abiertas, 0 resueltas", wizard.summary)

        negativa.with_user(self.buyer).action_reopen()
        self.assertEqual((negativa.state, negativa.accepted_by.id), ("pending", False))

    def test_aceptar_solo_pendientes(self):
        self._import(rows())
        negativa = self._by_code("negativa")["FTR-0903"]
        negativa.action_accept()

        with self.assertRaisesRegex(UserError, "Solo se pueden aceptar excepciones pendientes"):
            negativa.action_accept()

    def test_una_sola_tarea_abierta_para_el_comprador(self):
        self._import(rows())
        self._import(rows())

        tasks = self._open_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks.user_id, self.buyer)
        self.assertIn("Revisar excepciones: 0 nuevas, 3 abiertas", tasks.summary)

    def test_el_aviso_de_la_tarea_tiene_destinatario(self):
        self._import(rows())

        notice = self.env["mail.message"].search([
            ("model", "=", "purchase.replenishment.import"), ("message_type", "=", "user_notification"),
        ])
        self.assertIn(self.buyer.partner_id, notice.notification_ids.res_partner_id)

    def test_sin_pendientes_no_hay_tarea(self):
        self._import(rows(minimo_0904=10, stock_0903=5, inactive=False))

        self.assertFalse(self.Exception_.search([("state", "=", "pending")]))
        self.assertFalse(self._open_tasks())
