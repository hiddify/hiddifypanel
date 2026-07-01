from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from hiddifypanel import hutils
from hiddifypanel.hutils.network.auto_ip_selector import split_pattern
from hiddifypanel.hutils.proxy import random_or_none
from hiddifypanel.models import ConfigEnum, Domain, DomainType

from .cert import CertVar
from .ip import IPVar


class DomainIPVar(BaseModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    id: int | None = None
    name: str = ""
    ips: IPVar = Field(default_factory=IPVar.empty)
    host: str = ""
    sni: str = ""
    port: int = 443

    mode: DomainType
    alias: str = ""
    need_valid_ssl: bool = True
    child_id: int = 0
    ech: str = ""
    resolve_ip: bool = False

    cert: CertVar = Field(default_factory=CertVar.empty)
    download: DomainIPVar | None = None

    extra: dict[str, Any] = Field(default_factory=dict)

    _domain: Domain | None = PrivateAttr(default=None)
    _extracted: dict[str, Any] = PrivateAttr(default_factory=dict)

    @property
    def allow_insecure(self) -> bool:
        return (self.cert is not None) and not self.cert.valid_cert

    @classmethod
    def from_domain(cls, domain_db: Domain, hconfigs: dict[str, Any]) -> DomainIPVar:
        from hiddifypanel import hutils

        extracted_data = hutils.proxy.sni_host_server_extractor(domain_db, hconfigs)
        hostname = str(domain_db.domain or "").lower()

        cert = CertVar.for_domain(domain_db)

        download_var: DomainIPVar | None = None
        if domain_db.download_domain:
            download_var = cls.from_domain(domain_db.download_domain, hconfigs)

        hutils.proxy.attach_domain_ech(extracted_data, hconfigs)
        extra = domain_db.extra_params_json()
        extra.update(extracted_data.get("extra_params") or {})

        var = cls(
            name=hostname,
            host=extracted_data.get("host") or hostname,
            sni=extracted_data.get("sni") or hostname,
            mode=domain_db.mode,
            alias=domain_db.alias or "",
            need_valid_ssl=bool(domain_db.need_valid_ssl),
            child_id=int(domain_db.child_id or 0),
            ech=str(extracted_data.get("ech") or ""),
            cert=cert,
            id=domain_db.id,
            download=download_var,
            extra=extra,
            resolve_ip=bool(domain_db.resolve_ip),
        )
        var._domain = domain_db
        var._extracted = extracted_data
        return var

    def server(self, force_ip: bool) -> str:
        if force_ip or self.resolve_ip or not self.mode.name_is_real():
            return random_or_none(self.ips.ips) or self.name
        return self.name


def get_ips(domain_db: Domain) -> IPVar:
    ips = IPVar.empty()
    if auto_ips := domain_db.auto_cdn_ip():
        ips.merge(auto_ips)
    elif domain_db.mode.is_direct():
        ips.merge(hutils.network.get_ips())

    if domain_db.mode.name_is_real():
        ips.merge(hutils.network.get_domain_ips_cached(domain_db.domain))

    return ips


def sni_host_ip_extractor(domain_db: Domain, hconfigs):

    sni = host = domain_db.domain.replace("*", hutils.random.get_random_string(5, 15))
    if all_snis := split_pattern.split((domain_db.servernames or "").strip()):
        if "reality" in domain_db.mode and hconfigs[ConfigEnum.core_type] == "singbox":  # TODO
            sni = all_snis[0]
        else:
            sni = random_or_none(all_snis) or sni

    base = {"sni": sni, "host": host, "ech": get_domain_ech(sni or host, hconfigs)}

    return base


def get_domain_ech(domain_name: str, hconfigs: dict) -> None:
    """Populate domain.ech from DNS HTTPS records when ECH is enabled."""
    if not hconfigs.get(ConfigEnum.tls_ech_enable):
        return
    if domain_name:
        return hutils.network.get_ech_info(domain_name)
    return None
