from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from hiddifypanel import hutils
from hiddifypanel.hutils.network.auto_ip_selector import split_pattern
from hiddifypanel.hutils.proxy import random_or_none
from hiddifypanel.models import Domain, DomainType, FakeMode

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
    fake_mode: FakeMode = FakeMode.valid
    alias: str = ""
    need_valid_ssl: bool = True
    child_id: int = 0
    echinfo: str = ""
    resolve_ip: bool = False

    cert: CertVar = Field(default_factory=CertVar.empty)
    download: DomainIPVar | None = None

    extra: dict[str, Any] = Field(default_factory=dict)

    # _domain: Domain | None = PrivateAttr(default=None)
    # _extracted: dict[str, Any] = PrivateAttr(default_factory=dict)

    custom_proxy_id: int | None = None

    @property
    def special(self) -> bool:
        return self.fake_mode == FakeMode.reality

    def is_reality(self) -> bool:
        return self.fake_mode == FakeMode.reality

    def is_fake_tls(self) -> bool:
        return self.fake_mode == FakeMode.fake

    @property
    def allow_insecure(self) -> bool:
        return (self.cert is not None) and not self.cert.valid_cert

    @classmethod
    def from_name(cls, name: str, *, child_id: int = 0) -> DomainIPVar:
        hostname = str(name or "example.com").strip().lower()
        return cls(
            name=hostname,
            host=hostname,
            sni=hostname,
            mode=DomainType.direct,
            fake_mode=FakeMode.valid,
            child_id=child_id,
        )

    @classmethod
    def from_domain(cls, domain_db: Domain) -> DomainIPVar:

        extracted_data = sni_host_ip_extractor(domain_db)
        hostname = str(domain_db.domain or "").lower()

        cert = CertVar.for_domain(domain_db)

        extra = domain_db.extra_params_json()
        extra.update(extracted_data.get("extra_params") or {})

        var = cls(
            id=domain_db.id,
            name=hostname,
            host=extracted_data.get("host") or hostname,
            sni=extracted_data.get("sni") or hostname,
            mode=domain_db.mode,
            fake_mode=domain_db.fake_mode,
            alias=domain_db.alias or domain_db.name,
            need_valid_ssl=bool(domain_db.need_valid_ssl),
            child_id=int(domain_db.child_id or 0),
            echinfo=_resolve_domain_ech(domain_db),
            cert=cert,
            extra=extra,
            resolve_ip=bool(domain_db.resolve_ip),
            custom_proxy_id=domain_db.custom_proxy_id,
        )
        # if var.mode.is_special():
        #     var.mode = DomainType.special
        if domain_db.download_domain:
            var.download = cls.from_domain(domain_db.download_domain)
        else:
            # Same-domain download without a self-reference (breaks pydantic model_dump).
            var.download = var.model_copy(update={"download": None})

        # if var.download and var.alias != var.download.alias:
        #     var.alias = var.alias + " 📥" + var.download.alias
        # var._domain = domain_db
        # var._extracted = extracted_data
        return var

    def server(self, force_ip: bool = False) -> str:
        if force_ip or self.resolve_ip or not self.mode.name_is_real():
            return random_or_none(self.ips.ips) or self.name
        return self.host or self.name


def get_ips(domain_db: Domain) -> IPVar:
    ips = IPVar.empty()
    if auto_ips := domain_db.auto_cdn_ip():
        ips.merge(auto_ips)
    elif domain_db.mode.is_direct():
        ips.merge(hutils.network.get_ips())

    if domain_db.mode.name_is_real():
        ips.merge(hutils.network.get_domain_ips_cached(domain_db.domain))

    return ips


def sni_host_ip_extractor(domain_db: Domain):

    sni = host = domain_db.domain.replace("*", hutils.random.get_random_string(5, 15))
    if all_snis := split_pattern.split((domain_db.servernames or "").strip()):
        if domain_db.fake_mode == FakeMode.reality:
            sni = all_snis[0]
        else:
            sni = random_or_none(all_snis) or sni

    base = {
        "sni": sni,
        "host": host,
    }

    return base


def _resolve_domain_ech(domain_db: Domain) -> str:
    if not domain_db.ech or not domain_db.mode.is_cdn():
        return ""

    hostname = str(domain_db.domain or "").replace("*", hutils.random.get_random_string(5, 15))
    if not hostname:
        return ""
    return hutils.network.get_ech_info(hostname) or ""
