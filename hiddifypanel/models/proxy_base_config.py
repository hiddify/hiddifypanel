from __future__ import annotations

from enum import auto
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from strenum import StrEnum

from hiddifypanel.database import db
from hiddifypanel.proxy_v3.template_catalog.base_configs import default_base_content as _catalog_base_content

if TYPE_CHECKING:
    from hiddifypanel.models.external_model.proxy_v3 import ProxyBaseConfigModel


class BaseConfigSide(StrEnum):
    server = auto()
    client = auto()


BASE_CONFIG_MATRIX: dict[str, list[str]] = {
    BaseConfigSide.server.value: ['xray', 'hiddify-core', 'haproxy', 'nginx', 'rust-rpxy-l4', 'dns_proxy'],
    BaseConfigSide.client.value: ['xray', 'singbox', 'hiddify-core', 'sublink', 'clash'],
}


def default_base_content(side: str, core: str) -> str:
    """Builtin base shell from proxy_templates/{core}/{side}/base.j2 only."""
    return _catalog_base_content(side, core)


class ProxyBaseConfig(db.Model):  # type: ignore
    __tablename__ = 'proxy_base_config'
    __table_args__ = (
        UniqueConstraint('child_id', 'side', 'core', 'version', name='uq_proxy_base_config_child_side_core_ver'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), default=0)
    side: Mapped[BaseConfigSide] = mapped_column(Enum(BaseConfigSide))
    core: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(50), default="")
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    builtin_content: Mapped[str] = mapped_column(Text, default="")
    builtin_override: Mapped[bool] = mapped_column(default=False)
    is_builtin: Mapped[bool] = mapped_column(default=False)
    enable: Mapped[bool] = mapped_column(default=True)

    def effective_content(self) -> str:
        from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import effective_base_config_content
        return effective_base_config_content(self)

    def to_model(self) -> ProxyBaseConfigModel:
        from hiddifypanel.models.external_model.proxy_v3 import ProxyBaseConfigModel

        return ProxyBaseConfigModel(
            id=self.id,
            child_id=self.child_id,
            side=self.side,
            core=self.core,
            version=self.version or '',
            name=self.name,
            description=self.description or '',
            content=self.effective_content(),
            builtin_content=self.builtin_content or '',
            builtin_override=bool(self.builtin_override),
            is_builtin=bool(self.is_builtin),
            enable=bool(self.enable),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.to_model().to_dict()

    @classmethod
    def add_or_update(cls, child_id: int = 0, commit: bool = True, **data) -> ProxyBaseConfig:
        from hiddifypanel.models.external_model.proxy_v3 import ProxyBaseConfigModel

        return cls.upsert(ProxyBaseConfigModel.coerce(data), child_id=child_id, commit=commit)

    @classmethod
    def upsert(cls, data: ProxyBaseConfigModel, *, child_id: int = 0, commit: bool = True) -> ProxyBaseConfig:
        row = None
        if data.id:
            row = cls.query.filter(cls.id == data.id, cls.child_id == child_id).first()
        if not row:
            if data.side is None:
                raise ValueError('side is required')
            if not data.core:
                raise ValueError('core is required')
            row = cls.query.filter(
                cls.child_id == child_id,
                cls.side == data.side.value,
                cls.core == data.core,
                cls.version == data.clean_version,
            ).first()
        if not row:
            row = cls()
            row.child_id = child_id
            row.is_builtin = data.is_builtin
            db.session.add(row)

        if row.is_builtin:
            from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import apply_builtin_override_base_config
            if data.name is not None:
                row.name = data.name
            if data.has('enable'):
                row.enable = True
            if data.has('description'):
                row.description = data.description or ''
            if data.has('content'):
                new_content = data.content or ''
                if new_content != (row.builtin_content or ''):
                    apply_builtin_override_base_config(row, override=True)
                elif data.has('builtin_override'):
                    apply_builtin_override_base_config(row, override=data.builtin_override)
                if row.builtin_override:
                    row.content = new_content
            elif data.has('builtin_override'):
                apply_builtin_override_base_config(row, override=data.builtin_override)
            if commit:
                db.session.commit()
            return row

        if data.side is not None:
            row.side = data.side
        if data.core is not None:
            row.core = data.core
        row.version = (data.clean_version or row.version or '').strip()
        if data.name is not None:
            row.name = data.name
        row.description = (data.description if data.has('description') else row.description) or ''
        row.content = (data.content if data.has('content') else row.content) or ''
        if data.has('enable'):
            row.enable = bool(data.enable)

        if commit:
            db.session.commit()
        return row

    def duplicate(self, child_id: int | None = None) -> ProxyBaseConfig:
        child_id = child_id if child_id is not None else self.child_id
        base_version = self.version
        i = 1
        version = f'{base_version}-{i}'
        while ProxyBaseConfig.query.filter(
            ProxyBaseConfig.child_id == child_id,
            ProxyBaseConfig.side == self.side,
            ProxyBaseConfig.core == self.core,
            ProxyBaseConfig.version == version,
        ).first():
            i += 1
            version = f'{base_version}-{i}'
        return ProxyBaseConfig.add_or_update(
            child_id=child_id,
            side=self.side,
            core=self.core,
            version=version,
            name=f'{self.name} (copy)',
            description=self.description,
            content=self.effective_content(),
            enable=self.enable,
            is_builtin=False,
            builtin_override=False,
            builtin_content='',
        )


BUILTIN_BASE_CONFIGS: list[dict[str, Any]] = [
    {
        'side': BaseConfigSide.client,
        'core': 'xray',
        'version': '1.0.0',
        'name': 'Client Xray Base',
        'description': 'Full xray client config shell (logs, routing, inbounds, outbounds)',
    },
    {
        'side': BaseConfigSide.client,
        'core': 'singbox',
        'version': '1.0.0',
        'name': 'Client Sing-box Base',
        'description': 'Full sing-box client config shell',
    },
    {
        'side': BaseConfigSide.client,
        'core': 'hiddify-core',
        'version': '1.0.0',
        'name': 'Client Hiddify-core Base',
        'description': 'Full hiddify-core client config shell',
    },
    {
        'side': BaseConfigSide.client,
        'core': 'sublink',
        'version': '1.0.0',
        'name': 'Client Sublink Base',
        'description': 'Sublink bundle base structure',
    },
    {
        'side': BaseConfigSide.server,
        'core': 'xray',
        'version': '1.0.0',
        'name': 'Server Xray Base',
        'description': 'Full xray server config shell',
    },
    {
        'side': BaseConfigSide.server,
        'core': 'hiddify-core',
        'version': '1.0.0',
        'name': 'Server Hiddify-core Base',
        'description': 'Full hiddify-core server config shell',
    },
    {
        'side': BaseConfigSide.server,
        'core': 'haproxy',
        'version': '1.0.0',
        'name': 'Server HAProxy Base',
        'description': 'Full HAProxy gateway config (frontends, backends, routing)',
    },
    {
        'side': BaseConfigSide.server,
        'core': 'nginx',
        'version': '1.0.0',
        'name': 'Server Nginx Base',
        'description': 'Nginx HTTP dispatcher (panel, decoy, gRPC/WS/xHTTP paths, speedtest)',
    },
    {
        'side': BaseConfigSide.server,
        'core': 'rust-rpxy-l4',
        'version': '1.0.0',
        'name': 'Server rust-rpxy-l4 Base',
        'description': 'L4 TLS/QUIC SNI gateway multiplexer (domains_sni_gateway, Telegram, FakeTLS, ShadowTLS)',
    },
    {
        'side': BaseConfigSide.server,
        'core': 'dns_proxy',
        'version': '1.0.0',
        'name': 'Server DNSTM Base',
        'description': 'DNSTM DNS router config (tunnels for DNS-gateway proxies)',
    },
]


def seed_proxy_base_configs(child_id: int = 0, *, refresh_builtin: bool = False) -> None:
    from hiddifypanel.proxy_v3.builtin_proxy_sync.orchestrator import sync_base_configs

    sync_base_configs(child_id, refresh_builtin=refresh_builtin)
