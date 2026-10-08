"""Adaptador del motor `resurtido.odoo` al ORM de Odoo.

El motor habla con Odoo por una interfaz mínima (la de `resurtido.odoo.client.OdooClient`:
`search_read`, `create`, `write`, `unlink`, `call`, `execute`, `xmlid`, `uid`, `url`).
Esta clase la implementa sobre `env`, así el asistente corre exactamente el mismo código
que el comando de terminal, sin XML-RPC.
"""

from contextlib import contextmanager

from odoo.exceptions import AccessError, UserError, ValidationError

from resurtido.odoo.client import OdooError


class OrmClient:
    def __init__(self, env):
        self.env = env
        self.uid = env.uid
        # Sin URL: dentro de Odoo la dirección pública la mantiene Odoo y el motor no la fija
        # (ver `resurtido.odoo.sync.set_base_url`).
        self.url = None

    @contextmanager
    def _guard(self, model, method):
        """Como `OdooClient`: un error de Odoo llega como `OdooError`, y solo deshace esa operación.

        Así el motor puede seguir donde ya lo contempla (por ejemplo, si Odoo no deja cambiar
        la moneda porque ya hay asientos contables) sin dejar la transacción a medias.
        """
        try:
            with self.env.cr.savepoint():
                yield
        except (UserError, ValidationError, AccessError) as exc:
            raise OdooError(f"Odoo regresó un error en {model}.{method}: {exc}") from exc

    def _model(self, model, context=None):
        records = self.env[model]
        return records.with_context(**context) if context else records

    def search_read(self, model, domain, fields, context=None):
        with self._guard(model, "search_read"):
            return self._model(model, context).search_read(domain, fields)

    def create(self, model, vals_list, context=None):
        if not vals_list:
            return []
        with self._guard(model, "create"):
            return self._model(model, context).create(vals_list).ids

    def write(self, model, ids, vals):
        with self._guard(model, "write"):
            return self.env[model].browse(ids).write(vals)

    def unlink(self, model, ids):
        with self._guard(model, "unlink"):
            return self.env[model].browse(ids).unlink()

    def call(self, model, method, ids, context=None, **kwargs):
        with self._guard(model, method):
            return getattr(self._model(model, context).browse(ids), method)(**kwargs)

    def execute(self, model, method, *args, **kwargs):
        with self._guard(model, method):
            return getattr(self.env[model], method)(*args, **kwargs)

    def xmlid(self, full_id):
        record = self.env.ref(full_id, raise_if_not_found=False)
        if not record:
            module = full_id.split(".", 1)[0]
            raise OdooError(f"No existe {full_id} en Odoo: ¿está instalado el módulo {module}?")
        return record.id
