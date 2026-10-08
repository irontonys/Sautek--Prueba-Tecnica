"""Simula la respuesta de un proveedor a su RFQ: `python -m resurtido.odoo.proveedor P01`.

Arma el correo que mandaría el proveedor contestando a la RFQ enviada y lo mete en
Odoo por la misma entrada que usa Odoo para el correo real (`mail.thread.message_process`).
Así se prueba el seguimiento sin un buzón real.
"""

import argparse
import os
import sys
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from resurtido.cli import InputError
from resurtido.odoo.cli import connect, connection_settings
from resurtido.odoo.client import OdooError, m2o_id

WAITING_QUOTE = "waiting_quote"
# Etiquetas del módulo purchase_supply_tracking, para imprimir el estatus como se ve en Odoo.
STATUS_LABELS = {
    "prepared": "Pedido preparado", "waiting_quote": "Esperando cotización",
    "quote_received": "Cotización recibida", "approved": "Aprobada", "po_sent": "PO enviada",
    "partial": "Recibido parcial", "received": "Recibido", "cancelled": "Cancelado",
}


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="python -m resurtido.odoo.proveedor",
        description="Simula que el proveedor contesta por correo su RFQ enviada desde Odoo.",
    )
    parser.add_argument("proveedor_id", help="Proveedor_ID del Excel, por ejemplo P01")
    return parser.parse_args(argv)


def build_reply(vendor_name, vendor_email, to, subject, order_name, in_reply_to):
    message = EmailMessage()
    message["From"] = formataddr((vendor_name, vendor_email))
    message["To"] = to
    message["Subject"] = f"Re: {subject}" if subject else f"Re: Solicitud de cotización {order_name}"
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=vendor_email.rsplit("@", 1)[-1])
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    message.set_content(
        "Buen día:\n\n"
        f"Recibimos su solicitud de cotización {order_name}. Les confirmamos precios y "
        "disponibilidad tal como vienen en la solicitud.\n\n"
        f"Saludos,\n{vendor_name}\n"
    )
    return message


def _last_sent_email(client, order_id, vendor_partner_id):
    """El último correo que salió de Odoo en la compra: al que contesta el proveedor."""
    messages = client.search_read(
        "mail.message",
        [("model", "=", "purchase.order"), ("res_id", "=", order_id)],
        ["message_id", "subject", "email_from", "author_id", "message_type"],
    )
    sent = [
        m for m in messages
        if m["message_id"] and m["message_type"] != "notification"
        and m2o_id(m["author_id"]) != vendor_partner_id
    ]
    return max(sent, key=lambda m: m["id"]) if sent else None


def reply_to_order(client, order_id):
    """Mete en Odoo el correo del proveedor contestando esa compra. Regresa su estatus después."""
    orders = client.search_read("purchase.order", [("id", "=", order_id)], ["name", "partner_id"])
    if not orders:
        raise InputError(f"No existe la compra {order_id} en Odoo")
    order = orders[0]
    vendor = client.search_read(
        "res.partner", [("id", "=", m2o_id(order["partner_id"]))], ["name", "email"]
    )[0]
    if not vendor["email"]:
        raise InputError(f"El proveedor {vendor['name']} no tiene correo en Odoo")
    sent = _last_sent_email(client, order["id"], vendor["id"]) or {}
    reply = build_reply(
        vendor["name"], vendor["email"],
        to=sent.get("email_from") or "compras",
        subject=sent.get("subject"),
        order_name=order["name"],
        in_reply_to=sent.get("message_id"),
    )
    client.execute("mail.thread", "message_process", "purchase.order", reply.as_string(), thread_id=order["id"])
    after = client.search_read("purchase.order", [("id", "=", order["id"])], ["supply_status"])
    return after[0]["supply_status"] if after else None


def reply_as_vendor(client, supplier_id):
    """Ubica la RFQ del proveedor que espera cotización y la contesta. Regresa (RFQ, estatus)."""
    partners = client.search_read("res.partner", [("ref", "=", supplier_id)], ["name", "email"])
    if not partners:
        raise InputError(
            f"No existe en Odoo el proveedor {supplier_id}: corre primero python -m resurtido.odoo"
        )
    vendor = partners[0]
    if not vendor["email"]:
        raise InputError(f"El proveedor {supplier_id} no tiene correo en Odoo")
    orders = client.search_read(
        "purchase.order",
        [("partner_id", "=", vendor["id"]), ("supply_status", "=", WAITING_QUOTE)],
        ["name"],
    )
    if not orders:
        raise InputError(
            f"El proveedor {supplier_id} no tiene una RFQ esperando cotización: "
            "envíala primero desde Odoo con \"Send by Email\""
        )
    order = max(orders, key=lambda o: o["id"])
    return order["name"], reply_to_order(client, order["id"])


def main(argv=None, environ=None, connect=connect):
    args = parse_args(argv)
    try:
        settings = connection_settings(os.environ if environ is None else environ)
        client = connect(settings)
        order_name, status = reply_as_vendor(client, args.proveedor_id.strip().upper())
    except (InputError, OdooError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"El proveedor {args.proveedor_id.upper()} contestó la RFQ {order_name} por correo.")
    print(f"Estatus de seguimiento en Odoo: {STATUS_LABELS.get(status, status)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
