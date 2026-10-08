"""Odoo en memoria con la misma interfaz que `OdooClient`, para probar sin Docker.

Imita lo que el comando usa de Odoo 17: búsquedas con `=`/`in`, alta y edición,
ajuste de inventario en modo inventario y el reabastecimiento de `action_replenish`
(pronóstico < mínimo → máximo menos pronóstico, redondeado al múltiplo; una RFQ en
borrador por proveedor). Cada llamada queda en `calls`.
"""

import itertools
import math
from collections import defaultdict

from resurtido.odoo.client import OdooError

WAREHOUSE_ID, STOCK_LOCATION_ID, COMPANY_ID, BUY_ROUTE_ID = 1, 8, 1, 5
ADMIN_UID, ADMIN_PARTNER_ID = 2, 3
USD_ID, MXN_ID = 1, 33


class FakeOdooClient:
    def __init__(self, reject_currency=False):
        self.records = defaultdict(dict)
        self.calls = []
        self._ids = itertools.count(100)
        self.reject_currency = reject_currency
        self.uid = ADMIN_UID
        self.url = "http://localhost:8070"
        self.params = {}
        self.processed_emails = []
        self.records["res.users"][ADMIN_UID] = {"partner_id": ADMIN_PARTNER_ID, "login": "admin"}
        self.records["stock.warehouse"][WAREHOUSE_ID] = {
            "lot_stock_id": STOCK_LOCATION_ID, "company_id": COMPANY_ID,
        }
        self.records["res.company"][COMPANY_ID] = {"currency_id": USD_ID}
        self.records["res.currency"][USD_ID] = {"name": "USD", "active": True}
        self.records["res.currency"][MXN_ID] = {"name": "MXN", "active": False}
        self.xmlids = {"purchase_stock.route_warehouse0_buy": BUY_ROUTE_ID}

    # Interfaz de OdooClient

    def search_read(self, model, domain, fields, context=None):
        self.calls.append((model, "search_read", None))
        return [
            {"id": rec_id, **{f: record.get(f, False) for f in fields}}
            for rec_id, record in sorted(self.records[model].items())
            if all(self._match(record, rec_id, term) for term in domain)
        ]

    def create(self, model, vals_list, context=None):
        self.calls.append((model, "create", None))
        if model == "stock.quant":
            return [self._set_quant(vals) for vals in vals_list]
        ids = []
        for vals in vals_list:
            rec_id = next(self._ids)
            self.records[model][rec_id] = self._clean(vals)
            if model == "product.template":
                variant = next(self._ids)
                self.records["product.product"][variant] = {
                    "product_tmpl_id": rec_id, "default_code": vals.get("default_code"),
                }
                self.records[model][rec_id]["product_variant_id"] = variant
            ids.append(rec_id)
        return ids

    def write(self, model, ids, vals):
        self.calls.append((model, "write", tuple(ids)))
        if model == "res.company" and self.reject_currency:
            raise OdooError("Odoo regresó un error en res.company.write: hay asientos contables")
        for rec_id in ids:
            self.records[model][rec_id].update(self._clean(vals))
        return True

    def unlink(self, model, ids):
        self.calls.append((model, "unlink", tuple(ids)))
        for rec_id in ids:
            del self.records[model][rec_id]
        return True

    def call(self, model, method, ids, context=None, **kwargs):
        self.calls.append((model, method, tuple(ids)))
        if (model, method) == ("stock.warehouse.orderpoint", "action_replenish"):
            self._replenish(ids)
        elif (model, method) == ("purchase.order", "button_cancel"):
            for rec_id in ids:
                self.records[model][rec_id]["state"] = "cancel"
        elif (model, method) == ("purchase.order", "message_post"):
            self.create("mail.message", [{"model": model, "res_id": ids[0], **kwargs}])
        elif (model, method) == ("purchase.order", "message_subscribe"):
            self.create("mail.followers", [
                {"res_model": model, "res_id": rec_id, "partner_id": partner_id}
                for rec_id in ids for partner_id in kwargs["partner_ids"]
            ])
        else:
            raise AssertionError(f"Método no simulado: {model}.{method}")
        return False

    def execute(self, model, method, *args, **kwargs):
        """Solo `ir.config_parameter.set_param` y la entrada de correo (`mail.thread.message_process`)."""
        self.calls.append((model, method, None))
        if (model, method) == ("ir.config_parameter", "set_param"):
            key, value = args
            self.params[key] = value
            return True
        if (model, method) != ("mail.thread", "message_process"):
            raise AssertionError(f"Método no simulado: {model}.{method}")
        target_model, raw = args
        self.processed_emails.append({"model": target_model, "raw": raw, **kwargs})
        return kwargs.get("thread_id")

    def xmlid(self, full_id):
        return self.xmlids[full_id]

    # Ayudas para las pruebas

    def add_manual_rfq(self, partner_id, product_id, qty=1, price=10.0):
        order = self.create("purchase.order", [{
            "partner_id": partner_id, "state": "draft", "name": "P-MANUAL",
            "amount_untaxed": qty * price, "user_id": 2,
        }])[0]
        self.create("purchase.order.line", [{
            "order_id": order, "product_id": product_id, "product_qty": qty,
            "price_unit": price, "orderpoint_id": False,
        }])
        return order

    def notes(self, order_id):
        return [m["body"] for m in self.records["mail.message"].values() if m["res_id"] == order_id]

    def by(self, model, **values):
        return [
            {"id": rec_id, **rec} for rec_id, rec in sorted(self.records[model].items())
            if all(rec.get(k) == v for k, v in values.items())
        ]

    # Internos

    @staticmethod
    def _clean(vals):
        """Los comandos many2many `(6, 0, ids)` se guardan como la lista de ids."""
        cleaned = {}
        for key, value in vals.items():
            if isinstance(value, list) and value and isinstance(value[0], tuple):
                value = list(value[0][2])
            cleaned[key] = value
        return cleaned

    @staticmethod
    def _match(record, rec_id, term):
        field, op, value = term
        current = rec_id if field == "id" else record.get(field, False)
        if op == "=":
            return current == value
        if op == "in":
            return current in value
        raise AssertionError(f"Operador no simulado: {op}")

    def _set_quant(self, vals):
        key = (vals["product_id"], vals["location_id"])
        for rec_id, quant in self.records["stock.quant"].items():
            if (quant["product_id"], quant["location_id"]) == key:
                quant["quantity"] = vals["inventory_quantity_auto_apply"]
                return rec_id
        rec_id = next(self._ids)
        self.records["stock.quant"][rec_id] = {
            "product_id": vals["product_id"], "location_id": vals["location_id"],
            "quantity": vals["inventory_quantity_auto_apply"],
        }
        return rec_id

    def _forecast(self, product_id, location_id):
        on_hand = sum(
            q["quantity"] for q in self.records["stock.quant"].values()
            if (q["product_id"], q["location_id"]) == (product_id, location_id)
        )
        # Como Odoo: cuenta lo que viene en RFQ y compras abiertas, no en las canceladas.
        open_orders = {
            i for i, o in self.records["purchase.order"].items()
            if o["state"] in ("draft", "sent", "to approve", "purchase")
        }
        incoming = sum(
            line["product_qty"] for line in self.records["purchase.order.line"].values()
            if line["product_id"] == product_id and line["order_id"] in open_orders
        )
        return on_hand + incoming

    def _replenish(self, orderpoint_ids):
        for op_id in orderpoint_ids:
            op = self.records["stock.warehouse.orderpoint"][op_id]
            forecast = self._forecast(op["product_id"], op["location_id"])
            if not forecast < op["product_min_qty"]:
                continue
            qty = max(op["product_min_qty"], op["product_max_qty"]) - forecast
            multiple = op["qty_multiple"]
            if multiple:
                qty = math.ceil(qty / multiple) * multiple
            tmpl = self.records["product.product"][op["product_id"]]["product_tmpl_id"]
            seller = self.by("product.supplierinfo", product_tmpl_id=tmpl)[0]
            order = next(
                # Odoo junta en una RFQ en borrador del proveedor sin comprador asignado.
                (o for o in self.by("purchase.order", partner_id=seller["partner_id"], state="draft")
                 if not o.get("user_id")),
                None,
            )
            if order is None:
                order_id = self.create("purchase.order", [{
                    "partner_id": seller["partner_id"], "state": "draft",
                    "name": f"P{next(self._ids):05d}", "amount_untaxed": 0.0,
                }])[0]
            else:
                order_id = order["id"]
            self.create("purchase.order.line", [{
                "order_id": order_id, "product_id": op["product_id"], "product_qty": qty,
                "price_unit": seller["price"], "orderpoint_id": op_id,
            }])
            po = self.records["purchase.order"][order_id]
            po["amount_untaxed"] = round(po["amount_untaxed"] + qty * seller["price"], 2)
