import re
from collections.abc import Callable, Sequence
from typing import Any, Protocol

import json5
from pydantic import BaseModel

from hiddifypanel.models import ConfigEnum
from hiddifypanel.models.custom_proxy import CustomProxyTransport, TlsLayer
from hiddifypanel.models.proxy import ProxyProto
from hiddifypanel.proxy_v3.jinja_context import ConfigEnum, fake_ip_for_sub_link, include_path, jsbool, skip_proxy


def make_jinja_context(ctx: BaseModel) -> dict[str, Any]:
    return {
        "ctx": ctx,
        "skip": skip_proxy,
        "include_path": include_path,
        "jsbool": jsbool,
        "ConfigEnum": ConfigEnum,
        "enumerate": enumerate,
        "fake_ip_for_sub_link": fake_ip_for_sub_link(),
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


protocol_config_map: dict[ProxyProto, ConfigEnum] = {
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

transport_config_map: dict[CustomProxyTransport, ConfigEnum] = {
    CustomProxyTransport.tcp: ConfigEnum.tcp_enable,
    CustomProxyTransport.ws: ConfigEnum.ws_enable,
    CustomProxyTransport.httpupgrade: ConfigEnum.httpupgrade_enable,
    CustomProxyTransport.grpc: ConfigEnum.grpc_enable,
    CustomProxyTransport.xhttp: ConfigEnum.xhttp_enable,
}

tls_layer_config_map: dict[TlsLayer, ConfigEnum] = {
    TlsLayer.http: ConfigEnum.http_proxy_enable,
    TlsLayer.quic_tls: ConfigEnum.quic_enable,
    TlsLayer.quic_tcp_tls: ConfigEnum.quic_enable,
}

category_config_map: dict[str, ConfigEnum] = {
    "shadowtls": ConfigEnum.shadowtls_enable,
    "faketls": ConfigEnum.ssfaketls_enable,
}

domain_mode_config_map: dict[str, ConfigEnum] = {
    "reality": ConfigEnum.reality_enable,
}

ConfigFlagGetter = Callable[[ConfigEnum], bool | None]


class ParentEnableFields(Protocol):
    proto: ProxyProto | None
    transport: CustomProxyTransport | None
    tls_layer: TlsLayer | None
    download_tls_layer: TlsLayer | None
    domain_modes: Sequence[str] | None
    download_domain_modes: Sequence[str] | None
    categories: Sequence[str] | None


def parent_enable_keys(
    *,
    proto: ProxyProto | None = None,
    transport: CustomProxyTransport | None = None,
    tls_layer: TlsLayer | None = None,
    download_tls_layer: TlsLayer | None = None,
    domain_modes: Sequence[str] | None = None,
    download_domain_modes: Sequence[str] | None = None,
    categories: Sequence[str] | None = None,
) -> list[ConfigEnum]:
    """Global hconfig flags that must be on for this custom proxy to be enabled."""
    keys: list[ConfigEnum] = []
    seen: set[ConfigEnum] = set()

    def add(key: ConfigEnum | None) -> None:
        if key is not None and key not in seen:
            seen.add(key)
            keys.append(key)

    if proto is not None:
        add(protocol_config_map.get(proto))
    if transport is not None and not (proto == ProxyProto.mieru and transport == CustomProxyTransport.tcp):
        add(transport_config_map.get(transport))
    for layer in (tls_layer, download_tls_layer):
        if layer is not None:
            add(tls_layer_config_map.get(layer))
    for mode in list(domain_modes or []) + list(download_domain_modes or []):
        add(domain_mode_config_map.get(mode.lower()))
    for category in categories or []:
        add(category_config_map.get(category.lower()))
    return keys


def parent_enable_keys_for(proxy: ParentEnableFields) -> list[ConfigEnum]:
    return parent_enable_keys(
        proto=proxy.proto,
        transport=proxy.transport,
        tls_layer=proxy.tls_layer,
        download_tls_layer=proxy.download_tls_layer,
        domain_modes=proxy.domain_modes,
        download_domain_modes=proxy.download_domain_modes,
        categories=proxy.categories,
    )


def parent_enable_off(keys: Sequence[ConfigEnum], getter: ConfigFlagGetter) -> list[ConfigEnum]:
    return [key for key in keys if getter(key) is False]


def normalize_common_proxy_core(value: object) -> str:
    raw = str(getattr(value, "name", None) or value or "both").strip().lower().replace("-", "_")
    if raw in {"hiddify_core", "hiddifycore", "singbox"}:
        return "hiddify-core"
    if raw == "xray":
        return "xray"
    return "both"


def common_proxy_core_blocks(is_common_proxy: bool, server_core: str | None, selected: object) -> bool:
    if not is_common_proxy:
        return False
    chosen = normalize_common_proxy_core(selected)
    if chosen == "both":
        return False
    core = str(server_core or "")
    if chosen == "xray":
        return core == "hiddify-core"
    if chosen == "hiddify-core":
        return core == "xray"
    return False
