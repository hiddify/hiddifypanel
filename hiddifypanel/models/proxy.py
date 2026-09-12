from enum import auto
from typing import Any

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from strenum import StrEnum

from hiddifypanel.database import db


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

    def to_dict(self):
        return {
            "name": self.name,
            "enable": self.enable,
            "proto": self.proto,
            "l3": self.l3,
            "transport": self.transport,
            "cdn": self.cdn,
            "child_unique_id": self.child.unique_id if self.child else "",
            "params": self.params,
        }

    def __str__(self):
        return str(self.to_dict())

    @staticmethod
    def add_or_update(commit=True, child_id=0, **proxy):
        dbproxy = Proxy.query.filter(Proxy.name == proxy["name"]).first()
        if not dbproxy:
            dbproxy = Proxy()
            db.session.add(dbproxy)
        dbproxy.enable = proxy["enable"]
        dbproxy.name = proxy["name"]
        dbproxy.proto = proxy["proto"]
        if proxy["transport"] == "splithttp":
            proxy["transport"] = "xhttp"
        dbproxy.transport = proxy["transport"]
        dbproxy.cdn = proxy["cdn"]
        dbproxy.l3 = proxy["l3"]
        dbproxy.params = proxy["params"]
        dbproxy.child_id = child_id
        if commit:
            db.session.commit()

    @staticmethod
    def from_schema(schema):
        return schema.dump(Proxy())

    def to_schema(self):
        proxy_dict = self.to_dict()
        from hiddifypanel.panel.commercial.restapi.v2.parent.schema import ProxySchema

        return ProxySchema.model_validate(proxy_dict)

    @staticmethod
    def bulk_register(proxies, commit=True, force_child_unique_id: str | None = None):
        from hiddifypanel.panel import hiddify

        for proxy in proxies:
            row = proxy.model_dump() if hasattr(proxy, "model_dump") else proxy
            child_id = hiddify.get_child(unique_id=force_child_unique_id)
            Proxy.add_or_update(commit=False, child_id=child_id, **row)
        if commit:
            db.session.commit()
