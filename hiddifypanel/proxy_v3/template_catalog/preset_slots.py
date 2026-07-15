from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from hiddifypanel.proxy_v3.alpn_helpers import tls_layer_from_l3

from .inbound_builder import _raw_transport
from .proxy_matrix import ProxyCombination, iter_proxy_combinations

V2RAY_GATEWAY_PROTOS = frozenset({"vless", "vmess", "trojan"})
V2RAY_GATEWAY_TRANSPORTS = frozenset({"ws", "httpupgrade", "grpc", "tcp"})
H3_PROTOS = frozenset({"tuic", "hysteria", "hysteria2"})
HTTP_CAPABLE_TRANSPORTS = frozenset({"ws", "httpupgrade", "grpc", "tcp"})

XHTTP_ALPN_TAGS = ("http", "tls_h1", "tls_h2", "tls_h3")
XHTTP_ALPN_LABEL = {
    "http": "HTTP",
    "tls_h1": "TLS H1",
    "tls_h2": "TLS H2",
    "tls_h3": "QUIC",
}

NAIVE_L3_VARIANTS: tuple[tuple[str, str, str | None], ...] = (
    ("http", "http", "h2"),
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


def _expand_combo_variants(combo: ProxyCombination) -> list[tuple[ProxyCombination, str, str | None, str | None, str | None]]:
    """Return (effective_combo, tls_layer, upload_alpn, download_alpn, l7_reverse_proto)."""
    proto = combo.proto.lower()
    transport = _raw_transport(combo.transport)

    if transport == "xhttp" and proto in ("vless", "vmess"):
        variants: list[tuple[ProxyCombination, str, str | None, str | None, str | None]] = []
        for upload in XHTTP_ALPN_TAGS:
            for download in XHTTP_ALPN_TAGS:
                effective = _with_l3(combo, combo.l3, params=_xhttp_params(upload, download))
                if str(combo.l3).lower() == "reality":
                    layer = "tls"
                else:
                    layer = "http" if upload == "http" and download == "http" else "tls"
                l7 = "h2"
                variants.append((effective, layer, upload, download, l7))
        return variants

    if proto == "naive":
        out: list[tuple[ProxyCombination, str, str | None, str | None, str | None]] = []
        for l3, layer, l7 in NAIVE_L3_VARIANTS:
            out.append((_with_l3(combo, l3), layer, None, None, l7))
        return out

    if proto in H3_PROTOS:
        return [(combo, "tls", None, None, "h3")]

    if proto in V2RAY_GATEWAY_PROTOS and transport in V2RAY_GATEWAY_TRANSPORTS:
        tls_combo = combo if combo.l3 in ("reality", "tls", "tls_h2", "tls_h2_h1", "h3_quic") else _with_l3(combo, "tls")
        variants = [(tls_combo, "tls", None, None, _default_l7(transport, "tls"))]
        if proto != "trojan":
            variants.append((_with_l3(combo, "http"), "http", None, None, _default_l7(transport, "http")))
        return variants

    layer = tls_layer_from_l3(combo.l3)
    l7 = _default_l7(transport, layer) if layer == "http" else None
    return [(combo, layer, None, None, l7)]


def _default_l7(transport: str, layer: str) -> str | None:
    if transport == "xhttp":
        return "h2"
    if transport in ("ws", "httpupgrade"):
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
            key = (
                effective.proto.lower(),
                _raw_transport(effective.transport),
                str(effective.l3).lower(),
                layer,
                upload or "",
                download or "",
                l7 or "",
            )
            buckets[key].append((effective, layer, upload, download, l7))

    slots: list[PresetSlot] = []
    for items in buckets.values():
        combos = [item[0] for item in items]
        primary = min(combos, key=lambda c: ({"direct": 0, "relay": 1, "cdn": 2, "CDN": 2}.get(str(c.cdn).lower(), 9), c.name))
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


def preset_display_name(slot: PresetSlot) -> str:
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
    base = " ".join(filtered) if filtered else slot.primary.name

    if slot.upload_alpn and slot.download_alpn:
        up = XHTTP_ALPN_LABEL[slot.upload_alpn]
        down = XHTTP_ALPN_LABEL[slot.download_alpn]
        suffix = up if slot.upload_alpn == slot.download_alpn else f"📤{up} 📥{down}"
        return f"{base} {suffix}".strip()

    if slot.primary.proto.lower() == "naive":
        if slot.primary.l3 == "http":
            return f"{base} HTTP".strip()
        if slot.primary.l3 == "tls_h2":
            return f"{base} H2".strip()
        if slot.primary.l3 == "h3_quic":
            return f"{base} QUIC".strip()

    if slot.tls_layer == "http":
        return f"{base} HTTP".strip()

    if slot.primary.l3 == "h3_quic":
        return f"{base} QUIC".strip()

    return base
