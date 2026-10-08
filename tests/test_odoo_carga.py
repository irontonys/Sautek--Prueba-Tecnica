"""Escenarios de la capacidad `carga-odoo`, contra un Odoo simulado."""

import xmlrpc.client

import pytest

from resurtido.loader import load_sheets
from resurtido.odoo import cli
from resurtido.odoo.client import OdooClient, OdooError
from resurtido.odoo.sync import load
from resurtido.validation import validate
from tests.conftest import write_workbook
from tests.fake_odoo import BUY_ROUTE_ID, MXN_ID, STOCK_LOCATION_ID, FakeOdooClient

ENV = {"ODOO_PASSWORD": "prueba"}


def validated(tmp_path, overrides=None):
    return validate(load_sheets(write_workbook(tmp_path / "inv.xlsx", overrides=overrides)))


def never_connect(settings):
    raise AssertionError("No debía conectarse a Odoo")


# Ejecución y conexión

def test_excel_inexistente_no_se_conecta(tmp_path, capsys):
    missing = tmp_path / "no_existe.xlsx"

    assert cli.main(["--input", str(missing)], environ=ENV, connect=never_connect) == 1

    assert str(missing) in capsys.readouterr().err


def test_falta_la_contrasena(tmp_path, capsys):
    source = write_workbook(tmp_path / "inv.xlsx")

    assert cli.main(["--input", str(source)], environ={}, connect=never_connect) == 1

    assert "ODOO_PASSWORD" in capsys.readouterr().err


def test_valores_por_omision_de_la_conexion():
    settings = cli.connection_settings(ENV)

    assert settings["ODOO_URL"] == "http://localhost:8070"
    assert settings["ODOO_DB"] == "sautek"
    assert settings["ODOO_USER"] == "admin"


class _Proxy:
    def __init__(self, authenticate):
        self._authenticate = authenticate

    def authenticate(self, *args):
        return self._authenticate()


def _proxy_factory(authenticate):
    return lambda url, allow_none: _Proxy(authenticate)


def test_odoo_no_responde():
    def refuse():
        raise ConnectionRefusedError(61, "Connection refused")

    with pytest.raises(OdooError, match=r"no responde en http://localhost:8070 \(base sautek\)"):
        OdooClient("http://localhost:8070", "sautek", "admin", "x", _proxy_factory(refuse))


def test_credenciales_invalidas():
    with pytest.raises(OdooError, match=r"rechazó el usuario o la contraseña de 'admin'.*base sautek"):
        OdooClient("http://localhost:8070", "sautek", "admin", "x", _proxy_factory(lambda: False))


def test_base_inexistente():
    def fault():
        raise xmlrpc.client.Fault(1, "Traceback...\npsycopg2.OperationalError: database \"otra\" does not exist")

    with pytest.raises(OdooError, match=r"rechazó la conexión.*database \"otra\" does not exist"):
        OdooClient("http://localhost:8070", "otra", "admin", "x", _proxy_factory(fault))


class _ObjectProxy(_Proxy):
    def __init__(self, fault_text):
        super().__init__(lambda: 2)
        self._fault_text = fault_text

    def execute_kw(self, *args):
        raise xmlrpc.client.Fault(1, self._fault_text)


def _client_with_fault(fault_text):
    return OdooClient("http://localhost:8070", "sautek", "admin", "x",
                      lambda url, allow_none: _ObjectProxy(fault_text))


def test_boton_que_regresa_none_no_es_error():
    client = _client_with_fault("Traceback...\nTypeError: cannot marshal None unless allow_none is enabled")

    assert client.call("purchase.order", "button_cancel", [1]) is None


def test_otro_error_de_odoo_si_es_error():
    client = _client_with_fault("Traceback...\nodoo.exceptions.UserError: No se puede cancelar")

    with pytest.raises(OdooError, match=r"purchase.order.button_cancel: odoo.exceptions.UserError"):
        client.call("purchase.order", "button_cancel", [1])


def test_error_de_odoo_sin_traceback(tmp_path, capsys):
    source = write_workbook(tmp_path / "inv.xlsx")

    def fail(settings):
        raise OdooError("Odoo no responde en http://localhost:8070 (base sautek): refused")

    assert cli.main(["--input", str(source), "--output", str(tmp_path / "out")],
                    environ=ENV, connect=fail) == 1

    err = capsys.readouterr().err
    assert "no responde" in err and "Traceback" not in err


# Solo registros validados

def test_solo_se_cargan_procesables_y_sus_proveedores(tmp_path):
    result = validated(tmp_path, {
        "Existencias": [
            ["FTR-0001", "Martillo uña 16 oz", 3, "PZA", "ACTIVO"],
            ["FTR-0002", "Desarmador plano 1/4", 50, "PZA", "INACTIVO"],
        ],
        "Producto_Proveedor": [
            ["FTR-0001", "P01", 559.58, 6],
            ["FTR-0002", "P02", 66.26, 12],
        ],
        "Proveedores": [
            ["P01", "Distribuidora Truper Norte", "ventas@truper-norte.mx", 5000],
            ["P02", "Otro Proveedor", "otro@prueba.mx", 100],
        ],
    })
    odoo = FakeOdooClient()

    load(odoo, result)

    assert [t["default_code"] for t in odoo.by("product.template")] == ["FTR-0001"]
    assert [p["ref"] for p in odoo.by("res.partner")] == ["P01"]


