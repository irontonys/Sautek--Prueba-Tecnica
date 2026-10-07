"""Cálculo de los pedidos de la semana: qué pedir, cuánto y a quién."""

import math
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from resurtido.validation import PEDIDO_MINIMO_NO_ALCANZADO, DataException

SE_ENVIA = "Se envía"
NO_SE_ENVIA = "No se envía"
SIN_PRODUCTOS = "Sin productos por pedir"

CENT = Decimal("0.01")


def money(value):
    """Pesos con dos decimales; pasa por str para no arrastrar el error del float."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class OrderLine:
    product: object
    cantidad: int
    importe: Decimal


@dataclass
class SupplierOrder:
    supplier: object
    lines: list = field(default_factory=list)
    total: Decimal = Decimal("0.00")
    estado: str = SIN_PRODUCTOS


def needs_order(product):
    return product.existencia < product.minimo


def order_quantity(existencia, maximo, multiplo):
    """Lo que falta para el máximo, redondeado hacia arriba al múltiplo de empaque.

    Un faltante con decimales (por ejemplo, kg) se sube al entero siguiente antes
    de aplicar el múltiplo, para nunca pedir de menos.
    """
    faltante = math.ceil(maximo - existencia)
    return -(-faltante // multiplo) * multiplo


def minimum_shortfall_text(total, minimo):
    return f"Total ${total:,.2f} contra mínimo ${minimo:,.2f}; faltan ${minimo - total:,.2f}"


def minimum_not_reached(supplier, total):
    """Excepción de pedido mínimo no alcanzado para un total ya redondeado a centavos."""
    return DataException(
        "Proveedores", supplier.fila_excel, supplier.proveedor_id, PEDIDO_MINIMO_NO_ALCANZADO,
        minimum_shortfall_text(total, money(supplier.pedido_minimo)), f"{total:.2f}",
    )


def build_orders(products, suppliers):
    """Regresa (pedidos por proveedor, excepciones de pedido mínimo)."""
    lines_by_supplier = {supplier_id: [] for supplier_id in suppliers}
    for product in sorted(products, key=lambda p: p.codigo):
        if not needs_order(product):
            continue
        cantidad = order_quantity(product.existencia, product.maximo, product.empaque_multiplo)
        importe = money(product.costo_unitario) * cantidad
        lines_by_supplier[product.proveedor_id].append(OrderLine(product, cantidad, importe))

    orders, exceptions = [], []
    for supplier_id in sorted(lines_by_supplier):
        supplier = suppliers[supplier_id]
        lines = lines_by_supplier[supplier_id]
        order = SupplierOrder(supplier, lines, sum((l.importe for l in lines), Decimal("0.00")))
        minimo = money(supplier.pedido_minimo)
        if not lines:
            order.estado = SIN_PRODUCTOS
        elif order.total < minimo:
            order.estado = NO_SE_ENVIA
            exceptions.append(minimum_not_reached(supplier, order.total))
        else:
            order.estado = SE_ENVIA
        orders.append(order)
    return orders, exceptions


def order_summary_lines(orders):
    sent = [o for o in orders if o.estado == SE_ENVIA]
    not_sent = [o for o in orders if o.estado == NO_SE_ENVIA]
    total = sum((o.total for o in sent), Decimal("0.00"))
    lines = [
        f"Pedidos que se envían: {len(sent)}",
        f"Pedidos que no se envían (no alcanzan el pedido mínimo): {len(not_sent)}",
    ]
    lines += [f"  {o.supplier.proveedor_id} {o.supplier.nombre}: ${o.total:,.2f}" for o in not_sent]
    lines.append(f"Total a comprar: ${total:,.2f}")
    return lines
