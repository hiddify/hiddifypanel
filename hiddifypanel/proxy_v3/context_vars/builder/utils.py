import re
from typing import Any

import json5
from pydantic import BaseModel

from hiddifypanel.models import ConfigEnum
from hiddifypanel.models.custom_proxy import CustomProxyTransport
from hiddifypanel.models.proxy import ProxyProto
from hiddifypanel.proxy_v3.jinja_context import include_path, jsbool, skip_proxy


def make_jinja_context(ctx: BaseModel) -> dict[str, Any]:
    return {
        "ctx": ctx,
        "skip": skip_proxy,
        "include_path": include_path,
        "jsbool": jsbool,
        "ConfigEnum": ConfigEnum,
        "enumerate": enumerate,
    }


def load_json5(text: str) -> list[dict[str, Any]]:
    try:
        return json5.loads(fix_duplicate_json_commas(text))
    except ValueError as e:
        print(f"Invalid JSON5: {e}")
        print(text)
        raise


def fix_duplicate_json_commas(text: str) -> str:
    """Collapse `, ,` / `,,` artifacts from adjacent Jinja includes into one comma."""
    text = re.sub(r"\[\s*,", "[", text)
    text = re.sub(r",\s*\]", "]", text)
    text = re.sub(r",\s*\}", "}", text)
    pattern = re.compile(r",(?:\s*,)+")
    prev = None
    while prev != text:
        prev = text
        text = pattern.sub(",", text)
    return text


protocol_config_map = {
    ProxyProto.vless: ConfigEnum.vless_enable,
    ProxyProto.trojan: ConfigEnum.trojan_enable,
    ProxyProto.vmess: ConfigEnum.vmess_enable,
    ProxyProto.shadowsocks: ConfigEnum.shadowsocks2022_enable,
    ProxyProto.v2ray: ConfigEnum.v2ray_enable,
    ProxyProto.ssr: ConfigEnum.ssr_enable,
    ProxyProto.ssh: ConfigEnum.ssh_server_enable,
    ProxyProto.tuic: ConfigEnum.tuic_enable,
    ProxyProto.hysteria: ConfigEnum.hysteria_enable,
    ProxyProto.hysteria2: ConfigEnum.hysteria_enable,
    ProxyProto.wireguard: ConfigEnum.wireguard_enable,
    ProxyProto.naive: ConfigEnum.naive_enable,
    ProxyProto.mieru: ConfigEnum.mieru_enable,
    ProxyProto.anytls: ConfigEnum.anytls_enable,
    ProxyProto.dnstt: ConfigEnum.dnstt_enable,
    ProxyProto.snell: ConfigEnum.snell_enable,
    ProxyProto.socks: ConfigEnum.socks_enable,
}

transport_config_map = {
    CustomProxyTransport.tcp: ConfigEnum.tcp_enable,
    CustomProxyTransport.ws: ConfigEnum.ws_enable,
    CustomProxyTransport.httpupgrade: ConfigEnum.httpupgrade_enable,
    CustomProxyTransport.grpc: ConfigEnum.grpc_enable,
    CustomProxyTransport.xhttp: ConfigEnum.xhttp_enable,
}