def test_existencia_negativa_llega_como_cero(tmp_path):
    result = validated(tmp_path, {"Existencias": [
        ["FTR-0001", "Martillo uña 16 oz", -4, "PZA", "ACTIVO"],
        ["FTR-0002", "Desarmador plano 1/4", 50, "PZA", "ACTIVO"],
    ]})
    odoo = FakeOdooClient()

    loaded = load(odoo, result)

    quant = odoo.by("stock.quant", product_id=loaded.product_ids["FTR-0001"])[0]
    assert quant["quantity"] == 0
    assert [p.codigo for p in result.products if p.revisar] == ["FTR-0001"]


# Datos maestros, existencias y reglas

def test_datos_maestros(tmp_path):
    odoo = FakeOdooClient()

    loaded = load(odoo, validated(tmp_path))

    partner = odoo.by("res.partner", ref="P01")[0]
    assert (partner["name"], partner["email"], partner["is_company"]) == (
        "Distribuidora Truper Norte", "ventas@truper-norte.mx", True,
    )
    template = odoo.by("product.template", default_code="FTR-0001")[0]
    assert template["detailed_type"] == "product"
    assert template["route_ids"] == [BUY_ROUTE_ID]
    assert template["supplier_taxes_id"] == []
    seller = odoo.by("product.supplierinfo", product_tmpl_id=template["id"])
    assert [(s["partner_id"], s["price"]) for s in seller] == [(loaded.partner_ids["P01"], 559.58)]


def test_reglas_de_reabastecimiento(tmp_path):
    odoo = FakeOdooClient()

    loaded = load(odoo, validated(tmp_path))

    rule = odoo.records["stock.warehouse.orderpoint"][loaded.orderpoint_ids["FTR-0001"]]
    assert (rule["product_min_qty"], rule["product_max_qty"], rule["qty_multiple"]) == (30, 60, 6)
    assert rule["trigger"] == "manual"
    assert rule["location_id"] == STOCK_LOCATION_ID
    quant = odoo.by("stock.quant", product_id=loaded.product_ids["FTR-0001"])[0]
    assert quant["quantity"] == 3


def test_moneda_de_la_compania_en_pesos(tmp_path):
    odoo = FakeOdooClient()

    loaded = load(odoo, validated(tmp_path))

    assert odoo.records["res.company"][1]["currency_id"] == MXN_ID
    assert odoo.records["res.currency"][MXN_ID]["active"] is True
    assert all(s["currency_id"] == MXN_ID for s in odoo.by("product.supplierinfo"))
    assert loaded.warnings == []


def test_rechazo_de_moneda_no_detiene_la_carga(tmp_path):
    odoo = FakeOdooClient(reject_currency=True)

    loaded = load(odoo, validated(tmp_path))

    assert len(loaded.product_ids) == 2
    assert "no se pudo poner la compañía en MXN" in loaded.warnings[0]


def test_enlaces_de_los_correos_apuntan_al_odoo_de_la_conexion(tmp_path):
    odoo = FakeOdooClient()

    load(odoo, validated(tmp_path))

    assert odoo.params == {"web.base.url": "http://localhost:8070", "web.base.url.freeze": "True"}


def test_dentro_de_odoo_no_se_fija_la_direccion(tmp_path):
    odoo = FakeOdooClient()
    odoo.url = None

    load(odoo, validated(tmp_path))

    assert odoo.params == {}


# Carga repetible

def test_dos_cargas_no_duplican(tmp_path):
    result = validated(tmp_path)
    odoo = FakeOdooClient()

    load(odoo, result)
    load(odoo, result)

    assert len(odoo.by("res.partner")) == 1
    assert len(odoo.by("product.template")) == 2
    assert len(odoo.by("product.supplierinfo")) == 2
    assert len(odoo.by("stock.warehouse.orderpoint")) == 2
    assert sorted(q["quantity"] for q in odoo.by("stock.quant")) == [3, 50]


def test_cambio_de_proveedor_deja_una_sola_tarifa(tmp_path):
    odoo = FakeOdooClient()
    load(odoo, validated(tmp_path))

    loaded = load(odoo, validated(tmp_path, {
        "Producto_Proveedor": [["FTR-0001", "P02", 500.0, 6], ["FTR-0002", "P01", 66.26, 12]],
        "Proveedores": [
            ["P01", "Distribuidora Truper Norte", "ventas@truper-norte.mx", 5000],
            ["P02", "Otro Proveedor", "otro@prueba.mx", 100],
        ],
    }))

    template = odoo.by("product.template", default_code="FTR-0001")[0]
    sellers = odoo.by("product.supplierinfo", product_tmpl_id=template["id"])
    assert [(s["partner_id"], s["price"]) for s in sellers] == [(loaded.partner_ids["P02"], 500.0)]
