"""Conciliación por proveedor: total de la CLI contra total sin impuestos de la RFQ en Odoo."""

import csv
from dataclasses import dataclass
from decimal import Decimal

RECONCILIATION_FILE = "conciliacion.csv"
CUADRA = "Cuadra"
EN_PROCESO = "Compra en proceso"
NO_CUADRA = "No cuadra"
TOLERANCE = Decimal("0.01")
COLUMNS = ["proveedor_id", "proveedor", "rfq_odoo", "total_cli", "total_odoo", "diferencia", "estado"]


@dataclass
class ReconciliationRow:
    proveedor_id: str
    proveedor: str
    rfq_odoo: str
    total_cli: Decimal
    total_odoo: Decimal
    diferencia: Decimal
    estado: str


def _status(diferencia, supplier_id, in_progress):
    if abs(diferencia) <= TOLERANCE:
        return CUADRA
    # Odoo no vuelve a pedir lo que ya está en camino: la diferencia no es un error.
    return EN_PROCESO if supplier_id in in_progress else NO_CUADRA


def reconcile(orders, rfqs, supplier_ids, in_progress=frozenset()):
    """Un renglón por proveedor cargado. `orders` viene de `build_orders`; `rfqs` de Odoo.

    `in_progress`: proveedores con compras ya enviadas, por aprobar o confirmadas sin recibir.
    """
    by_supplier = {o.supplier.proveedor_id: o for o in orders}
    rows = []
    for supplier_id in sorted(supplier_ids):
        order = by_supplier[supplier_id]
        rfq = rfqs.get(supplier_id)
        total_odoo = rfq.total if rfq else Decimal("0.00")
        diferencia = total_odoo - order.total
        rows.append(
            ReconciliationRow(
                supplier_id, order.supplier.nombre, ", ".join(rfq.names) if rfq else "",
                order.total, total_odoo, diferencia, _status(diferencia, supplier_id, in_progress),
            )
        )
    return rows


def write_reconciliation(rows, output_dir):
    path = output_dir / RECONCILIATION_FILE
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([getattr(row, column) for column in COLUMNS])
    return path


def reconciliation_lines(rows):
    ok = [row for row in rows if row.estado == CUADRA]
    busy = [row for row in rows if row.estado == EN_PROCESO]
    bad = [row for row in rows if row.estado == NO_CUADRA]
    lines = [f"Comprobación del cálculo: {len(ok)} de {len(rows)} proveedores cuadran"]
    if busy:
        lines.append(
            f"  Con compra en proceso (Odoo no vuelve a pedir lo que ya está en camino): "
            + ", ".join(row.proveedor_id for row in busy)
        )
    lines += [
        f"  No cuadra {row.proveedor_id} {row.proveedor}: CLI ${row.total_cli:,.2f}, "
        f"Odoo ${row.total_odoo:,.2f} (diferencia ${row.diferencia:,.2f})"
        for row in bad
    ]
    return lines
