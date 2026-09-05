from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hiddifypanel import hutils
from hiddifypanel.models import Domain, get_hconfigs
from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyMode
from hiddifypanel.proxy_v3.context_vars.domain import DomainIPVar

from .custom_proxy_ports import default_domain_modes_for_mode, mode_value, ports_dict_for_proxy_row
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
            cache.domains.append(_domain_dict_for_proxy(domain_db, hconfigs))

        rows = (
            CustomProxy.query.filter(CustomProxy.child_id == child_id)
            .order_by(CustomProxy.sort_order, CustomProxy.id)
            .all()
        )
        domain_rows = [
            d
            for d in Domain.query.filter(Domain.child_id == child_id, Domain.sub_link_only == False).all()  # noqa: E712
        ]
        for row in rows:
            from hiddifypanel.proxy_v3.template_catalog.custom_proxy_builtin import effective_field

            related = _domains_for_proxy_row(row, domain_rows)
            entry = {
                "id": row.id,
                "enable": bool(row.enable),
                "mode": row.mode.value if row.mode else "",
                "l7_reverse_proto": row.l7_reverse_proto.value if row.l7_reverse_proto else None,
                "download_tls_layer": row.download_tls_layer.value if row.download_tls_layer else None,
                "download_domain_modes": list(row.download_domain_modes or []),
                "tls_layer": row.tls_layer.value if row.tls_layer else None,
                "custom_path": row.custom_path or "",
                "server_core": row.server_core.value if row.server_core else "",
                "server_tag": str(effective_field(row, "server_tag") or row.slug or ""),
                "domain_modes": list(row.domain_modes or []),
                "server_config": row.effective_server_config_text(),
                "domains": [_domain_dict_for_proxy(d, hconfigs) for d in related],
                **ports_dict_for_proxy_row(row),
            }
            cache.proxies.append(entry)

        for ip_row in ServerIp.query.filter(ServerIp.child_id == child_id).order_by(ServerIp.id).all():
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
    return base


def _domains_for_proxy_row(proxy: CustomProxy, all_domains: list[Domain]) -> list[Domain]:
    if mode_value(proxy.mode) == CustomProxyMode.domains_sni_gateway.value:
        pid = int(proxy.id or 0)
        return [d for d in all_domains if d.custom_proxy_id is not None and int(d.custom_proxy_id) == pid]
    if mode_value(proxy.mode) == CustomProxyMode.ip.value:
        buckets = [m for m in (proxy.domain_modes or []) if m in ("direct", "relay")]
        if not buckets:
            buckets = ["direct", "relay"]
        return [d for d in all_domains if domain_matches_modes(d, buckets)]
    buckets = list(proxy.domain_modes or default_domain_modes_for_mode(proxy.mode))
    return [d for d in all_domains if domain_matches_modes(d, buckets)]


def client_domain_vars_for_proxy(child_id: int, proxy_id: int) -> list[DomainIPVar]:
    """Domain list for client presets; SNI-gateway proxies only use assigned domains."""
    proxy = CustomProxy.query.filter(
        CustomProxy.id == int(proxy_id),
        CustomProxy.child_id == child_id,
    ).first()
    if not proxy:
        return []

    domain_rows = [
        d
        for d in Domain.query.filter(
            Domain.child_id == child_id,
            Domain.sub_link_only == False,  # noqa: E712
        ).all()
        if not d.custom_proxy_id or int(d.custom_proxy_id) == int(proxy_id)
    ]
    return [DomainIPVar.from_domain(domain_db) for domain_db in _domains_for_proxy_row(proxy, domain_rows)]
