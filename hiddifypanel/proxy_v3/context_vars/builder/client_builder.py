from pydantic import BaseModel
from sqlalchemy.orm import selectinload

from hiddifypanel.cache import cache
from hiddifypanel.models.child import Child
from hiddifypanel.models.config import get_hconfigs_json
from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyMode
from hiddifypanel.models.domain import Domain
from hiddifypanel.models.user import User
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar
from hiddifypanel.proxy_v3.context_vars.domain import DomainIPVar
from hiddifypanel.proxy_v3.context_vars.hconfig import HConfigVar
from hiddifypanel.proxy_v3.context_vars.platform import PlatformVar
from hiddifypanel.proxy_v3.context_vars.proxy import ClientBuilderProxyVar, ProxyVar
from hiddifypanel.proxy_v3.context_vars.user import UserVar

from .utils import protocol_config_map, transport_config_map


def build_client_template_context(user: User, sublink_domain: str, user_agent: str) -> list[ClientContextVar]:
    """Full Jinja context with UserVar, DomainVar, HConfigVar, PlatformVar, ProxyVar."""
    bases = get_bases(sublink_domain)
    user_var = UserVar.from_user(user)
    platform_var = get_platform_var(user_agent)
    return [ClientContextVar(user=user_var, platform=platform_var, hconfig=b.hconfig, proxy=b.proxy) for b in bases]


class BaseVar(BaseModel):
    proxy: ClientBuilderProxyVar
    hconfig: HConfigVar


@cache.cache(600)
def get_bases(sublink_domain: str) -> list[BaseVar]:
    proxies: list[CustomProxy] = CustomProxy.query.options(selectinload(CustomProxy.client_cores)).filter(CustomProxy.enable == True).all()
    child_hconfigs: dict[int, HConfigVar] = get_all_hconfigs()
    domains: list[DomainIPVar] = get_availble_domains(sublink_domain)
    all_bases = []
    for p in proxies:
        proxy_var = ClientBuilderProxyVar.from_custom_proxy(p, child_hconfigs[int(p.child_id)])
        proxy_var.domains = [d for d in domains if filter_domain_for_proxy(d, proxy_var)]
        base = BaseVar(
            proxy=proxy_var,
            hconfig=child_hconfigs[int(p.child_id)],
        )
        all_bases.append(base)

    return [b for b in all_bases if filter_proxy(b)]


def filter_domain_for_proxy(d: DomainIPVar, proxy: ProxyVar) -> bool:
    if d.custom_proxy_id == proxy.id:
        return True
    if d.mode in proxy.domain_modes:
        if d.download is None or d.download.mode in proxy.download_domain_modes:
            return True

    return False


def filter_proxy(base: BaseVar) -> bool:
    if not base.proxy.domains and base.proxy.mode != CustomProxyMode.ip:
        return False

    if (cfg := base.hconfig.get(protocol_config_map[base.proxy.proto])) and cfg is False:
        return False

    if (cfg := base.hconfig.get(transport_config_map.get(base.proxy.transport))) and cfg is False:
        return False

    # if not base.proxy.availble_alpns:
    #     return False

    return True


@cache.cache(600)
def get_client_hconfigs_child(child_id: int | None):
    return HConfigVar(get_hconfigs_json(child_id), server_side=False)


@cache.cache(600)
def get_all_hconfigs():
    return {child.id: HConfigVar(get_hconfigs_json(child.id), server_side=False) for child in Child.query.all()}


@cache.cache(600)
def get_platform_var(user_agent: str) -> PlatformVar:
    return PlatformVar.from_user_agent(user_agent)


@cache.cache(600)
def get_availble_domains(sublink_domain: str | None):
    if not sublink_domain:
        domains = Domain.query.all()
    else:
        db_domain = Domain.query.filter(Domain.domain == sublink_domain).first()

        if not db_domain:
            parts = sublink_domain.split(".")  # TODO fix bug domain maybe null
            parts[0] = "*"
            domain_new = ".".join(parts)
            db_domain = Domain.query.filter(Domain.domain == domain_new).first()

        if not db_domain:
            db_domain = Domain(domain=sublink_domain, show_domains=[])

        domains = db_domain.show_domains or Domain.query.filter(Domain.sub_link_only != True).all()

    return [DomainIPVar.from_domain(d) for d in domains]
