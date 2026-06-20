from flask import g
from flask.views import MethodView
from apiflask import Schema, fields
from flask import current_app as app

from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models.role import Role
from hiddifypanel.models.server_ip import ServerIp
from hiddifypanel.health_check import run_domain_health_check, run_ip_health_check
from hiddifypanel.hutils.network.server_ip_sync import sync_server_ips


def _child_id() -> int:
    return g.child.id if g.child else 0


class ServerIpSchema(Schema):
    id = fields.Integer(dump_only=True)
    child_id = fields.Integer()
    address = fields.String(required=True)
    version = fields.Integer(load_default=4)
    enabled = fields.Boolean(load_default=True)
    is_auto = fields.Boolean(dump_only=True)
    label = fields.String(load_default='')
    health_status = fields.String(dump_only=True)
    last_health_check = fields.String(dump_only=True)
    last_health_error = fields.String(dump_only=True)


class HealthCheckResultSchema(Schema):
    ok = fields.Boolean()
    url = fields.String()
    result = fields.String()
    error = fields.String()
    probe_host = fields.String()


class ServerIpsApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(list[ServerIpSchema])  # type: ignore
    def get(self):
        sync_server_ips(_child_id())
        rows = ServerIp.query.filter(ServerIp.child_id == _child_id()).order_by(ServerIp.id).all()
        return [row.to_dict() for row in rows]

    @app.input(ServerIpSchema, arg_name='data')  # type: ignore
    @app.output(ServerIpSchema)  # type: ignore
    def post(self, data):
        row = ServerIp(
            child_id=_child_id(),
            address=str(data['address']).strip(),
            version=int(data.get('version') or 4),
            enabled=bool(data.get('enabled', True)),
            is_auto=False,
            label=str(data.get('label') or ''),
        )
        db.session.add(row)
        db.session.commit()
        return row.to_dict()


class ServerIpApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(ServerIpSchema)  # type: ignore
    def get(self, ip_id: int):
        row = ServerIp.query.filter(ServerIp.id == ip_id, ServerIp.child_id == _child_id()).first()
        if not row:
            from apiflask import abort
            abort(404, 'Server IP not found')
        return row.to_dict()

    @app.input(ServerIpSchema(partial=True), arg_name='data')  # type: ignore
    @app.output(ServerIpSchema)  # type: ignore
    def patch(self, ip_id: int, data):
        row = ServerIp.query.filter(ServerIp.id == ip_id, ServerIp.child_id == _child_id()).first()
        if not row:
            from apiflask import abort
            abort(404, 'Server IP not found')
        if 'address' in data:
            row.address = str(data['address']).strip()
        if 'version' in data:
            row.version = int(data['version'])
        if 'enabled' in data:
            row.enabled = bool(data['enabled'])
        if 'label' in data:
            row.label = str(data['label'] or '')
        db.session.commit()
        return row.to_dict()

    def delete(self, ip_id: int):
        row = ServerIp.query.filter(ServerIp.id == ip_id, ServerIp.child_id == _child_id()).first()
        if not row:
            from apiflask import abort
            abort(404, 'Server IP not found')
        db.session.delete(row)
        db.session.commit()
        return '', 204


class ServerIpHealthCheckApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(HealthCheckResultSchema)  # type: ignore
    def post(self, ip_id: int):
        return run_ip_health_check(ip_id, _child_id())


class DomainHealthCheckApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(HealthCheckResultSchema)  # type: ignore
    def post(self, domain_id: int):
        return run_domain_health_check(domain_id, _child_id())
