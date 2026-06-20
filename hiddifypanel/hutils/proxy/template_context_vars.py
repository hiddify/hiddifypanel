from __future__ import annotations

import hashlib
import re
import subprocess
from base64 import b64encode
from pathlib import Path
from typing import Any

from hiddifypanel.models import ConfigEnum
from hiddifypanel.models.custom_proxy import normalize_custom_path

from .alpn_helpers import alpn_list_for_tag, is_tls_alpn_tag

_SSL_ROOT = Path("/opt/hiddify-manager/ssl")

_HCONFIG_BLOCKED = frozenset(
    {
        "admin_secret",
        "proxy_path_admin",
    }
)

_OS_NORMALIZE = {
    "android": "android",
    "ios": "ios",
    "windows": "windows",
    "linux": "linux",
    "mac os x": "macos",
    "macos": "macos",
}

_APP_GROUP_MAP: list[tuple[str, str]] = [
    (r"(?i)(hiddify|sing-box|singbox|sfa|sfi|dart)", "singbox"),
    (r"(?i)(clash|stash|nekobox|nekoray|pharos|meta)", "clash"),
    (r"(?i)(v2ray|v2rayng|sagernet|foxray|fair|shadowrocket|v2box|loon|liberty)", "xray"),
    (r"(?i)(sub|subscription|sublink)", "sublink"),
]


def _normalize_os(family: str | None) -> str:
    if not family:
        return "linux"
    key = family.strip().lower()
    return _OS_NORMALIZE.get(key, key)


def _sha256_pin_from_pem(pem: str) -> str | None:
    if not pem:
        return None
    try:
        proc = subprocess.run(
            ["openssl", "x509", "-pubkey", "-noout"],
            input=pem,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        proc2 = subprocess.run(
            ["openssl", "pkey", "-pubin", "-outform", "der"],
            input=proc.stdout.encode(),
            capture_output=True,
            check=False,
        )
        if proc2.returncode != 0:
            return None
        return b64encode(hashlib.sha256(proc2.stdout).digest()).decode()
    except OSError:
        return None


def _resolve_ssl_material(hostname: str, child_id: int = 0, domain_id: int | None = None) -> dict[str, Any]:
    from hiddifypanel.hutils.ssl.tls_store_sync import tls_material_for_domain

    material = tls_material_for_domain(
        hostname,
        child_id=child_id,
        domain_id=domain_id,
        auto_sync=True,
    )
    if material:
        return material

    host = (hostname or "").lower().strip()
    safe = host[:64]
    cert_path = _SSL_ROOT / f"{safe}.crt"
    key_path = _SSL_ROOT / f"{safe}.crt.key"
    if not cert_path.is_file():
        certs = sorted(_SSL_ROOT.glob("*.crt"))
        if certs:
            cert_path = certs[-1]
            key_path = Path(f"{cert_path}.key")
    cert_pem = ""
    key_pem = ""
    pin: list[str] = []
    if cert_path.is_file():
        try:
            cert_pem = cert_path.read_text(encoding="utf-8")
        except OSError:
            cert_pem = ""
        digest = _sha256_pin_from_pem(cert_pem)
        if digest:
            pin = [digest]
    if key_path.is_file():
        try:
            key_pem = key_path.read_text(encoding="utf-8")
        except OSError:
            key_pem = ""
    return {
        "tls_cert_path": str(cert_path) if cert_path.is_file() else "",
        "tls_key_path": str(key_path) if key_path.is_file() else "",
        "tls_cert": cert_pem,
        "tls_key": key_pem,
        "tls_cert_lines": [ln for ln in cert_pem.splitlines() if ln.strip()],
        "tls_key_lines": [ln for ln in key_pem.splitlines() if ln.strip()],
        "tls_pinnedPeerCertSha256": pin,
        "tls_public_key_sha256": pin[0] if pin else "",
        "tls_fingerprint": pin[0] if pin else "",
        "tls_valid_cert": False,
        "tls_expires_at": None,
        "tls_issuer": "",
        "tls_auto_renew": False,
        "tls_last_renewal_error": "",
    }


class _AttrDict:
    """Read-only attribute + mapping access."""

    def __init__(self, data: dict[str, Any]):
        self._data = dict(data)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._data.get(name)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in self._data.items():
            if isinstance(value, _AttrDict):
                out[key] = value.to_dict()
            else:
                out[key] = value
        return out


class TemplateVersion:
    """Semantic version for Jinja comparisons: platform.app.version < \"1.2.3\"."""

    def __init__(self, version: str | list | tuple | None = None):
        if isinstance(version, (list, tuple)):
            parts = [str(x) for x in version if x is not None and str(x) != ""]
            version = ".".join(parts)
        self._version = str(version or "0")

    def _other_str(self, other: Any) -> str:
        if isinstance(other, TemplateVersion):
            return other._version
        return str(other)

    def _compare(self, other: Any) -> int:
        from hiddifypanel import hutils

        return hutils.utils.compare_versions(self._version, self._other_str(other))

    def __str__(self) -> str:
        return self._version

    def __repr__(self) -> str:
        return f"TemplateVersion({self._version!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (TemplateVersion, str)):
            return NotImplemented
        return self._compare(other) == 0

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, (TemplateVersion, str)):
            return NotImplemented
        return self._compare(other) != 0

    def __lt__(self, other: Any) -> bool:
        return self._compare(other) == -1

    def __le__(self, other: Any) -> bool:
        return self._compare(other) in (-1, 0)

    def __gt__(self, other: Any) -> bool:
        return self._compare(other) == 1

    def __ge__(self, other: Any) -> bool:
        return self._compare(other) in (0, 1)


