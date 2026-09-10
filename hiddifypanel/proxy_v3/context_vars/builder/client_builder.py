from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import selectinload

from hiddifypanel.cache import cache
from hiddifypanel.models.child import Child
from hiddifypanel.models.config import get_hconfigs_json, hconfig
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyMode
from hiddifypanel.models.domain import Domain
from hiddifypanel.models.user import User
from hiddifypanel.proxy_v3.context_vars.builder.utils import normalize_common_proxy_core
from hiddifypanel.proxy_v3.context_vars.cert import CertVar, select_shared_certificate
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar
from hiddifypanel.proxy_v3.context_vars.domain import DomainIPVar
from hiddifypanel.proxy_v3.context_vars.hconfig import HConfigVar
from hiddifypanel.proxy_v3.context_vars.platform import PlatformVar
from hiddifypanel.proxy_v3.context_vars.proxy import ClientBuilderProxyVar, ProxyVar
from hiddifypanel.proxy_v3.context_vars.user import UserVar
from hiddifypanel.proxy_v3.domain_mode_filter import domain_ip_matches_modes
from hiddifypanel.proxy_v3.domain_proxy_options import REALITY_TERMINATION_SLUG


def _common_proxy_core_cache_token() -> str:
    tokens: list[str] = []
    for child in Child.query.all():
        selected = hconfig(ConfigEnum.common_proxy_core, child.id)
        tokens.append(f"{child.id}:{normalize_common_proxy_core(selected if isinstance(selected, str) or selected is None else None)}")
    return ",".join(tokens)


def build_client_template_context(user: User, sublink_domain: str, user_agent: str, domain_names: list[str] | None = None) -> list[ClientContextVar]:
    """One ``ClientContextVar`` per enabled proxy (domains already filtered on proxy).

    When ``domain_names`` is given, those domains are used instead of the ones the
    sublink domain would expose.
    """
    bases = get_bases(sublink_domain, _common_proxy_core_cache_token(), domain_names)
    user_var = UserVar.from_user(user)
    platform_var = get_platform_var(user_agent)
    return [
        ClientContextVar(
            user=user_var,
            platform=platform_var,
            hconfig=b.hconfig,
            proxy=b.proxy,
            shared_cert=b.shared_cert,
        )
        for b in bases
    ]


class BaseVar(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    proxy: ClientBuilderProxyVar
    hconfig: HConfigVar
    shared_cert: CertVar


@cache.cache(600)
def get_bases(sublink_domain: str, common_core_token: str = "", domain_names: list[str] | None = None) -> list[BaseVar]:
    del common_core_token  # cache key only; selection is re-read from hconfig below
    proxies: list[CustomProxy] = CustomProxy.query.options(selectinload(CustomProxy.client_cores)).filter(CustomProxy.enable == True).all()
    child_hconfigs: dict[int, HConfigVar] = get_all_hconfigs()
    domains: list[DomainIPVar] = get_domains_by_name(domain_names) if domain_names else get_availble_domains(sublink_domain)
    shared_cert = select_shared_certificate()
    all_bases = []
    for p in proxies:
        if not p.enable:
            continue
        child_id = int(p.child_id or 0)
        proxy_var = ClientBuilderProxyVar.from_custom_proxy(p, child_hconfigs[child_id])
        proxy_var.domains = [d for d in domains if filter_domain_for_proxy(d, proxy_var)]
        base = BaseVar(
            proxy=proxy_var,
            hconfig=child_hconfigs[child_id],
            shared_cert=shared_cert,
        )
        all_bases.append(base)

    return [b for b in all_bases if filter_proxy(b)]


def filter_domain_for_proxy(d: DomainIPVar, proxy: ProxyVar) -> bool:
    if proxy.slug == REALITY_TERMINATION_SLUG:
        return d.is_reality()

    if proxy.mode == CustomProxyMode.domains_sni_gateway:
        return d.custom_proxy_id is not None and d.custom_proxy_id == proxy.id

    if d.custom_proxy_id == proxy.id:
        return True
    if not d.is_reality() and d.custom_proxy_id is not None and d.custom_proxy_id != proxy.id:
        return False
    if not domain_ip_matches_modes(d, proxy.domain_modes):
        return False
    # Every DomainIPVar has a download copy of itself. Only a *different*
    # download domain is constrained by download_domain_modes (xhttp).
    if not proxy.download_domain_modes:
        return True
    if d.download is None or d.download.name == d.name:
        return True
    return domain_ip_matches_modes(d.download, proxy.download_domain_modes)


def filter_proxy(base: BaseVar) -> bool:
    # additional_config is client-only and has no domain bindings.
    if base.proxy.slug == "additional-config":
        return True

    if not base.proxy.domains and base.proxy.mode != CustomProxyMode.ip:
        return False

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


def normalize_domain_names(domain_names: list[str] | None) -> list[str]:
    """Trim/lowercase the given names, dropping blanks and duplicates but keeping order."""
    cleaned = (str(name or "").strip().lower() for name in (domain_names or []))
    return list({name for name in cleaned if name})


def find_domains_by_name(domain_names: list[str] | None) -> list[Domain]:
    """Db rows for the given names, in the requested order. Unknown names are ignored."""
    wanted = normalize_domain_names(domain_names)
    if not wanted:
        return []
    found = {str(d.domain or "").lower(): d for d in Domain.query.filter(Domain.domain.in_(wanted)).all()}
    return list(found.values())


@cache.cache(600)
def get_domains_by_name(domain_names: list[str] | None) -> list[DomainIPVar]:
    return [DomainIPVar.from_domain(d) for d in find_domains_by_name(domain_names)]


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
