from flask import g, request
from flask.views import MethodView
from apiflask import abort
from flask import current_app as app

from hiddifypanel.auth import login_required
from hiddifypanel.models import Domain, DomainType
from hiddifypanel.models.role import Role
from hiddifypanel.hutils.proxy.domain_mode_filter import domain_matches_modes

from .custom_proxy_schema import DomainOptionSchema, PostDomainSchema

_SPECIAL_DOMAIN_TYPES = {
    DomainType.special_reality_tcp,
    DomainType.special_reality_xhttp,
    DomainType.special_reality_grpc,
}


def _child_id() -> int:
    return g.child.id if g.child else 0


def _domain_matches_modes(domain: Domain, modes: list[str]) -> bool:
    return domain_matches_modes(domain, modes)


class DomainsOptionsApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(list[DomainOptionSchema])  # type: ignore
    def get(self):
        modes_param = request.args.get('modes', '')
        modes = [m.strip() for m in modes_param.split(',') if m.strip()] if modes_param else []
        domains = Domain.query.filter(
            Domain.child_id == _child_id(),
            Domain.sub_link_only == False,  # noqa: E712
        ).order_by(Domain.domain).all()
        if modes:
            domains = [d for d in domains if _domain_matches_modes(d, modes)]
        return [
            {
                'id': d.id,
                'domain': d.domain,
                'alias': d.alias,
                'mode': d.mode.value if d.mode else None,
            }
            for d in domains
        ]


class DomainsQuickAddApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(PostDomainSchema, arg_name='data')  # type: ignore
    @app.output(DomainOptionSchema)  # type: ignore
    def post(self, data):
        mode_str = data.get('mode') or 'direct'
        if mode_str == 'special':
            mode_str = DomainType.special_reality_tcp.value
        try:
            mode = DomainType(mode_str)
        except ValueError:
            abort(400, 'Invalid domain mode')
        domain = Domain.add_or_update(
            child_id=_child_id(),
            domain=data['domain'].strip(),
            alias=data.get('alias') or data['domain'].strip(),
            mode=mode,
            sub_link_only=False,
            cdn_ip='',
            grpc=False,
            servernames='',
            show_domains=[],
        )
        return {
            'id': domain.id,
            'domain': domain.domain,
            'alias': domain.alias,
            'mode': domain.mode.value if domain.mode else None,
        }
