from __future__ import annotations

import functools
from typing import Any

from loguru import logger

_HCONFIG_BLOCKED = frozenset(
    {
        "admin_secret",
        # "proxy_path_admin",
    }
)


@functools.lru_cache(maxsize=4)
def _warn_vless_encryption_off(error: str) -> None:
    logger.warning(f"VLESS encryption is off in the configs: the {error} setting is invalid")


class HConfigVar:
    """Panel settings with sensitive keys filtered for templates."""

    def __init__(self, raw: dict[str, int | str | bool] | None = None, *, server_side: bool = False):
        self._server_side = server_side
        self._values: dict[str, Any] = {}
        for key, value in (raw or {}).items():
            name = getattr(key, "name", None) or str(key)
            self._values[name] = value
        self._vless_encryption_safe()

    def _vless_encryption_safe(self) -> None:
        """A VLESS encryption Xray would refuse (it then stays "activating") or a pair the clients can't use: off."""
        enc, dec = self._values.get("vless_encryption") or "", self._values.get("vless_decryption") or ""
        if not enc and not dec:
            return
        from hiddifypanel.hutils.crypto import vless_encryption_error, vless_encryption_pair

        if error := vless_encryption_error(enc, dec):
            _warn_vless_encryption_off(error)
        self._values["vless_encryption"], self._values["vless_decryption"] = vless_encryption_pair(enc, dec)

    @property
    def ipv6_enabled(self) -> bool:
        """Listen on IPv6 only when the admin did not choose IPv4 only and the kernel has IPv6."""
        from hiddifypanel.hutils.network.net import kernel_ipv6_available

        return not self._values.get("only_ipv4") and kernel_ipv6_available()

    def __getitem__(self, key: Any) -> Any:
        name = self._alias_key(getattr(key, "name", None) or str(key))
        if not self._visible(name):
            return None
        return self._values.get(name)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        key = self._alias_key(name)
        if not self._visible(key):
            return None
        return self._values.get(key)

    def get(self, key: Any, default: Any = None) -> Any:
        name = self._alias_key(getattr(key, "name", None) or str(key))
        if not self._visible(name):
            return default
        return self._values.get(name, default)

    def __call__(self, key: Any, default: Any = None) -> Any:
        return self.get(key, default)

    @staticmethod
    def _alias_key(name: str) -> str:
        return {"flow_vless": "vless_flow"}.get(name, name)

    def _visible(self, name: str) -> bool:
        if name in _HCONFIG_BLOCKED:
            if self._server_side:
                return name in {
                    "admin_secret",
                    "reality_private_key",
                    "ssh_host_rsa_pk",
                    "ssh_host_ecdsa_pk",
                    "ssh_host_ed25519_pk",
                }
            return False
        return True
