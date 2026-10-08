# Spec Delta

## ADDED Requirements

### Requirement: Comprador como seguidor
Después de reabastecer, el comando SHALL agregar al usuario de la conexión (`ODOO_USER`) como seguidor de cada RFQ vigente que generó, para que reciba los avisos de esa compra. MUST NOT asignarlo como comprador responsable de la RFQ, para no cambiar cómo Odoo agrupa compras nuevas.

#### Scenario: RFQ generadas
- **WHEN** el comando termina de reabastecer
- **THEN** el usuario de la conexión sigue cada RFQ vigente generada
- **AND** ninguna RFQ generada tiene comprador responsable asignado
