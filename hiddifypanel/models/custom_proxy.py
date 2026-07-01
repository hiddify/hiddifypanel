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


class L7Proto(StrEnum):
    h1 = auto()
    h2 = auto()
    tls_h3_quic = auto()


class CustomProxyMode(StrEnum):
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


class ServerCore(StrEnum):
    xray = "xray"
    hiddify_core = "hiddify-core"
    haproxy = "haproxy"
    nginx = "nginx"
    dns_gateway = "dns_gateway"
    dnstt = "dnstt"


class ClientCore(StrEnum):
    sublink = "sublink"
    xray = "xray"
    singbox = "singbox"
    hiddify_core = "hiddify-core"
    clash = "clash"


class TemplateCore(StrEnum):
    xray = "xray"
    hiddify_core = "hiddify-core"
    singbox = "singbox"
    sublink = "sublink"
    haproxy = "haproxy"
    clash = "clash"
    nginx = "nginx"
    dnstt = "dnstt"
    dns_gateway = "dns_gateway"


class TemplateCategory(StrEnum):
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
        from hiddifypanel.proxy_v3.builtin_proxy_sync import effective_template_content

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
            from hiddifypanel.proxy_v3.builtin_proxy_sync import apply_builtin_override_template

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
    l7_proto = Column(Enum(L7Proto), nullable=True)
    alpns = Column(JSON, default=list)
    download_alpns = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    domain_modes = Column(JSON, default=list)
    custom_path = Column(String(500), default="")
    server_core = Column(Enum(ServerCore), nullable=False, default=ServerCore.xray)

    server_inbound_tcp_ports = Column(JSON, default=list)
    server_inbound_udp_ports = Column(JSON, default=list)
    server_config = Column(Text, nullable=False, default="")
    builtin = Column(JSON, default=dict)
    builtin_overrides = Column(JSON, default=dict)
    builtin_server_config = Column(Text, nullable=False, default="")
    server_override = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0)
    is_builtin = Column(Boolean, default=False, nullable=False)

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
        return infer_proto_from_tags(self.tags)

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
            "l7_proto": self.l7_proto.value if self.l7_proto else None,
            "alpns": list(self.alpns or []),
            "download_alpns": list(self.download_alpns or []),
            "tags": self.tags or [],
            "domain_modes": list(self.domain_modes or []),
            "custom_path": self.custom_path or "",
            "server_config": {
                "core": self.server_core.value if self.server_core else None,
                "inbound_template": self.effective_server_config_text(),
                "tag": self.server_tag or "",
                "inbound_tcp_ports": list(self.server_inbound_tcp_ports or []),
                "inbound_udp_ports": list(self.server_inbound_udp_ports or []),
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
                dbproxy.proto = infer_proto_from_tags(data.get("tags") or dbproxy.tags)

            from hiddifypanel.proxy_v3.builtin_proxy_sync import apply_custom_proxy_general, apply_server_override
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
            if "tags" in data:
                dbproxy.tags = list(data.get("tags") or [])
            if "builtin_overrides" in data:
                for key, enabled in (data.get("builtin_overrides") or {}).items():
                    set_field_override(dbproxy, str(key), bool(enabled))
            if "server_override" in data:
                set_field_override(dbproxy, "server_config", bool(data["server_override"]))
            if "l7_proto" in data and data.get("l7_proto") not in (None, ""):
                if "l7_proto" in (data.get("builtin_overrides") or {}) or data.get("server_override") is not None:
                    dbproxy.l7_proto = _parse_l7_proto(data.get("l7_proto"))
                else:
                    dbproxy.l7_proto = _parse_l7_proto(data.get("l7_proto"))
            apply_server = bool((data.get("builtin_overrides") or {}).get("server_config") or dbproxy.server_override or dbproxy.id is None)
            if "server_config" in data and apply_server:
                payload = data["server_config"] or {}
                if "core" in payload:
                    dbproxy.server_core = _parse_server_core(payload["core"])
                if "tag" in payload:
                    dbproxy.server_tag = str(payload.get("tag") or "")
                if "inbound_template" in payload:
                    dbproxy.server_config = payload.get("inbound_template") or ""
                _apply_server_ports(dbproxy, payload)
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
            dbproxy.proto = infer_proto_from_tags(data.get("tags") or dbproxy.tags)
        if "l7_proto" in data and data.get("l7_proto") not in (None, ""):
            dbproxy.l7_proto = _parse_l7_proto(data.get("l7_proto"))
        if "alpns" in data:
            dbproxy.alpns = [str(v).strip() for v in (data.get("alpns") or []) if str(v).strip()]
        if "download_alpns" in data:
            dbproxy.download_alpns = [str(v).strip() for v in (data.get("download_alpns") or []) if str(v).strip()]
        if "tags" in data:
            dbproxy.tags = list(data.get("tags") or [])
        if "domain_modes" in data:
            _apply_domain_modes(dbproxy, list(data.get("domain_modes") or []))
        if "custom_path" in data:
            dbproxy.custom_path = normalize_custom_path(data["custom_path"])
        if "server_config" in data:
            payload = data["server_config"] or {}
            if "core" in payload:
                dbproxy.server_core = _parse_server_core(payload["core"])
            if "tag" in payload:
                dbproxy.server_tag = str(payload.get("tag") or "")
            if "inbound_template" in payload:
                dbproxy.server_config = payload.get("inbound_template") or ""
            _apply_server_ports(dbproxy, payload)
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
    from hiddifypanel.proxy_v3.builtin_proxy_sync import sync_custom_proxy_presets, sync_templates

    sync_templates(child_id)
    sync_custom_proxy_presets(child_id)


def normalize_custom_path(path: str | None) -> str:
    return (path or "").strip().lstrip("/")


def infer_proto_from_tags(tags: list[str] | None) -> ProxyProto:
    for tag in tags or []:
        key = str(tag).strip().lower()
        try:
            return ProxyProto(key)
        except ValueError:
            continue
    return ProxyProto.vless


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
        return ProxyProto(str(value).strip().lower())
    except ValueError as exc:
        allowed = ", ".join(m.value for m in ProxyProto)
        raise ValueError(f"Invalid proto {value!r}. Must be one of: {allowed}") from exc


def _parse_l7_proto(value: Any) -> L7Proto | None:
    if value is None or value == "":
        return None
    if isinstance(value, L7Proto):
        return value
    try:
        return L7Proto(str(value).strip().lower())
    except ValueError as exc:
        allowed = ", ".join(m.value for m in L7Proto)
        raise ValueError(f"Invalid l7_proto {value!r}. Must be one of: {allowed}") from exc


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
        return
    if dbproxy.mode == CustomProxyMode.domains_l7_gateway:
        allowed = {"direct", "cdn", "relay", "fake"}
        dbproxy.domain_modes = [m for m in domain_modes if m in allowed] or ["direct"]
        return
    if dbproxy.mode == CustomProxyMode.ip:
        allowed = {"direct", "relay"}
        dbproxy.domain_modes = [m for m in domain_modes if m in allowed]
        return
    dbproxy.domain_modes = default_domain_modes_for_mode(dbproxy.mode)


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
