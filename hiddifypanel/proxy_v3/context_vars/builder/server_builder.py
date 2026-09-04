import sys

from pydantic import BaseModel, ConfigDict

from hiddifypanel import hutils
from hiddifypanel.cache import cache
from hiddifypanel.models.config import get_hconfigs_json
from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyMode
from hiddifypanel.models.domain import Domain, FakeMode
from hiddifypanel.models.proxy import ProxyTransport
from hiddifypanel.models.user import User
from hiddifypanel.proxy_v3.context_vars.builder.utils import make_jinja_context
from hiddifypanel.proxy_v3.context_vars.ctx_server import ServerContextProxyVar, ServerContextVar
from hiddifypanel.proxy_v3.context_vars.domain import DomainIPVar
from hiddifypanel.proxy_v3.context_vars.hconfig import HConfigVar
from hiddifypanel.proxy_v3.context_vars.proxy import ProxyVar, ServerBuilderProxyVar
from hiddifypanel.proxy_v3.context_vars.server_platform_var import ServerPlatformVar, get_server_platform_var
from hiddifypanel.proxy_v3.context_vars.user import UserVar
from hiddifypanel.proxy_v3.domain_mode_filter import domain_ip_matches_modes
from hiddifypanel.proxy_v3.proxy_render_matrix import _domains_for_proxy_row

from ..ip import IPVar


def build_server_template_context(child_id: int = 0) -> ServerContextVar:
    """Full Jinja context with UserVar, DomainVar, HConfigVar, PlatformVar, ProxyVar."""
    all_users = User.query.all()
    users = [UserVar.from_user(user) for user in all_users if user.is_active]
    inactive_users = [UserVar.from_user(user) for user in all_users if not user.is_active]

    base = get_server_base(child_id)
    return ServerContextVar(
        child_id=child_id,
        users=users,
        inactive_users=inactive_users,
        domains=base.domains,
        hconfig=base.hconfig,
        proxies=base.proxies,
        ips=base.ips,
        platform=base.platform,
    )


class ServerBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    domains: list[DomainIPVar]
    hconfig: HConfigVar
    proxies: list[ServerBuilderProxyVar]
    ips: IPVar
    platform: ServerPlatformVar


def get_server_base(child_id: int) -> ServerBase:
    hconfig: HConfigVar = get_server_hconfigs_child(child_id)
    platform = get_server_platform_var()

    domains: list[DomainIPVar] = get_server_domains(child_id=child_id)
    ips: IPVar = IPVar.from_strings(*hutils.network.net.get_ips())

    proxies: list[ServerBuilderProxyVar] = get_server_builder_proxies(child_id)
    for proxy in proxies:
        proxy.domains = [d for d in domains if filter_domain_for_proxy(d, proxy)]
    proxies = [b for b in proxies if filter_server_proxy(b)]
    return ServerBase(domains=domains, hconfig=hconfig, proxies=proxies, ips=ips, platform=platform)


def filter_domain_for_proxy(d: DomainIPVar, proxy: ProxyVar) -> bool:
    if proxy.slug == "xray-reality-termination":
        return d.is_reality()

    if d.fake_mode == FakeMode.reality and d.custom_proxy_id is None:
        print(f"Domain {d.name} is reality but has no custom proxy", file=sys.stderr)
        return False
    if proxy.mode == CustomProxyMode.domains_sni_gateway and d.custom_proxy_id is None:
        return False

    if d.custom_proxy_id is not None and d.custom_proxy_id != proxy.id:
        return False

    if not domain_ip_matches_modes(d, proxy.domain_modes):
        return False

    if proxy.transport != ProxyTransport.xhttp:
        return True
    if (d.download is None or d.download.name == d.name) or domain_ip_matches_modes(d.download, proxy.download_domain_modes):
        return True

    return False


def filter_server_proxy(proxy: ProxyVar) -> bool:
    if not proxy.domains and proxy.mode != CustomProxyMode.ip:
        return False

    return True