class _PlatformPart:
    """Named platform facet with comparable version (platform.app.version)."""

    __slots__ = ("name", "version")

    def __init__(self, name: str, version: str | list | tuple | None = None):
        self.name = name or ""
        self.version = TemplateVersion(version)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def __str__(self) -> str:
        return self.name


class ProxyVar(_AttrDict):
    """Current proxy link fields for custom-proxy and legacy link templates."""

    def _resolve_ports(self, domain: Any = None) -> Any:
        from .custom_proxy_ports import normalize_port_list, resolve_inbound_ports

        mode = self._data.get("mode") or ""
        proxy_id = int(self._data.get("id") or 0)
        domain_id = _domain_id_from_context(domain) if domain is not None else None
        stored_tcp = normalize_port_list(self._data.get("server_inbound_tcp_ports") or self._data.get("tcp_ports"))
        stored_udp = normalize_port_list(self._data.get("server_inbound_udp_ports") or self._data.get("udp_ports"))
        return resolve_inbound_ports(
            mode,
            proxy_id,
            domain_id=domain_id,
            stored_tcp_ports=stored_tcp,
            stored_udp_ports=stored_udp,
        )

    def with_domain(self, domain: Any) -> "ProxyVar":
        resolved = self._resolve_ports(domain)
        data = dict(self._data)
        data["tcp_ports"] = list(resolved.tcp_ports)
        data["udp_ports"] = list(resolved.udp_ports)
        data["tcp_port"] = resolved.tcp_port
        data["udp_port"] = resolved.udp_port
        primary = int(resolved.tcp_port or resolved.udp_port or 0)
        if primary:
            data["port"] = primary
        return ProxyVar(data)

    def port_for_domain(self, domain: Any) -> int:
        resolved = self._resolve_ports(domain)
        return int(resolved.tcp_port or resolved.udp_port or 0)

    @property
    def tcp_port(self) -> int:
        tcp_ports = list(self._data.get('tcp_ports') or [])
        if tcp_ports:
            return int(tcp_ports[0])
        raw = self._data.get('tcp_port')
        return int(raw) if raw else 0

    @property
    def udp_port(self) -> int:
        udp_ports = list(self._data.get('udp_ports') or [])
        if udp_ports:
            return int(udp_ports[0])
        raw = self._data.get('udp_port')
        return int(raw) if raw else 0

    @property
    def tcp_port_ranges(self) -> list[int | str]:
        from .custom_proxy_ports import ports_list_to_ranges

        return ports_list_to_ranges(list(self._data.get('tcp_ports') or []))

    @property
    def udp_port_ranges(self) -> list[int | str]:
        from .custom_proxy_ports import ports_list_to_ranges

        return ports_list_to_ranges(list(self._data.get('udp_ports') or []))

    @property
    def port(self) -> int:
        from .custom_proxy_ports import mode_port_requires_domain

        mode = self._data.get('mode') or ''
        if mode_port_requires_domain(mode):
            raise AttributeError(
                f'proxy.port is not available for mode {mode!r}; use proxy.tcp_port / proxy.udp_port with domain'
            )
        return int(self._data.get('port') or self.tcp_port or self.udp_port or 0)

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            raise AttributeError(name)
        return self._data.get(name)

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, Any] | None = None,
        *,
        port: int = 0,
        path: str = "",
        public_access: bool = False,
        tag: str = "",
        server: str = "",
        domain_binding: str = "domain",
    ) -> ProxyVar:
        base = dict(data or {})
        resolved_tag = str(base.get("tag") or tag or "")
        mode = str(base.get("mode") or "")
        from .custom_proxy_ports import mode_port_requires_domain

        resolved_port = int(base.get("port") or port or 0)
        if mode_port_requires_domain(mode):
            resolved_port = 0
        resolved_path = normalize_custom_path(base.get("path") or path)
        resolved_server = str(base.get("server") or server or "")
        alpn_tag = str(base.get("alpn") or resolved_tag)
        alpns = base.get("alpns")
        if alpns is None:
            alpns = alpn_list_for_tag(alpn_tag) if is_tls_alpn_tag(alpn_tag) else []
        elif not isinstance(alpns, list):
            alpns = alpn_list_for_tag(str(alpns))
        payload = {
            "id": base.get("id"),
            "mode": mode,
            "tag": resolved_tag,
            "tcp_ports": list(base.get("tcp_ports") or ([resolved_port] if resolved_port else [])),
            "udp_ports": list(base.get("udp_ports") or ([resolved_port] if resolved_port else [])),
            "tcp_port": base.get("tcp_port", resolved_port),
            "udp_port": base.get("udp_port", resolved_port),
            "path": resolved_path,
            "server": resolved_server,
            "public_access": bool(base.get("public_access", base.get("direct_port_access", public_access))),
            "domain_binding": str(base.get("domain_binding") or domain_binding or "domain"),
            "alpn": alpn_tag,
            "alpns": alpns,
            "download_alpn": str(base.get("download_alpn") or ""),
            "download_alpn_list": list(base.get("download_alpn_list") or []),
            "tls": bool(base.get("tls", is_tls_alpn_tag(alpn_tag))),
            "l3": str(base.get("l3") or ""),
            "server_inbound_tcp_ports": base.get("server_inbound_tcp_ports"),
            "server_inbound_udp_ports": base.get("server_inbound_udp_ports"),
        }
        if not mode_port_requires_domain(mode):
            payload["port"] = resolved_port
        return cls(payload)


