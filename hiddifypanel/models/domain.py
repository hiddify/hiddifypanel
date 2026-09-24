from __future__ import annotations

import ipaddress
import json
import re
from collections.abc import Sequence
from datetime import datetime
from enum import auto
from typing import TYPE_CHECKING

import json5
from flask import request
from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship
from strenum import StrEnum

from hiddifypanel.database import db
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum

from .child import Child

if TYPE_CHECKING:
    from hiddifypanel.models.custom_proxy import CustomProxy
    from hiddifypanel.models.external_model.network import DomainModel
    from hiddifypanel.models.tls_store import TlsStore


class FakeMode(StrEnum):
    valid = auto()
    fake = auto()
    reality = auto()
    dns = auto()


class DomainType(StrEnum):
    direct = auto()
    sub_link_only = auto()
    cdn = auto()
    relay = auto()
    worker = auto()

    def is_cdn(self) -> bool:
        return self == DomainType.cdn

    def is_direct(self) -> bool:
        return self == DomainType.direct

    def name_is_real(self) -> bool:
        return self in {
            DomainType.direct,
            DomainType.cdn,
            DomainType.worker,
            DomainType.relay,
            DomainType.sub_link_only,
        }


ShowDomain = db.Table("show_domain", db.Column("domain_id", db.Integer, db.ForeignKey("domain.id"), primary_key=True), db.Column("related_id", db.Integer, db.ForeignKey("domain.id"), primary_key=True))

DomainCustomProxy = db.Table(
    "domain_custom_proxy",
    db.Column("domain_id", db.Integer, db.ForeignKey("domain.id", ondelete="CASCADE"), primary_key=True),
    db.Column("custom_proxy_id", db.Integer, db.ForeignKey("custom_proxy.id", ondelete="CASCADE"), primary_key=True),
)


