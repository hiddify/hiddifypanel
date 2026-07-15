from __future__ import annotations

from enum import auto
from typing import Any

from slugify import slugify
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from strenum import StrEnum

from hiddifypanel.database import db
from hiddifypanel.models.proxy import ProxyProto
from hiddifypanel.proxy_v3.custom_proxy_ports import (
    default_domain_modes_for_mode,
    mode_requires_static_ports,
    mode_uses_auto_ports,
    mode_uses_gateway_port,
    normalize_port_list,
)


class JinjaEnum(StrEnum):
    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: Any) -> bool:
        return self.value == other

    def __ne__(self, other: Any) -> bool:
        return self.value != other

    def __lt__(self, other: Any) -> bool:
        return self.value < other


class L7Proto(JinjaEnum):
    h1 = auto()
    h2 = auto()
    tls_h3_quic = auto()


class TlsLayer(JinjaEnum):
    http = auto()
    tls = auto()


class CustomProxyTransport(JinjaEnum):
    tcp = auto()
    ws = auto()
    httpupgrade = auto()
    grpc = auto()
    xhttp = auto()
    other = auto()


class CustomProxyMode(JinjaEnum):
    domains_l7_gateway = auto()
    domains_sni_gateway = auto()
    domains_dns_gateway = auto()

    domains_auto_public_ports = auto()
    domains_single_public_port = auto()
    ip = auto()

    def template_domain_binding(self) -> str:
        return "ip" if self == CustomProxyMode.ip else "domain"

    def direct_port_access(self) -> bool:
        return self in [
            CustomProxyMode.domains_auto_public_ports,
            CustomProxyMode.domains_single_public_port,
            CustomProxyMode.ip,
        ]


class InboundTcpUdp(JinjaEnum):
    tcp = auto()
    udp = auto()
    both = auto()


class ServerCore(JinjaEnum):
    xray = "xray"
    hiddify_core = "hiddify-core"
    haproxy = "haproxy"
    nginx = "nginx"
    rust_rpxy_l4 = "rust-rpxy-l4"
    dns_gateway = "dns_gateway"
    dnstt = "dnstt"

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))


class ClientCore(JinjaEnum):
    sublink = "sublink"
    xray = "xray"
    singbox = "singbox"
    hiddify_core = "hiddify-core"
    clash = "clash"

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))


class TemplateCore(JinjaEnum):
    xray = "xray"
    hiddify_core = "hiddify-core"
    singbox = "singbox"
    sublink = "sublink"
    haproxy = "haproxy"
    clash = "clash"
    nginx = "nginx"
    rust_rpxy_l4 = "rust-rpxy-l4"
    dnstt = "dnstt"
    dns_gateway = "dns_gateway"

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))


class TemplateCategory(JinjaEnum):
    server_inbound = auto()
    client_outbound = auto()
    base_config = auto()


TEMPLATE_CATEGORIES_ACTIVE = (
    TemplateCategory.server_inbound,
    TemplateCategory.client_outbound,
    TemplateCategory.base_config,
)

DEFAULT_SERVER_TEMPLATE_SLUG = "default/server/xray-inbound"
DEFAULT_SUBLINK_TEMPLATE_SLUG = "default/client/sublink-link"


