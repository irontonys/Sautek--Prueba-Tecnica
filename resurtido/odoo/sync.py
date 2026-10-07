"""Carga a Odoo de los datos ya validados: proveedores, productos, existencias y reglas.

Cada registro se busca por su llave del Excel (`Proveedor_ID` en `ref`, código en
`default_code`) y se actualiza si ya existe, así la carga se puede repetir.
"""

from dataclasses import dataclass, field

from resurtido.odoo.client import OdooError, m2o_id

BUY_ROUTE = "purchase_stock.route_warehouse0_buy"
CURRENCY = "MXN"


@dataclass
class LoadResult:
    warehouse_id: int
    location_id: int
    partner_ids: dict = field(default_factory=dict)  # Proveedor_ID -> res.partner
    product_ids: dict = field(default_factory=dict)  # código -> product.product
    orderpoint_ids: dict = field(default_factory=dict)  # código -> regla
    warnings: list = field(default_factory=list)


def _main_warehouse(client):
    rows = client.search_read("stock.warehouse", [], ["lot_stock_id", "company_id"])
    if not rows:
        raise OdooError("Odoo no tiene ningún almacén: ¿está instalado Inventario?")
    warehouse = min(rows, key=lambda row: row["id"])
    return warehouse["id"], m2o_id(warehouse["lot_stock_id"]), m2o_id(warehouse["company_id"])


def set_company_currency(client, company_id):
    """Pone la compañía en pesos. Regresa un aviso si Odoo no lo permite."""
    try:
        rows = client.search_read(
            "res.currency", [("name", "=", CURRENCY)], ["active"], context={"active_test": False}
        )
        if not rows:
            return f"Aviso: Odoo no tiene la moneda {CURRENCY}; los importes salen en la moneda de la compañía"
        if not rows[0]["active"]:
            client.write("res.currency", [rows[0]["id"]], {"active": True})
        client.write("res.company", [company_id], {"currency_id": rows[0]["id"]})
    except OdooError as exc:
        return f"Aviso: no se pudo poner la compañía en {CURRENCY} ({exc}); los totales no cambian"
    return None


def _upsert(client, model, existing_ids, vals_by_key):
    """Escribe los registros que ya existen y crea el resto. Regresa {llave: id}."""
    ids = {}
    to_create = []
    for key, vals in vals_by_key.items():
        if key in existing_ids:
            client.write(model, [existing_ids[key]], vals)
            ids[key] = existing_ids[key]
        else:
            to_create.append((key, vals))
    created = client.create(model, [vals for _, vals in to_create])
    ids.update({key: new_id for (key, _), new_id in zip(to_create, created)})
    return ids


def load_partners(client, suppliers):
    rows = client.search_read("res.partner", [("ref", "in", sorted(suppliers))], ["ref"])
    existing = {row["ref"]: row["id"] for row in rows}
    vals = {
        supplier_id: {
            "name": supplier.nombre,
            "email": supplier.correo,
            "ref": supplier_id,
            "is_company": True,
            "supplier_rank": 1,
        }
        for supplier_id, supplier in sorted(suppliers.items())
    }
    return _upsert(client, "res.partner", existing, vals)


def load_products(client, products, buy_route_id):
    """Plantillas almacenables con la ruta Comprar. Regresa {código: (plantilla, variante)}."""
    codes = sorted(p.codigo for p in products)
    rows = client.search_read("product.template", [("default_code", "in", codes)], ["default_code"])
    existing = {row["default_code"]: row["id"] for row in rows}
    vals = {
        p.codigo: {
            "name": p.descripcion,
            "default_code": p.codigo,
            "detailed_type": "product",
            "purchase_ok": True,
            "route_ids": [(6, 0, [buy_route_id])],
            # Sin impuestos de compra: los totales se comparan contra la CLI, que no los lleva.
            "supplier_taxes_id": [(6, 0, [])],
        }
        for p in sorted(products, key=lambda p: p.codigo)
    }
    templates = _upsert(client, "product.template", existing, vals)
    rows = client.search_read(
        "product.product", [("product_tmpl_id", "in", sorted(templates.values()))], ["product_tmpl_id"]
    )
    variant_by_template = {m2o_id(row["product_tmpl_id"]): row["id"] for row in rows}
    return {code: (tmpl, variant_by_template[tmpl]) for code, tmpl in templates.items()}


