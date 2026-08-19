from __future__ import annotations

import copy
from enum import auto
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON
from strenum import StrEnum

from hiddifypanel.database import db

from hiddifypanel.proxy_v3.template_catalog.base_configs import default_base_content as _catalog_base_content

_PANEL_TEMPLATES = Path(__file__).resolve().parent.parent / 'panel' / 'user' / 'templates'


class BaseConfigSide(StrEnum):
    server = auto()
    client = auto()


BASE_CONFIG_MATRIX: dict[str, list[str]] = {
    BaseConfigSide.server.value: ['xray', 'hiddify-core', 'haproxy', 'nginx', 'rust-rpxy-l4'],
    BaseConfigSide.client.value: ['xray', 'singbox', 'hiddify-core', 'sublink', 'clash'],
}


def _load_panel_template(name: str, fallback: str = '{}') -> str:
    path = _PANEL_TEMPLATES / name
    if path.is_file():
        return path.read_text(encoding='utf-8')
    return fallback


DEFAULT_SERVER_XRAY_BASE = _load_panel_template(
    'base_xray_config.json.j2',
    '{\n  "log": {"loglevel": "warning"},\n  "inbounds": [],\n  "outbounds": [],\n  "routing": {"rules": []}\n}',
)

DEFAULT_CLIENT_XRAY_BASE = DEFAULT_SERVER_XRAY_BASE

DEFAULT_CLIENT_SINGBOX_BASE = _load_panel_template(
    'base_singbox_config.json.j2',
    '{\n  "outbounds": [],\n  "route": {"rules": []}\n}',
)

DEFAULT_SERVER_HIDDIFY_BASE = (
    '{\n'
    '  "log": {"level": "warn"},\n'
    '  "inbounds": [],\n'
    '  "outbounds": [{"type": "direct", "tag": "direct"}],\n'
    '  "route": {"rules": []}\n'
    '}'
)

DEFAULT_CLIENT_HIDDIFY_BASE = DEFAULT_CLIENT_SINGBOX_BASE

DEFAULT_CLIENT_SUBLINK_BASE = _catalog_base_content(BaseConfigSide.client.value, 'sublink')

def default_base_content(side: str, core: str) -> str:
    try:
        return _catalog_base_content(side, core)
    except FileNotFoundError:
        pass
    if side == BaseConfigSide.server.value:
        if core == 'xray':
            return copy.deepcopy(DEFAULT_SERVER_XRAY_BASE)
        if core == 'hiddify-core':
            return copy.deepcopy(DEFAULT_SERVER_HIDDIFY_BASE)
        if core == 'haproxy':
            return ''
    if side == BaseConfigSide.client.value:
        if core == 'xray':
            return copy.deepcopy(DEFAULT_CLIENT_XRAY_BASE)
        if core == 'singbox':
            return copy.deepcopy(DEFAULT_CLIENT_SINGBOX_BASE)
        if core == 'hiddify-core':
            return copy.deepcopy(DEFAULT_CLIENT_HIDDIFY_BASE)
        if core == 'sublink':
            return copy.deepcopy(DEFAULT_CLIENT_SUBLINK_BASE)
    return '{}'


class ProxyBaseConfig(db.Model):  # type: ignore
    __tablename__ = 'proxy_base_config'
    __table_args__ = (
        UniqueConstraint('child_id', 'side', 'core', 'version', name='uq_proxy_base_config_child_side_core_ver'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey('child.id'), default=0, nullable=False)
    side = Column(Enum(BaseConfigSide), nullable=False)
    core = Column(String(50), nullable=False)
    version = Column(String(50), nullable=False, default='')
    name = Column(String(200), nullable=False)
    description = Column(String(500), default='')
    content = Column(Text, nullable=False, default='')
    builtin_content = Column(Text, nullable=False, default='')
    builtin_override = Column(Boolean, default=False, nullable=False)
    is_builtin = Column(Boolean, default=False, nullable=False)
    enable = Column(Boolean, default=True, nullable=False)

    def effective_content(self) -> str:
        from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import effective_base_config_content
        return effective_base_config_content(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'child_id': self.child_id,
            'side': self.side.value if self.side else None,
            'core': self.core,
            'version': self.version or '',
            'name': self.name,
            'description': self.description or '',
            'content': self.effective_content(),
            'builtin_content': self.builtin_content or '',
            'builtin_override': bool(self.builtin_override),
            'is_builtin': bool(self.is_builtin),
            'enable': bool(self.enable),
        }

    @classmethod
    def add_or_update(cls, child_id: int = 0, commit: bool = True, **data) -> 'ProxyBaseConfig':
        row = None
        row_id = data.get('id')
        if row_id:
            row = cls.query.filter(cls.id == row_id, cls.child_id == child_id).first()
        if not row:
            side = data['side']
            side_val = side.value if isinstance(side, BaseConfigSide) else side
            core = data['core']
            version = (data.get('version') or '').strip() or ''
            row = cls.query.filter(
                cls.child_id == child_id,
                cls.side == side_val,
                cls.core == core,
                cls.version == version,
            ).first()
        if not row:
            row = cls()
            row.child_id = child_id
            row.is_builtin = bool(data.get('is_builtin', False))
            db.session.add(row)

        if row.is_builtin:
            from hiddifypanel.proxy_v3.builtin_proxy_sync.sync import apply_builtin_override_base_config
            if 'name' in data:
                row.name = data['name']
            if 'enable' in data:
                row.enable = True
            if 'description' in data:
                row.description = data.get('description') or ''
            if 'content' in data:
                new_content = data.get('content') or ''
                if new_content != (row.builtin_content or ''):
                    apply_builtin_override_base_config(row, override=True)
                elif 'builtin_override' in data:
                    apply_builtin_override_base_config(row, override=bool(data['builtin_override']))
                if row.builtin_override:
                    row.content = new_content
            elif 'builtin_override' in data:
                apply_builtin_override_base_config(row, override=bool(data['builtin_override']))
            if commit:
                db.session.commit()
            return row

        side = data.get('side', row.side)
        row.side = side if isinstance(side, BaseConfigSide) else BaseConfigSide(side)
        row.core = data.get('core', row.core)
        row.version = (data.get('version') or row.version or '').strip()
        row.name = data.get('name', row.name)
        row.description = data.get('description', row.description) or ''
        row.content = data.get('content', row.content) or ''
        if 'enable' in data:
            row.enable = bool(data['enable'])

        if commit:
            db.session.commit()
        return row

    def duplicate(self, child_id: int | None = None) -> 'ProxyBaseConfig':
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
]


def seed_proxy_base_configs(child_id: int = 0, *, refresh_builtin: bool = False) -> None:
    from hiddifypanel.proxy_v3.builtin_proxy_sync.orchestrator import sync_base_configs

    sync_base_configs(child_id, refresh_builtin=refresh_builtin)
