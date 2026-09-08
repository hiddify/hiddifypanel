from datetime import datetime
from enum import auto
import ipaddress
import json
import re
from typing import Dict, List
from flask import request

from sqlalchemy.orm import backref
from strenum import StrEnum


from hiddifypanel.database import db
from hiddifypanel.models.config import hconfig
from .child import Child
from hiddifypanel.models.config_enum import ConfigEnum


class FakeMode(StrEnum):
    valid = auto()
    fake = auto()
    reality = auto()
    dns = auto()


class DomainType(StrEnum):
    direct = auto()
    sub_link_only = auto()
    cdn = auto()
    auto_cdn_ip = auto()
    relay = auto()
    worker = auto()

    old_xtls_direct = auto()  # deprecated
    dnstt = auto()
    special = auto()

    def is_cdn(self) -> bool:
        return self in [DomainType.cdn, DomainType.auto_cdn_ip]

    def is_direct(self) -> bool:
        return self in [DomainType.direct, DomainType.old_xtls_direct]

    def is_dnstt(self) -> bool:
        return self == DomainType.dnstt

    def name_is_real(self) -> bool:
        return self in {
            DomainType.direct,
            DomainType.cdn,
            DomainType.auto_cdn_ip,
            DomainType.worker,
            DomainType.relay,
            DomainType.sub_link_only,
            DomainType.old_xtls_direct,
            DomainType.dnstt,
        }


ShowDomain = db.Table("show_domain", db.Column("domain_id", db.Integer, db.ForeignKey("domain.id"), primary_key=True), db.Column("related_id", db.Integer, db.ForeignKey("domain.id"), primary_key=True))