def load_supplier_prices(client, products, templates, partner_ids, currency_id):
    """Una sola tarifa por producto, con su proveedor actual y su costo unitario."""
    by_template = {templates[p.codigo][0]: p for p in products}
    rows = client.search_read(
        "product.supplierinfo",
        [("product_tmpl_id", "in", sorted(by_template))],
        ["product_tmpl_id", "partner_id"],
    )
    existing, stale = {}, []
    for row in rows:
        tmpl = m2o_id(row["product_tmpl_id"])
        product = by_template[tmpl]
        if m2o_id(row["partner_id"]) == partner_ids[product.proveedor_id] and tmpl not in existing:
            existing[tmpl] = row["id"]
        else:
            stale.append(row["id"])
    if stale:
        client.unlink("product.supplierinfo", stale)
    vals = {}
    for tmpl, product in sorted(by_template.items()):
        vals[tmpl] = {
            "product_tmpl_id": tmpl,
            "partner_id": partner_ids[product.proveedor_id],
            "price": product.costo_unitario,
            "min_qty": 0,
        }
        if currency_id:
            vals[tmpl]["currency_id"] = currency_id
    _upsert(client, "product.supplierinfo", existing, vals)


def load_stock(client, products, variants, location_id):
    """Fija la existencia (ya ajustada por la validación) como ajuste de inventario."""
    client.create(
        "stock.quant",
        [
            {
                "product_id": variants[p.codigo],
                "location_id": location_id,
                "inventory_quantity_auto_apply": p.existencia,
            }
            for p in sorted(products, key=lambda p: p.codigo)
        ],
        context={"inventory_mode": True},
    )


def load_orderpoints(client, products, variants, warehouse_id, location_id, buy_route_id):
    by_variant = {variants[p.codigo]: p.codigo for p in products}
    rows = client.search_read(
        "stock.warehouse.orderpoint",
        [("product_id", "in", sorted(by_variant)), ("location_id", "=", location_id)],
        ["product_id"],
    )
    existing = {by_variant[m2o_id(row["product_id"])]: row["id"] for row in rows}
    vals = {
        p.codigo: {
            "product_id": variants[p.codigo],
            "warehouse_id": warehouse_id,
            "location_id": location_id,
            "route_id": buy_route_id,
            "product_min_qty": p.minimo,
            "product_max_qty": p.maximo,
            "qty_multiple": p.empaque_multiplo,
            # Manual: solo este comando dispara compras, no el scheduler nocturno.
            "trigger": "manual",
        }
        for p in sorted(products, key=lambda p: p.codigo)
    }
    return _upsert(client, "stock.warehouse.orderpoint", existing, vals)


def load(client, result):
    """Carga los productos procesables y sus proveedores. Regresa un `LoadResult`."""
    products = result.products
    used = {p.proveedor_id for p in products}
    suppliers = {sid: s for sid, s in result.suppliers.items() if sid in used}

    warehouse_id, location_id, company_id = _main_warehouse(client)
    loaded = LoadResult(warehouse_id, location_id)
    warning = set_company_currency(client, company_id)
    if warning:
        loaded.warnings.append(warning)
    company = client.search_read("res.company", [("id", "=", company_id)], ["currency_id"])
    currency_id = m2o_id(company[0]["currency_id"]) if company else False

    buy_route_id = client.xmlid(BUY_ROUTE)
    loaded.partner_ids = load_partners(client, suppliers)
    templates = load_products(client, products, buy_route_id)
    variants = {code: variant for code, (_, variant) in templates.items()}
    loaded.product_ids = variants
    load_supplier_prices(client, products, templates, loaded.partner_ids, currency_id)
    load_stock(client, products, variants, location_id)
    loaded.orderpoint_ids = load_orderpoints(
        client, products, variants, warehouse_id, location_id, buy_route_id
    )
    return loaded
