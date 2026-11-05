import unittest
from unittest import mock

from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.custom_proxy import CustomProxyTransport, TlsLayer
from hiddifypanel.models.proxy import ProxyProto
from hiddifypanel.proxy_v3.context_vars.builder.utils import parent_enable_keys, parent_enable_off
from hiddifypanel.proxy_v3.template_catalog import custom_proxy_presets as presets


def http_off(key: ConfigEnum) -> bool:
    """Every global switch on except "Allow HTTP Connection"."""
    return key != ConfigEnum.http_proxy_enable


def blocked(**fields) -> list[ConfigEnum]:
    return parent_enable_off(parent_enable_keys(**fields), http_off)


class HttpProxySwitchTest(unittest.TestCase):
    """Hiddify-Manager#5666: turning off plain HTTP proxies also turned off Shadowsocks 2022 and Mieru."""

    def test_non_http_protocols_stay_enabled(self):
        cases = [
            dict(proto=ProxyProto.shadowsocks, transport=CustomProxyTransport.other),
            dict(proto=ProxyProto.mieru, transport=CustomProxyTransport.tcp),
            dict(proto=ProxyProto.mieru, transport=CustomProxyTransport.other),
            dict(proto=ProxyProto.dnstt, transport=CustomProxyTransport.other),
            dict(proto=ProxyProto.slipstream, transport=CustomProxyTransport.other),
            dict(proto=ProxyProto.masterdns, transport=CustomProxyTransport.other),
        ]
        for fields in cases:
            with self.subTest(**fields):
                self.assertEqual(blocked(tls_layer=TlsLayer.http, **fields), [])

    def test_plain_http_proxies_still_follow_the_switch(self):
        for proto in (ProxyProto.vless, ProxyProto.vmess, ProxyProto.trojan):
            for transport in (CustomProxyTransport.ws, CustomProxyTransport.httpupgrade, CustomProxyTransport.http, CustomProxyTransport.grpc, CustomProxyTransport.tcp):
                with self.subTest(proto=proto, transport=transport):
                    self.assertEqual(blocked(proto=proto, transport=transport, tls_layer=TlsLayer.http), [ConfigEnum.http_proxy_enable])
        # An xHTTP download leg over plain HTTP is still plain HTTP.
        self.assertEqual(
            blocked(proto=ProxyProto.vless, transport=CustomProxyTransport.xhttp, tls_layer=TlsLayer.tls_h2, download_tls_layer=TlsLayer.http),
            [ConfigEnum.http_proxy_enable],
        )

    def test_builtin_presets(self):
        with mock.patch.object(presets, "hconfig", return_value=None):
            rows = presets.iter_custom_proxy_presets()
        http_rows = [p for p in rows if p.tls_layer == "http" and p.mode != "no_inbound"]
        self.assertTrue(any(p.proto == "shadowsocks" for p in http_rows))
        self.assertTrue(any(p.proto == "mieru" for p in http_rows))
        self.assertTrue(any(p.proto == "vless" and p.transport == "ws" for p in http_rows))
        for p in http_rows:
            with self.subTest(slug=p.slug):
                keys = blocked(
                    proto=ProxyProto(p.proto),
                    transport=CustomProxyTransport(p.transport),
                    tls_layer=TlsLayer(p.tls_layer),
                    download_tls_layer=TlsLayer(p.download_tls_layer) if p.download_tls_layer else None,
                    categories=p.categories,
                )
                expected = [] if p.proto in ("shadowsocks", "mieru", "dnstt", "slipstream", "masterdns") else [ConfigEnum.http_proxy_enable]
                self.assertEqual(keys, expected)


if __name__ == "__main__":
    unittest.main()