def _domain_id_from_context(domain: Any) -> int | None:
    if domain is None:
        return None
    if isinstance(domain, dict):
        raw = domain.get("id") or domain.get("domain_id")
    elif hasattr(domain, "_data"):
        raw = domain._data.get("id") or domain._data.get("domain_id")
    else:
        raw = getattr(domain, "id", None) or getattr(domain, "domain_id", None)
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _version_gte(info: dict[str, Any], key: str, major: int, minor: int = 0, patch: int = 0) -> bool:
    ver = info.get(key)
    if not ver:
        return False
    if isinstance(ver, str):
        parts = [int(x) for x in ver.split(".")[:3]]
    else:
        parts = [int(x) for x in list(ver)[:3]]
    while len(parts) < 3:
        parts.append(0)
    from hiddifypanel import hutils

    user_v = f"{parts[0]}.{parts[1]}.{parts[2]}"
    needed = f"{major}.{minor}.{patch}"
    return hutils.utils.compare_versions(user_v, needed) in (0, 1)


class UserVar(_AttrDict):
    """Current user for client/outbound templates."""

    @classmethod
    def from_user(cls, user: dict[str, Any] | None) -> UserVar:
        data = dict(user or {})
        uuid = data.get("uuid") or ""
        return cls(
            {
                "uuid": uuid,
                "uuid_hex": uuid.replace("-", ""),
                "name": data.get("name") or "",
                "username": data.get("username") or data.get("name") or "",
                "id": data.get("id"),
                "lang": data.get("lang") or "",
                "is_active": data.get("is_active", True),
                "enable": data.get("enable", True),
                "ed25519_public_key": data.get("ed25519_public_key") or "",
                "ed25519_private_key": data.get("ed25519_private_key") or "",
                "wg_pk": data.get("wg_pk") or "",
                "wg_pub": data.get("wg_pub") or "",
                "wg_psk": data.get("wg_psk") or "",
                "wg_ipv4": data.get("wg_ipv4") or "",
                "wg_ipv6": data.get("wg_ipv6") or "",
                "password": uuid,
            }
        )


