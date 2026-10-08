{
    "name": "Correo de demostración (Ferretera Garza)",
    "summary": "Configura el correo de prueba del repo: buzón de compras, servidor de entrada y comprador.",
    "description": "Solo para el entorno de demostración de odoo/docker-compose.yml. En producción "
                   "se configura lo mismo con los servidores de correo de la empresa (ver README).",
    "version": "17.0.1.0.0",
    "category": "Hidden",
    "license": "LGPL-3",
    "depends": ["mail", "purchase_supply_tracking"],
    "data": ["data/demo_mail.xml"],
    "installable": True,
}
