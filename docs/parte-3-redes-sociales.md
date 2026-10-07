# Parte 3. Redes sociales

## Cómo llevar los contactos al CRM sin capturarlos

**Que el mensaje llegue solo.** Cuando un cliente escribe por Facebook o Instagram, la API de Meta avisa por **webhook**. Es directo y no hay que estar consultando a cada rato si hay mensajes nuevos. El webhook lo recibe Odoo directamente; otra opción es un servicio intermedio como n8n.

**Qué se guarda del cliente:**
- Nombre y giro.
- Datos de contacto.
- Qué compra con frecuencia y en qué cantidades.
- Ubicación de entrega.
- De dónde vino: Facebook, Instagram o WhatsApp. Esto queda en un campo del registro y es la base de los números para dirección.

**Clientes repetidos.** Antes de crear un registro, se compara contra los que ya existen por **nombre y teléfono**. Si hay coincidencia clara, se une al cliente existente. Si no está seguro, el lead se marca para revisión y una persona decide a qué cliente pertenece.

**La cotización deja de vivir en Excel.** Se hace dentro del CRM, sobre el mismo lead. Así queda registrada, es más fácil y se puede medir.

## Qué dejaría a la IA y qué no

**Sí, a la IA:** la entrada de los mensajes. Que entienda lo que escribe el cliente aunque tenga errores, detecte su intención (cotizar, preguntar por un pedido, quejarse) y extraiga los datos valiosos, como productos, cantidades o fechas.

**No, a la IA sola:**
- **Enviar pedidos** sin que alguien de ventas los confirme.
- **Dar descuentos.** Todo lo que toca las finanzas de la empresa lo decide una persona.

**Cuando la IA se equivoca o no entiende**, entra una persona (*human in the loop*):
- **Rápido:** la persona corrige lo que hizo la IA y atiende al cliente.
- **De fondo:** se investiga de dónde salió el error para que no se repita.

## Qué números le daría a dirección

| Número | Para qué sirve |
|---|---|
| **Leads de redes realmente interesados** (ya filtrados, por canal) | Saber si las redes atraen clientes, no solo mensajes |
| **Cotizaciones de redes en proceso** | Ver lo que viene en camino |
| **Cotizaciones de redes ya surtidas**, en pesos | Saber si las redes **venden** |

Se sabe que una venta vino de redes por el campo de origen que se guarda desde el primer mensaje.

Dirección los ve **en Odoo, en vivo**, sin esperar un reporte semanal ni triangular información entre Excel y otros sistemas.
