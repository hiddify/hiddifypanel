from __future__ import annotations

from typing import Any

from jinja2 import nodes
from jinja2.ext import Extension

from hiddifypanel.models import ConfigEnum, get_hconfigs
from hiddifypanel.models.custom_proxy import normalize_custom_path
from hiddifypanel.hutils.proxy.proxy_render_matrix import ProxyRenderCache, client_domain_vars_for_proxy

from .custom_proxy_ports import ports_dict_for_proxy_row
from .template_context_vars import build_var_context, wrap_domain, wrap_hconfig


class TemplateSkip(Exception):
    """Raised when a template intentionally skips rendering (outputs SKIP)."""


class SkipExtension(Extension):
    """Jinja tag for {% skip() if condition %} used in proxy templates."""

    tags = {'skip'}

    def parse(self, parser):
        next(parser.stream)
        if parser.stream.current.test('lparen'):
            parser.stream.skip()
            parser.stream.skip()
        if parser.stream.skip_if('name:if'):
            cond = parser.parse_expression()
        else:
            cond = nodes.Const(True)
        return nodes.If(cond, [nodes.ExprStmt(self.call_method('_do_skip'))], [], [])

    def _do_skip(self):
        raise TemplateSkip()


class HconfigsAccessor(dict):
    """Legacy hconfigs accessor — prefer hconfig in new templates."""

    def __init__(self, hconfigs: dict | None = None):
        super().__init__()
        for key, value in (hconfigs or {}).items():
            name = getattr(key, 'name', None) or str(key)
            super().__setitem__(name, value)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, ConfigEnum):
            key = key.name
        return super().get(str(key))

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_') or name in ('get', 'keys', 'items', 'values'):
            raise AttributeError(name)
        return self.get(name)

    def get(self, key: Any, default: Any = None) -> Any:  # type: ignore[override]
        if isinstance(key, ConfigEnum):
            key = key.name
        return super().get(str(key), default)


def wrap_hconfigs(hconfigs: dict | None) -> HconfigsAccessor:
    return HconfigsAccessor(hconfigs)


HIDDIFY_MANAGER_ROOT = '/opt/hiddify-manager'


def include_path(slug: str, prefix: str = '.cache/') -> str:
    """Return deployed path for a rendered sidecar file referenced by template slug.

    Usage in templates:
        path,map_beg({{ include_path('haproxy/server/maps/path_v10') }})
        req.ssl_sni,map_str({{ include_path('haproxy/server/maps/sni') }})

    HAProxy map slugs (haproxy/server/maps/*) resolve under haproxy/maps/.
    Other slugs resolve under /opt/hiddify-manager/{prefix}/{slug}.
    """
    rel = (slug or '').strip().lstrip('/')
    if not rel:
        raise ValueError('slug is required')
    
    rel_prefix = (prefix or '.cache/').strip().strip('/')
    rel = f'{rel_prefix}/{rel}' if rel_prefix else rel
    return f'{HIDDIFY_MANAGER_ROOT}/{rel}'


def skip_proxy() -> str:
    """Jinja callable fallback — templates should use {% skip() if cond %}."""
    raise TemplateSkip()




def _load_raw_hconfigs(child_id: int = 0) -> dict[str, Any]:
    try:
        raw = get_hconfigs(child_id)
        return {
            (getattr(k, 'name', None) or str(k)): v
            for k, v in raw.items()
        }
    except RuntimeError:
        return {}


def build_hconfigs_context(child_id: int = 0) -> HconfigsAccessor:
    return wrap_hconfigs(_load_raw_hconfigs(child_id))