_CERT_FIELDS: tuple[str, ...] = (
    "certificate",
    "private_key",
    "cert_lines",
    "key_lines",
    "cert_path",
    "key_path",
    "verifyPeerCertByName",
    "pinnedPeerCertSha256",
    "public_key_sha256",
    "fingerprint",
    "valid_cert",
    "expires_at",
    "issuer",
    "auto_renew",
    "last_renewal_error",
)

_TLS_MATERIAL_TO_CERT: dict[str, str] = {
    "tls_cert": "certificate",
    "tls_key": "private_key",
    "tls_cert_lines": "cert_lines",
    "tls_key_lines": "key_lines",
    "tls_cert_path": "cert_path",
    "tls_key_path": "key_path",
    "tls_verifyPeerCertByName": "verifyPeerCertByName",
    "tls_pinnedPeerCertSha256": "pinnedPeerCertSha256",
    "tls_public_key_sha256": "public_key_sha256",
    "tls_fingerprint": "fingerprint",
    "tls_valid_cert": "valid_cert",
    "tls_expires_at": "expires_at",
    "tls_issuer": "issuer",
    "tls_auto_renew": "auto_renew",
    "tls_last_renewal_error": "last_renewal_error",
}


def _empty_cert_payload() -> dict[str, Any]:
    return {
        "certificate": "",
        "private_key": "",
        "cert_lines": [],
        "key_lines": [],
        "cert_path": "",
        "key_path": "",
        "verifyPeerCertByName": True,
        "pinnedPeerCertSha256": [],
        "public_key_sha256": "",
        "fingerprint": "",
        "valid_cert": False,
        "expires_at": None,
        "issuer": "",
        "auto_renew": False,
        "last_renewal_error": "",
    }


def _cert_payload_from_store(data: dict[str, Any]) -> dict[str, Any]:
    cert_pem = data.get("certificate") or ""
    key_pem = data.get("private_key") or ""
    fp = str(data.get("fingerprint") or "").strip()
    return {
        "certificate": cert_pem,
        "private_key": key_pem,
        "cert_lines": [ln for ln in cert_pem.splitlines() if ln.strip()],
        "key_lines": [ln for ln in key_pem.splitlines() if ln.strip()],
        "cert_path": data.get("cert_path") or "",
        "key_path": data.get("key_path") or "",
        "verifyPeerCertByName": True,
        "pinnedPeerCertSha256": [fp] if fp else [],
        "public_key_sha256": fp,
        "fingerprint": fp,
        "valid_cert": bool(data.get("valid_cert")),
        "expires_at": data.get("expires_at"),
        "issuer": data.get("issuer") or "",
        "auto_renew": bool(data.get("auto_renew")),
        "last_renewal_error": data.get("last_renewal_error") or "",
    }


