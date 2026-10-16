from __future__ import annotations

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.text_server import TextServerDriver
from hiddifypanel.proxy_v3.context_vars.ctx_server import ServerContextVar


class FirewallServerDriver(TextServerDriver):
    """iptables rules written to generated/firewall.sh (services/firewall/run.sh runs it)."""

    core = TemplateCore.firewall
    side = BaseConfigSide.server

    def extra_jinja(self, ctx: ServerContextVar) -> dict:
        from hiddifypanel import hutils

        # What the firewall opens: the gateway, the services and the custom proxies' own ports ({"tcp": {port: name}, "udp": ...}).
        return {"public_ports": hutils.network.all_public_ports()}