@cache.cache(600)
def get_server_domains(child_id: int = 0) -> list[DomainIPVar]:
    return [DomainIPVar.from_domain(domain) for domain in Domain.query.filter(Domain.child_id == child_id).all()]


@cache.cache(600)
def get_server_builder_proxies(child_id: int = 0) -> list[ServerBuilderProxyVar]:
    hconfig = get_server_hconfigs_child(child_id)
    custom_proxies = CustomProxy.query.filter(CustomProxy.enable == True, CustomProxy.child_id == child_id).all()
    return [ServerBuilderProxyVar.from_custom_proxy(proxy, hconfig) for proxy in custom_proxies if proxy.enable]


@cache.cache(600)
def get_server_hconfigs_child(child_id: int | None) -> HConfigVar:
    return HConfigVar(get_hconfigs_json(child_id), server_side=True)


def resolve_custom_proxy(child_id: int, proxy_id: int | None) -> CustomProxy | None:
    if proxy_id is None:
        return None
    return CustomProxy.query.filter(CustomProxy.id == int(proxy_id), CustomProxy.child_id == child_id).first()


def _domains_for_custom_proxy(proxy: CustomProxy, child_id: int) -> list[DomainIPVar]:
    domain_rows = [
        row
        for row in Domain.query.filter(
            Domain.child_id == child_id,
            Domain.sub_link_only == False,  # noqa: E712
        ).all()
        if not row.custom_proxy_id or int(row.custom_proxy_id) == int(proxy.id or 0)
    ]
    matched = _domains_for_proxy_row(proxy, domain_rows)
    return [DomainIPVar.from_domain(domain) for domain in matched]


def _filter_domains(
    domains: list[DomainIPVar],
    *,
    domain_id: int | None = None,
    domain_host: str | None = None,
) -> list[DomainIPVar]:
    if domain_id is not None:
        return [domain for domain in domains if domain.id == int(domain_id)]
    host = str(domain_host or "").strip().lower()
    if host:
        return [domain for domain in domains if domain.name == host or domain.host == host]
    return domains


def build_proxy_jinja_context(
    child_id: int,
    proxy: CustomProxy,
    *,
    core: str = "xray",
    domain_id: int | None = None,
    domain_host: str | None = None,
    user_id: int | None = None,
    user_uuid: str | None = None,
) -> dict:
    del core, user_id, user_uuid
    hconfig = get_server_hconfigs_child(child_id)
    all_users = User.query.all()
    users = [UserVar.from_user(user) for user in all_users if user.is_active]
    inactive_users = [UserVar.from_user(user) for user in all_users if not user.is_active]
    platform = get_server_platform_var()
    ips = IPVar.from_strings(*hutils.network.net.get_ips())
    domains = _filter_domains(
        _domains_for_custom_proxy(proxy, child_id),
        domain_id=domain_id,
        domain_host=domain_host,
    )
    proxy_var = ServerBuilderProxyVar.from_custom_proxy(proxy, hconfig)
    proxy_var.domains = domains
    ctx = ServerContextProxyVar(
        child_id=child_id,
        users=users,
        inactive_users=inactive_users,
        domains=domains,
        hconfig=hconfig,
        proxies=[proxy_var],
        proxy=proxy_var,
        ips=ips,
        platform=platform,
    )
    return make_jinja_context(ctx)


def build_bundle_jinja_context(
    child_id: int,
    *,
    domain_id: int | None = None,
    domain_host: str | None = None,
    user_id: int | None = None,
    user_uuid: str | None = None,
) -> dict:
    del user_id, user_uuid
    ctx = build_server_template_context(child_id)
    domains = _filter_domains(list(ctx.domains), domain_id=domain_id, domain_host=domain_host)
    return make_jinja_context(
        ServerContextVar(
            child_id=ctx.child_id,
            users=ctx.users,
            inactive_users=ctx.inactive_users,
            domains=domains,
            hconfig=ctx.hconfig,
            proxies=ctx.proxies,
            ips=ctx.ips,
            platform=ctx.platform,
            client_proxy_tags=list(ctx.client_proxy_tags),
        )
    )
