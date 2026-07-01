from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hiddifypanel import hutils
from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyMode
from hiddifypanel.models import Domain, get_hconfigs

from .custom_proxy_ports import default_domain_modes_for_mode, mode_value, ports_dict_for_proxy_row, ports_dict_for_proxy_row
from .domain_mode_filter import domain_matches_modes


@dataclass
class ProxyRenderCache:
    child_id: int
    domains: list[dict[str, Any]] = field(default_factory=list)
    proxies: list[dict[str, Any]] = field(default_factory=list)
    ips_v4: list[dict[str, Any]] = field(default_factory=list)
    ips_v6: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, child_id: int) -> ProxyRenderCache:
        from hiddifypanel.models.server_ip import ServerIp

        cache = cls(child_id=child_id)
        hconfigs = get_hconfigs(child_id)
        for domain_db in Domain.query.filter(Domain.child_id == child_id).order_by(Domain.id).all():
            if domain_db.sub_link_only:
                continue
            extracted = hutils.proxy.sni_host_server_extractor(domain_db, hconfigs)
            base = domain_db.to_dict(dump_ports=True, dump_child_id=True)
            base.update(
                {
                    "domain_id": domain_db.id,
                    "sni": extracted.get("sni"),
                    "host": extracted.get("host"),
                    "server": extracted.get("server") or domain_db.domain,
                }
            )
            if domain_db.download_domain:
                base["download"] = hutils.proxy.sni_host_server_extractor(domain_db.download_domain, hconfigs)
            cert = domain_db.certificate
            if cert:
                base["cert"] = cert.to_dict()
            cache.domains.append(base)

        import re as _re

        rows = CustomProxy.query.filter(CustomProxy.child_id == child_id).order_by(CustomProxy.sort_order, CustomProxy.id).all()
        domain_rows = [
            d
            for d in Domain.query.filter(Domain.child_id == child_id, Domain.sub_link_only == False).all()  # noqa: E712
        ]
        for row in rows:
            if not row.enable:
                continue
            related = _domain_rows_for_proxy(row, domain_rows)
            _safe = _re.sub(r"[^\w.-]+", "_", (row.name or row.slug or "proxy").strip()).strip("_") or "proxy"
            entry = {
                "id": row.id,
                "name": row.name or "",
                "slug": row.slug or "",
                "inbound_tag": f"{row.id}_{_safe}",
                "enable": bool(row.enable),
                "mode": row.mode.value if row.mode else "",
                "l7_proto": row.l7_proto.value if row.l7_proto else None,
                "custom_path": row.custom_path or "",
                "server_core": row.server_core.value if row.server_core else "",
                "server_tag": row.server_tag or "",
                "domain_modes": list(row.domain_modes or []),
                "server_config": row.effective_server_config_text(),
                "domains": [_domain_dict_for_proxy(d, hconfigs) for d in related],
                **ports_dict_for_proxy_row(row),
            }
            cache.proxies.append(entry)

        for ip_row in ServerIp.query.filter(ServerIp.child_id == child_id, ServerIp.enabled == True).order_by(ServerIp.id).all():
            payload = ip_row.to_dict()
            if int(ip_row.version or 4) == 6:
                cache.ips_v6.append(payload)
            else:
                cache.ips_v4.append(payload)

        return cache


def _domain_dict_for_proxy(domain_db: Domain, hconfigs: dict) -> dict[str, Any]:
    extracted = hutils.proxy.sni_host_server_extractor(domain_db, hconfigs)
    base = domain_db.to_dict(dump_ports=True, dump_child_id=True)
    base.update(
        {
            "domain_id": domain_db.id,
            "sni": extracted.get("sni"),
            "host": extracted.get("host"),
            "server": extracted.get("server") or domain_db.domain,
        }
    )
    if domain_db.download_domain:
        base["download"] = hutils.proxy.sni_host_server_extractor(domain_db.download_domain, hconfigs)
        base["download"]["cert"] = domain_db.download_domain.certificate.to_dict() if domain_db.download_domain.certificate else None
    base["cert"] = domain_db.certificate.to_dict() if domain_db.certificate else None
    hutils.proxy.attach_domain_ech(base, hconfigs)
    return base


def _domain_rows_for_proxy(proxy: CustomProxy, all_domains: list[Domain]) -> list[Domain]:
    proxy_id = int(proxy.id)
    eligible = [d for d in all_domains if not d.custom_proxy_id or int(d.custom_proxy_id) == proxy_id]
    return _domains_for_proxy_row(proxy, eligible)


def _domains_for_proxy_row(proxy: CustomProxy, all_domains: list[Domain]) -> list[Domain]:
    mode = mode_value(proxy.mode)
    if mode == CustomProxyMode.domains_sni_gateway.value:
        return [d for d in all_domains if domain_matches_modes(d, ["special"])]
    if mode == CustomProxyMode.ip.value:
        buckets = [m for m in (proxy.domain_modes or []) if m in ("direct", "relay")]
        if not buckets:
            buckets = ["direct", "relay"]
        return [d for d in all_domains if domain_matches_modes(d, buckets)]
    buckets = list(proxy.domain_modes or default_domain_modes_for_mode(proxy.mode))
    return [d for d in all_domains if domain_matches_modes(d, buckets)]


def client_domain_vars_for_proxy(child_id: int, proxy_id: int) -> list:
    """DomainVar list for client presets; skips domains bound to other proxies."""
    from hiddifypanel.models.custom_proxy import CustomProxy
    from hiddifypanel.proxy_v3.context_vars import DomainIPVar

    proxy = CustomProxy.query.filter(
        CustomProxy.id == int(proxy_id),
        CustomProxy.child_id == child_id,
    ).first()
    if not proxy:
        return []

    hconfigs = get_hconfigs(child_id)
    domain_rows = Domain.query.filter(
        Domain.child_id == child_id,
        Domain.sub_link_only == False,  # noqa: E712
    ).all()
    result = []
    for domain_db in _domain_rows_for_proxy(proxy, domain_rows):
        base = _domain_dict_for_proxy(domain_db, hconfigs)
        result.append(DomainIPVar.from_domain(domain_db, hconfigs))
    return result
