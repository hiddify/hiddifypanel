from flask.views import MethodView
from pydantic import Field

from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models.role import Role
from hiddifypanel.models.server_ip import ServerIp
from hiddifypanel.health_check import run_domain_health_check, run_ip_health_check
from hiddifypanel.hutils.network.server_ip_sync import sync_server_ips
from hiddifypanel import g, current_app as app
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel


def _child_id() -> int:
    return g.child.id if g.child else 0


class ServerIpSchema(ApiModel):
    id: int | None = None
    child_id: int | None = None
    address: str
    version: int = 4
    enabled: bool = True
    is_auto: bool | None = None
    label: str = ''
    health_status: str | None = None
    last_health_check: str | None = None
    last_health_error: str | None = None


class PatchServerIpSchema(ApiModel):
    address: str | None = None
    version: int | None = None
    enabled: bool | None = None
    label: str | None = None


class HealthCheckResultSchema(ApiModel):
    ok: bool | None = None
    url: str | None = None
    result: str | None = None
    error: str | None = None
    probe_host: str | None = None


class ServerIpsApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(list[ServerIpSchema])  # type: ignore
    def get(self):
        sync_server_ips(_child_id())
        rows = ServerIp.query.filter(ServerIp.child_id == _child_id()).order_by(ServerIp.id).all()
        return [row.to_dict() for row in rows]

    @app.input(ServerIpSchema, arg_name='data')  # type: ignore
    @app.output(ServerIpSchema)  # type: ignore
    def post(self, data: ServerIpSchema):
        payload = data.model_dump(exclude_unset=True)
        row = ServerIp(
            child_id=_child_id(),
            address=str(payload['address']).strip(),
            version=int(payload.get('version') or 4),
            enabled=bool(payload.get('enabled', True)),
            is_auto=False,
            label=str(payload.get('label') or ''),
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

    @app.input(PatchServerIpSchema, arg_name='data')  # type: ignore
    @app.output(ServerIpSchema)  # type: ignore
    def patch(self, ip_id: int, data: PatchServerIpSchema):
        row = ServerIp.query.filter(ServerIp.id == ip_id, ServerIp.child_id == _child_id()).first()
        if not row:
            from apiflask import abort
            abort(404, 'Server IP not found')
        payload = data.model_dump(exclude_unset=True)
        if 'address' in payload:
            row.address = str(payload['address']).strip()
        if 'version' in payload:
            row.version = int(payload['version'])
        if 'enabled' in payload:
            row.enabled = bool(payload['enabled'])
        if 'label' in payload:
            row.label = str(payload['label'] or '')
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
