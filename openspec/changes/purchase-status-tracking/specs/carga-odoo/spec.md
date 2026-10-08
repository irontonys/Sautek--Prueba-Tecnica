# Spec Delta

## ADDED Requirements

### Requirement: Enlaces de los correos al Odoo de la conexión
Al cargar, el comando SHALL fijar la dirección pública de Odoo (`web.base.url`) igual a `ODOO_URL` y dejarla fija, para que los enlaces de los correos que envía Odoo (como "View Purchase Order" en los avisos) abran el mismo Odoo al que se conectó el comando.

#### Scenario: Base nueva en otro puerto
- **WHEN** el comando carga a un Odoo recién creado que escucha en `http://localhost:8070`
- **THEN** los enlaces de los avisos que envíe Odoo apuntan a `http://localhost:8070`