class ProxyTemplate(db.Model):  # type: ignore
    __tablename__ = "proxy_template"
    __table_args__ = (UniqueConstraint("child_id", "slug", name="uq_proxy_template_child_slug"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey("child.id"), default=0, nullable=False)
    slug = Column(String(200), nullable=False)
    core = Column(Enum(TemplateCore), nullable=False)
    category = Column(Enum(TemplateCategory), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(500), default="")
    content = Column(Text, nullable=False, default="")
    builtin_content = Column(Text, nullable=False, default="")
    builtin_override = Column(Boolean, default=False, nullable=False)
    is_builtin = Column(Boolean, default=False, nullable=False)

    def effective_content(self) -> str:
        from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import effective_template_content

        return effective_template_content(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "child_id": self.child_id,
            "slug": self.slug,
            "core": self.core.value if self.core else None,
            "category": self.category.value if self.category else None,
            "name": self.name,
            "description": self.description or "",
            "content": self.effective_content(),
            "builtin_content": self.builtin_content or "",
            "builtin_override": bool(self.builtin_override),
            "is_builtin": bool(self.is_builtin),
        }

    @classmethod
    def add_or_update(cls, child_id: int = 0, commit: bool = True, **data) -> ProxyTemplate:
        slug = (data.get("slug") or "").strip()
        if not slug:
            raise ValueError("Template slug is required")

        db_tpl = None
        template_id = data.get("id")
        if template_id:
            db_tpl = cls.query.filter(cls.id == template_id).first()
        if not db_tpl:
            db_tpl = cls.query.filter(cls.slug == slug, cls.child_id == child_id).first()

        if db_tpl and db_tpl.is_builtin and not template_id:
            raise ValueError(f'Slug "{slug}" is reserved by a built-in template')

        if not db_tpl:
            db_tpl = cls()
            db_tpl.child_id = child_id
            db_tpl.slug = slug
            db_tpl.is_builtin = bool(data.get("is_builtin", False))
            db_tpl.builtin_override = bool(data.get("builtin_override", False))
            db.session.add(db_tpl)

        if db_tpl.is_builtin:
            if "slug" in data and data.get("slug") != db_tpl.slug:
                raise ValueError("Built-in template slug cannot be changed")
            from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import apply_builtin_override_template

            if "name" in data:
                db_tpl.name = data["name"]
            if "description" in data:
                db_tpl.description = data.get("description") or ""
            if "content" in data:
                new_content = data.get("content") or ""
                if new_content != (db_tpl.builtin_content or ""):
                    apply_builtin_override_template(db_tpl, override=True)
                elif "builtin_override" in data:
                    apply_builtin_override_template(db_tpl, override=bool(data["builtin_override"]))
                if db_tpl.builtin_override:
                    db_tpl.content = new_content
            elif "builtin_override" in data:
                apply_builtin_override_template(db_tpl, override=bool(data["builtin_override"]))
            if commit:
                db.session.commit()
            return db_tpl

        if "core" not in data:
            raise ValueError("Template core is required")
        if "category" not in data:
            raise ValueError("Template category is required")
        if "name" not in data:
            raise ValueError("Template name is required")

        db_tpl.slug = slug
        db_tpl.core = _parse_template_core(data["core"])
        category = data["category"]
        db_tpl.category = category if isinstance(category, TemplateCategory) else TemplateCategory(category)
        db_tpl.name = data["name"]
        db_tpl.description = data.get("description") or ""
        db_tpl.content = data.get("content") or ""

        if commit:
            db.session.commit()
        return db_tpl


class CustomProxyClientCore(db.Model):  # type: ignore
    __tablename__ = "custom_proxy_client_core"
    __table_args__ = (UniqueConstraint("custom_proxy_id", "core", "version", name="uq_custom_proxy_client_core"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    custom_proxy_id = Column(Integer, ForeignKey("custom_proxy.id", ondelete="CASCADE"), nullable=False)
    core = Column(Enum(ClientCore), nullable=False)
    version = Column(String(50), nullable=False, default="")
    slug = Column(String(200), nullable=False, default="")
    outbounds_template = Column(Text, nullable=False, default="")
    is_builtin = Column(Boolean, default=False, nullable=False)
    builtin_outbounds_template = Column(Text, nullable=False, default="")
    override = Column(Boolean, default=False, nullable=False)

    proxy = relationship("CustomProxy", back_populates="client_cores")

    def effective_outbounds_template(self) -> str:
        if self.override and (self.outbounds_template or "").strip():
            return self.outbounds_template or ""
        return self.builtin_outbounds_template or self.outbounds_template or ""

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "core": self.core.value,
            "version": self.version or "",
            "slug": self.slug or f"client-{self.core.value}",
            "is_builtin": bool(self.is_builtin),
            "outbounds_template": self.effective_outbounds_template(),
        }
        if self.override:
            payload["override"] = True
        return payload


class CustomProxy(db.Model):  # type: ignore
    __tablename__ = "custom_proxy"
    __table_args__ = (UniqueConstraint("child_id", "slug", name="uq_custom_proxy_child_slug"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey("child.id"), default=0, nullable=False)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False)
    enable = Column(Boolean, default=True, nullable=False)
    mode = Column(Enum(CustomProxyMode), nullable=False)
    proto = Column(Enum(ProxyProto), nullable=True)
    transport = Column(Enum(CustomProxyTransport), nullable=True)
    tls_layer = Column(Enum(TlsLayer), nullable=True)
    l7_reverse_proto = Column(Enum(L7Proto), nullable=True)
    categories = Column(JSON, default=list)
    domain_modes = Column(JSON, default=list)
    custom_path = Column(String(500), default="")
    server_core = Column(Enum(ServerCore), nullable=False, default=ServerCore.xray)

    server_inbound_tcp_ports = Column(JSON, default=list)
    server_inbound_udp_ports = Column(JSON, default=list)
    server_inbound_tcp_udp = Column(Enum(InboundTcpUdp), nullable=False, default=InboundTcpUdp.both)
    server_inbound_download_tcp_udp = Column(Enum(InboundTcpUdp), nullable=True)
    server_config = Column(Text, nullable=False, default="")
    builtin = Column(JSON, default=dict)
    builtin_overrides = Column(JSON, default=dict)
    builtin_server_config = Column(Text, nullable=False, default="")
    server_override = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0)
    is_builtin = Column(Boolean, default=False, nullable=False)

    download_tls_layer = Column(Enum(TlsLayer), nullable=True)
    download_domain_modes = Column(JSON, default=list)

    client_cores = relationship(
        "CustomProxyClientCore",
        back_populates="proxy",
        cascade="all, delete-orphan",
        order_by="CustomProxyClientCore.id",
    )

    def effective_server_config_text(self) -> str:
        from hiddifypanel.proxy_v3.template_catalog.custom_proxy_builtin import effective_field

        if self.is_builtin:
            return str(effective_field(self, "server_config") or "")
        return self.server_config or ""

    def effective_proto(self) -> ProxyProto:
        if self.proto:
            return self.proto
        return infer_proto_from_categories(self.categories)

    def effective_transport(self) -> CustomProxyTransport:
        if self.transport:
            return self.transport
        return infer_transport_from_categories(self.categories)

    def effective_server_tcp_udp(self) -> InboundTcpUdp:
        """Firewall/ports view: for xhttp, union of upload (tcp_udp) and download."""
        if uses_xhttp_download_settings(self):
            upload = self.server_inbound_tcp_udp or InboundTcpUdp.tcp
            download = self.server_inbound_download_tcp_udp or InboundTcpUdp.tcp
            if upload != download:
                return InboundTcpUdp.both
            return upload
        return self.server_inbound_tcp_udp or InboundTcpUdp.both

    def to_dict(self) -> dict[str, Any]:
        from hiddifypanel.proxy_v3.template_catalog.custom_proxy_builtin import (
            builtin_payload,
            client_override_key,
            is_field_overridden,
            overrides_payload,
        )

        client_configs = [row.to_dict() for row in self.client_cores]
        builtin_client_configs = [
            {
                "core": row.core.value,
                "version": row.version or "",
                "outbounds_template": ((self.builtin or {}).get(client_override_key(row.core.value), "") if self.is_builtin else (row.builtin_outbounds_template or "")),
                "slug": row.slug or f"client-{row.core.value}",
                "is_builtin": bool(row.is_builtin),
                "override": is_field_overridden(self, client_override_key(row.core.value)),
            }
            for row in self.client_cores
        ]
        return {
            "id": self.id,
            "child_id": self.child_id,
            "name": self.name,
            "slug": self.slug,
            "enable": bool(self.enable),
            "mode": self.mode.value if self.mode else None,
            "proto": self.effective_proto().value,
            "transport": self.effective_transport().value,
            "tls_layer": self.tls_layer.value if self.tls_layer else None,
            "l7_reverse_proto": self.l7_reverse_proto.value if self.l7_reverse_proto else None,
            "download_tls_layer": self.download_tls_layer.value if self.download_tls_layer else None,
            "download_domain_modes": list(self.download_domain_modes or []),
            "categories": self.categories or [],
            "domain_modes": list(self.domain_modes or []),
            "custom_path": self.custom_path or "",
            "server_config": {
                "core": self.server_core.value if self.server_core else None,
                "inbound_template": self.effective_server_config_text(),
                "inbound_tcp_ports": list(self.server_inbound_tcp_ports or []),
                "inbound_udp_ports": list(self.server_inbound_udp_ports or []),
                "tcp_udp": (self.server_inbound_tcp_udp or InboundTcpUdp.both).value,
                "download_tcp_udp": (
                    self.server_inbound_download_tcp_udp.value
                    if self.server_inbound_download_tcp_udp
                    else None
                ),
            },
            "client_config": {"core_configs": client_configs},
            "builtin": builtin_payload(self) if self.is_builtin else {},
            "builtin_overrides": overrides_payload(self) if self.is_builtin else {},
            "builtin_server_config": (self.builtin or {}).get("server_config") or self.builtin_server_config or "",
            "builtin_client_config": {"core_configs": builtin_client_configs},
            "server_override": bool((self.builtin_overrides or {}).get("server_config")),
            "client_override": any((self.builtin_overrides or {}).get(client_override_key(row.core.value)) for row in self.client_cores),
            "sort_order": self.sort_order or 0,
            "is_builtin": bool(self.is_builtin),
            "client_cores": [row.core.value for row in self.client_cores if row.core],
            "server_core": self.server_core.value if self.server_core else None,
        }

    @classmethod
    def add_or_update(cls, child_id: int = 0, commit: bool = True, **data) -> CustomProxy:
        proxy_id = data.get("id")
        dbproxy = None
        if proxy_id:
            dbproxy = cls.query.filter(cls.id == proxy_id, cls.child_id == child_id).first()
            if not dbproxy:
                raise ValueError(f"Custom proxy id={proxy_id} not found")
        if not dbproxy and data.get("slug"):
            dbproxy = cls.query.filter(cls.slug == data["slug"], cls.child_id == child_id).first()
        if not dbproxy:
            if "name" not in data:
                raise ValueError("name is required")
            if "mode" not in data:
                raise ValueError("mode is required")
            dbproxy = cls()
            dbproxy.child_id = child_id
            dbproxy.is_builtin = bool(data.get("is_builtin", False))
            dbproxy.server_override = bool(data.get("server_override", False))
            db.session.add(dbproxy)

        if dbproxy.is_builtin:
            if "slug" in data:
                new_slug = (data.get("slug") or "").strip()
                if dbproxy.slug and new_slug and dbproxy.slug != new_slug:
                    raise ValueError("Built-in proxy slug cannot be changed")
                if new_slug:
                    dbproxy.slug = new_slug
            if not dbproxy.slug:
                raise ValueError("slug is required")
            if "mode" in data:
                dbproxy.mode = _parse_mode(data["mode"])
            elif not dbproxy.mode:
                raise ValueError("mode is required")
            if "proto" in data and data.get("proto") not in (None, ""):
                dbproxy.proto = _parse_proto(data.get("proto"))
            elif not dbproxy.proto:
                dbproxy.proto = infer_proto_from_categories(data.get("categories") or dbproxy.categories)
            if "transport" in data and data.get("transport") not in (None, ""):
                dbproxy.transport = _parse_transport(data.get("transport"))
            elif not dbproxy.transport:
                dbproxy.transport = infer_transport_from_categories(data.get("categories") or dbproxy.categories)

            from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import apply_custom_proxy_general, apply_server_override
            from hiddifypanel.proxy_v3.template_catalog.custom_proxy_builtin import (
                client_override_key,
                set_field_override,
                sync_catalog_field,
                GENERAL_OVERRIDE_FIELDS,
                SERVER_OVERRIDE_FIELDS,
            )

            if "name" in data:
                dbproxy.name = data["name"]
            if "enable" in data:
                dbproxy.enable = bool(data["enable"])
            if "categories" in data:
                dbproxy.categories = list(data.get("categories") or [])
            if "builtin_overrides" in data:
                for key, enabled in (data.get("builtin_overrides") or {}).items():
                    set_field_override(dbproxy, str(key), bool(enabled))
            if "server_override" in data:
                set_field_override(dbproxy, "server_config", bool(data["server_override"]))
            if "l7_reverse_proto" in data and data.get("l7_reverse_proto") not in (None, ""):
                dbproxy.l7_reverse_proto = _parse_l7_reverse_proto(data.get("l7_reverse_proto"))
            elif "l7_proto" in data and data.get("l7_proto") not in (None, ""):
                dbproxy.l7_reverse_proto = _parse_l7_reverse_proto(data.get("l7_proto"))
            _apply_download_xhttp_fields(dbproxy, data)
            if "tls_layer" in data and data.get("tls_layer") not in (None, ""):
                dbproxy.tls_layer = _parse_tls_layer(data.get("tls_layer"))
            apply_server = bool((data.get("builtin_overrides") or {}).get("server_config") or dbproxy.server_override or dbproxy.id is None)
            if "server_config" in data and apply_server:
                payload = data["server_config"] or {}
                if "core" in payload:
                    dbproxy.server_core = _parse_server_core(payload["core"])
                if "inbound_template" in payload:
                    dbproxy.server_config = payload.get("inbound_template") or ""
                _apply_server_ports(dbproxy, payload)
                _apply_server_tcp_udp(dbproxy, payload)
            if "client_config" in data and dbproxy.id is not None:
                cls._sync_builtin_client_overrides(dbproxy, data.get("client_config") or {})
            general_keys = tuple(GENERAL_OVERRIDE_FIELDS)
            if any(k in data for k in general_keys):
                apply_custom_proxy_general(dbproxy, data)
            for field in general_keys:
                if field in data and (data.get("builtin_overrides") or {}).get(field):
                    setattr(dbproxy, field, data[field])
            if "domain_modes" in data:
                _apply_domain_modes(dbproxy, list(data.get("domain_modes") or []))
            elif "mode" in data and "domain_modes" not in data:
                _apply_domain_modes(dbproxy, None)
            if commit:
                db.session.commit()
            return dbproxy

        if "name" in data:
            dbproxy.name = data["name"]
        if "slug" in data:
            dbproxy.slug = data["slug"]
        elif not dbproxy.slug:
            dbproxy.slug = proxy_slug(dbproxy.name)
        if "enable" in data:
            dbproxy.enable = bool(data["enable"])
        if "mode" in data:
            dbproxy.mode = _parse_mode(data["mode"])
            if "domain_modes" not in data:
                _apply_domain_modes(dbproxy, None)
        if "proto" in data and data.get("proto") not in (None, ""):
            dbproxy.proto = _parse_proto(data.get("proto"))
        elif not dbproxy.proto:
            dbproxy.proto = infer_proto_from_categories(data.get("categories") or dbproxy.categories)
        if "transport" in data and data.get("transport") not in (None, ""):
            dbproxy.transport = _parse_transport(data.get("transport"))
        elif not dbproxy.transport:
            dbproxy.transport = infer_transport_from_categories(data.get("categories") or dbproxy.categories)
        if "tls_layer" in data and data.get("tls_layer") not in (None, ""):
            dbproxy.tls_layer = _parse_tls_layer(data.get("tls_layer"))
        if "l7_reverse_proto" in data and data.get("l7_reverse_proto") not in (None, ""):
            dbproxy.l7_reverse_proto = _parse_l7_reverse_proto(data.get("l7_reverse_proto"))
        elif "l7_proto" in data and data.get("l7_proto") not in (None, ""):
            dbproxy.l7_reverse_proto = _parse_l7_reverse_proto(data.get("l7_proto"))
        _apply_download_xhttp_fields(dbproxy, data)
        if "categories" in data:
            dbproxy.categories = list(data.get("categories") or [])
        if "domain_modes" in data:
            _apply_domain_modes(dbproxy, list(data.get("domain_modes") or []))
        if "custom_path" in data:
            dbproxy.custom_path = normalize_custom_path(data["custom_path"])
        if "server_config" in data:
            payload = data["server_config"] or {}
            if "core" in payload:
                dbproxy.server_core = _parse_server_core(payload["core"])
            if "inbound_template" in payload:
                dbproxy.server_config = payload.get("inbound_template") or ""
            _apply_server_ports(dbproxy, payload)
            _apply_server_tcp_udp(dbproxy, payload)
        if "client_config" in data:
            core_configs = list((data.get("client_config") or {}).get("core_configs") or [])
            if not core_configs:
                raise ValueError("client_config.core_configs must contain at least one client core")
            dbproxy.client_cores.clear()
            for item in core_configs:
                core = _parse_client_core(item.get("core"))
                template = str(item.get("outbounds_template") or item.get("link_template") or "")
                slug = str(item.get("slug") or f"client-{core.value}")
                dbproxy.client_cores.append(
                    CustomProxyClientCore(
                        core=core,
                        version=str(item.get("version") or ""),
                        slug=slug,
                        is_builtin=bool(item.get("is_builtin")),
                        outbounds_template=template,
                    )
                )
        if "sort_order" in data:
            dbproxy.sort_order = int(data["sort_order"])

        _validate_required_server_ports(dbproxy)

        if commit:
            db.session.commit()
        return dbproxy

    @classmethod
    def _sync_builtin_client_overrides(cls, dbproxy: CustomProxy, client_config: dict[str, Any]) -> None:
        from hiddifypanel.proxy_v3.template_catalog.custom_proxy_builtin import client_override_key, set_field_override

        for item in client_config.get("core_configs") or []:
            core = _parse_client_core(item.get("core"))
            key = client_override_key(core.value)
            row = next((r for r in dbproxy.client_cores if r.core == core), None)
            if not row:
                slug = str(item.get("slug") or f"client-{core.value}")
                row = CustomProxyClientCore(
                    core=core,
                    version=str(item.get("version") or ""),
                    slug=slug,
                    is_builtin=bool(item.get("is_builtin")),
                )
                dbproxy.client_cores.append(row)
            if "override" in item:
                set_field_override(dbproxy, key, bool(item.get("override")))
            elif item.get("outbounds_template") is not None or item.get("link_template") is not None:
                set_field_override(dbproxy, key, True)
            if "outbounds_template" in item:
                row.outbounds_template = item.get("outbounds_template") or ""
            elif "link_template" in item:
                row.outbounds_template = item.get("link_template") or ""
            if "version" in item:
                row.version = str(item.get("version") or "")
            if "slug" in item and item.get("slug"):
                row.slug = str(item.get("slug"))

    def duplicate(self, child_id: int | None = None) -> CustomProxy:
        child_id = child_id if child_id is not None else self.child_id
        base_slug = f"{self.slug}-copy"
        slug = base_slug
        i = 1
        while CustomProxy.query.filter(CustomProxy.slug == slug, CustomProxy.child_id == child_id).first():
            slug = f"{base_slug}-{i}"
            i += 1
        data = self.to_dict()
        data.pop("id", None)
        data.pop("child_id", None)
        data.pop("client_cores", None)
        data["name"] = f"{self.name} (copy)"
        data["slug"] = slug
        data["is_builtin"] = False
        data["server_override"] = False
        for cc in data.get("client_config", {}).get("core_configs", []):
            cc.pop("override", None)
        return CustomProxy.add_or_update(child_id=child_id, **data)


def seed_default_proxy_shells(child_id: int = 0) -> None:
    from hiddifypanel.proxy_v3.template_catalog.template_defaults import (
        default_server_inbound_template,
        default_sublink_link_template,
    )

    shells = [
        {
            "slug": DEFAULT_SERVER_TEMPLATE_SLUG,
            "core": TemplateCore.xray,
            "category": TemplateCategory.server_inbound,
            "name": "Default Xray server inbound",
            "description": "Default listen snippet for new custom proxies",
            "content": default_server_inbound_template(),
        },
        {
            "slug": DEFAULT_SUBLINK_TEMPLATE_SLUG,
            "core": TemplateCore.sublink,
            "category": TemplateCategory.client_outbound,
            "name": "Default sublink client",
            "description": "Default sublink URI template for new custom proxies",
            "content": default_sublink_link_template(),
        },
    ]
    for spec in shells:
        row = ProxyTemplate.query.filter(
            ProxyTemplate.child_id == child_id,
            ProxyTemplate.slug == spec["slug"],
        ).first()
        content = spec["content"] or ""
        if row:
            if row.builtin_content != content:
                row.builtin_content = content
            if not row.builtin_override:
                row.content = content
            continue
        db.session.add(
            ProxyTemplate(
                child_id=child_id,
                slug=spec["slug"],
                core=spec["core"],
                category=spec["category"],
                name=spec["name"],
                description=spec["description"],
                content=content,
                builtin_content=content,
                is_builtin=True,
            )
        )
    db.session.commit()


def seed_proxy_templates(child_id: int = 0) -> None:
    from hiddifypanel.proxy_v3.builtin_proxy_sync.orchestrator import sync_custom_proxy_presets, sync_templates

    sync_templates(child_id)
    sync_custom_proxy_presets(child_id)


def normalize_custom_path(path: str | None) -> str:
    return (path or "").strip().lstrip("/")


def infer_proto_from_categories(categories: list[str] | None) -> ProxyProto:
    for tag in categories or []:
        key = _normalize_proto_key(str(tag).strip().lower())
        if not key:
            continue
        try:
            return ProxyProto(key)
        except ValueError:
            continue
    return ProxyProto.vless


def _normalize_proto_key(value: str) -> str:
    aliases = {"ss": "shadowsocks"}
    return aliases.get(value, value)


_TRANSPORT_TAG_ALIASES: dict[str, CustomProxyTransport] = {
    "ws": CustomProxyTransport.ws,
    "splithttp": CustomProxyTransport.xhttp,
    "shadowtls": CustomProxyTransport.other,
    "faketls": CustomProxyTransport.other,
    "ssh": CustomProxyTransport.other,
    "shadowsocks": CustomProxyTransport.other,
    "udp": CustomProxyTransport.other,
    "custom": CustomProxyTransport.other,
}


def infer_transport_from_categories(categories: list[str] | None) -> CustomProxyTransport:
    for tag in categories or []:
        key = str(tag).strip().lower()
        if key in _TRANSPORT_TAG_ALIASES:
            return _TRANSPORT_TAG_ALIASES[key]
        try:
            return _parse_transport(key)
        except ValueError:
            continue
    return CustomProxyTransport.tcp


def _parse_transport(value: Any) -> CustomProxyTransport:
    if isinstance(value, CustomProxyTransport):
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        return CustomProxyTransport.tcp
    text = str(value).strip()
    key = text.lower()
    if key in _TRANSPORT_TAG_ALIASES:
        return _TRANSPORT_TAG_ALIASES[key]
    for member in CustomProxyTransport:
        if member.value.lower() == key or member.name.lower() == key:
            return member
    allowed = ", ".join(m.value for m in CustomProxyTransport)
    raise ValueError(f"Invalid transport {value!r}. Must be one of: {allowed}")


def _parse_mode(value: Any) -> CustomProxyMode:
    if isinstance(value, CustomProxyMode):
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("mode is required")
    try:
        return CustomProxyMode(str(value).strip())
    except ValueError as exc:
        allowed = ", ".join(m.value for m in CustomProxyMode)
        raise ValueError(f"Invalid mode {value!r}. Must be one of: {allowed}") from exc


def _parse_proto(value: Any) -> ProxyProto:
    if isinstance(value, ProxyProto):
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("proto is required")
    try:
        return ProxyProto(_normalize_proto_key(str(value).strip().lower()))
    except ValueError as exc:
        allowed = ", ".join(m.value for m in ProxyProto)
        raise ValueError(f"Invalid proto {value!r}. Must be one of: {allowed}") from exc


def _parse_l7_reverse_proto(value: Any) -> L7Proto | None:
    if value is None or value == "":
        return None
    if isinstance(value, L7Proto):
        return value
    raw = str(value).strip().lower()
    if raw == "h3":
        raw = "tls_h3_quic"
    try:
        return L7Proto(raw)
    except ValueError as exc:
        allowed = ", ".join(m.value for m in L7Proto)
        raise ValueError(f"Invalid l7_reverse_proto {value!r}. Must be one of: {allowed}") from exc


def _parse_l7_proto(value: Any) -> L7Proto | None:
    return _parse_l7_reverse_proto(value)


def _parse_tls_layer(value: Any) -> TlsLayer | None:
    if value is None or value == "":
        return None
    if isinstance(value, TlsLayer):
        return value
    try:
        return TlsLayer(str(value).strip().lower())
    except ValueError as exc:
        allowed = ", ".join(m.value for m in TlsLayer)
        raise ValueError(f"Invalid tls_layer {value!r}. Must be one of: {allowed}") from exc


def domain_modes_use_reality(domain_modes: list[str] | None) -> bool:
    modes = {str(m).strip().lower() for m in (domain_modes or []) if str(m).strip()}
    return bool(modes & {"reality"})


def validate_tls_layer_domain_modes(tls_layer: TlsLayer | None, domain_modes: list[str] | None) -> None:
    if tls_layer == TlsLayer.http and domain_modes_use_reality(domain_modes):
        raise ValueError("HTTP TLS layer is incompatible with reality/special domain modes")


def uses_xhttp_download_settings(proxy: CustomProxy) -> bool:
    transport = proxy.effective_transport()
    return transport == CustomProxyTransport.xhttp


def xhttp_upload_is_quic(categories: list[str] | None) -> bool:
    return any(str(category).lower() == "up:quic" for category in (categories or []))


def xhttp_download_is_quic(categories: list[str] | None) -> bool:
    return any(str(category).lower() == "down:quic" for category in (categories or []))


def xhttp_alpn_is_quic(alpn: str | None) -> bool:
    return bool(alpn and str(alpn).lower() in {"tls_h3", "h3"})


def filter_domain_modes_without_reality(domain_modes: list[str] | tuple[str, ...]) -> list[str]:
    return [mode for mode in domain_modes if mode != "reality"]


def effective_server_tcp_udp(proxy: CustomProxy) -> InboundTcpUdp:
    return proxy.effective_server_tcp_udp()


def validate_xhttp_domain_modes(proxy: CustomProxy) -> None:
    if not uses_xhttp_download_settings(proxy):
        return
    categories = list(proxy.categories or [])
    if xhttp_upload_is_quic(categories) and "reality" in (proxy.domain_modes or []):
        raise ValueError("REALITY is incompatible with QUIC upload in xhttp")
    if xhttp_download_is_quic(categories) and "reality" in (proxy.download_domain_modes or []):
        raise ValueError("REALITY is incompatible with QUIC download in xhttp")


def _apply_download_xhttp_fields(dbproxy: CustomProxy, data: dict[str, Any]) -> None:
    if not uses_xhttp_download_settings(dbproxy):
        if any(key in data for key in ("download_tls_layer", "download_domain_modes")):
            dbproxy.download_tls_layer = None
            dbproxy.download_domain_modes = []
        return
    if "download_tls_layer" in data:
        raw = data.get("download_tls_layer")
        dbproxy.download_tls_layer = _parse_tls_layer(raw) if raw not in (None, "") else None
    if "download_domain_modes" in data:
        _apply_download_domain_modes(dbproxy, list(data.get("download_domain_modes") or []))
    validate_download_xhttp_fields(dbproxy)
    validate_xhttp_domain_modes(dbproxy)


def _apply_download_domain_modes(dbproxy: CustomProxy, domain_modes: list[str]) -> None:
    allowed = {"direct", "cdn", "relay", "fake", "reality"}
    dbproxy.download_domain_modes = [m for m in domain_modes if m in allowed] or ["direct"]
    validate_download_xhttp_fields(dbproxy)


def validate_download_xhttp_fields(proxy: CustomProxy) -> None:
    if not uses_xhttp_download_settings(proxy):
        return
    allowed_modes = {"direct", "cdn", "relay", "fake", "reality"}
    modes = list(proxy.download_domain_modes or [])
    invalid = [m for m in modes if m not in allowed_modes]
    if invalid:
        raise ValueError(f"Invalid download_domain_modes: {invalid!r}")
    if proxy.download_tls_layer == TlsLayer.http and domain_modes_use_reality(modes):
        raise ValueError("HTTP download TLS layer is incompatible with reality domain modes")


def _parse_server_core(value: Any) -> ServerCore:
    if isinstance(value, ServerCore):
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("server_core is required")
    try:
        return ServerCore(str(value).strip())
    except ValueError as exc:
        allowed = ", ".join(c.value for c in ServerCore)
        raise ValueError(f"Invalid server_core {value!r}. Must be one of: {allowed}") from exc


def _parse_template_core(value: Any) -> TemplateCore:
    if isinstance(value, TemplateCore):
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("Template core is required")
    try:
        return TemplateCore(str(value).strip())
    except ValueError as exc:
        allowed = ", ".join(c.value for c in TemplateCore)
        raise ValueError(f"Invalid template core {value!r}. Must be one of: {allowed}") from exc


def normalize_mode_value(value: Any) -> CustomProxyMode | None:
    try:
        return _parse_mode(value)
    except ValueError:
        return None


def _parse_client_core(value: Any) -> ClientCore:
    if isinstance(value, ClientCore):
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("client core is required")
    try:
        return ClientCore(str(value).strip())
    except ValueError as exc:
        allowed = ", ".join(c.value for c in ClientCore)
        raise ValueError(f"Invalid client core {value!r}. Must be one of: {allowed}") from exc


def _parse_tcp_udp(value: Any) -> InboundTcpUdp:
    if isinstance(value, InboundTcpUdp):
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        return InboundTcpUdp.both
    try:
        return InboundTcpUdp(str(value).strip())
    except ValueError as exc:
        allowed = ", ".join(m.value for m in InboundTcpUdp)
        raise ValueError(f"Invalid tcp_udp {value!r}. Must be one of: {allowed}") from exc


def _apply_server_tcp_udp(dbproxy: CustomProxy, payload: dict[str, Any]) -> None:
    if dbproxy.is_builtin:
        return
    if uses_xhttp_download_settings(dbproxy):
        # Upload uses server_inbound_tcp_udp; accept legacy upload_tcp_udp as alias.
        if "tcp_udp" in payload:
            dbproxy.server_inbound_tcp_udp = _parse_tcp_udp(payload.get("tcp_udp"))
        elif "upload_tcp_udp" in payload:
            dbproxy.server_inbound_tcp_udp = _parse_tcp_udp(payload.get("upload_tcp_udp"))
        if "download_tcp_udp" in payload:
            dbproxy.server_inbound_download_tcp_udp = _parse_tcp_udp(payload.get("download_tcp_udp"))
        return
    dbproxy.server_inbound_download_tcp_udp = None
    if "tcp_udp" in payload:
        dbproxy.server_inbound_tcp_udp = _parse_tcp_udp(payload.get("tcp_udp"))


def _apply_server_ports(dbproxy: CustomProxy, payload: dict[str, Any]) -> None:
    mode = dbproxy.mode
    if mode_uses_gateway_port(mode) or mode_uses_auto_ports(mode):
        dbproxy.server_inbound_tcp_ports = []
        dbproxy.server_inbound_udp_ports = []
        return
    if not any(key in payload for key in ("inbound_tcp_ports", "inbound_udp_ports", "inbound_port")):
        return
    tcp_ports = normalize_port_list(payload.get("inbound_tcp_ports"))
    if not tcp_ports and payload.get("inbound_port") is not None:
        tcp_ports = normalize_port_list(payload.get("inbound_port"))
    dbproxy.server_inbound_tcp_ports = tcp_ports
    if "inbound_udp_ports" in payload:
        dbproxy.server_inbound_udp_ports = normalize_port_list(payload.get("inbound_udp_ports"))
    else:
        dbproxy.server_inbound_udp_ports = list(tcp_ports)


def _apply_domain_modes(dbproxy: CustomProxy, domain_modes: list[str] | None) -> None:
    if domain_modes is None:
        dbproxy.domain_modes = default_domain_modes_for_mode(dbproxy.mode)
    elif dbproxy.mode == CustomProxyMode.domains_l7_gateway:
        allowed = {"direct", "cdn", "relay"}
        dbproxy.domain_modes = [m for m in domain_modes if m in allowed] or ["direct"]
        validate_tls_layer_domain_modes(dbproxy.tls_layer, dbproxy.domain_modes)
    elif dbproxy.mode == CustomProxyMode.domains_sni_gateway:
        allowed = {"fake", "direct", "relay", "reality"}
        dbproxy.domain_modes = [m for m in domain_modes if m in allowed] or ["direct", "relay"]
        validate_tls_layer_domain_modes(dbproxy.tls_layer, dbproxy.domain_modes)
    elif dbproxy.mode in (
        CustomProxyMode.domains_auto_public_ports,
        CustomProxyMode.domains_single_public_port,
    ):
        allowed = {"direct", "relay"}
        dbproxy.domain_modes = [m for m in domain_modes if m in allowed] or ["direct", "relay"]
    elif dbproxy.mode == CustomProxyMode.ip:
        allowed = {"direct", "relay"}
        dbproxy.domain_modes = [m for m in domain_modes if m in allowed]
    else:
        dbproxy.domain_modes = default_domain_modes_for_mode(dbproxy.mode)
    validate_xhttp_domain_modes(dbproxy)


def proxy_slug(name: str) -> str:
    return slugify(name, lowercase=True) or "custom-proxy"


def _validate_required_server_ports(dbproxy: CustomProxy) -> None:
    if dbproxy.is_builtin:
        return
    mode = dbproxy.mode
    if mode_uses_gateway_port(mode) or mode_uses_auto_ports(mode):
        return
    if mode_requires_static_ports(mode) and not normalize_port_list(dbproxy.server_inbound_tcp_ports):
        raise ValueError("At least one inbound TCP port is required for this mode")
