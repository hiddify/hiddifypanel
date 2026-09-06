from flask import g, request
from flask.views import MethodView
from apiflask import abort
from flask import current_app as app

from hiddifypanel.auth import login_required
from hiddifypanel.models import Domain, DomainType, FakeMode
from hiddifypanel.models.role import Role
from hiddifypanel.proxy_v3.domain_mode_filter import domain_matches_modes

from hiddifypanel.proxy_v3.api.custom_proxy_schema import DomainOptionSchema, PostDomainSchema


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
                'fake_mode': d.fake_mode.value if d.fake_mode else None,
            }
            for d in domains
        ]


class DomainsQuickAddApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(PostDomainSchema, arg_name='data')  # type: ignore
    @app.output(DomainOptionSchema)  # type: ignore
    def post(self, data):
        mode_str = data.get('mode') or 'direct'
        fake_mode_str = data.get('fake_mode') or FakeMode.valid.value
        if '-' in mode_str and mode_str in (
            'direct-valid',
            'direct-fake',
            'direct-reality',
            'relay-valid',
            'relay-fake',
            'relay-reality',
        ):
            mode_str, fake_mode_str = mode_str.split('-', 1)
        elif mode_str in ('fake', 'reality', 'special'):
            fake_mode_str = 'reality' if mode_str in ('reality', 'special') else 'fake'
            mode_str = 'direct'
        try:
            mode = DomainType(mode_str)
            fake_mode = FakeMode(fake_mode_str)
        except ValueError:
            abort(400, 'Invalid domain mode')
        if mode.is_cdn() and fake_mode != FakeMode.valid:
            abort(400, 'CDN domains require valid fake mode')
        domain = Domain.add_or_update(
            child_id=_child_id(),
            domain=data['domain'].strip(),
            alias=data.get('alias') or data['domain'].strip(),
            mode=mode,
            fake_mode=fake_mode,
            sub_link_only=False,
            cdn_ip='',
            grpc=False,
            ech=False,
            servernames='',
            show_domains=[],
        )
        return {
            'id': domain.id,
            'domain': domain.domain,
            'alias': domain.alias,
            'mode': domain.mode.value if domain.mode else None,
            'fake_mode': domain.fake_mode.value if domain.fake_mode else None,
        }
