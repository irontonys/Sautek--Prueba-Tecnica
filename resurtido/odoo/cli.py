"""Punto de entrada: `python -m resurtido.odoo`.

Valida el Excel con el mismo motor de la CLI, carga a Odoo lo procesable, dispara
el reabastecimiento nativo y concilia los totales de Odoo contra los de la CLI.
"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from resurtido.cli import DEFAULT_INPUT, DEFAULT_OUTPUT, InputError, check_sheets, read_sheet_names
from resurtido.loader import ColumnError, load_sheets
from resurtido.odoo.client import OdooClient, OdooError
from resurtido.odoo.reconcile import reconcile, reconciliation_lines, write_reconciliation
from resurtido.odoo.replenish import (
    cancel_previous, in_progress_suppliers, post_notes, read_rfqs, run_replenishment, subscribe_buyer,
)
from resurtido.odoo.sync import load
from resurtido.orders import build_orders
from resurtido.report import summary_lines, write_exceptions
from resurtido.validation import sort_exceptions, validate

ODOO_SUBDIR = "odoo"
# Apuntan al Odoo de odoo/docker-compose.yml. La contraseña no tiene valor por omisión.
DEFAULTS = {"ODOO_URL": "http://localhost:8070", "ODOO_DB": "sautek", "ODOO_USER": "admin"}


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="python -m resurtido.odoo",
        description="Carga el Excel de inventario a Odoo y genera las RFQ con su reabastecimiento.",
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help="Excel de entrada (por omisión: data/inventario_ferreteria_garza.xlsx)",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help="Carpeta de salida; los archivos van en su subcarpeta odoo/ (por omisión: output/)",
    )
    return parser.parse_args(argv)


def connection_settings(environ):
    settings = {name: environ.get(name) or default for name, default in DEFAULTS.items()}
    settings["ODOO_PASSWORD"] = environ.get("ODOO_PASSWORD")
    if not settings["ODOO_PASSWORD"]:
        raise InputError("Falta la variable de entorno ODOO_PASSWORD (ver README, sección Odoo)")
    return settings


def connect(settings):
    return OdooClient(
        settings["ODOO_URL"], settings["ODOO_DB"], settings["ODOO_USER"], settings["ODOO_PASSWORD"]
    )


@dataclass
class ImportResult:
    loaded: object
    cancelled: list
    rfqs: dict
    minimum_exceptions: list
    rows: list


def run_import(client, result):
    """Carga lo procesable, cancela las RFQ anteriores, reabastece, avisa y concilia.

    La comparten la terminal y el asistente de Odoo. Agrega a `result.exceptions` las
    de pedido mínimo calculadas contra Odoo.
    """
    orders, _ = build_orders(result.products, result.suppliers)
    loaded = load(client, result)
    cancelled = cancel_previous(client, loaded.partner_ids.values())
    run_replenishment(client, loaded.orderpoint_ids.values())
    rfqs = read_rfqs(client, loaded)
    subscribe_buyer(client, rfqs)
    minimum_exceptions = post_notes(client, rfqs, result.suppliers, result.products)
    result.exceptions = sort_exceptions(result.exceptions + minimum_exceptions)
    rows = reconcile(orders, rfqs, loaded.partner_ids, in_progress_suppliers(client, loaded))
    return ImportResult(loaded, cancelled, rfqs, minimum_exceptions, rows)


def import_summary_lines(result, imported):
    lines = summary_lines(result) + list(imported.loaded.warnings)
    lines.append(
        f"Cargados a Odoo: {len(imported.loaded.partner_ids)} proveedores, "
        f"{len(imported.loaded.product_ids)} productos con su existencia y su regla de reabastecimiento"
    )
    if imported.cancelled:
        lines.append(f"RFQ en borrador de la corrida anterior, canceladas: {', '.join(imported.cancelled)}")
    lines.append(
        f"RFQ en borrador generadas por Odoo (sin enviar): {sum(len(r.names) for r in imported.rfqs.values())}"
    )
    lines += [
        f"  {exception.codigo} no alcanza el pedido mínimo: lleva la nota \"No enviar\""
        for exception in imported.minimum_exceptions
    ]
    return lines + reconciliation_lines(imported.rows)


def main(argv=None, environ=None, connect=connect):
    args = parse_args(argv)
    environ = os.environ if environ is None else environ
    try:
        check_sheets(read_sheet_names(args.input))
        sheets = load_sheets(args.input)
        settings = connection_settings(environ)
    except (InputError, ColumnError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    result = validate(sheets)
    try:
        imported = run_import(connect(settings), result)
    except OdooError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output = args.output / ODOO_SUBDIR
    output.mkdir(parents=True, exist_ok=True)
    report = write_exceptions(result.exceptions, output)
    reconciliation = write_reconciliation(imported.rows, output)

    print(f"Excel leído: {args.input}")
    print(f"Odoo: {settings['ODOO_URL']} (base {settings['ODOO_DB']})")
    for line in import_summary_lines(result, imported):
        print(line)
    print(f"Conciliación: {reconciliation}")
    print(f"Reporte de excepciones: {report}")
    return 0
