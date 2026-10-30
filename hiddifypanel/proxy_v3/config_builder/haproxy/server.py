from __future__ import annotations

import ipaddress
import re

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel
from hiddifypanel.proxy_v3.config_builder.text_server import TextServerDriver
from hiddifypanel.proxy_v3.context_vars.ctx_server import ServerContextVar
from hiddifypanel.proxy_v3.tls_store_sync import CERT_ROOT

# Only data/cert is supported. Old templates/overrides that still say data/ssl are rewritten here.
_HAPROXY_CERT_DIR = str(CERT_ROOT).rstrip("/") + "/"
_SSL_CRT_LEGACY_RE = re.compile(
    r"(ssl\s+crt\s+)/opt/hiddify-manager/data/ssl/?",
    re.IGNORECASE,
)


def rewrite_haproxy_cert_paths(config: str) -> str:
    """Force HAProxy ``ssl crt`` binds onto ``data/cert`` (never ``data/ssl``)."""
    if not config:
        return config
    return _SSL_CRT_LEGACY_RE.sub(rf"\1{_HAPROXY_CERT_DIR}", config)


def ip_default_certs() -> dict[int, str]:
    """This server's IP certificates in data/cert, by IP version (4 / 6): the panel opened by IP sends no SNI, so HAProxy
    serves the bind's default certificate. Without one, that is the first file of the folder: the IPv4 certificate for a
    visitor who dialled the IPv6 address (or the other way round), and the browser says the name does not match."""
    out: dict[int, str] = {}
    for path in sorted(CERT_ROOT.glob("*.crt")):
        try:
            ip = ipaddress.ip_address(path.name[: -len(".crt")])
        except ValueError:
            continue
        if path.with_name(path.name + ".key").is_file():
            out.setdefault(ip.version, str(path))
    return out


class HaproxyServerDriver(TextServerDriver):
    core = TemplateCore.haproxy
    side = BaseConfigSide.server

    def extra_jinja(self, ctx: ServerContextVar) -> dict:
        return {"haproxy_cert_dir": _HAPROXY_CERT_DIR, "haproxy_ip_crt": ip_default_certs()}

    def build(self, child_id: int, ctx: ServerContextVar) -> ConfigBuilderModel:
        result = super().build(child_id, ctx)
        result.config = rewrite_haproxy_cert_paths(result.config or "")
        return result
