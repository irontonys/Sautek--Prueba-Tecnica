"""Conexión a Odoo por XML-RPC con mensajes de error en español."""

import xmlrpc.client

NONE_RESPONSE = "cannot marshal None"


class OdooError(Exception):
    """Problema al hablar con Odoo que se reporta sin traceback."""


def m2o_id(value):
    """Odoo regresa un many2one como `[id, nombre]`, o `False` si está vacío."""
    if isinstance(value, (list, tuple)):
        return value[0]
    return value or False


def _fault_text(fault):
    lines = [line for line in str(fault.faultString).strip().splitlines() if line.strip()]
    return lines[-1] if lines else str(fault.faultCode)


class OdooClient:
    def __init__(self, url, db, user, password, server_proxy=xmlrpc.client.ServerProxy):
        self.url = url.rstrip("/")
        self.db = db
        self._password = password
        where = f"{self.url} (base {db})"
        try:
            common = server_proxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
            self.uid = common.authenticate(db, user, password, {})
        except xmlrpc.client.Fault as exc:
            raise OdooError(f"Odoo rechazó la conexión a {where}: {_fault_text(exc)}") from exc
        except (OSError, xmlrpc.client.ProtocolError) as exc:
            raise OdooError(f"Odoo no responde en {where}: {exc}") from exc
        if not self.uid:
            raise OdooError(f"Odoo rechazó el usuario o la contraseña de {user!r} en {where}")
        self._models = server_proxy(f"{self.url}/xmlrpc/2/object", allow_none=True)

    def _execute(self, model, method, args, kwargs=None):
        try:
            return self._models.execute_kw(
                self.db, self.uid, self._password, model, method, args, kwargs or {}
            )
        except xmlrpc.client.Fault as exc:
            # Botones como `button_cancel` regresan None: Odoo ya hizo el cambio, pero su
            # servidor XML-RPC no puede enviar None de respuesta.
            if NONE_RESPONSE in str(exc.faultString):
                return None
            raise OdooError(f"Odoo regresó un error en {model}.{method}: {_fault_text(exc)}") from exc
        except (OSError, xmlrpc.client.ProtocolError) as exc:
            raise OdooError(f"Se perdió la conexión con Odoo en {self.url}: {exc}") from exc

    def search_read(self, model, domain, fields, context=None):
        kwargs = {"fields": fields}
        if context:
            kwargs["context"] = context
        return self._execute(model, "search_read", [domain], kwargs)

    def create(self, model, vals_list, context=None):
        """Crea varios registros en una llamada y regresa sus ids."""
        if not vals_list:
            return []
        return self._execute(model, "create", [vals_list], {"context": context} if context else {})

    def write(self, model, ids, vals):
        return self._execute(model, "write", [ids, vals])

    def unlink(self, model, ids):
        return self._execute(model, "unlink", [ids])

    def execute(self, model, method, *args, **kwargs):
        """Llama un método de modelo que no va sobre registros (por ejemplo, `message_process`)."""
        return self._execute(model, method, list(args), kwargs)

    def call(self, model, method, ids, context=None, **kwargs):
        """Llama un método público sobre registros (por ejemplo, un botón)."""
        if context:
            kwargs["context"] = context
        return self._execute(model, method, [ids], kwargs)

    def xmlid(self, full_id):
        module, name = full_id.split(".", 1)
        rows = self.search_read(
            "ir.model.data", [("module", "=", module), ("name", "=", name)], ["res_id"]
        )
        if not rows:
            raise OdooError(f"No existe {full_id} en Odoo: ¿está instalado el módulo {module}?")
        return rows[0]["res_id"]