def _cert_payload_from_material(data: dict[str, Any]) -> dict[str, Any]:
    payload = _empty_cert_payload()
    for src, dst in _TLS_MATERIAL_TO_CERT.items():
        if src in data:
            payload[dst] = data[src]
    return payload


class CertVar(_AttrDict):
    """TLS certificate material for a domain (domain.cert in templates)."""

    @classmethod
    def from_data(cls, data: dict[str, Any] | None, *, verify_peer: bool | None = None) -> CertVar:
        if not data:
            payload = _empty_cert_payload()
        elif "certificate" in data or "fingerprint" in data:
            payload = _cert_payload_from_store(data)
        elif "tls_cert" in data or "tls_cert_path" in data:
            payload = _cert_payload_from_material(data)
        else:
            payload = _empty_cert_payload()
            for key in _CERT_FIELDS:
                if key in data:
                    payload[key] = data[key]
        if verify_peer is not None:
            payload["verifyPeerCertByName"] = verify_peer
        return cls(payload)


class DomainVar(_AttrDict):
    """Resolved domain connection + TLS material."""

    def __getattr__(self, name: str) -> Any:
        if name == "domain":
            return self._data.get("name")
        return super().__getattr__(name)

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> DomainVar:
        base = dict(data or {})
        hostname = base.get("name") or base.get("domain") or base.get("host") or base.get("sni") or "example.com"
        child_id = int(base.get("child_id") or 0)
        domain_id = base.get("domain_id") or base.get("id")
        cert_raw = base.get("cert")
        if isinstance(cert_raw, dict) and (cert_raw.get("certificate") or cert_raw.get("fingerprint")):
            cert_source = cert_raw
        else:
            cert_source = _resolve_ssl_material(str(hostname), child_id=child_id, domain_id=domain_id)
        verify = not bool(base.get("allow_insecure"))
        if base.get("need_valid_ssl") is False:
            verify = False
        elif cert_source.get("valid_cert") or cert_source.get("tls_valid_cert"):
            verify = True
        cert = CertVar.from_data(cert_source, verify_peer=verify)
        merged = {
            "name": str(hostname).lower(),
            "host": base.get("host") or hostname,
            "sni": base.get("sni") or hostname,
            "server": base.get("server") or hostname,
            "port": base.get("port") or 443,
            "ip": base.get("ip") or base.get("server") or hostname,
            "ipv4": base.get("ipv4") or "",
            "ipv6": base.get("ipv6") or "",
            "ips": list(base.get("ips") or []),
            "ipsv4": list(base.get("ipsv4") or []),
            "ipsv6": list(base.get("ipsv6") or []),
            "mode": base.get("mode"),
            "alias": base.get("alias") or "",
            "cdn_ip": base.get("cdn_ip") or "",
            "servernames": base.get("servernames") or "",
            "internal_port_special": base.get("internal_port_special") or 0,
            "internal_port_tuic": base.get("internal_port_tuic") or 0,
            "internal_port_hysteria2": base.get("internal_port_hysteria2") or 0,
            "internal_port_naive": base.get("internal_port_naive") or 0,
            "need_valid_ssl": base.get("need_valid_ssl", True),
            "child_id": base.get("child_id", 0),
            "allow_insecure": base.get("allow_insecure", False),
            "cdn": base.get("cdn", False),
            "reality_pbk": base.get("reality_pbk") or "",
            "reality_short_id": base.get("reality_short_id") or "",
            "cert": cert,
        }
        if base.get("download"):
            merged["download"] = cls.from_mapping(base["download"])
        return cls(merged)


class HConfigVar:
    """Panel settings with sensitive keys filtered for templates."""

    def __init__(self, raw: dict[str, Any] | None = None, *, server_side: bool = False):
        self._server_side = server_side
        self._values: dict[str, Any] = {}
        for key, value in (raw or {}).items():
            name = getattr(key, "name", None) or str(key)
            self._values[name] = value

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

    @staticmethod
    def _alias_key(name: str) -> str:
        aliases = {
            "flow_vless": "vless_flow",
        }
        return aliases.get(name, name)

    def _visible(self, name: str) -> bool:
        if name in _HCONFIG_BLOCKED:
            if self._server_side:
                return name in {
                    "reality_private_key",
                    "ssh_host_rsa_pk",
                    "ssh_host_ecdsa_pk",
                    "ssh_host_ed25519_pk",
                }
            return False
        return True


