from __future__ import annotations

from collections.abc import Iterable
from enum import auto
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from strenum import StrEnum

from hiddifypanel.database import db

if TYPE_CHECKING:
    from hiddifypanel.models.external_model.node import ProxyModel


class ProxyTransport(StrEnum):
    h2 = auto()
    grpc = auto()
    # XTLS = auto()
    faketls = auto()
    shadowtls = auto()
    restls1_2 = auto()
    restls1_3 = auto()
    # h1=auto()
    WS = auto()
    tcp = auto()
    http = auto()
    ssh = auto()
    httpupgrade = auto()
    xhttp = auto()
    custom = auto()
    shadowsocks = auto()
    udp = auto()


class ProxyCDN(StrEnum):
    CDN = auto()
    direct = auto()
    Fake = auto()
    relay = auto()


class ProxyProto(StrEnum):
    vless = auto()
    trojan = auto()
    vmess = auto()
    shadowsocks = auto()
    socks = auto()
    v2ray = auto()
    ssr = auto()
    ssh = auto()
    tuic = auto()
    hysteria = auto()
    hysteria2 = auto()
    wireguard = auto()
    naive = auto()
    mieru = auto()
    anytls = auto()
    dnstt = auto()
    slipstream = auto()
    masterdns = auto()
    snell = auto()


class ProxyL3(StrEnum):
    tls = auto()
    tls_h2 = auto()
    tls_h2_h1 = auto()
    h3_quic = auto()
    reality = auto()
    http = auto()
    kcp = auto()
    ssh = auto()
    udp = auto()
    custom = auto()


class Proxy(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int | None] = mapped_column(ForeignKey("child.id"), default=0)
    name: Mapped[str] = mapped_column(String(200))
    enable: Mapped[bool] = mapped_column()
    proto: Mapped[ProxyProto] = mapped_column(Enum(ProxyProto))
    l3: Mapped[ProxyL3] = mapped_column(Enum(ProxyL3))
    transport: Mapped[ProxyTransport] = mapped_column(Enum(ProxyTransport))
    cdn: Mapped[ProxyCDN] = mapped_column(Enum(ProxyCDN))
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)

    @property
    def enabled(self):
        return self.enable * 1

    def to_model(self) -> ProxyModel:
        from hiddifypanel.models.external_model.node import ProxyModel

        return ProxyModel(
            name=self.name,
            enable=self.enable,
            proto=self.proto,
            l3=self.l3,
            transport=self.transport,
            cdn=self.cdn,
            child_unique_id=self.child.unique_id if self.child else "",
            params=self.params,
        )

    def to_dict(self):
        return self.to_model().to_dict()

    def __str__(self):
        return str(self.to_dict())

    @staticmethod
    def add_or_update(commit=True, child_id=0, **proxy) -> Proxy:
        from hiddifypanel.models.external_model.node import ProxyModel

        return Proxy.upsert(ProxyModel.coerce(proxy), child_id=child_id, commit=commit)

    @staticmethod
    def upsert(data: ProxyModel, *, child_id: int = 0, commit: bool = True) -> Proxy:
        """``data.proto``/``transport`` already map legacy ``ss``/``splithttp`` aliases."""
        dbproxy = Proxy.query.filter(Proxy.name == data.name).first()
        if not dbproxy:
            dbproxy = Proxy()
            db.session.add(dbproxy)
        dbproxy.enable = data.enable
        dbproxy.name = data.name
        dbproxy.proto = data.proto
        dbproxy.transport = data.transport
        dbproxy.cdn = data.cdn
        dbproxy.l3 = data.l3
        if data.has("params"):
            dbproxy.params = data.params
        dbproxy.child_id = child_id
        if commit:
            db.session.commit()
        return dbproxy

    @staticmethod
    def from_schema(schema):
        return schema.dump(Proxy())

    def to_schema(self):
        proxy_dict = self.to_dict()
        from hiddifypanel.panel.commercial.restapi.v2.parent.schema import ProxySchema

        return ProxySchema.model_validate(proxy_dict)

    @staticmethod
    def bulk_register(proxies: Iterable[Any], commit=True, force_child_unique_id: str | None = None):
        from hiddifypanel.models.external_model.node import ProxyModel
        from hiddifypanel.panel import hiddify

        for row in ProxyModel.coerce_many(proxies):
            child_id = hiddify.child_id_from_row({"child_unique_id": row.child_unique_id}, force_child_unique_id)
            Proxy.upsert(row, child_id=child_id, commit=False)
        if commit:
            db.session.commit()
