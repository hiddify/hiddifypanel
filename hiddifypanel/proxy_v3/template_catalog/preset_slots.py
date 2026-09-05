from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from hiddifypanel.proxy_v3.alpn_helpers import XHTTP_ALPN_PAIRS, XHTTP_DIRECTION_TAGS, tls_layer_from_l3

from .inbound_builder import _raw_transport
from .proxy_matrix import ProxyCombination, iter_proxy_combinations

V2RAY_GATEWAY_PROTOS = frozenset({"vless", "vmess", "trojan"})
V2RAY_GATEWAY_TRANSPORTS = frozenset({"ws", "httpupgrade", "grpc", "tcp", "http"})
H3_PROTOS = frozenset({"tuic", "hysteria", "hysteria2"})
HTTP_CAPABLE_TRANSPORTS = frozenset({"ws", "httpupgrade", "grpc", "tcp", "http"})
TRANSPORT_DISPLAY_NAME = {
    "tcp": "raw",
    "http": "rawhttp",
}

XHTTP_ALPN_TAGS = XHTTP_DIRECTION_TAGS
XHTTP_ALPN_LABEL = {
    "http": "HTTP",
    "tls_h1": "TLS H1",
    "tls_h2": "TLS H2",
    "tls_h3": "QUIC",
}

NAIVE_L3_VARIANTS: tuple[tuple[str, str, str | None], ...] = (
    ("tls_h2", "tls", "h2"),
    ("h3_quic", "tls", "h2"),
)


@dataclass(frozen=True)
class PresetSlot:
    primary: ProxyCombination
    related: tuple[ProxyCombination, ...]
    tls_layer: str
    upload_alpn: str | None = None
    download_alpn: str | None = None
    l7_reverse_proto: str | None = None

    @property
    def slot_key(self) -> tuple:
        transport = _raw_transport(self.primary.transport)
        return (
            self.primary.proto.lower(),
            transport,
            str(self.primary.l3).lower(),
            self.tls_layer,
            self.upload_alpn or "",
            self.download_alpn or "",
            self.l7_reverse_proto or "",
        )


def _with_l3(combo: ProxyCombination, l3: str, *, params: dict | None = None) -> ProxyCombination:
    return ProxyCombination(
        l3=l3,
        transport=combo.transport,
        cdn=combo.cdn,
        proto=combo.proto,
        enable=combo.enable,
        name=f"{l3} {combo.transport} {combo.cdn} {combo.proto}",
        params=dict(params if params is not None else combo.params),
    )


def _xhttp_params(upload: str, download: str) -> dict:
    wire = {
        "http": "http/1.1",
        "tls_h1": "http/1.1",
        "tls_h2": "h2",
        "tls_h3": "h3",
    }
    return {
        "upload_alpn": upload,
        "download_alpn": download,
        "download": {"alpn": wire.get(download, download)},
    }


def tls_layer_for_xhttp_alpn(alpn: str | None, *, reality: bool = False) -> str:
    """Map an xhttp ALPN tag to the TLS layer used in the title and editor."""
    del reality
    tag = str(alpn or "").lower()
    if tag == "http":
        return "http"
    if tag in ("tls_h1", "h1"):
        return "tls_h1"
    if tag in ("tls_h2", "h2"):
        return "tls_h2"
    if tag in ("tls_h3", "h3"):
        return "quic_tls"
    return "tls"


def _expand_combo_variants(combo: ProxyCombination) -> list[tuple[ProxyCombination, str, str | None, str | None, str | None]]:
    """Return (effective_combo, tls_layer, upload_alpn, download_alpn, l7_reverse_proto)."""
    proto = combo.proto.lower()
    transport = _raw_transport(combo.transport)

    if transport == "xhttp" and proto in ("vless", "vmess", "trojan"):
        variants: list[tuple[ProxyCombination, str, str | None, str | None, str | None]] = []
        reality = str(combo.l3).lower() == "reality"
        pairs = tuple((tag, tag) for tag in XHTTP_ALPN_TAGS)
        if proto == "vless":
            pairs = pairs + XHTTP_ALPN_PAIRS
        for upload, download in pairs:
            if reality and (upload == "http" or download == "http"):
                continue
            effective = _with_l3(combo, combo.l3, params=_xhttp_params(upload, download))
            layer = tls_layer_for_xhttp_alpn(upload, reality=reality)
            l7 = _l7_for_xhttp_alpn(upload)
            variants.append((effective, layer, upload, download, l7))
        return variants

    if proto == "naive":
        out: list[tuple[ProxyCombination, str, str | None, str | None, str | None]] = []
        for l3, layer, l7 in NAIVE_L3_VARIANTS:
            out.append((_with_l3(combo, l3), layer, None, None, l7))
        return out

    if proto in H3_PROTOS:
        return [(combo, "tls", None, None, "h3")]

    # ShadowSocks2022 / SOCKS are IP-based with no TLS wrapper.
    if proto in ("shadowsocks", "ss", "socks") and transport not in ("shadowtls", "faketls"):
        return [(combo, "http", None, None, None)]

    if proto in V2RAY_GATEWAY_PROTOS and transport in V2RAY_GATEWAY_TRANSPORTS:
        if transport == "tcp":
            if str(combo.l3).lower() == "reality":
                return [(combo, "tls", None, None, None)]
            return [(_with_l3(combo, "http"), "http", None, None, None)]
        tls_combo = combo if combo.l3 in ("reality", "tls", "tls_h2", "tls_h2_h1", "h3_quic") else _with_l3(combo, "tls")
        variants = [(tls_combo, "tls", None, None, _default_l7(transport, "tls"))]
        if proto != "trojan":
            variants.append((_with_l3(combo, "http"), "http", None, None, _default_l7(transport, "http")))
        return variants

    layer = tls_layer_from_l3(combo.l3)
    l7 = _default_l7(transport, layer) if layer == "http" else None
    return [(combo, layer, None, None, l7)]