class PlatformVar(_AttrDict):
    """Client platform derived from User-Agent."""

    @classmethod
    def from_user_agent(cls, ua: str | None = None, parsed: dict[str, Any] | None = None) -> PlatformVar:
        raw = (ua or "").strip()
        info = dict(parsed or {})
        os_family = cls._detect_os(raw, info)
        app = cls._detect_app(raw, info)
        app_group = cls._detect_app_group(raw, info, app)
        app_version = cls._detect_app_version(raw, info, app, app_group)
        group_version = cls._detect_group_version(info, app_group)
        os_version = ".".join(str(x) for x in (info.get("os_version") or []) if x) or ""
        singbox_version = ".".join(str(x) for x in (info.get("singbox_version") or []) if x) or ""
        hiddify_version = ".".join(str(x) for x in (info.get("hiddify_version") or []) if x) or ""
        return cls(
            {
                "os": _PlatformPart(os_family, os_version),
                "os_version": os_version,
                "root_access": bool(info.get("root_access", False)),
                "app": _PlatformPart(app, app_version),
                "app_version": TemplateVersion(app_version),
                "app_group": _PlatformPart(app_group, group_version or singbox_version),
                "app_group_version": group_version,
                "singbox": _PlatformPart("singbox", singbox_version),
                "hiddify": _PlatformPart("hiddify", hiddify_version),
                "useragent": raw,
                "tls_engine": cls._tls_engine(os_family),
                "is_hiddify": bool(info.get("is_hiddify")),
                "compare_version": cls.version_compare,
            }
        )

    @staticmethod
    def version_compare(left: str | TemplateVersion, right: str | TemplateVersion) -> int:
        """Return -1, 0, or 1 — usable as platform.version_compare(a, b)."""
        lv = left if isinstance(left, TemplateVersion) else TemplateVersion(left)
        return lv._compare(right)

    @staticmethod
    def _detect_os(ua: str, info: dict[str, Any]) -> str:
        lowered = ua.lower()
        for token, name in (
            ("(android)", "android"),
            ("(ios)", "ios"),
            ("(iphone)", "ios"),
            ("(ipad)", "ios"),
            ("(windows)", "windows"),
            ("(linux)", "linux"),
            ("(macos)", "macos"),
            ("(mac os", "macos"),
        ):
            if token in lowered:
                return name
        return _normalize_os(info.get("os"))

    @staticmethod
    def _tls_engine(os_name: str) -> str:
        if os_name in ("ios", "macos"):
            return "apple"
        if os_name == "windows":
            return "windows"
        return "go"

    @staticmethod
    def _detect_app(ua: str, info: dict[str, Any]) -> str:
        if info.get("app"):
            return str(info["app"]).lower()
        if info.get("is_hiddify"):
            return "hiddify"
        if info.get("is_singbox"):
            return "singbox"
        if info.get("is_v2rayng"):
            return "v2rayng"
        if info.get("is_clash_meta"):
            return "clash-meta"
        if info.get("is_clash"):
            return "clash"
        lowered = ua.lower()
        if "hiddify" in lowered:
            return "hiddify"
        if "sing-box" in lowered or "singbox" in lowered:
            return "singbox"
        if "xray" in lowered:
            return "xray"
        return "unknown"

    @staticmethod
    def _detect_app_group(ua: str, info: dict[str, Any], app: str) -> str:
        if info.get("is_singbox") or info.get("is_hiddify"):
            return "singbox"
        if info.get("is_clash") or info.get("is_clash_meta"):
            return "clash"
        if info.get("is_v2ray") or info.get("is_v2rayng"):
            return "xray"
        for pattern, group in _APP_GROUP_MAP:
            if re.search(pattern, ua):
                return group
        if app in ("hiddify", "singbox"):
            return "singbox"
        if "clash" in app:
            return "clash"
        if "v2ray" in app or app == "xray":
            return "xray"
        return "singbox"

    @staticmethod
    def _detect_app_version(ua: str, info: dict[str, Any], app: str, group: str) -> str:
        for key in ("hiddify_version", "singbox_version", "v2rayng_version"):
            ver = info.get(key)
            if ver:
                return ".".join(str(x) for x in ver)
        match = re.search(r"/(\d+\.\d+(?:\.\d+)?)", ua)
        if match:
            return match.group(1)
        return ""

    @staticmethod
    def _detect_group_version(info: dict[str, Any], group: str) -> str:
        if group == "singbox" and info.get("singbox_version"):
            return ".".join(str(x) for x in info["singbox_version"])
        if group == "xray" and info.get("v2rayng_version"):
            return ".".join(str(x) for x in info["v2rayng_version"])
        return ""


