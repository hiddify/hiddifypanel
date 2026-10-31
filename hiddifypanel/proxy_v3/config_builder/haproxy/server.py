from __future__ import annotations

import re

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel
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


_BACKEND_DEF_RE = re.compile(r"^\s*backend\s+(\S+)", re.MULTILINE)
# use_backend / default_backend with a fixed name (not "%[...]"), and the default of a map lookup: map_beg(<map>,<backend>)
_BACKEND_USE_RE = re.compile(r"^\s*(?:use_backend|default_backend)\s+([\w.:-]+)", re.MULTILINE)
_BACKEND_MAP_DEFAULT_RE = re.compile(r"map_\w+\([^,()]*,\s*([\w.:-]+)\s*\)")


def missing_backends(config: str) -> list[str]:
    """Backends the config sends traffic to but never defines: HAProxy refuses such a config and does not start."""
    defined = set(_BACKEND_DEF_RE.findall(config or ""))
    used = set(_BACKEND_USE_RE.findall(config or "")) | set(_BACKEND_MAP_DEFAULT_RE.findall(config or ""))
    return sorted(used - defined)


def _haproxy_overrides(child_id: int) -> list[str]:
    """The admin's overrides of built-in HAProxy templates (and of the HAProxy base config)."""
    from hiddifypanel.models.custom_proxy import ProxyTemplate
    from hiddifypanel.models.proxy_base_config import ProxyBaseConfig

    in_child = (ProxyTemplate.child_id == child_id) | (ProxyTemplate.child_id == 0)
    rows = ProxyTemplate.query.filter(in_child, ProxyTemplate.is_builtin, ProxyTemplate.builtin_override, ProxyTemplate.slug.like("haproxy/%")).all()
    names = sorted({row.slug for row in rows})
    base = ProxyBaseConfig.query.filter(
        (ProxyBaseConfig.child_id == child_id) | (ProxyBaseConfig.child_id == 0),
        ProxyBaseConfig.core == TemplateCore.haproxy.value,
        ProxyBaseConfig.side == BaseConfigSide.server,
        ProxyBaseConfig.builtin_override,
    ).first()
    if base is not None:
        names.insert(0, "haproxy/server/base")
    return names


class HaproxyServerDriver(TextServerDriver):
    core = TemplateCore.haproxy
    side = BaseConfigSide.server

    def extra_jinja(self, ctx: ServerContextVar) -> dict:
        return {"haproxy_cert_dir": _HAPROXY_CERT_DIR}

    def build(self, child_id: int, ctx: ServerContextVar, *, builtin_only: bool = False) -> ConfigBuilderModel:
        result = super().build(child_id, ctx, builtin_only=builtin_only)
        result.config = rewrite_haproxy_cert_paths(result.config or "")
        missing = missing_backends(result.config)
        if not missing or builtin_only:
            if missing:
                result.messages.append(MessageModel(level="error", message=f"HAProxy: backend(s) used but not defined: {', '.join(missing)}"))
            return result
        # An override from an older version can lack a backend the new templates use (to_httpmode_from_tls after
        # 14.1.0b2): HAProxy would not start and the panel would be unreachable. Use the shipped templates instead.
        fallback = self.build(child_id, ctx, builtin_only=True)
        if missing_backends(fallback.config or "") or any(m.level == "error" for m in fallback.messages):
            result.messages.append(MessageModel(level="error", message=f"HAProxy: backend(s) used but not defined: {', '.join(missing)}"))
            return result
        overrides = _haproxy_overrides(child_id)
        fallback.messages.append(
            MessageModel(
                level="warning",
                message=(
                    f"HAProxy: your edited templates ({', '.join(overrides) or 'none found'}) lack backend(s) "
                    f"{', '.join(missing)} that this version uses; the built-in templates were used instead. "
                    "Reset or update those templates to use your changes again."
                ),
                data={"missing_backends": missing, "overrides": overrides},
            )
        )
        return fallback