def _l7_for_xhttp_alpn(alpn: str | None) -> str:
    """HAProxy reverse-proto for the xhttp *upload* direction.

    Client QUIC/H3 is terminated at the L7 gateway; the backend is always
    HTTP/1 or HTTP/2 over TCP.
    """
    tag = str(alpn or "").lower()
    if tag in ("http", "tls_h1", "h1"):
        return "h1"
    return "h2"


def _default_l7(transport: str, layer: str) -> str | None:
    if transport == "xhttp":
        return "h2"
    if transport in ("ws", "httpupgrade", "http"):
        return "h1"
    if transport == "grpc":
        return "h2"
    if layer == "http":
        return "h1"
    return "h2"


def iter_grouped_preset_slots() -> list[PresetSlot]:
    buckets: dict[tuple, list[tuple[ProxyCombination, str, str | None, str | None, str | None]]] = defaultdict(list)

    for combo in iter_proxy_combinations():
        if not combo.enable:
            continue
        for variant in _expand_combo_variants(combo):
            effective, layer, upload, download, l7 = variant
            l3_key = "" if (upload or download) else str(effective.l3).lower()
            key = (
                effective.proto.lower(),
                _raw_transport(effective.transport),
                l3_key,
                layer,
                upload or "",
                download or "",
                l7 or "",
            )
            buckets[key].append((effective, layer, upload, download, l7))

    slots: list[PresetSlot] = []
    for items in buckets.values():
        combos = [item[0] for item in items]
        primary = min(
            combos,
            key=lambda c: (
                1 if str(c.l3).lower() == "reality" else 0,
                {"direct": 0, "relay": 1, "cdn": 2, "CDN": 2}.get(str(c.cdn).lower(), 9),
                c.name,
            ),
        )
        _, layer, upload, download, l7 = items[0]
        slots.append(
            PresetSlot(
                primary=primary,
                related=tuple(combos),
                tls_layer=layer,
                upload_alpn=upload,
                download_alpn=download,
                l7_reverse_proto=l7,
            )
        )
    return slots


def _preset_base_name(slot: PresetSlot, *, include_custom_transport: bool = True) -> str:
    parts = slot.primary.name.split()
    skip = {
        "direct",
        "relay",
        "cdn",
        "fake",
        "special",
        "http",
        "tls",
        "tls_h2",
        "tls_h2_h1",
        "h3_quic",
        "reality",
        "custom",
    }
    filtered = [part for part in parts if part.lower() not in skip]
    transport = _raw_transport(slot.primary.transport)
    proto = slot.primary.proto.lower()
    # raw / rawhttp names are only for vless/vmess/trojan TCP shapes
    display = TRANSPORT_DISPLAY_NAME.get(transport, transport) if proto in V2RAY_GATEWAY_PROTOS else transport
    if proto in V2RAY_GATEWAY_PROTOS:
        filtered = [part for part in filtered if part.lower() != transport]
    # "custom" is a matrix placeholder. Keep it in slugs for identity; omit from display names.
    if display and display.lower() not in {p.lower() for p in filtered} and (include_custom_transport or display.lower() != "custom"):
        filtered.insert(0, display)
    return " ".join(filtered) if filtered else slot.primary.name


def _xhttp_direction_suffix(slot: PresetSlot) -> str:
    up = XHTTP_ALPN_LABEL[slot.upload_alpn]
    down = XHTTP_ALPN_LABEL[slot.download_alpn]
    if slot.upload_alpn == slot.download_alpn:
        return up
    return f"📤{up} 📥{down}"


def _preset_title(slot: PresetSlot, *, include_custom_transport: bool = True) -> str:
    base = _preset_base_name(slot, include_custom_transport=include_custom_transport)

    if slot.upload_alpn and slot.download_alpn:
        return f"{base} {_xhttp_direction_suffix(slot)}".strip()

    if slot.primary.proto.lower() == "naive":
        if slot.primary.l3 == "tls_h2":
            return f"{base} H2".strip()
        if slot.primary.l3 == "h3_quic":
            return f"{base} QUIC".strip()

    if slot.tls_layer == "http" and slot.primary.proto.lower() in V2RAY_GATEWAY_PROTOS and _raw_transport(slot.primary.transport) != "tcp":
        return f"{base} HTTP".strip()

    if str(slot.primary.l3).lower() == "reality":
        return f"{base} REALITY".strip()

    if slot.primary.l3 == "h3_quic":
        return f"{base} QUIC".strip()

    return base


def preset_display_name(slot: PresetSlot) -> str:
    return _preset_title(slot, include_custom_transport=False)


def preset_slug_name(slot: PresetSlot) -> str:
    """Same title shape as display, but keeps a `custom` transport token for stable slugs."""
    return _preset_title(slot, include_custom_transport=True)
