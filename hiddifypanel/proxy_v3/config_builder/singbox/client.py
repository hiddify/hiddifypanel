from __future__ import annotations

import re

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.proxy_v3.config_builder.base_json_client_drivers import JsonClientOutboundDriver
from hiddifypanel.proxy_v3.config_builder.client_selection import select_client_config
from hiddifypanel.proxy_v3.config_builder.models import MessageModel
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar
from hiddifypanel.proxy_v3.context_vars.proxy import ConfigVar
from hiddifypanel.proxy_v3.template_catalog.client_builder import USE_HIDDIFY_CORE_PLACEHOLDER

_USE_HIDDIFY_CORE_RE = re.compile(r"\{#\s*use_hiddify_core\s*\(\s*\)\s*#\}")
_SINGBOX_UNSUPPORTED_TRANSPORTS = frozenset({"xhttp", "splithttp"})
_XHTTP_SKIP_TEMPLATE = "{% block outbounds %}\n{{ skip('xhttp is not supported by sing-box') }}\n{% endblock %}\n"


def _proxy_transport_key(proxy: object) -> str:
    transport = getattr(proxy, "transport", None)
    return (getattr(transport, "value", None) or str(transport or "")).lower()


class SingboxClientDriver(JsonClientOutboundDriver):
    """Sing-box client driver; resolves ``{#use_hiddify_core()#}`` to hiddify-core templates."""

    core = TemplateCore.singbox

    def _resolve_client_template(
        self,
        ctx: ClientContextVar,
        client_config: ConfigVar,
        messages: list[MessageModel],
    ) -> str | None:
        if _proxy_transport_key(ctx.proxy) in _SINGBOX_UNSUPPORTED_TRANSPORTS:
            return _XHTTP_SKIP_TEMPLATE

        content = client_config.content or ""
        if not _USE_HIDDIFY_CORE_RE.search(content):
            return content

        hiddify_cfg = select_client_config(
            ctx.proxy.client_configs,
            TemplateCore.hiddify_core,
            ctx.platform.hiddify.version or ctx.platform.app_version,
        )
        if hiddify_cfg is None or not (hiddify_cfg.content or "").strip():
            messages.append(
                MessageModel(
                    level="warning",
                    message=f"{ctx.proxy.tag or ctx.proxy.id}: singbox {USE_HIDDIFY_CORE_PLACEHOLDER} but no hiddify-core client config",
                )
            )
            return None
        return hiddify_cfg.content
