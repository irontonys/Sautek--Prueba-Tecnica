{
    "name": "Lectura de cotizaciones por código (Ferretera Garza)",
    "summary": "Lee la cotización adjunta del proveedor por códigos de producto y propone los cambios a la RFQ.",
    "version": "17.0.1.0.0",
    "category": "Inventory/Purchase",
    "license": "LGPL-3",
    "depends": ["purchase_supply_tracking"],
    "external_dependencies": {"python": ["openpyxl", "resurtido"], "bin": ["pdftotext"]},
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
}
