"""Detección de problemas en los datos y aplicación de la decisión de cada caso.

La detección (las reglas) y la decisión (qué hacer con cada tipo) están separadas:
las reglas solo reportan; `DECISIONS` dice si el producto se excluye y qué se
escribe en el reporte. Cambiar una decisión es cambiar una línea de `DECISIONS`.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

from resurtido.loader import ROW_COLUMN, SHEET_COLUMNS

# Tipos de excepción (se escriben tal cual en la columna `tipo` del reporte).
EXISTENCIA_TEXTO = "Existencia como texto"
EXISTENCIA_NO_NUMERICA = "Existencia no numérica"
EXISTENCIA_VACIA = "Existencia vacía"
EXISTENCIA_NEGATIVA = "Existencia negativa"
CODIGO_VACIO = "Código vacío"
CODIGO_FORMATO = "Código con formato distinto"
CODIGO_NO_NORMALIZABLE = "Código no normalizable"
CODIGO_REPETIDO = "Código repetido en Existencias"
CODIGO_REPETIDO_REFERENCIA = "Código repetido en hoja de referencia"
PRODUCTO_INACTIVO = "Producto inactivo"
POSIBLE_DUPLICADO = "Mismo producto con dos códigos"
UNIDAD_INCONSISTENTE = "Unidad distinta a la descripción"
CODIGO_SIN_EXISTENCIA = "Código ausente de Existencias"
SIN_MINIMO = "Producto sin mínimo"
SIN_PROVEEDOR = "Producto sin proveedor"
MINIMO_INVALIDO = "Mínimo o máximo inválido"
MINIMO_MAYOR_MAXIMO = "Mínimo mayor que máximo"
COSTO_INVALIDO = "Costo inválido"
MULTIPLO_INVALIDO = "Múltiplo de empaque inválido"
PROVEEDOR_INEXISTENTE = "Proveedor inexistente"
PEDIDO_MINIMO_INVALIDO = "Pedido mínimo inválido"
CORREO_INVALIDO = "Correo inválido"
PEDIDO_MINIMO_NO_ALCANZADO = "Pedido mínimo no alcanzado"

PENDING = "Pendiente de decisión"


@dataclass(frozen=True)
class Decision:
    text: str
    excludes: bool


# Decisiones del autor (design.md → Decisiones del autor). Un tipo que no está
# aquí sale "Pendiente de decisión" y excluye al producto.
DECISIONS = {
    EXISTENCIA_TEXTO: Decision("Se convirtió a número y se procesa", False),
    EXISTENCIA_NO_NUMERICA: Decision("No se puede convertir a número: no se procesa", True),
    EXISTENCIA_VACIA: Decision("No se procesa", True),
    EXISTENCIA_NEGATIVA: Decision(
        "Se pide tomando existencia 0 y se marca para revisión del comprador", False
    ),
    CODIGO_VACIO: Decision("No se puede identificar el producto: no se procesa", True),
    CODIGO_FORMATO: Decision("Se normalizó el código y se procesa", False),
    CODIGO_REPETIDO: Decision("Se conserva la primera aparición; este renglón se ignora", False),
    PRODUCTO_INACTIVO: Decision("No se pide", True),
    POSIBLE_DUPLICADO: Decision(
        "No se procesa ningún código del grupo hasta definir cuál es el bueno", True
    ),
    UNIDAD_INCONSISTENTE: Decision(
        "Se supone la misma unidad en existencia, mínimo y máximo (ver SUPUESTOS.md)", False
    ),
    CODIGO_SIN_EXISTENCIA: Decision("No se procesa", True),
    SIN_MINIMO: Decision("No se procesa", True),
    SIN_PROVEEDOR: Decision("No se procesa", True),
    MINIMO_INVALIDO: Decision("No se procesa", True),
    MINIMO_MAYOR_MAXIMO: Decision("No se procesa", True),
    PEDIDO_MINIMO_NO_ALCANZADO: Decision(
        "No se envía el pedido; el comprador decide si lo completa", False
    ),
}


@dataclass
class DataException:
    hoja: str
    fila_excel: int
    codigo: str
    tipo: str
    detalle: str
    valor_original: str = ""

    @property
    def decision(self):
        known = DECISIONS.get(self.tipo)
        return known.text if known else PENDING

    @property
    def excludes(self):
        known = DECISIONS.get(self.tipo)
        return known.excludes if known else True


@dataclass
class Supplier:
    proveedor_id: str
    nombre: str
    correo: str
    pedido_minimo: float
    fila_excel: int = 0


@dataclass
class Product:
    codigo: str
    descripcion: str
    existencia: float
    minimo: float
    maximo: float
    proveedor_id: str
    costo_unitario: float
    empaque_multiplo: int
    fila_excel: int
    revisar: bool = False


@dataclass
class ValidationResult:
    rows_read: int
    repeated: int
    products: list = field(default_factory=list)
    excluded: list = field(default_factory=list)
    suppliers: dict = field(default_factory=dict)
    exceptions: list = field(default_factory=list)


STANDARD_CODE = re.compile(r"FTR-\d{4}")
SHORT_CODE = re.compile(r"FTR-?(\d{1,4})")
THOUSANDS_NUMBER = re.compile(r"-?\d{1,3}(,\d{3})+(\.\d+)?")
PLAIN_NUMBER = re.compile(r"-?\d+(\.\d+)?")
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
UNIT_IN_DESCRIPTION = re.compile(r"\((caja|bolsa|kg|m|par)\)\s*$", re.IGNORECASE)


def is_blank(value):
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ""


def as_text(value):
    return "" if is_blank(value) else str(value)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and not pd.isna(value)


def parse_text_number(text):
    """Convierte `"1,250"` o `"35"` a número; regresa None si no representa uno."""
    text = text.strip()
    if THOUSANDS_NUMBER.fullmatch(text) or PLAIN_NUMBER.fullmatch(text):
        return float(text.replace(",", ""))
    return None


def normalize_code(value):
    """Regresa (código, ¿es estándar?) en mayúsculas, sin espacios y con 4 dígitos."""
    text = str(value).strip().upper()
    match = SHORT_CODE.fullmatch(text)
    if match:
        text = f"FTR-{int(match.group(1)):04d}"
    return text, bool(STANDARD_CODE.fullmatch(text))


def normalize_description(text):
    text = re.sub(r"[\"']", "", str(text).lower())
    return re.sub(r"\s+", " ", text).strip()


class _Collector:
    def __init__(self):
        self.items = []

    def add(self, hoja, fila, codigo, tipo, detalle, valor=""):
        self.items.append(DataException(hoja, int(fila), codigo, tipo, detalle, as_text(valor)))


def _read_codes(frame, hoja, found, column="Codigo"):
    """Normaliza los códigos de una hoja y reporta los vacíos y los que cambiaron.

    Regresa una lista de (renglón, código normalizado), sin los de código vacío.
    """
    rows = []
    for _, row in frame.iterrows():
        raw = row[column]
        if is_blank(raw):
            found.add(hoja, row[ROW_COLUMN], "", CODIGO_VACIO, f"El renglón no tiene {column}")
            continue
        code, standard = normalize_code(raw)
        if not standard:
            found.add(
                hoja, row[ROW_COLUMN], code, CODIGO_NO_NORMALIZABLE,
                "No sigue el formato FTR-0000 y no se pudo normalizar", raw,
            )
        elif code != str(raw):
            found.add(
                hoja, row[ROW_COLUMN], code, CODIGO_FORMATO,
                f"Se escribió {str(raw)!r}; corresponde a {code}", raw,
            )
        rows.append((row, code))
    return rows


def _first_by_code(rows, hoja, found):
    """Primer renglón por código; los repetidos se reportan como ambiguos."""
    first, repeated = {}, set()
    for row, code in rows:
        if code in first:
            repeated.add(code)
            found.add(
                hoja, row[ROW_COLUMN], code, CODIGO_REPETIDO_REFERENCIA,
                f"El código ya aparece en la fila {first[code][ROW_COLUMN]} de {hoja}",
            )
        else:
            first[code] = row
    return first, repeated


def _validate_suppliers(frame, found):
    suppliers, invalid = {}, set()
    seen = {}
    for _, row in frame.iterrows():
        fila = row[ROW_COLUMN]
        if is_blank(row["Proveedor_ID"]):
            found.add("Proveedores", fila, "", CODIGO_VACIO, "El renglón no tiene Proveedor_ID")
            continue
        supplier_id = str(row["Proveedor_ID"]).strip().upper()
        if supplier_id in seen:
            invalid.add(supplier_id)
            found.add(
                "Proveedores", fila, supplier_id, CODIGO_REPETIDO_REFERENCIA,
                f"El proveedor ya aparece en la fila {seen[supplier_id]}",
            )
            continue
        seen[supplier_id] = fila

        correo = as_text(row["Correo"]).strip()
        if not EMAIL.fullmatch(correo):
            invalid.add(supplier_id)
            found.add(
                "Proveedores", fila, supplier_id, CORREO_INVALIDO,
                "El correo no tiene formato válido", row["Correo"],
            )
        pedido_minimo = row["Pedido_minimo_MXN"]
        if not is_number(pedido_minimo) or pedido_minimo < 0:
            invalid.add(supplier_id)
            found.add(
                "Proveedores", fila, supplier_id, PEDIDO_MINIMO_INVALIDO,
                "El pedido mínimo debe ser un número mayor o igual a 0", pedido_minimo,
            )
            pedido_minimo = 0
        suppliers[supplier_id] = Supplier(
            supplier_id, as_text(row["Nombre"]).strip(), correo, float(pedido_minimo), int(fila)
        )
    return suppliers, invalid


def _read_stock(row, code, found):
    """Regresa (existencia para el cálculo o None, ¿marcar para revisión?)."""
    fila, value = row[ROW_COLUMN], row["Existencia"]
    if is_blank(value):
        found.add("Existencias", fila, code, EXISTENCIA_VACIA, "La existencia está vacía")
        return None, False
    if isinstance(value, str):
        number = parse_text_number(value)
        if number is None:
            found.add(
                "Existencias", fila, code, EXISTENCIA_NO_NUMERICA,
                "La existencia no es un número", value,
            )
            return None, False
        found.add(
            "Existencias", fila, code, EXISTENCIA_TEXTO,
            f"Venía como texto; se tomó como {number:g}", value,
        )
        value = number
    if not is_number(value):
        found.add(
            "Existencias", fila, code, EXISTENCIA_NO_NUMERICA, "La existencia no es un número", value
        )
        return None, False
    if value < 0:
        found.add(
            "Existencias", fila, code, EXISTENCIA_NEGATIVA,
            f"Existencia {value:g}; se toma como 0 para el cálculo", value,
        )
        return 0.0, True
    return float(value), False


def validate(sheets):
    found = _Collector()
    existencias = sheets["Existencias"]

    # Existencias: códigos, repetidos (se conserva el primero) y datos de cada producto.
    stock_rows, first_row, repeated = [], {}, 0
    for row, code in _read_codes(existencias, "Existencias", found):
        if code in first_row:
            repeated += 1
            found.add(
                "Existencias", row[ROW_COLUMN], code, CODIGO_REPETIDO,
                f"El código ya aparece en la fila {first_row[code]}",
            )
            continue
        first_row[code] = row[ROW_COLUMN]
        stock_rows.append((row, code))
    blank_codes = len(existencias) - repeated - len(stock_rows)

    stock, review = {}, set()
    for row, code in stock_rows:
        fila = row[ROW_COLUMN]
        estatus = as_text(row["Estatus"]).strip().upper()
        if estatus != "ACTIVO":
            found.add(
                "Existencias", fila, code, PRODUCTO_INACTIVO,
                f"Estatus {estatus or 'vacío'}", row["Estatus"],
            )
        stock[code], needs_review = _read_stock(row, code, found)
        if needs_review:
            review.add(code)
        unit = UNIT_IN_DESCRIPTION.search(as_text(row["Descripcion"]))
        declared = as_text(row["Unidad"]).strip().upper()
        if unit and unit.group(1).upper() != declared:
            found.add(
                "Existencias", fila, code, UNIDAD_INCONSISTENTE,
                f"La descripción dice ({unit.group(1)}) y la unidad es {declared or 'vacía'}",
                row["Descripcion"],
            )

    by_description = defaultdict(list)
    for row, code in stock_rows:
        if not is_blank(row["Descripcion"]):
            by_description[normalize_description(row["Descripcion"])].append((row, code))
    for group in by_description.values():
        if len(group) > 1:
            for row, code in group:
                others = ", ".join(other for _, other in group if other != code)
                found.add(
                    "Existencias", row[ROW_COLUMN], code, POSIBLE_DUPLICADO,
                    f"Misma descripción que {others}", row["Descripcion"],
                )

    # Minimos.
    minimos_rows = _read_codes(sheets["Minimos"], "Minimos", found)
    minimos, _ = _first_by_code(minimos_rows, "Minimos", found)
    limits = {}
    for code, row in minimos.items():
        fila = row[ROW_COLUMN]
        if code not in first_row:
            found.add("Minimos", fila, code, CODIGO_SIN_EXISTENCIA, "No aparece en Existencias")
        minimo, maximo = row["Minimo"], row["Maximo"]
        if not (is_number(minimo) and is_number(maximo) and minimo >= 0 and maximo >= 0):
            found.add(
                "Minimos", fila, code, MINIMO_INVALIDO,
                "Mínimo y máximo deben ser números mayores o iguales a 0",
                f"{as_text(minimo)} / {as_text(maximo)}",
            )
        elif minimo > maximo:
            found.add(
                "Minimos", fila, code, MINIMO_MAYOR_MAXIMO,
                f"Mínimo {minimo:g} mayor que máximo {maximo:g}", f"{minimo:g} / {maximo:g}",
            )
        else:
            limits[code] = (float(minimo), float(maximo))

    # Proveedores y Producto_Proveedor.
    suppliers, invalid_suppliers = _validate_suppliers(sheets["Proveedores"], found)
    pp_rows = _read_codes(sheets["Producto_Proveedor"], "Producto_Proveedor", found)
    product_supplier, _ = _first_by_code(pp_rows, "Producto_Proveedor", found)
    purchase = {}
    for code, row in product_supplier.items():
        fila = row[ROW_COLUMN]
        if code not in first_row:
            found.add(
                "Producto_Proveedor", fila, code, CODIGO_SIN_EXISTENCIA, "No aparece en Existencias"
            )
        supplier_id = as_text(row["Proveedor_ID"]).strip().upper()
        costo, multiplo = row["Costo_unitario_MXN"], row["Empaque_multiplo"]
        valid = True
        if supplier_id not in suppliers:
            valid = False
            found.add(
                "Producto_Proveedor", fila, code, PROVEEDOR_INEXISTENTE,
                "El proveedor no está en la hoja Proveedores", row["Proveedor_ID"],
            )
        if not is_number(costo) or costo <= 0:
            valid = False
            found.add(
                "Producto_Proveedor", fila, code, COSTO_INVALIDO,
                "El costo debe ser un número mayor a 0", costo,
            )
        if not is_number(multiplo) or multiplo <= 0 or float(multiplo) != int(multiplo):
            valid = False
            found.add(
                "Producto_Proveedor", fila, code, MULTIPLO_INVALIDO,
                "El múltiplo debe ser un entero mayor a 0", multiplo,
            )
        if valid:
            purchase[code] = (supplier_id, float(costo), int(multiplo))

    # Referencias faltantes de cada producto.
    for row, code in stock_rows:
        if code not in minimos:
            found.add("Existencias", row[ROW_COLUMN], code, SIN_MINIMO, "No aparece en Minimos")
        if code not in product_supplier:
            found.add(
                "Existencias", row[ROW_COLUMN], code, SIN_PROVEEDOR,
                "No aparece en Producto_Proveedor",
            )

    # Clasificación: un producto se excluye si alguna de sus excepciones lo excluye.
    excluded_codes = {
        e.codigo for e in found.items if e.excludes and e.hoja != "Proveedores"
    }
    result = ValidationResult(rows_read=len(existencias), repeated=repeated, suppliers=suppliers)
    result.excluded.extend([""] * blank_codes)
    for row, code in stock_rows:
        supplier_id = purchase.get(code, (None,))[0]
        if (
            code in excluded_codes
            or supplier_id in invalid_suppliers
            or stock[code] is None
            or code not in limits
            or code not in purchase
        ):
            result.excluded.append(code)
            continue
        _, costo, multiplo = purchase[code]
        minimo, maximo = limits[code]
        result.products.append(
            Product(
                codigo=code,
                descripcion=as_text(row["Descripcion"]).strip(),
                existencia=stock[code],
                minimo=minimo,
                maximo=maximo,
                proveedor_id=supplier_id,
                costo_unitario=costo,
                empaque_multiplo=multiplo,
                fila_excel=int(row[ROW_COLUMN]),
                revisar=code in review,
            )
        )

    result.exceptions = sort_exceptions(found.items)
    return result


def sort_exceptions(items):
    """Ordena las excepciones como aparecen en el Excel: por hoja y luego por fila."""
    sheet_order = {name: i for i, name in enumerate(SHEET_COLUMNS)}
    return sorted(items, key=lambda e: (sheet_order[e.hoja], e.fila_excel))
