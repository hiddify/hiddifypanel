import sys
from pydantic import BaseModel, ConfigDict

from hiddifypanel import hutils
from hiddifypanel.cache import cache
from hiddifypanel.models.config import get_hconfigs_json
from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyMode
from hiddifypanel.models.domain import Domain, DomainType, FakeMode
from hiddifypanel.models.user import User
from hiddifypanel.proxy_v3.context_vars.ctx_server import ServerContextVar
from hiddifypanel.proxy_v3.context_vars.domain import DomainIPVar
from hiddifypanel.proxy_v3.context_vars.hconfig import HConfigVar
from hiddifypanel.proxy_v3.context_vars.proxy import ProxyVar, ServerBuilderProxyVar
from hiddifypanel.proxy_v3.context_vars.server_platform_var import ServerPlatformVar, get_server_platform_var
from hiddifypanel.proxy_v3.context_vars.user import UserVar
from hiddifypanel.proxy_v3.domain_mode_filter import domain_ip_matches_modes

from hiddifypanel.models.proxy import ProxyTransport
from ..ip import IPVar
from .utils import protocol_config_map, transport_config_map


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


# @cache.cache(600)
def get_server_base(child_id: int) -> ServerBase:
    hconfig: HConfigVar = get_server_hconfigs_child(child_id)
    platform = get_server_platform_var()

    child_hconfigs: HConfigVar = get_server_hconfigs_child(0)
    domains: list[DomainIPVar] = get_server_domains(child_id=child_id)
    ips: IPVar = IPVar.from_strings(*hutils.network.net.get_ips())

    proxies: list[ServerBuilderProxyVar] = get_server_builder_proxies(child_id)
    for proxy in proxies:
        proxy.domains = [d for d in domains if filter_domain_for_proxy(d, proxy)]
    proxies = [b for b in proxies if filter_server_proxy(b, child_hconfigs)]
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


def filter_server_proxy(proxy: ProxyVar, hconfig: HConfigVar) -> bool:
    if not proxy.domains and proxy.mode != CustomProxyMode.ip:
        return False

    if (cfg := hconfig.get(protocol_config_map[proxy.proto])) and cfg is False:
        return False

    if (cfg := hconfig.get(transport_config_map.get(proxy.transport))) and cfg is False:
        return False

    return True


# @cache.cache(600)
def get_server_domains(child_id: int = 0) -> list[DomainIPVar]:
    return [DomainIPVar.from_domain(domain) for domain in Domain.query.filter(Domain.child_id == child_id).all()]


# @cache.cache(600)
def get_server_builder_proxies(child_id: int = 0) -> list[ServerBuilderProxyVar]:
    hconfig = get_server_hconfigs_child(child_id)
    custom_proxies = CustomProxy.query.filter(CustomProxy.enable == True, CustomProxy.child_id == child_id).all()
    return [ServerBuilderProxyVar.from_custom_proxy(proxy, hconfig) for proxy in custom_proxies]


# @cache.cache(600)
def get_server_hconfigs_child(child_id: int | None) -> HConfigVar:
    return HConfigVar(get_hconfigs_json(child_id), server_side=True)