def wrap_user(user: dict[str, Any] | None) -> UserVar:
    return UserVar.from_user(user)


def wrap_domain(data: dict[str, Any] | None) -> DomainVar:
    return DomainVar.from_mapping(data)


def wrap_hconfig(raw: dict[str, Any] | None, *, server_side: bool = False) -> HConfigVar:
    return HConfigVar(raw, server_side=server_side)


def wrap_platform(ua: str | None = None, parsed: dict[str, Any] | None = None) -> PlatformVar:
    return PlatformVar.from_user_agent(ua, parsed)


def reality_public_key(hconfig: HConfigVar) -> str:
    return str(hconfig.get("reality_public_key") or "")


def wrap_proxy(
    data: dict[str, Any] | None = None,
    *,
    port: int = 0,
    path: str = "",
    public_access: bool = False,
    tag: str = "",
    server: str = "",
    domain_binding: str = "domain",
) -> ProxyVar:
    return ProxyVar.from_mapping(
        data,
        port=port,
        path=path,
        public_access=public_access,
        tag=tag,
        server=server,
        domain_binding=domain_binding,
    )


def build_var_context(
    *,
    user: dict[str, Any] | None = None,
    domain_data: dict[str, Any] | None = None,
    proxy_data: dict[str, Any] | None = None,
    hconfigs_raw: dict[str, Any] | None = None,
    user_agent: str | None = None,
    user_agent_parsed: dict[str, Any] | None = None,
    server_side: bool = False,
    port: int = 0,
    path: str = "",
    public_access: bool = False,
    tag: str = "",
    server: str = "",
    domain_binding: str = "domain",
) -> dict[str, Any]:
    """Structured template roots: user, domain, hconfig, platform, proxy."""
    hconfig = wrap_hconfig(hconfigs_raw, server_side=server_side)
    domain = wrap_domain(domain_data)
    platform = wrap_platform(user_agent, user_agent_parsed)
    user_var = wrap_user(user)
    binding = domain_binding
    if not server:
        if binding == "ip":
            server = str(getattr(domain, "ip", "") or getattr(domain, "ipv4", "") or "")
        else:
            server = str(getattr(domain, "server", "") or getattr(domain, "name", "") or "")
    proxy = wrap_proxy(
        proxy_data,
        port=port or int(getattr(domain, "port", 0) or 0),
        path=path,
        public_access=public_access,
        tag=tag,
        server=server,
        domain_binding=binding,
    )
    short_ids = str(hconfig.get("reality_short_ids") or "").split(",")
    reality_short_id = next((s.strip() for s in short_ids if s.strip()), "")
    return {
        "user": user_var,
        "domain": domain,
        "hconfig": hconfig,
        "platform": platform,
        "proxy": proxy,
        "REALITY_PUBLIC_KEY": domain.reality_pbk or reality_public_key(hconfig),
        "REALITY_SHORT_ID": reality_short_id or domain.reality_short_id or "",
        "ConfigEnum": ConfigEnum,
    }
