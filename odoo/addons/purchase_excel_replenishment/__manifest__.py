{
    "name": "Importar inventario desde Excel (Ferretera Garza)",
    "summary": "Sube el Excel de inventario desde Compras y genera las RFQ con el mismo motor de la CLI.",
    "version": "17.0.1.0.0",
    "category": "Inventory/Purchase",
    "license": "LGPL-3",
    "depends": ["purchase_supply_tracking"],
    "external_dependencies": {"python": ["pandas", "openpyxl", "resurtido"]},
    "data": [
        "security/ir.model.access.csv",
        "data/mail_activity_type.xml",
        "views/replenishment_exception_views.xml",
        "wizard/excel_import_views.xml",
        "views/purchase_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
}
