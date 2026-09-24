from __future__ import annotations

from enum import auto
from typing import TYPE_CHECKING, Any

from slugify import slugify
from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from strenum import StrEnum

from hiddifypanel.database import db
from hiddifypanel.models.proxy import ProxyProto

if TYPE_CHECKING:
    from hiddifypanel.models.external_model.proxy_v3 import (
        CustomProxyClientConfigModel,
        CustomProxyClientCoreModel,
        CustomProxyModel,
        ProxyTemplateModel,
    )
from hiddifypanel.proxy_v3.custom_proxy_ports import (
    default_domain_modes_for_mode,
    mode_requires_static_ports,
    mode_uses_auto_ports,
    mode_uses_gateway_port,
    normalize_port_list,
)
from hiddifypanel.proxy_v3.domain_mode_filter import (
    ALLOWED_DOMAIN_MODES,
    domain_modes_use_reality,
    normalize_domain_modes,
    transport_tls_supports_reality,
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
    tls_h1 = auto()
    tls_h2 = auto()
    tls = auto()  # TCP TLS h2 h1
    quic_tls = auto()
    quic_tcp_tls = auto()  # QUIC + TLS h2 h1

    def uses_tls(self) -> bool:
        return self != TlsLayer.http

    def uses_tcp(self) -> bool:
        return self in (TlsLayer.http, TlsLayer.tls_h1, TlsLayer.tls_h2, TlsLayer.tls, TlsLayer.quic_tcp_tls)

    def uses_udp(self) -> bool:
        return self in (TlsLayer.quic_tls, TlsLayer.quic_tcp_tls)

    def alpns(self) -> list[str]:
        if self == TlsLayer.http:
            return ["http/1.1"]
        if self == TlsLayer.tls_h1:
            return ["http/1.1"]
        elif self == TlsLayer.tls_h2:
            return ["h2"]
        elif self == TlsLayer.tls:
            return ["h2", "http/1.1"]
        elif self == TlsLayer.quic_tls:
            return ["h3"]
        elif self == TlsLayer.quic_tcp_tls:
            return ["h3", "h2", "http/1.1"]
        raise ValueError(f"Invalid TLS layer: {self}")


class CustomProxyTransport(JinjaEnum):
    tcp = auto()
    http = auto()
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
    no_inbound = auto()

    def template_domain_binding(self) -> str:
        if self == CustomProxyMode.ip:
            return "ip"
        if self == CustomProxyMode.no_inbound:
            return "none"
        return "domain"

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
    dns_proxy = "dns_proxy"
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
    dns_proxy = "dns_proxy"

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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), default=0)
    slug: Mapped[str] = mapped_column(String(200))
    core: Mapped[TemplateCore] = mapped_column(Enum(TemplateCore))
    category: Mapped[TemplateCategory] = mapped_column(Enum(TemplateCategory))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    builtin_content: Mapped[str] = mapped_column(Text, default="")
    builtin_override: Mapped[bool] = mapped_column(default=False)
    is_builtin: Mapped[bool] = mapped_column(default=False)

    def effective_content(self) -> str:
        from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import effective_template_content

        return effective_template_content(self)

    def to_model(self) -> ProxyTemplateModel:
        from hiddifypanel.models.child import Child
        from hiddifypanel.models.external_model.proxy_v3 import ProxyTemplateModel

        child = Child.by_id(self.child_id) if self.child_id is not None else None
        return ProxyTemplateModel(
            id=self.id,
            child_id=self.child_id,
            child_unique_id=child.unique_id if child else "",
            slug=self.slug,
            core=self.core,
            category=self.category,
            name=self.name,
            description=self.description or "",
            content=self.effective_content(),
            builtin_content=self.builtin_content or "",
            builtin_override=bool(self.builtin_override),
            is_builtin=bool(self.is_builtin),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.to_model().to_dict()

    @classmethod
    def add_or_update(cls, child_id: int = 0, commit: bool = True, **data) -> ProxyTemplate:
        from hiddifypanel.models.external_model.proxy_v3 import ProxyTemplateModel

        return cls.upsert(ProxyTemplateModel.coerce(data), child_id=child_id, commit=commit)

    @classmethod
    def upsert(cls, data: ProxyTemplateModel, *, child_id: int = 0, commit: bool = True) -> ProxyTemplate:
        slug = data.slug
        if not slug:
            raise ValueError("Template slug is required")

        db_tpl = None
        template_id = data.id
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
            db_tpl.is_builtin = data.is_builtin
            db_tpl.builtin_override = data.builtin_override
            db.session.add(db_tpl)

        if db_tpl.is_builtin:
            if data.has("slug") and slug != db_tpl.slug:
                raise ValueError("Built-in template slug cannot be changed")
            from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import apply_builtin_override_template

            if data.name is not None:
                db_tpl.name = data.name
            if data.has("description"):
                db_tpl.description = data.description or ""
            if data.has("content"):
                new_content = data.content or ""
                if new_content != (db_tpl.builtin_content or ""):
                    apply_builtin_override_template(db_tpl, override=True)
                elif data.has("builtin_override"):
                    apply_builtin_override_template(db_tpl, override=data.builtin_override)
                if db_tpl.builtin_override:
                    db_tpl.content = new_content
            elif data.has("builtin_override"):
                apply_builtin_override_template(db_tpl, override=data.builtin_override)
            if commit:
                db.session.commit()
            return db_tpl

        if data.core is None:
            raise ValueError("Template core is required")
        if data.category is None:
            raise ValueError("Template category is required")
        if data.name is None:
            raise ValueError("Template name is required")

        db_tpl.slug = slug
        db_tpl.core = data.core
        db_tpl.category = data.category
        db_tpl.name = data.name
        db_tpl.description = data.description or ""
        db_tpl.content = data.content or ""

        if commit:
            db.session.commit()
        return db_tpl

    @classmethod
    def bulk_register(cls, templates, commit: bool = True, force_child_unique_id: str | None = None) -> None:
        from hiddifypanel.models.external_model.base import as_row
        from hiddifypanel.models.external_model.proxy_v3 import ProxyTemplateModel
        from hiddifypanel.panel import hiddify

        for tpl in templates:
            row = as_row(tpl)
            child_id = hiddify.child_id_from_row(row, force_child_unique_id)
            data = ProxyTemplateModel.coerce({k: v for k, v in row.items() if k not in {"id", "child_id", "child_unique_id"}})
            # Built-ins are keyed by slug; pass existing id so upsert can update them.
            existing = cls.query.filter(cls.slug == data.slug, cls.child_id == child_id).first()
            if existing:
                data = ProxyTemplateModel.coerce(data, id=existing.id)
            cls.upsert(data, child_id=child_id, commit=False)
        if commit:
            db.session.commit()


class CustomProxyClientCore(db.Model):  # type: ignore
    __tablename__ = "custom_proxy_client_core"
    __table_args__ = (UniqueConstraint("custom_proxy_id", "core", "version", name="uq_custom_proxy_client_core"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    custom_proxy_id: Mapped[int] = mapped_column(ForeignKey("custom_proxy.id", ondelete="CASCADE"))
    core: Mapped[ClientCore] = mapped_column(Enum(ClientCore))
    version: Mapped[str] = mapped_column(String(50), default="")
    slug: Mapped[str] = mapped_column(String(200), default="")
    outbounds_template: Mapped[str] = mapped_column(Text, default="")
    is_builtin: Mapped[bool] = mapped_column(default=False)
    builtin_outbounds_template: Mapped[str] = mapped_column(Text, default="")
    override: Mapped[bool] = mapped_column(default=False)

    proxy: Mapped[CustomProxy] = relationship("CustomProxy", back_populates="client_cores")

    def effective_outbounds_template(self) -> str:
        if self.override and (self.outbounds_template or "").strip():
            return self.outbounds_template or ""
        return self.builtin_outbounds_template or self.outbounds_template or ""

    def to_model(self) -> CustomProxyClientCoreModel:
        from hiddifypanel.models.external_model.proxy_v3 import CustomProxyClientCoreModel

        model = CustomProxyClientCoreModel(
            core=self.core,
            version=self.version or "",
            slug=self.slug or f"client-{self.core.value}",
            is_builtin=bool(self.is_builtin),
            outbounds_template=self.effective_outbounds_template(),
        )
        if self.override:
            model.override = True  # only emitted when set
        return model

    def to_dict(self) -> dict[str, Any]:
        return self.to_model().to_dict()


class CustomProxy(db.Model):  # type: ignore
    __tablename__ = "custom_proxy"
    __table_args__ = (UniqueConstraint("child_id", "slug", name="uq_custom_proxy_child_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), default=0)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200))
    _enable: Mapped[bool] = mapped_column("enable", default=True)
    mode: Mapped[CustomProxyMode] = mapped_column(Enum(CustomProxyMode))
    proto: Mapped[ProxyProto | None] = mapped_column(Enum(ProxyProto))
    transport: Mapped[CustomProxyTransport | None] = mapped_column(Enum(CustomProxyTransport))
    tls_layer: Mapped[TlsLayer | None] = mapped_column(Enum(TlsLayer))
    l7_reverse_proto: Mapped[L7Proto | None] = mapped_column(Enum(L7Proto))
    categories: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    domain_modes: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    custom_path: Mapped[str | None] = mapped_column(String(500), default="")
    server_core: Mapped[ServerCore] = mapped_column(Enum(ServerCore), default=ServerCore.xray)

    server_inbound_tcp_ports: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    server_inbound_udp_ports: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    server_inbound_tcp_udp: Mapped[InboundTcpUdp] = mapped_column(Enum(InboundTcpUdp), default=InboundTcpUdp.both)
    server_inbound_download_tcp_udp: Mapped[InboundTcpUdp | None] = mapped_column(Enum(InboundTcpUdp))
    server_config: Mapped[str] = mapped_column(Text, default="")
    builtin: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    builtin_overrides: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    builtin_server_config: Mapped[str] = mapped_column(Text, default="")
    server_override: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int | None] = mapped_column(default=0)
    is_builtin: Mapped[bool] = mapped_column(default=False)
    is_common_proxy: Mapped[bool] = mapped_column(default=False, server_default="0")

    download_tls_layer: Mapped[TlsLayer | None] = mapped_column(Enum(TlsLayer))
    download_domain_modes: Mapped[list[Any] | None] = mapped_column(JSON, default=list)

    client_cores: Mapped[list[CustomProxyClientCore]] = relationship(
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

    def effective_server_tcp_udp(self) -> InboundTcpUdp:
        """Firewall/ports view: for xhttp, union of upload (tcp_udp) and download."""
        if uses_xhttp_download_settings(self):
            upload = self.server_inbound_tcp_udp or InboundTcpUdp.tcp
            download = self.server_inbound_download_tcp_udp or InboundTcpUdp.tcp
            if upload != download:
                return InboundTcpUdp.both
            return upload
        return self.server_inbound_tcp_udp or InboundTcpUdp.both

    @hybrid_property
    def enable(self) -> bool:
        return bool(self._enable) and not self.blocked_parent_enables()

    @enable.inplace.setter
    def _set_enable(self, value: bool) -> None:
        self._enable = bool(value)

    @enable.inplace.expression
    def _enable_expression(cls):
        return cls._enable

    def blocked_parent_enables(self) -> list[dict[str, str]]:
        from flask_babel import gettext

        def _(text: str) -> str:
            try:
                return gettext(text)
            except Exception:
                # print(e)
                return text

        from hiddifypanel.models.config import hconfig
        from hiddifypanel.models.config_enum import ConfigEnum
        from hiddifypanel.proxy_v3.context_vars.builder.utils import common_proxy_core_blocks, parent_enable_keys_for, parent_enable_off

        child_id = int(self.child_id or 0)

        def flag(key: ConfigEnum) -> bool | None:
            value = hconfig(key, child_id)
            return value if isinstance(value, bool) else None

        keys = parent_enable_off(parent_enable_keys_for(self), flag)
        blocked = [{"key": key.name, "label": str(_(f"config.{key.name}.label"))} for key in keys]
        selected = hconfig(ConfigEnum.common_proxy_core, child_id)
        if common_proxy_core_blocks(self.is_common_proxy, self.server_core, selected):
            blocked.append({"key": ConfigEnum.common_proxy_core.name, "label": str(_(f"config.{ConfigEnum.common_proxy_core.name}.label"))})
        return blocked

    def is_effectively_enabled(self) -> bool:
        return bool(self.enable)

    def to_model(self) -> CustomProxyModel:
        from hiddifypanel.models.child import Child
        from hiddifypanel.models.external_model.proxy_v3 import (
            BlockedByModel,
            CustomProxyClientConfigModel,
            CustomProxyClientCoreModel,
            CustomProxyModel,
            CustomProxyServerConfigModel,
        )
        from hiddifypanel.proxy_v3.template_catalog.custom_proxy_builtin import (
            builtin_payload,
            client_override_key,
            is_field_overridden,
            overrides_payload,
        )

        builtin_client_configs = [
            CustomProxyClientCoreModel(
                core=row.core,
                version=row.version or "",
                outbounds_template=((self.builtin or {}).get(client_override_key(row.core.value), "") if self.is_builtin else (row.builtin_outbounds_template or "")),
                slug=row.slug or f"client-{row.core.value}",
                is_builtin=bool(row.is_builtin),
                override=is_field_overridden(self, client_override_key(row.core.value)),
            )
            for row in self.client_cores
        ]
        blocked = self.blocked_parent_enables()
        stored_enable = bool(self._enable)
        child = Child.by_id(self.child_id) if self.child_id is not None else None
        return CustomProxyModel(
            id=self.id,
            child_id=self.child_id,
            child_unique_id=child.unique_id if child else "",
            name=self.name,
            slug=self.slug,
            enable=stored_enable,
            effective_enable=stored_enable and not blocked,
            blocked_by=[BlockedByModel(key=b["key"], label=b["label"]) for b in blocked],
            mode=self.mode,
            proto=self.proto,
            transport=self.transport,
            tls_layer=self.tls_layer,
            l7_reverse_proto=self.l7_reverse_proto,
            download_tls_layer=self.download_tls_layer,
            download_domain_modes=list(self.download_domain_modes or []),
            categories=self.categories or [],
            domain_modes=list(self.domain_modes or []),
            custom_path=self.custom_path or "",
            server_config=CustomProxyServerConfigModel(
                core=self.server_core,
                inbound_template=self.effective_server_config_text(),
                inbound_tcp_ports=list(self.server_inbound_tcp_ports or []),
                inbound_udp_ports=list(self.server_inbound_udp_ports or []),
                tcp_udp=self.server_inbound_tcp_udp or InboundTcpUdp.both,
                download_tcp_udp=self.server_inbound_download_tcp_udp,
            ),
            client_config=CustomProxyClientConfigModel(core_configs=[row.to_model() for row in self.client_cores]),
            builtin=builtin_payload(self) if self.is_builtin else {},
            builtin_overrides=overrides_payload(self) if self.is_builtin else {},
            builtin_server_config=(self.builtin or {}).get("server_config") or self.builtin_server_config or "",
            builtin_client_config=CustomProxyClientConfigModel(core_configs=builtin_client_configs),
            server_override=bool((self.builtin_overrides or {}).get("server_config")),
            client_override=any((self.builtin_overrides or {}).get(client_override_key(row.core.value)) for row in self.client_cores),
            sort_order=self.sort_order or 0,
            is_builtin=bool(self.is_builtin),
            is_common_proxy=bool(self.is_common_proxy),
            client_cores=[row.core.value for row in self.client_cores if row.core],
            server_core=self.server_core,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.to_model().to_dict()

    @classmethod
    def add_or_update(cls, child_id: int = 0, commit: bool = True, **data) -> CustomProxy:
        from hiddifypanel.models.external_model.proxy_v3 import CustomProxyModel

        return cls.upsert(CustomProxyModel.coerce(data), child_id=child_id, commit=commit)

    @classmethod
    def upsert(cls, data: CustomProxyModel, *, child_id: int = 0, commit: bool = True) -> CustomProxy:
        dbproxy = None
        if data.id:
            dbproxy = cls.query.filter(cls.id == data.id, cls.child_id == child_id).first()
            if not dbproxy:
                raise ValueError(f"Custom proxy id={data.id} not found")
        if not dbproxy and data.slug:
            dbproxy = cls.query.filter(cls.slug == data.slug, cls.child_id == child_id).first()
        if not dbproxy:
            if not data.has("name"):
                raise ValueError("name is required")
            if not data.has("mode"):
                raise ValueError("mode is required")
            dbproxy = cls()
            dbproxy.child_id = child_id
            dbproxy.is_builtin = data.is_builtin
            dbproxy.server_override = data.server_override
            dbproxy.is_common_proxy = data.is_common_proxy
            db.session.add(dbproxy)

        if dbproxy.is_builtin:
            cls._upsert_builtin(dbproxy, data)
        else:
            cls._upsert_custom(dbproxy, data)
        validate_naive_tls_layer(dbproxy.proto, dbproxy.tls_layer)
        if commit:
            db.session.commit()
        return dbproxy

    @classmethod
    def _upsert_builtin(cls, dbproxy: CustomProxy, data: CustomProxyModel) -> None:
        """Built-ins only take fields the admin explicitly overrode; the rest track the catalog."""
        from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import apply_custom_proxy_general
        from hiddifypanel.proxy_v3.template_catalog.custom_proxy_builtin import (
            GENERAL_OVERRIDE_FIELDS,
            set_field_override,
        )

        body = data.provided()
        if data.has("slug"):
            new_slug = (data.slug or "").strip()
            if dbproxy.slug and new_slug and dbproxy.slug != new_slug:
                raise ValueError("Built-in proxy slug cannot be changed")
            if new_slug:
                dbproxy.slug = new_slug
        if not dbproxy.slug:
            raise ValueError("slug is required")
        if data.mode is not None:
            dbproxy.mode = data.mode
        elif not dbproxy.mode:
            raise ValueError("mode is required")
        if data.proto is not None:
            dbproxy.proto = data.proto
        elif not dbproxy.proto:
            dbproxy.proto = infer_proto_from_categories(data.categories or dbproxy.categories)
        if data.transport is not None:
            dbproxy.transport = data.transport

        if data.name is not None:
            dbproxy.name = data.name
        if data.has("enable"):
            dbproxy.enable = bool(data.enable)
        if data.has("is_common_proxy"):
            dbproxy.is_common_proxy = data.is_common_proxy
        if data.has("categories"):
            dbproxy.categories = list(data.categories or [])
        if data.has("builtin_overrides"):
            incoming = data.builtin_overrides or {}
            # Replace override set: keys omitted from the data are cleared so revert sticks.
            existing = set((dbproxy.builtin_overrides or {}).keys())
            for key in existing | set(incoming.keys()):
                set_field_override(dbproxy, key, incoming.get(key, False))
        if data.has("server_override"):
            set_field_override(dbproxy, "server_config", data.server_override)
        if data.l7_reverse_proto is not None:
            dbproxy.l7_reverse_proto = data.l7_reverse_proto
        _apply_download_xhttp_fields(dbproxy, body)
        if data.tls_layer is not None:
            dbproxy.tls_layer = data.tls_layer
        apply_server = bool(data.override_requested("server_config") or data.server_override or dbproxy.server_override or dbproxy.id is None)
        if data.server_config is not None and apply_server:
            cls._apply_server_config(dbproxy, data)
        if data.client_config is not None and dbproxy.id is not None:
            cls._sync_builtin_client_overrides(dbproxy, data.client_config)
        general_keys = tuple(GENERAL_OVERRIDE_FIELDS)
        if any(data.has(k) for k in general_keys):
            apply_custom_proxy_general(dbproxy, body)
        for field in general_keys:
            if data.has(field) and data.override_requested(field):
                setattr(dbproxy, field, getattr(data, field))
        if data.has("domain_modes"):
            _apply_domain_modes(dbproxy, list(data.domain_modes or []))
        elif data.has("mode"):
            _apply_domain_modes(dbproxy, None)

    @classmethod
    def _upsert_custom(cls, dbproxy: CustomProxy, data: CustomProxyModel) -> None:
        if data.name is not None:
            dbproxy.name = data.name
        if data.slug is not None:
            dbproxy.slug = data.slug
        elif not dbproxy.slug:
            dbproxy.slug = proxy_slug(dbproxy.name)
        if data.has("enable"):
            dbproxy.enable = bool(data.enable)
        if data.mode is not None:
            dbproxy.mode = data.mode
            if not data.has("domain_modes"):
                _apply_domain_modes(dbproxy, None)
        if data.proto is not None:
            dbproxy.proto = data.proto
        elif not dbproxy.proto:
            dbproxy.proto = infer_proto_from_categories(data.categories or dbproxy.categories)
        if data.transport is not None:
            dbproxy.transport = data.transport

        if data.tls_layer is not None:
            dbproxy.tls_layer = data.tls_layer
        if data.l7_reverse_proto is not None:
            dbproxy.l7_reverse_proto = data.l7_reverse_proto
        _apply_download_xhttp_fields(dbproxy, data.provided())
        if data.has("categories"):
            dbproxy.categories = list(data.categories or [])
        if data.has("domain_modes"):
            _apply_domain_modes(dbproxy, list(data.domain_modes or []))
        if data.has("custom_path"):
            dbproxy.custom_path = normalize_custom_path(data.custom_path)
        if data.server_config is not None:
            cls._apply_server_config(dbproxy, data)
        if data.client_config is not None:
            core_configs = data.client_config.core_configs or []
            if not core_configs:
                raise ValueError("client_config.core_configs must contain at least one client core")
            dbproxy.client_cores.clear()
            if dbproxy.id is not None:
                # Delete the old rows before re-inserting the same (core, version) keys.
                db.session.flush()
            for item in core_configs:
                dbproxy.client_cores.append(
                    CustomProxyClientCore(
                        core=item.core,
                        version=item.version,
                        slug=item.default_slug,
                        is_builtin=item.is_builtin,
                        outbounds_template=item.template,
                    )
                )
        if data.sort_order is not None:
            dbproxy.sort_order = data.sort_order

        _validate_required_server_ports(dbproxy)

    @staticmethod
    def _apply_server_config(dbproxy: CustomProxy, data: CustomProxyModel) -> None:
        server = data.server_config
        assert server is not None
        if server.core is not None:
            dbproxy.server_core = server.core
        if server.has("inbound_template"):
            dbproxy.server_config = server.inbound_template or ""
        body = server.provided()
        _apply_server_ports(dbproxy, body)
        _apply_server_tcp_udp(dbproxy, body)

    @classmethod
    def bulk_register(cls, proxies, commit: bool = True, force_child_unique_id: str | None = None) -> None:
        from hiddifypanel.models.external_model.base import as_row
        from hiddifypanel.models.external_model.proxy_v3 import CustomProxyModel
        from hiddifypanel.panel import hiddify

        for proxy in proxies:
            row = as_row(proxy)
            child_id = hiddify.child_id_from_row(row, force_child_unique_id)
            # Match by slug on this child; drop cross-DB ids and computed fields.
            data = {k: v for k, v in row.items() if k not in {"id", "child_id", "child_unique_id", "effective_enable", "blocked_by", "client_cores"}}
            existing = cls.query.filter(cls.slug == data.get("slug"), cls.child_id == child_id).first()
            if existing:
                data["id"] = existing.id
            try:
                cls.upsert(CustomProxyModel.coerce(data), child_id=child_id, commit=False)
            except ValueError:
                # Skip incomplete / incompatible legacy rows rather than aborting restore.
                continue
        if commit:
            db.session.commit()

    @classmethod
    def _sync_builtin_client_overrides(cls, dbproxy: CustomProxy, client_config: CustomProxyClientConfigModel) -> None:
        from hiddifypanel.proxy_v3.template_catalog.custom_proxy_builtin import client_override_key, set_field_override

        for item in client_config.core_configs or []:
            core = item.core
            key = client_override_key(core.value)
            row = next((r for r in dbproxy.client_cores if r.core == core), None)
            if not row:
                row = CustomProxyClientCore(
                    core=core,
                    version=item.version,
                    slug=item.default_slug,
                    is_builtin=item.is_builtin,
                )
                dbproxy.client_cores.append(row)
            if item.has("override"):
                set_field_override(dbproxy, key, bool(item.override))
            elif item.outbounds_template is not None or item.link_template is not None:
                set_field_override(dbproxy, key, True)
            if item.has("outbounds_template"):
                row.outbounds_template = item.outbounds_template or ""
            elif item.has("link_template"):
                row.outbounds_template = item.link_template or ""
            if item.has("version"):
                row.version = item.version
            if item.has("slug") and item.slug:
                row.slug = str(item.slug)

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


_TLS_LAYER_ALIASES = {
    "tcp_tls": "tls",
    "tcp-tls": "tls",
    "tls_h2_h1": "tls",
    "tls-h2-h1": "tls",
    "tls-h1": "tls_h1",
    "tls-h2": "tls_h2",
    "quic+tcp_tls": "quic_tcp_tls",
    "quic+tcp-tls": "quic_tcp_tls",
    "quic-tcp-tls": "quic_tcp_tls",
}


def _parse_tls_layer(value: Any) -> TlsLayer | None:
    if value is None or value == "":
        return None
    if isinstance(value, TlsLayer):
        return value
    raw = str(value).strip().lower()
    raw = _TLS_LAYER_ALIASES.get(raw, raw)
    try:
        return TlsLayer(raw)
    except ValueError as exc:
        allowed = ", ".join(m.value for m in TlsLayer)
        raise ValueError(f"Invalid tls_layer {value!r}. Must be one of: {allowed}") from exc


def validate_tls_layer_domain_modes(
    tls_layer: TlsLayer | None,
    domain_modes: list[str] | None,
    transport: CustomProxyTransport | str | None = None,
) -> None:
    if not domain_modes_use_reality(domain_modes):
        return
    layer = tls_layer.value if isinstance(tls_layer, TlsLayer) else tls_layer
    transport_key = transport.value if isinstance(transport, CustomProxyTransport) else transport
    if not transport_tls_supports_reality(transport_key, layer):
        raise ValueError("REALITY is only supported on gRPC, xHTTP H2, and raw HTTP with TLS")


def validate_naive_tls_layer(proto: ProxyProto | str | None, tls_layer: TlsLayer | None) -> None:
    if proto is None or proto == "":
        return
    parsed = proto if isinstance(proto, ProxyProto) else _parse_proto(proto)
    if parsed == ProxyProto.naive and tls_layer == TlsLayer.http:
        raise ValueError("Naive cannot use HTTP TLS layer")


def uses_xhttp_download_settings(proxy: CustomProxy) -> bool:
    return proxy.transport == CustomProxyTransport.xhttp


def xhttp_upload_is_quic(categories: list[str] | None) -> bool:
    return any(str(category).lower() == "up:quic" for category in (categories or []))


def xhttp_download_is_quic(categories: list[str] | None) -> bool:
    return any(str(category).lower() == "down:quic" for category in (categories or []))


def xhttp_alpn_is_quic(alpn: str | None) -> bool:
    return bool(alpn and str(alpn).lower() in {"tls_h3", "h3"})


def effective_server_tcp_udp(proxy: CustomProxy) -> InboundTcpUdp:
    return proxy.effective_server_tcp_udp()


def validate_xhttp_domain_modes(proxy: CustomProxy) -> None:
    if not uses_xhttp_download_settings(proxy):
        return
    categories = list(proxy.categories or [])
    if xhttp_upload_is_quic(categories) and domain_modes_use_reality(list(proxy.domain_modes or [])):
        raise ValueError("REALITY is incompatible with QUIC upload in xhttp")
    if xhttp_download_is_quic(categories) and domain_modes_use_reality(list(proxy.download_domain_modes or [])):
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
    dbproxy.download_domain_modes = normalize_domain_modes(domain_modes, default=("direct-valid",))
    validate_download_xhttp_fields(dbproxy)


def validate_download_xhttp_fields(proxy: CustomProxy) -> None:
    if not uses_xhttp_download_settings(proxy):
        return
    modes = normalize_domain_modes(proxy.download_domain_modes)
    invalid = [m for m in (proxy.download_domain_modes or []) if str(m).strip().lower() not in ALLOWED_DOMAIN_MODES and str(m).strip().lower() not in {"direct", "relay", "fake", "reality", "special"}]
    if invalid:
        raise ValueError(f"Invalid download_domain_modes: {invalid!r}")
    proxy.download_domain_modes = modes or ["direct-valid"]
    download_layer = proxy.download_tls_layer.value if proxy.download_tls_layer else None
    if domain_modes_use_reality(list(proxy.download_domain_modes or [])) and not transport_tls_supports_reality("xhttp", download_layer):
        raise ValueError("REALITY download is only supported on xHTTP H2")


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


def _apply_server_tcp_udp(dbproxy: CustomProxy, data: dict[str, Any]) -> None:
    if dbproxy.is_builtin:
        return
    if uses_xhttp_download_settings(dbproxy):
        # Upload uses server_inbound_tcp_udp; accept legacy upload_tcp_udp as alias.
        if "tcp_udp" in data:
            dbproxy.server_inbound_tcp_udp = _parse_tcp_udp(data.get("tcp_udp"))
        elif "upload_tcp_udp" in data:
            dbproxy.server_inbound_tcp_udp = _parse_tcp_udp(data.get("upload_tcp_udp"))
        if "download_tcp_udp" in data:
            dbproxy.server_inbound_download_tcp_udp = _parse_tcp_udp(data.get("download_tcp_udp"))
        return
    dbproxy.server_inbound_download_tcp_udp = None
    if "tcp_udp" in data:
        dbproxy.server_inbound_tcp_udp = _parse_tcp_udp(data.get("tcp_udp"))


def _apply_server_ports(dbproxy: CustomProxy, data: dict[str, Any]) -> None:
    mode = dbproxy.mode
    if mode_uses_gateway_port(mode) or mode_uses_auto_ports(mode):
        dbproxy.server_inbound_tcp_ports = []
        dbproxy.server_inbound_udp_ports = []
        return
    if not any(key in data for key in ("inbound_tcp_ports", "inbound_udp_ports", "inbound_port")):
        return
    tcp_ports = normalize_port_list(data.get("inbound_tcp_ports"))
    if not tcp_ports and data.get("inbound_port") is not None:
        tcp_ports = normalize_port_list(data.get("inbound_port"))
    dbproxy.server_inbound_tcp_ports = tcp_ports
    if "inbound_udp_ports" in data:
        dbproxy.server_inbound_udp_ports = normalize_port_list(data.get("inbound_udp_ports"))
    else:
        dbproxy.server_inbound_udp_ports = list(tcp_ports)


def _apply_domain_modes(dbproxy: CustomProxy, domain_modes: list[str] | None) -> None:
    fallback = default_domain_modes_for_mode(dbproxy.mode)
    if domain_modes is None:
        dbproxy.domain_modes = list(fallback)
    else:
        dbproxy.domain_modes = normalize_domain_modes(domain_modes, default=fallback)
    validate_tls_layer_domain_modes(dbproxy.tls_layer, dbproxy.domain_modes, dbproxy.transport)
    validate_xhttp_domain_modes(dbproxy)


def proxy_slug(name: str) -> str:
    return slugify(name, lowercase=True) or "custom-proxy"


def _validate_required_server_ports(dbproxy: CustomProxy) -> None:
    if dbproxy.is_builtin:
        return
    mode = dbproxy.mode
    if mode_uses_gateway_port(mode) or mode_uses_auto_ports(mode):
        return
    if mode_requires_static_ports(mode) and not (
        normalize_port_list(dbproxy.server_inbound_tcp_ports) or normalize_port_list(dbproxy.server_inbound_udp_ports)
    ):
        raise ValueError("At least one inbound TCP or UDP port is required for this mode")
