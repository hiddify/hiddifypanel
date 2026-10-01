"""Rules for saving and deleting a domain, shared by the Domains page (admin v2 API) and the classic DomainAdmin.

``validate_domain`` normalizes the row in place and raises ``DomainRuleError`` (message for the admin) when it
can not be saved; it returns warnings (saved anyway). Same checks as the classic form always made:
DNS must point here for direct, elsewhere for CDN/relay, custom proxies must fit the domain (one SNI proxy,
or L7 proxies, never both; REALITY only with REALITY L7 proxies), Cloudflare DNS records are kept in sync.
"""

from __future__ import annotations

from flask_babel import gettext as _
from loguru import logger

from hiddifypanel import hutils
from hiddifypanel.models import ConfigEnum, CustomProxyMode, Domain, DomainType, FakeMode, get_hconfigs, hconfig, set_hconfig
from hiddifypanel.proxy_v3.domain_mode_filter import domain_modes_use_reality, expand_domain_mode_tokens, proxy_buckets_for_domain
from hiddifypanel.proxy_v3.domain_proxy_options import REALITY_TERMINATION_SLUG


class DomainRuleError(ValueError):
    """The domain can not be saved; ``str(e)`` is shown to the admin."""


def proxy_fits_domain(proxy, mode, fake_mode) -> bool:
    """A custom proxy can serve this kind of domain (its domain modes include the domain's bucket)."""
    if proxy is None or proxy.slug == REALITY_TERMINATION_SLUG:
        return False
    if fake_mode == FakeMode.reality and (proxy.mode != CustomProxyMode.domains_l7_gateway or not domain_modes_use_reality(proxy.domain_modes)):
        return False
    buckets = set(proxy_buckets_for_domain(mode, fake_mode))
    return bool(buckets & expand_domain_mode_tokens(proxy.domain_modes))


def check_proxy_selection(proxies) -> None:
    """One SNI proxy at most, and SNI and L7 proxies are never mixed."""
    sni = sum(1 for p in proxies if p and p.mode == CustomProxyMode.domains_sni_gateway)
    has_l7 = any(p and p.mode == CustomProxyMode.domains_l7_gateway for p in proxies)
    if sni > 1:
        raise DomainRuleError(_("domain.custom_proxy.sni_single_only"))
    if sni and has_l7:
        raise DomainRuleError(_("domain.custom_proxy.sni_l7_mutex"))