class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child.id"), default=0)
    domain = db.Column(db.String(200), nullable=True, unique=False)
    alias = db.Column(db.String(200))
    sub_link_only = db.Column(db.Boolean, nullable=False, default=False)
    mode = db.Column(db.Enum(DomainType), nullable=False, default=DomainType.direct)
    fake_mode = db.Column(db.Enum(FakeMode), nullable=False, default=FakeMode.valid)
    cdn_ip = db.Column(db.Text(2000), nullable=True, default="")
    server_domain_id = db.Column(db.Integer, db.ForeignKey("domain.id"), nullable=True, default=None)
    server_domain = db.relationship("Domain", remote_side=[id], foreign_keys=[server_domain_id])

    # port_index=db.Column(db.Integer, nullable=True, default=0)
    grpc = db.Column(db.Boolean, nullable=True, default=False)
    ech = db.Column(db.Boolean, nullable=False, default=False)
    servernames = db.Column(db.String(1000), nullable=True, default="")
    # show_all=db.Column(db.Boolean, nullable=True)
    show_domains = db.relationship("Domain", secondary=ShowDomain, primaryjoin=id == ShowDomain.c.domain_id, secondaryjoin=id == ShowDomain.c.related_id, backref=backref("showed_by_domains", lazy="dynamic"))
    download_domain_id = db.Column(db.Integer, db.ForeignKey("domain.id", ondelete="SET NULL"), default=None, nullable=True)
    download_domain = db.relationship("Domain", remote_side=[id], foreign_keys=[download_domain_id])
    extra_params = db.Column(db.String(2000), nullable=True, default="{}")
    resolve_ip = db.Column(db.Boolean, nullable=True, default=False)

    custom_proxy_id = db.Column(db.Integer, db.ForeignKey("custom_proxy.id", ondelete="SET NULL"), default=None, nullable=True)
    custom_proxy = db.relationship("CustomProxy")
    certificate = db.relationship(
        "TlsStore",
        back_populates="domain",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def is_reality(self) -> bool:
        return self.fake_mode == FakeMode.reality

    def is_fake_tls(self) -> bool:
        return self.fake_mode == FakeMode.fake

    def is_accessible(self) -> bool:
        if self.mode in (DomainType.direct, DomainType.relay):
            return self.fake_mode == FakeMode.valid
        return self.fake_mode == FakeMode.valid

    def extra_params_json(self):
        import json

        try:
            return json.loads(self.extra_params)
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

    def to_dict(self, dump_ports=False, dump_child_id=False):
        try:
            extra = json.loads(self.extra_params or "{}")
        except:
            extra = {}
        data = {
            "domain": self.domain.lower(),
            "mode": self.mode,
            "fake_mode": self.fake_mode,
            "alias": self.alias,
            "sub_link_only": self.sub_link_only,
            "child_unique_id": self.child.unique_id if self.child else "",  # type: ignore
            "cdn_ip": self.cdn_ip,
            "servernames": self.servernames,
            "grpc": self.grpc,
            "ech": bool(self.ech),
            "download_domain": self.download_domain.domain if self.download_domain else "",
            "show_domains": [dd.domain for dd in self.show_domains],  # type: ignore
            "resolve_ip": self.resolve_ip,
            "extra_params": extra,
            "custom_proxy_id": self.custom_proxy_id,
        }
        if dump_child_id:
            data["child_id"] = self.child_id
        if dump_ports:
            data["internal_port_hysteria2"] = self.internal_port_hysteria2
            data["internal_port_tuic"] = self.internal_port_tuic
            data["internal_port_naive"] = self.internal_port_naive
            data["internal_port_special"] = self.internal_port_special
            data["internal_port_dnstt"] = self.internal_port_dnstt
            data["need_valid_ssl"] = self.need_valid_ssl

        return data

    def get_server(self):
        if self.server_domain_id:
            return self.server_domain.domain
        if cdn_ip := self.auto_cdn_ip():
            return cdn_ip[0]
        if self.fake_mode != FakeMode.valid:
            from hiddifypanel import hutils

            return str(hutils.proxy.shared.random_or_none(hutils.network.get_ips()))

        return self.domain

    @staticmethod
    def from_schema(schema):
        return schema.dump(Domain())

    def to_schema(self):
        domain_dict = self.to_dict()
        from hiddifypanel.panel.commercial.restapi.v2.parent.schema import DomainSchema

        return DomainSchema().load(domain_dict)

    def auto_cdn_ip(self):
        from hiddifypanel import hutils

        if self.cdn_ip.strip():
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
            DomainType.auto_cdn_ip,
            DomainType.old_xtls_direct,
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
    def internal_port_dnstt(self):
        if self.mode not in [DomainType.dnstt]:
            return 0
        return int(5400) + self.port_index

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
    def by_mode(cls, mode: DomainType) -> List["Domain"]:
        domains = Domain.query.filter(Domain.mode == mode).all()
        if domains:
            return [d.domain for d in domains]
        return []

    @classmethod
    def modes_and_domains(cls) -> Dict[DomainType, List["Domain"]]:
        return {mode: cls.by_mode(mode) for mode in DomainType}

    @classmethod
    def by_domain(cls, domain: str) -> "Domain | None":
        return Domain.query.filter(Domain.domain == domain).first()

    @classmethod
    def get_panel_link(cls, child_id: int | None = None) -> str | None:
        if child_id is None:
            child_id = Child.current().id  # type: ignore
        domains = Domain.query.filter(
            Domain.mode.in_(
                [
                    DomainType.direct,
                    DomainType.cdn,
                    DomainType.worker,
                    DomainType.relay,
                    DomainType.auto_cdn_ip,
                    DomainType.old_xtls_direct,
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
    def get_domains(cls, always_add_ip=False, always_add_all_domains=False) -> List["Domain"]:
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
                )
                .all()
            )

        if len(domains) == 0 and request:
            domains = [Domain(domain=request.host)]  # type: ignore
        if len(domains) == 0 or always_add_ip:
            domains += [Domain(domain=hutils.network.get_ip_str(4))]  # type: ignore
        return domains

    @classmethod
    def add_or_update(cls, commit=True, child_id=0, **domain):
        dbdomain = Domain.query.filter(Domain.domain == domain["domain"]).first()
        if not dbdomain:
            dbdomain = Domain(domain=domain["domain"])  # type: ignore
            db.session.add(dbdomain)
        dbdomain.child_id = child_id

        dbdomain.mode = domain["mode"]
        if str(domain.get("sub_link_only", False)).lower() == "true":
            dbdomain.mode = DomainType.sub_link_only
        if domain.get("fake_mode") is not None:
            dbdomain.fake_mode = domain["fake_mode"]
        if domain.get("custom_proxy_id") is not None:
            dbdomain.custom_proxy_id = domain.get("custom_proxy_id") or None
        dbdomain.cdn_ip = domain.get("cdn_ip", "")
        dbdomain.alias = domain.get("alias", "")
        dbdomain.grpc = domain.get("grpc", False)
        dbdomain.ech = bool(domain.get("ech", False))
        dbdomain.servernames = domain.get("servernames", "")
        dbdomain.resolve_ip = domain.get("resolve_ip", False)
        dbdomain.extra_params = domain.get("extra_params", "")
        show_domains = domain.get("show_domains", [])
        dbdomain.show_domains = Domain.query.filter(Domain.domain.in_(show_domains)).all()
        dl_domain = domain.get("download_domain")
        if dl_domain:
            dbdldomain = Domain.query.filter(Domain.domain == dl_domain).first()
            if not dbdldomain:
                dbdldomain = Domain(domain=dl_domain)  # type: ignore
                db.session.add(dbdldomain)
                db.session.commit()
                dbdldomain = Domain.query.filter(Domain.domain == dl_domain).first()
            assert dbdldomain
            dbdomain.download_domain_id = dbdldomain.id
        if commit:
            db.session.commit()

    @classmethod
    def bulk_register(cls, domains, commit=True, remove=False, force_child_unique_id: str | None = None):
        from hiddifypanel.panel import hiddify

        child_ids = {}
        for domain in domains:
            child_id = hiddify.get_child(unique_id=force_child_unique_id)
            child_ids[child_id] = 1
            cls.add_or_update(commit=False, child_id=child_id, **domain)
        if remove and len(child_ids):
            dd = {d["domain"]: 1 for d in domains}
            for d in Domain.query.filter(Domain.child_id.in_(child_ids)):
                if d.domain not in dd:
                    db.session.delete(d)

        if commit:
            db.session.commit()
