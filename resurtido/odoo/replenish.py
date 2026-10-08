"""Reabastecimiento nativo de Odoo y avisos en las RFQ que genera.

Odoo calcula las cantidades con sus reglas; aquí solo se disparan, se leen las
RFQ resultantes y se dejan notas internas. Nunca se confirma ni se envía nada.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from resurtido.odoo.client import m2o_id
from resurtido.orders import minimum_not_reached, minimum_shortfall_text, money

# `qty_to_order` se guarda en la base; sin este contexto Odoo puede usar un valor viejo.
RECOMPUTE = {"recompute_qty_to_order": True}


@dataclass
class Rfq:
    proveedor_id: str
    order_ids: list = field(default_factory=list)
    names: list = field(default_factory=list)
    total: Decimal = Decimal("0.00")
    codes: set = field(default_factory=set)


def own_draft_rfqs(client, partner_ids):
    """RFQ en borrador de los proveedores cargados cuyos renglones vienen todos de una regla.

    Una RFQ hecha a mano no tiene renglones con `orderpoint_id`, así que nunca entra.
    """
    if not partner_ids:
        return []
    orders = client.search_read(
        "purchase.order",
        [("state", "=", "draft"), ("partner_id", "in", sorted(partner_ids))],
        ["partner_id", "name", "amount_untaxed"],
    )
    if not orders:
        return []
    lines = client.search_read(
        "purchase.order.line",
        [("order_id", "in", [o["id"] for o in orders])],
        ["order_id", "orderpoint_id", "product_id"],
    )
    lines_by_order = defaultdict(list)
    for line in lines:
        lines_by_order[m2o_id(line["order_id"])].append(line)
    own = []
    for order in orders:
        order_lines = lines_by_order[order["id"]]
        if order_lines and all(m2o_id(line["orderpoint_id"]) for line in order_lines):
            own.append({**order, "lines": order_lines})
    return own


def in_progress_suppliers(client, loaded):
    """Proveedores con compras enviadas, por aprobar o confirmadas que aún no se reciben completas."""
    if not loaded.partner_ids:
        return set()
    supplier_by_partner = {pid: sid for sid, pid in loaded.partner_ids.items()}
    orders = client.search_read(
        "purchase.order",
        [("partner_id", "in", sorted(supplier_by_partner)), ("state", "in", ["sent", "to approve", "purchase"])],
        ["partner_id", "receipt_status"],
    )
    return {
        supplier_by_partner[m2o_id(order["partner_id"])]
        for order in orders if order.get("receipt_status") != "full"
    }


def cancel_previous(client, partner_ids):
    """Cancela las RFQ en borrador que dejó una corrida anterior. Regresa sus nombres."""
    previous = own_draft_rfqs(client, partner_ids)
    if previous:
        client.call("purchase.order", "button_cancel", [o["id"] for o in previous])
    return [o["name"] for o in previous]


def run_replenishment(client, orderpoint_ids):
    """Equivale al botón "Ordenar una vez" sobre las reglas cargadas."""
    if orderpoint_ids:
        client.call(
            "stock.warehouse.orderpoint", "action_replenish", sorted(orderpoint_ids), context=RECOMPUTE
        )


def read_rfqs(client, loaded):
    """Regresa {Proveedor_ID: Rfq} con las RFQ vigentes que generó el reabastecimiento."""
    supplier_by_partner = {pid: sid for sid, pid in loaded.partner_ids.items()}
    code_by_product = {pid: code for code, pid in loaded.product_ids.items()}
    rfqs = {}
    for order in own_draft_rfqs(client, loaded.partner_ids.values()):
        supplier_id = supplier_by_partner[m2o_id(order["partner_id"])]
        rfq = rfqs.setdefault(supplier_id, Rfq(supplier_id))
        rfq.order_ids.append(order["id"])
        rfq.names.append(order["name"])
        rfq.total += money(order["amount_untaxed"])
        rfq.codes.update(
            code_by_product[m2o_id(line["product_id"])]
            for line in order["lines"]
            if m2o_id(line["product_id"]) in code_by_product
        )
    return rfqs


def subscribe_buyer(client, rfqs):
    """El usuario de la conexión sigue las RFQ para recibir sus avisos.

    Se agrega como seguidor y no como comprador (`user_id`): Odoo junta compras nuevas
    en RFQ cuyo comprador coincide con el del proveedor (supuesto 19).
    """
    order_ids = sorted(order_id for rfq in rfqs.values() for order_id in rfq.order_ids)
    if not order_ids:
        return
    user = client.search_read("res.users", [("id", "=", client.uid)], ["partner_id"])
    client.call("purchase.order", "message_subscribe", order_ids, partner_ids=[m2o_id(user[0]["partner_id"])])


def _note(client, order_ids, body):
    for order_id in order_ids:
        client.call(
            "purchase.order", "message_post", [order_id],
            body=body, message_type="comment", subtype_xmlid="mail.mt_note",
        )


def post_notes(client, rfqs, suppliers, products):
    """Notas internas de pedido mínimo y de productos a revisar. Regresa las excepciones."""
    review = {p.codigo for p in products if p.revisar}
    exceptions = []
    for supplier_id, rfq in sorted(rfqs.items()):
        supplier = suppliers[supplier_id]
        minimo = money(supplier.pedido_minimo)
        if rfq.total < minimo:
            _note(
                client, rfq.order_ids,
                "No enviar: no alcanza el pedido mínimo del proveedor. "
                + minimum_shortfall_text(rfq.total, minimo)
                + ". El comprador decide si lo completa.",
            )
            exceptions.append(minimum_not_reached(supplier, rfq.total))
        to_review = sorted(rfq.codes & review)
        if to_review:
            _note(
                client, rfq.order_ids,
                "Revisar antes de enviar (existencia negativa en el Excel, se pidió con 0): "
                + ", ".join(to_review),
            )
    return exceptions
