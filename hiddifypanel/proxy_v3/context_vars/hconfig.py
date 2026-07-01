from __future__ import annotations

from typing import Any

_HCONFIG_BLOCKED = frozenset({
    'admin_secret',
    'proxy_path_admin',
})


class HConfigVar:
    """Panel settings with sensitive keys filtered for templates."""

    def __init__(self, raw: dict[str, Any] | None = None, *, server_side: bool = False):
        self._server_side = server_side
        self._values: dict[str, Any] = {}
        for key, value in (raw or {}).items():
            name = getattr(key, 'name', None) or str(key)
            self._values[name] = value

    def __getitem__(self, key: Any) -> Any:
        name = self._alias_key(getattr(key, 'name', None) or str(key))
        if not self._visible(name):
            return None
        return self._values.get(name)

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            raise AttributeError(name)
        key = self._alias_key(name)
        if not self._visible(key):
            return None
        return self._values.get(key)

    def get(self, key: Any, default: Any = None) -> Any:
        name = self._alias_key(getattr(key, 'name', None) or str(key))
        if not self._visible(name):
            return default
        return self._values.get(name, default)

    def __call__(self, key: Any, default: Any = None) -> Any:
        return self.get(key, default)

    @staticmethod
    def _alias_key(name: str) -> str:
        return {'flow_vless': 'vless_flow'}.get(name, name)

    def _visible(self, name: str) -> bool:
        if name in _HCONFIG_BLOCKED:
            if self._server_side:
                return name in {
                    'reality_private_key',
                    'ssh_host_rsa_pk',
                    'ssh_host_ecdsa_pk',
                    'ssh_host_ed25519_pk',
                }
            return False
        return True
