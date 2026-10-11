from __future__ import annotations

import subprocess

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.text_server import TextServerDriver
from hiddifypanel.proxy_v3.context_vars.ctx_server import ServerContextVar

# services/wireguard/wg_utils.sh
WG_NIC = "hiddifywg"


def default_ipv4_interface() -> str:
    """Default IPv4 route device, the same lookup install.sh uses for PostUp."""
    try:
        out = subprocess.check_output(["ip", "-4", "route", "show", "default"], text=True)
    except Exception:
        return "eth0"
    for line in out.splitlines():
        parts = line.split()
        if "dev" not in parts:
            continue
        idx = parts.index("dev")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "eth0"


class WireguardServerDriver(TextServerDriver):
    """wg-quick config written to generated/wireguard.conf."""

    core = TemplateCore.wireguard
    side = BaseConfigSide.server

    def extra_jinja(self, ctx: ServerContextVar) -> dict[str, str]:
        return {"pub_nic": default_ipv4_interface(), "wg_nic": WG_NIC}