class Domain(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), default=0)
    domain: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    alias: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    mode: Mapped[DomainType] = mapped_column(Enum(DomainType), default=DomainType.direct)
    fake_mode: Mapped[FakeMode] = mapped_column(Enum(FakeMode), default=FakeMode.valid)
    cdn_ip: Mapped[str] = mapped_column(Text(2000), nullable=False, default="")
    server_domain_id: Mapped[int | None] = mapped_column(ForeignKey("domain.id"), default=None)
    server_domain: Mapped[Domain | None] = relationship("Domain", remote_side=[id], foreign_keys=[server_domain_id])

    # port_index=db.Column(db.Integer, nullable=True, default=0)
    grpc: Mapped[bool | None] = mapped_column(default=False)
    ech: Mapped[bool] = mapped_column(default=False)
    servernames: Mapped[str | None] = mapped_column(String(1000), default="")
    # show_all=db.Column(db.Boolean, nullable=True)
    show_domains: Mapped[list[Domain]] = relationship(
        "Domain",
        secondary=ShowDomain,
        primaryjoin=id == ShowDomain.c.domain_id,
        secondaryjoin=id == ShowDomain.c.related_id,
        backref=backref("showed_by_domains", lazy="dynamic"),
    )
    download_domain_id: Mapped[int | None] = mapped_column(ForeignKey("domain.id", ondelete="SET NULL"), default=None)
    download_domain: Mapped[Domain | None] = relationship("Domain", remote_side=[id], foreign_keys=[download_domain_id])
    resolve_ip: Mapped[bool | None] = mapped_column(default=False)

    custom_proxies: Mapped[list[CustomProxy]] = relationship("CustomProxy", secondary=DomainCustomProxy, lazy="selectin")
    certificate: Mapped[TlsStore | None] = relationship(
        "TlsStore",
        back_populates="domain",
        uselist=False,
        cascade="all, delete-orphan",
    )
    extra_params: Mapped[str | None] = mapped_column(String(2000), default="{}")

    def is_reality(self) -> bool:
        return self.fake_mode == FakeMode.reality

    def is_fake_tls(self) -> bool:
        return self.fake_mode == FakeMode.fake

    def is_sub_link_only(self) -> bool:
        return self.mode == DomainType.sub_link_only

    def usable_server_domain(self) -> Domain | None:
        """Upstream hostname used as client ``server``: valid direct/relay only."""
        sd = self.server_domain
        if sd is None or sd.is_sub_link_only():
            return None
        if sd.mode not in (DomainType.direct, DomainType.relay):
            return None
        if sd.fake_mode != FakeMode.valid:
            return None
        return sd

    @property
    def custom_proxy_ids(self) -> list[int]:
        return [proxy.id for proxy in self.custom_proxies]

    @property
    def custom_proxy_slugs(self) -> list[str]:

        return [proxy.slug for proxy in self.custom_proxies]

    def set_custom_proxies_by_slugs(self, slugs: Sequence[str] | None) -> None:
        from hiddifypanel.models.custom_proxy import CustomProxy
        from hiddifypanel.proxy_v3.domain_proxy_options import REALITY_TERMINATION_SLUG

        wanted = [slug for slug in (slugs or []) if slug and slug != REALITY_TERMINATION_SLUG]
        if not wanted:
            self.custom_proxies = []
            return
        proxies = CustomProxy.query.filter(
            CustomProxy.child_id == self.child_id,
            CustomProxy.slug.in_(wanted),
        ).all()
        by_slug = {proxy.slug: proxy for proxy in proxies if proxy.slug}
        self.custom_proxies = [by_slug[slug] for slug in wanted if slug in by_slug]

    def is_accessible(self) -> bool:
        if self.mode in (DomainType.direct, DomainType.relay):
            return self.fake_mode == FakeMode.valid
        return self.fake_mode == FakeMode.valid

    def extra_params_json(self):

        try:
            return json5.loads(self.extra_params)
        except:
            return {}

    def __repr__(self):
        return f"{self.domain}"

    def get_cdn_ips_parsed(self):
        ips = re.split("[ \t\r\n;,]+", self.cdn_ip.strip())
        res = set()
        for ip in ips:
            try:
                res.add(ipaddress.ip_address(ip))
            except:
                pass
        return res

    def to_model(self, dump_ports=False, for_parent=False) -> DomainModel:
        """Port fields need hconfig lookups, so they are only filled with ``dump_ports``."""
        from hiddifypanel.models.external_model.network import DomainModel

        try:
            extra = json.loads(self.extra_params or "{}")
        except:
            extra = {}
        return DomainModel(
            domain=self.domain.lower(),
            mode=self.mode,
            fake_mode=self.fake_mode,
            alias=self.alias,
            child_unique_id=self.child.unique_id if self.child else "",
            cdn_ip=self.cdn_ip,
            servernames=self.servernames,
            grpc=self.grpc,
            ech=bool(self.ech),
            download_domain=self.download_domain.domain if self.download_domain else "",
            server_domain=self.server_domain.domain if self.server_domain else "",
            show_domains=[dd.domain for dd in self.show_domains] if not for_parent else None,
            resolve_ip=self.resolve_ip,
            extra_params=extra if isinstance(extra, (dict, list)) else {},
            custom_proxy_slugs=self.custom_proxy_slugs if not for_parent else None,
            child_id=self.child_id,
            internal_port_hysteria2=self.internal_port_hysteria2 if dump_ports else None,
            internal_port_tuic=self.internal_port_tuic if dump_ports else None,
            internal_port_naive=self.internal_port_naive if dump_ports else None,
            internal_port_special=self.internal_port_special if dump_ports else None,
            need_valid_ssl=self.need_valid_ssl if dump_ports else None,
        )

    def to_dict(self, dump_ports=False, dump_child_id=False, for_parent=False):
        from hiddifypanel.models.external_model.network import DOMAIN_PORT_FIELDS

        exclude = set() if dump_ports else set(DOMAIN_PORT_FIELDS)
        if not dump_child_id:
            exclude.add("child_id")
        return self.to_model(dump_ports=dump_ports, for_parent=for_parent).to_dict(exclude=exclude)

    def get_server(self):
        if sd := self.usable_server_domain():
            return sd.domain
        if cdn_ip := self.auto_cdn_ip():
            selected = cdn_ip[0] if isinstance(cdn_ip, (tuple, list)) else cdn_ip
            return selected
        if self.fake_mode != FakeMode.valid:
            return None
        return self.domain

    @staticmethod
    def from_schema(schema):
        return schema.dump(Domain())

    def to_schema(self, for_parent=False):
        domain_dict = self.to_dict(for_parent=for_parent)
        from hiddifypanel.panel.commercial.restapi.v2.parent.schema import DomainSchema

        return DomainSchema.model_validate(domain_dict)

    def auto_cdn_ip(self):
        from hiddifypanel import hutils

        if (self.cdn_ip or "").strip():
            return hutils.network.auto_ip_selector.get_clean_ip(self.cdn_ip)
        return None

    @property
    def need_valid_ssl(self):
        if self.fake_mode != FakeMode.valid:
            return False
        return self.mode in [
            DomainType.direct,
            DomainType.cdn,
            DomainType.worker,
            DomainType.relay,
            DomainType.sub_link_only,
        ]

    @property
    def tls_status(self) -> str:
        cert = self.certificate
        if not cert or not str(cert.certificate or "").strip():
            return "missing"
        if cert.valid_cert:
            return "self_signed" if cert.self_signed else "valid"
        if cert.expires_at and cert.expires_at < datetime.utcnow():
            return "expired"
        return "invalid"

    @property
    def port_index(self):
        return self.id

    @property
    def name(self):
        return self.domain

    @property
    def internal_port_hysteria2(self):
        if self.fake_mode == FakeMode.reality:
            return 0
        if self.mode not in [DomainType.direct, DomainType.relay]:
            return 0
        return int(hconfig(ConfigEnum.hysteria_port, self.child_id)) + self.port_index

    @property
    def internal_port_tuic(self):
        if self.fake_mode == FakeMode.reality:
            return 0
        if self.mode not in [DomainType.direct, DomainType.relay]:
            return 0
        return int(hconfig(ConfigEnum.tuic_port, self.child_id)) + self.port_index

    @property
    def internal_port_naive(self):
        if self.mode not in [DomainType.direct, DomainType.relay]:
            return 0
        return int(hconfig(ConfigEnum.naive_port, self.child_id)) + self.port_index

    @property
    def internal_port_special(self):
        if self.fake_mode != FakeMode.reality:
            return 0
        return int(hconfig(ConfigEnum.special_port, self.child_id)) + self.port_index

    @classmethod
    def by_mode(cls, mode: DomainType) -> list[Domain]:
        domains = Domain.query.filter(Domain.mode == mode).all()
        if domains:
            return [d.domain for d in domains]
        return []

    @classmethod
    def modes_and_domains(cls) -> dict[DomainType, list[Domain]]:
        return {mode: cls.by_mode(mode) for mode in DomainType}

    @classmethod
    def by_domain(cls, domain: str) -> Domain | None:
        return Domain.query.filter(Domain.domain == domain).first()

    @classmethod
    def child_has_sub_link_only(cls, child_id: int) -> bool:
        return cls.query.filter(cls.child_id == child_id, cls.mode == DomainType.sub_link_only).first() is not None

    @classmethod
    def get_panel_link(cls, child_id: int | None = None) -> str | None:
        if child_id is None:
            child_id = Child.current().id
        domains = Domain.query.filter(
            Domain.mode.in_(
                [
                    DomainType.direct,
                    DomainType.cdn,
                    DomainType.worker,
                    DomainType.relay,
                    DomainType.sub_link_only,
                ]
            ),
            Domain.fake_mode == FakeMode.valid,
            Domain.child_id == child_id,
        ).all()
        if not domains:
            return None
        return domains[0].domain

    @classmethod
    def get_domains(cls, always_add_ip=False, always_add_all_domains=False) -> list[Domain]:
        from hiddifypanel import hutils

        domains = []
        domains = (
            db.session.query(Domain)
            .filter(
                Domain.mode == DomainType.sub_link_only,
                Domain.child_id == Child.current().id,
            )
            .all()
        )
        if not len(domains) or always_add_all_domains:
            domains = (
                db.session.query(Domain)
                .filter(
                    Domain.fake_mode == FakeMode.valid,
                    Domain.child_id == Child.current().id,
                )
                .all()
            )

        if len(domains) == 0 and request:
            domains = [Domain(domain=request.host)]
        if len(domains) == 0 or always_add_ip:
            domains += [Domain(domain=hutils.network.get_ip_str(4))]
        return domains

    @classmethod
    def add_or_update(cls, commit=True, child_id=0, *, apply_links: bool = True, **domain) -> Domain:
        from hiddifypanel.models.external_model.network import DomainModel

        return cls.upsert(DomainModel.coerce(domain), child_id=child_id, commit=commit, apply_links=apply_links)

    @classmethod
    def upsert(cls, data: DomainModel, *, child_id: int = 0, commit: bool = True, apply_links: bool = True) -> Domain:
        dbdomain = Domain.query.filter(Domain.domain == data.domain, Domain.child_id == child_id).first()
        if not dbdomain:
            dbdomain = Domain(domain=data.domain)
            db.session.add(dbdomain)
        dbdomain.child_id = child_id

        dbdomain.mode = data.mode
        if data.fake_mode is not None:
            dbdomain.fake_mode = data.fake_mode
        dbdomain.cdn_ip = data.cdn_ip
        dbdomain.alias = data.alias
        dbdomain.grpc = data.grpc
        dbdomain.ech = data.ech
        dbdomain.servernames = data.servernames
        dbdomain.resolve_ip = data.resolve_ip
        dbdomain.extra_params = data.extra_params_text()

        if apply_links:
            cls._apply_domain_links(dbdomain, data, preferred_child_id=child_id)

        if commit:
            db.session.commit()
        return dbdomain

    @classmethod
    def _normalize_legacy_mode(cls, mode, fake_mode):
        """Map ≤12.x domain modes (reality/fake/special_*/…) to DomainType + FakeMode."""
        from hiddifypanel.models.external_model.network import normalize_legacy_domain_mode

        return normalize_legacy_domain_mode(mode, fake_mode)

    @classmethod
    def _lookup_domain_ref(cls, name: str | None, preferred_child_id: int = 0) -> Domain | None:
        if not name:
            return None
        name = str(name).strip().lower()
        if not name:
            return None
        row = cls.query.filter(cls.domain == name, cls.child_id == preferred_child_id).first()
        if row:
            return row
        return cls.query.filter(cls.domain == name).first()

    @classmethod
    def _apply_domain_links(cls, dbdomain: Domain, data: DomainModel, preferred_child_id: int = 0) -> None:
        if data.show_domains:
            resolved: list[Domain] = []
            for name in data.show_domains:
                ref = cls._lookup_domain_ref(name, preferred_child_id)
                # show_domain is a set (PK domain_id+related_id): skip repeated names.
                if ref and ref not in resolved:
                    resolved.append(ref)
            dbdomain.show_domains = resolved
        elif data.has("show_domains"):
            dbdomain.show_domains = []

        if data.has("download_domain"):
            dl = cls._lookup_domain_ref(data.download_domain, preferred_child_id)
            dbdomain.download_domain_id = dl.id if dl else None

        if data.has("server_domain"):
            sd = cls._lookup_domain_ref(data.server_domain, preferred_child_id)
            dbdomain.server_domain_id = sd.id if sd else None

        if data.has("custom_proxy_slugs"):
            dbdomain.set_custom_proxies_by_slugs(data.custom_proxy_slugs or [])

    @classmethod
    def bulk_register(cls, domains, commit=True, remove=False, force_child_unique_id: str | None = None):
        from hiddifypanel.models.external_model.network import DomainModel
        from hiddifypanel.panel import hiddify

        rows = DomainModel.coerce_many(domains)
        child_ids = {}
        for data in rows:
            child_id = hiddify.child_id_from_row({"child_unique_id": data.child_unique_id}, force_child_unique_id)
            child_ids[child_id] = 1
            # First pass: create rows without cross-domain links (later rows may not exist yet).
            cls.upsert(data.without_links(), child_id=child_id, commit=False, apply_links=False)
        if remove and len(child_ids):
            dd = {p.domain: 1 for p in rows}
            for d in Domain.query.filter(Domain.child_id.in_(child_ids)):
                if d.domain not in dd:
                    db.session.delete(d)

        db.session.flush()
        # Always resolve cross-domain links once all rows exist (even if commit=False).
        # set_db_from_json re-runs this after custom proxies so custom_proxy_slugs stick.
        cls.bulk_apply_links(rows, force_child_unique_id=force_child_unique_id, commit=False)
        if commit:
            db.session.commit()

    @classmethod
    def bulk_apply_links(cls, domains, force_child_unique_id: str | None = None, commit: bool = True):
        from hiddifypanel.models.external_model.network import DomainModel
        from hiddifypanel.panel import hiddify

        for data in DomainModel.coerce_many(domains):
            child_id = hiddify.child_id_from_row({"child_unique_id": data.child_unique_id}, force_child_unique_id)
            dbdomain = cls.query.filter(cls.domain == data.domain, cls.child_id == child_id).first()
            if not dbdomain:
                continue
            cls._apply_domain_links(dbdomain, data, preferred_child_id=child_id)
        if commit:
            db.session.commit()