def _load_panel_domains(child_id: int) -> list[dict[str, Any]]:
    from hiddifypanel import hutils
    from hiddifypanel.models import Domain, get_hconfigs

    hconfigs = get_hconfigs(child_id)
    result: list[dict[str, Any]] = []
    for domain_db in Domain.query.filter(Domain.child_id == child_id).order_by(Domain.id).all():
        extracted = hutils.proxy.sni_host_server_extractor(domain_db, hconfigs)
        base = domain_db.to_dict(dump_ports=True, dump_child_id=True)
        base.update({
            'sni': extracted.get('sni'),
            'host': extracted.get('host'),
            'server': extracted.get('server') or domain_db.domain,
        })
        if domain_db.download_domain:
            base['download'] = hutils.proxy.sni_host_server_extractor(domain_db.download_domain, hconfigs)
        result.append(base)
    return result


def _load_custom_proxies(child_id: int) -> list[dict[str, Any]]:
    from hiddifypanel.models.custom_proxy import CustomProxy

    rows = (
        CustomProxy.query.filter(CustomProxy.child_id == child_id)
        .order_by(CustomProxy.sort_order, CustomProxy.id)
        .all()
    )
    return [
        {
            'id': row.id,
            'enable': bool(row.enable),
            'mode': row.mode.value if row.mode else '',
            'l7_proto': row.l7_proto.value if row.l7_proto else None,
            'custom_path': row.custom_path or '',
            'server_core': row.server_core.value if row.server_core else '',
            'server_tag': row.server_tag or '',
            'server_config': row.effective_server_config_text(),
            **ports_dict_for_proxy_row(row),
        }
        for row in rows
    ]


def build_template_context(
    child_id: int = 0,
    *,
    user: dict[str, Any] | None = None,
    domain_data: dict[str, Any] | None = None,
    proxy_data: dict[str, Any] | None = None,
    tag: str = '',
    port: int = 443,
    ip: str = '',
    custom_path: str = '',
    public_access: bool = False,
    domain_binding: str = 'domain',
    user_agent: str | None = None,
    user_agent_parsed: dict[str, Any] | None = None,
    server_side: bool = False,
    users: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Full Jinja context with UserVar, DomainVar, HConfigVar, PlatformVar, ProxyVar."""
    raw_hconfigs = _load_raw_hconfigs(child_id)
    hconfigs = wrap_hconfigs(raw_hconfigs)
    normalized_path = normalize_custom_path(custom_path)
    merged_proxy = dict(proxy_data or {})
    if tag:
        merged_proxy.setdefault('tag', tag)
    if port:
        merged_proxy.setdefault('port', port)
    if normalized_path:
        merged_proxy.setdefault('path', normalized_path)
    if ip:
        merged_proxy.setdefault('server', ip)
    if domain_binding:
        merged_proxy.setdefault('domain_binding', domain_binding)
    vars_ctx = build_var_context(
        user=user,
        domain_data=domain_data,
        proxy_data=merged_proxy,
        hconfigs_raw=raw_hconfigs,
        user_agent=user_agent,
        user_agent_parsed=user_agent_parsed,
        server_side=server_side,
        port=port,
        path=normalized_path,
        public_access=public_access,
        tag=tag,
        server=ip or str(merged_proxy.get('server') or ''),
        domain_binding=domain_binding,
    )
    users = users or ([user] if user else [])
    ctx: dict[str, Any] = {
        **vars_ctx,
        'hconfigs': hconfigs,
        'users': users,
        'skip': skip_proxy,
        'enumerate': enumerate,
        'include_path': include_path,
    }
    if server_side:
        cache = ProxyRenderCache.load(child_id)
        ctx['domains'] = [wrap_domain(d) for d in cache.domains]
        ctx['custom_proxies'] = cache.proxies
        ctx['ips_v4'] = cache.ips_v4
        ctx['ips_v6'] = cache.ips_v6
    else:
        proxy_id = merged_proxy.get('id')
        if proxy_id:
            ctx['domains'] = client_domain_vars_for_proxy(child_id, int(proxy_id))
        elif vars_ctx.get('domain') is not None:
            ctx['domains'] = [vars_ctx['domain']]
        else:
            ctx['domains'] = []
    return ctx