def validate_domain(model: Domain, *, is_created: bool) -> list[str]:
    """Normalize ``model`` and check it; raises DomainRuleError, returns warnings."""
    warnings: list[str] = []
    model.domain = (model.domain or "").lower().strip()
    model.mode = DomainType(model.mode)
    if model.server_domain:
        model.cdn_ip = ""
        sd = model.server_domain
        if sd.mode not in (DomainType.direct, DomainType.relay) or sd.fake_mode != FakeMode.valid or sd.is_sub_link_only():
            raise DomainRuleError(_("domain.server_domain.must_be_valid_direct_or_relay"))

    if model.download_domain and model.domain == model.download_domain.domain:
        model.download_domain_id = None
        model.download_domain = None

    if model.mode == DomainType.sub_link_only:
        model.fake_mode = FakeMode.valid

    if (model.mode.is_cdn() or model.mode == DomainType.worker) and model.fake_mode != FakeMode.valid:
        raise DomainRuleError(_("CDN and worker domains must use valid fake mode"))

    if model.domain == "" and model.fake_mode != FakeMode.fake:
        raise DomainRuleError(_("domain.empty.allowed_for_fake_only"))

    _check_not_used_before(model)
    ipv4_list = hutils.network.get_ips(4)
    ipv6_list = hutils.network.get_ips(6)
    server_ips = [*ipv4_list, *ipv6_list]
    if not server_ips:
        raise DomainRuleError(_("Couldn't find your ip addresses"))

    if "*" in model.domain and model.mode != DomainType.cdn:
        raise DomainRuleError(_("Domain can not be resolved! there is a problem in your domain"))

    if model.mode == DomainType.relay and model.fake_mode != FakeMode.valid and not (model.cdn_ip or "").strip():
        raise DomainRuleError(_("Relay domains with non-valid fake mode require an IP address"))

    selected = [p for p in (model.custom_proxies or []) if p and p.slug != REALITY_TERMINATION_SLUG]
    if model.fake_mode == FakeMode.reality:
        for proxy in selected:
            if proxy.mode != CustomProxyMode.domains_l7_gateway or not domain_modes_use_reality(proxy.domain_modes):
                raise DomainRuleError(_("domain.custom_proxy.reality_only"))
    else:
        check_proxy_selection(selected)
    model.custom_proxies = [p for p in selected if proxy_fits_domain(p, model.mode, model.fake_mode)]

    if not update_cloudflare(model, ipv4_list, ipv6_list):
        _check_domain_ips(model, server_ips)

    if model.mode == DomainType.direct and model.cdn_ip:
        model.cdn_ip = ""
        raise DomainRuleError(_("Specifying CDN IP is only valid for CDN mode"))

    if not model.mode.is_cdn():
        model.ech = False
    elif model.ech and not hconfig(ConfigEnum.tls_ech_enable):
        raise DomainRuleError(_("Enable TLS ECH in panel settings before using ECH on a CDN domain"))

    if model.fake_mode == FakeMode.fake and not model.cdn_ip:
        model.cdn_ip = str(server_ips[0])

    if model.cdn_ip:
        try:
            hutils.network.auto_ip_selector.get_clean_ip(str(model.cdn_ip))
        except Exception:
            raise DomainRuleError(_("Error in auto cdn format"))

    model.show_domains = [d for d in (model.show_domains or []) if not d.is_sub_link_only()]
    if len(model.show_domains) == Domain.query.count():
        model.show_domains = []

    if model.fake_mode == FakeMode.reality:
        warnings += _check_reality(model, server_ips)
    return warnings


def update_cloudflare(model: Domain, ipv4_list, ipv6_list) -> bool:
    if hconfig(ConfigEnum.cloudflare) and model.fake_mode == FakeMode.valid and model.mode not in [DomainType.relay]:
        try:
            proxied = model.mode == DomainType.cdn
            if ipv4_list:
                hutils.network.cf_api.add_or_update_dns_record(model.domain, str(ipv4_list[0]), "A", proxied=proxied)
            if ipv6_list:
                hutils.network.cf_api.add_or_update_dns_record(model.domain, str(ipv6_list[0]), "AAAA", proxied=proxied)
            return True
        except Exception as e:
            raise DomainRuleError(_("cloudflare.error") + f" {e}")
    return False


def _check_reality(model: Domain, server_ips) -> list[str]:
    warnings: list[str] = []
    if not hconfig(ConfigEnum.reality_enable):
        set_hconfig(ConfigEnum.reality_enable, True)
        hutils.proxy.get_proxies.invalidate_all()

    model.servernames = (model.servernames or model.domain).lower().strip()
    domains_to_check = set()
    for v in [model.domain, model.servernames]:
        domains_to_check.update(d.strip() for d in v.split(",") if d.strip())

    for d in domains_to_check:
        if not hutils.network.is_domain_reality_friendly(d):
            warnings.append(_("Domain is not REALITY friendly!") + f" {d}")
        try:
            if not hutils.network.is_in_same_asn(d, server_ips[0]):
                domain_ips = hutils.network.get_domain_ips(d)
                if domain_ips:
                    dip = next(iter(domain_ips))
                    server_asn = hutils.network.get_ip_asn(server_ips[0])
                    domain_asn = hutils.network.get_ip_asn(dip)
                    msg = _("domain.reality.asn_issue")
                    if server_asn or domain_asn:
                        msg += f"<br> Server ASN={server_asn}<br>{d}_ASN={domain_asn}"
                    warnings.append(msg)
        except Exception as e:
            logger.warning(f"ASN check failed for domain {d}: {str(e)}")

    for d in model.servernames.split(","):
        if d.strip() and not hutils.network.fallback_domain_compatible_with_servernames(model.domain, d):
            warnings.append(_("REALITY Fallback domain is not compatible with server names!") + f" {d} != {model.domain}")
    return warnings


