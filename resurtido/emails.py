"""Borradores de correo por proveedor. Nunca se envían: solo se escriben archivos."""

import csv
import re
import unicodedata
from datetime import date
from email import policy
from email.message import EmailMessage

from resurtido.orders import NO_SE_ENVIA, SE_ENVIA

EMAILS_DIR = "correos"
INDEX_FILE = "indice.csv"
INDEX_COLUMNS = [
    "proveedor_id", "proveedor", "correo", "estado", "archivo",
    "productos", "total_mxn", "revisar_antes_de_enviar",
]
COMPANY = "Ferretera Garza"
MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def long_date(day):
    return f"{day.day} de {MONTHS[day.month - 1]} de {day.year}"


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def draft_filename(order):
    supplier = order.supplier
    return f"{supplier.proveedor_id}_{slugify(supplier.nombre)}.eml"


def draft_body(order, day):
    rows = [
        (
            line.product.codigo,
            line.product.descripcion,
            str(line.cantidad),
            f"${line.product.costo_unitario:,.2f}",
            f"${line.importe:,.2f}",
        )
        for line in order.lines
    ]
    header = ("Código", "Descripción", "Cantidad", "Costo unitario", "Importe")
    widths = [max(len(row[i]) for row in [header] + rows) for i in range(len(header))]

    def format_row(row):
        left = [row[0].ljust(widths[0]), row[1].ljust(widths[1])]
        right = [value.rjust(width) for value, width in zip(row[2:], widths[2:])]
        return "  ".join(left + right).rstrip()

    table = [format_row(header), format_row(["-" * w for w in widths])]
    table += [format_row(row) for row in rows]
    total = f"Total del pedido: ${order.total:,.2f}"
    table.append(total.rjust(len(table[0])))

    return "\n".join(
        [
            f"Estimado equipo de {order.supplier.nombre}:",
            "",
            f"Les compartimos nuestro pedido de resurtido del {long_date(day)}:",
            "",
            *table,
            "",
            "Les pedimos confirmar por este medio las cantidades y la fecha de entrega"
            " de cada producto.",
            "",
            "Saludos,",
            "Compras",
            COMPANY,
            "",
        ]
    )


def build_draft(order, day):
    message = EmailMessage(policy=policy.default)
    message["To"] = order.supplier.correo
    message["Subject"] = f"Pedido de resurtido {COMPANY} - {day.isoformat()}"
    # Outlook abre como borrador editable un .eml con esta marca. Sin `From`:
    # el cliente de correo pone la cuenta de quien lo abre.
    message["X-Unsent"] = "1"
    message.set_content(draft_body(order, day), charset="utf-8", cte="8bit")
    return message


def write_drafts(orders, output_dir, day=None):
    """Escribe un .eml por pedido que se envía y el índice interno. Regresa la carpeta."""
    day = day or date.today()
    folder = output_dir / EMAILS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    # Un borrador viejo de un proveedor que ya no tiene pedido podría enviarse por error.
    for old in folder.glob("*.eml"):
        old.unlink()

    index_rows = []
    for order in orders:
        if order.estado not in (SE_ENVIA, NO_SE_ENVIA):
            continue
        filename = ""
        if order.estado == SE_ENVIA:
            filename = draft_filename(order)
            (folder / filename).write_bytes(build_draft(order, day).as_bytes())
        index_rows.append(
            [
                order.supplier.proveedor_id,
                order.supplier.nombre,
                order.supplier.correo,
                order.estado,
                filename,
                len(order.lines),
                f"{order.total:.2f}",
                "; ".join(l.product.codigo for l in order.lines if l.product.revisar),
            ]
        )

    with (folder / INDEX_FILE).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(INDEX_COLUMNS)
        writer.writerows(index_rows)
    return folder