def _check_not_used_before(model: Domain) -> None:
    configs = get_hconfigs()
    for c in configs:
        if "domain" in c and c not in [ConfigEnum.decoy_domain, ConfigEnum.reality_fallback_domain] and c.category != "hidden":
            if model.domain == configs[c]:
                raise DomainRuleError(_("You have used this domain in: ") + _(f"config.{c}.label"))

    for td in Domain.query.filter(Domain.fake_mode == FakeMode.reality, Domain.domain != model.domain).all():
        if td.servernames and (model.domain in td.servernames.split(",")):
            raise DomainRuleError(_("You have used this domain in: ") + _("config.reality_server_names.label") + td.domain)

    # One row per (child, domain), also when an existing domain is renamed to a used name.
    # Empty names (fake mode) may repeat.
    if model.domain:
        same = Domain.query.filter(Domain.domain == model.domain, Domain.child_id == model.child_id).all()
        if any(d is not model and d.id != model.id for d in same):
            raise DomainRuleError(_("You have used this domain in: ") + model.domain)


def _check_domain_ips(model: Domain, server_ips) -> None:
    if (model.domain.startswith("*") or not model.domain) and model.mode not in [DomainType.direct]:
        return
    if model.fake_mode in (FakeMode.fake, FakeMode.reality, FakeMode.dns):
        return
    if model.mode in [DomainType.relay]:
        return
    try:
        dips = hutils.network.get_domain_ips(model.domain)
    except Exception as e:
        logger.error(f"Error resolving domain {model.domain}: {str(e)}")
        raise DomainRuleError(_("Domain cannot be resolved! Please check DNS settings"))
    if not dips:
        raise DomainRuleError(_("Domain cannot be resolved! Please check DNS settings"))

    domain_ip_matches_server = any(ip in dips for ip in server_ips)
    server_ips_str = ", ".join(map(str, server_ips))
    dips_str = ", ".join(map(str, dips))
    if not domain_ip_matches_server and model.mode in [DomainType.direct]:
        raise DomainRuleError(_("Domain IP=%(domain_ip)s is not matched with your ip=%(server_ip)s which is required in direct mode", server_ip=server_ips_str, domain_ip=dips_str))
    if domain_ip_matches_server and model.mode in [DomainType.cdn, DomainType.relay]:
        raise DomainRuleError(_("In CDN mode, Domain IP=%(domain_ip)s should be different to your ip=%(server_ip)s", server_ip=server_ips_str, domain_ip=dips_str))


def before_delete(model: Domain) -> list[str]:
    """Raises DomainRuleError when the domain can not go; returns warnings."""
    warnings: list[str] = []
    if Domain.query.count() <= 1:
        raise DomainRuleError(_("at least one domain should exist"))
    if hconfig(ConfigEnum.cloudflare) and model.fake_mode == FakeMode.valid and model.mode not in [DomainType.relay]:
        if not hutils.network.cf_api.delete_dns_record(model.domain):
            warnings.append(_("cf-delete.failed"))
    model.showed_by_domains = []
    return warnings


def request_certificate(model: Domain) -> bool:
    """Ask acme.sh for a real certificate (runs in the background). False when the domain needs none."""
    from hiddifypanel.panel.run_commander import Command, commander

    if not model.need_valid_ssl or "*" in (model.domain or "") or not model.domain:
        return False
    commander(Command.get_cert, domain=model.domain)
    return True
