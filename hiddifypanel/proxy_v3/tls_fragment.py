"""Domain FinalMask tricks (TLS fragment and future templates).

Stored on the domain as ``extra_params.tricks``::

    {
      "tricks": {
        "template": "tls_fragment",
        "finalmask": {
          "tcp": [
            {
              "type": "fragment",
              "settings": {
                "packets": "tlshello",
                "lengths": ["3-5", "6-8", "10-20"],
                "delays": ["10-20"],
                "maxSplit": "3-6"
              }
            }
          ]
        }
      }
    }

See https://xtls.github.io/en/config/transports/finalmask.html
Clients (hiddify-core + xray) receive ``finalmask`` on the outbound; there is no dialerProxy fragment outbound.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

DEFAULT_PACKETS = "tlshello"
DEFAULT_LENGTHS = ["10-100"]
DEFAULT_DELAYS = ["50-200"]
DEFAULT_MAX_SPLIT = "3-6"
TEMPLATE_TLS_FRAGMENT = "tls_fragment"
_ELIGIBLE = frozenset({"cdn", "worker"})


def fragment_eligible(mode: object) -> bool:
    value = getattr(mode, "value", mode)
    return str(value or "") in _ELIGIBLE


def _str(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _str_list(value: Any, *, fallback: list[str]) -> list[str]:
    if isinstance(value, str):
        parts = [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]
        return parts or list(fallback)
    if isinstance(value, (list, tuple)):
        out = [str(p).strip() for p in value if str(p).strip()]
        return out or list(fallback)
    return list(fallback)


def tricks_of(extra: Any) -> dict[str, Any]:
    if not isinstance(extra, Mapping):
        return {}
    tricks = extra.get("tricks")
    return dict(tricks) if isinstance(tricks, Mapping) else {}


def _legacy_flat_fragment(extra: Mapping[str, Any]) -> dict[str, Any] | None:
    """Older flat ``{type:fragment,settings}`` or ``tricks.tls_fragment`` UI blob."""
    tricks = tricks_of(extra)
    for candidate in (tricks.get("finalmask"), extra.get("finalmask"), tricks.get("tls_fragment"), extra.get("tls_fragment")):
        if not isinstance(candidate, Mapping):
            continue
        if str(candidate.get("type") or "").lower() == "fragment" and isinstance(candidate.get("settings"), Mapping):
            return dict(candidate["settings"])
        if "packets" in candidate or "lengths" in candidate or "size" in candidate:
            return {
                "packets": candidate.get("packets"),
                "lengths": candidate.get("lengths", candidate.get("size")),
                "delays": candidate.get("delays", candidate.get("sleep")),
                "maxSplit": candidate.get("maxSplit", candidate.get("max_split")),
            }
    return None


def fragment_settings_of(extra: Any) -> dict[str, Any] | None:
    """Fragment settings dict if this domain uses the TLS Fragment template, else None."""
    if not isinstance(extra, Mapping):
        return None
    tricks = tricks_of(extra)
    fm = tricks.get("finalmask") if "finalmask" in tricks else extra.get("finalmask")
    if isinstance(fm, Mapping):
        tcp = fm.get("tcp")
        if isinstance(tcp, list):
            for layer in tcp:
                if isinstance(layer, Mapping) and str(layer.get("type") or "").lower() == "fragment":
                    settings = layer.get("settings") if isinstance(layer.get("settings"), Mapping) else {}
                    return {
                        "packets": _str(settings.get("packets"), DEFAULT_PACKETS),
                        "lengths": _str_list(settings.get("lengths"), fallback=DEFAULT_LENGTHS),
                        "delays": _str_list(settings.get("delays"), fallback=DEFAULT_DELAYS),
                        "maxSplit": _str(settings.get("maxSplit") or settings.get("max_split"), DEFAULT_MAX_SPLIT),
                    }
    legacy = _legacy_flat_fragment(extra)
    if not legacy:
        return None
    return {
        "packets": _str(legacy.get("packets"), DEFAULT_PACKETS),
        "lengths": _str_list(legacy.get("lengths"), fallback=DEFAULT_LENGTHS),
        "delays": _str_list(legacy.get("delays"), fallback=DEFAULT_DELAYS),
        "maxSplit": _str(legacy.get("maxSplit") or legacy.get("max_split"), DEFAULT_MAX_SPLIT),
    }


def build_fragment_finalmask(
    *,
    packets: str | None = None,
    lengths: Any = None,
    delays: Any = None,
    max_split: str | None = None,
) -> dict[str, Any]:
    """FinalMaskObject with a single TCP fragment layer (Xray / Hiddify Core)."""
    return {
        "tcp": [
            {
                "type": "fragment",
                "settings": {
                    "packets": _str(packets, DEFAULT_PACKETS),
                    "lengths": _str_list(lengths, fallback=DEFAULT_LENGTHS),
                    "delays": _str_list(delays, fallback=DEFAULT_DELAYS),
                    "maxSplit": _str(max_split, DEFAULT_MAX_SPLIT),
                },
            }
        ]
    }


def finalmask_of(extra: Any, *, domain_mode: object | None = None) -> Any:
    """FinalMask object for client templates, or None."""
    if domain_mode is not None and not fragment_eligible(domain_mode):
        # Non-CDN domains: still allow an explicit custom finalmask if present.
        pass

    if not isinstance(extra, Mapping):
        return None
    tricks = tricks_of(extra)
    fm = tricks.get("finalmask") if "finalmask" in tricks else None
    if isinstance(fm, Mapping) and fm:
        # Already a FinalMaskObject with tcp/udp/quicParams
        if any(k in fm for k in ("tcp", "udp", "quicParams")):
            return dict(fm)
        # Legacy flat {type, settings}
        if str(fm.get("type") or "").lower() == "fragment":
            settings = fm.get("settings") if isinstance(fm.get("settings"), Mapping) else {}
            return build_fragment_finalmask(
                packets=settings.get("packets"),
                lengths=settings.get("lengths"),
                delays=settings.get("delays"),
                max_split=settings.get("maxSplit") or settings.get("max_split"),
            )

    legacy_top = extra.get("finalmask")
    if isinstance(legacy_top, Mapping) and legacy_top:
        if any(k in legacy_top for k in ("tcp", "udp", "quicParams")):
            return dict(legacy_top)
        if str(legacy_top.get("type") or "").lower() == "fragment":
            settings = legacy_top.get("settings") if isinstance(legacy_top.get("settings"), Mapping) else {}
            return build_fragment_finalmask(
                packets=settings.get("packets"),
                lengths=settings.get("lengths"),
                delays=settings.get("delays"),
                max_split=settings.get("maxSplit") or settings.get("max_split"),
            )

    # Legacy tricks.tls_fragment / top-level tls_fragment → synthesize
    settings = fragment_settings_of(extra)
    if settings and (domain_mode is None or fragment_eligible(domain_mode)):
        # Only synthesize when something looks like an intentional fragment config
        if tricks.get("template") == TEMPLATE_TLS_FRAGMENT or tricks.get("tls_fragment") or extra.get("tls_fragment"):
            return build_fragment_finalmask(
                packets=settings["packets"],
                lengths=settings["lengths"],
                delays=settings["delays"],
                max_split=settings["maxSplit"],
            )
    return None


def set_tls_fragment(extra: MutableMapping[str, Any] | dict[str, Any], frag: Mapping[str, Any] | None) -> dict[str, Any]:
    """Enable/update/clear the TLS Fragment trick → writes ``tricks.finalmask``."""
    obj: dict[str, Any] = dict(extra) if isinstance(extra, Mapping) else {}
    tricks: dict[str, Any] = dict(tricks_of(obj))

    obj.pop("finalmask", None)
    obj.pop("tls_fragment", None)
    tricks.pop("tls_fragment", None)

    if frag is None or str(frag.get("mode") or "").lower() == "off":
        tricks.pop("template", None)
        tricks.pop("finalmask", None)
    else:
        tricks["template"] = TEMPLATE_TLS_FRAGMENT
        tricks["finalmask"] = build_fragment_finalmask(
            packets=frag.get("packets"),
            lengths=frag.get("lengths", frag.get("size")),
            delays=frag.get("delays", frag.get("sleep")),
            max_split=frag.get("maxSplit") or frag.get("max_split"),
        )

    if tricks:
        obj["tricks"] = tricks
    else:
        obj.pop("tricks", None)
    return obj


def resolve(*, domain_mode: object, extra: Any, **_ignored: Any) -> dict[str, Any]:
    """UI-oriented resolve: enable + fragment settings (no panel globals)."""
    eligible = fragment_eligible(domain_mode)
    settings = fragment_settings_of(extra) if eligible else None
    enable = bool(settings) and eligible
    packets = settings["packets"] if settings else DEFAULT_PACKETS
    lengths = settings["lengths"] if settings else list(DEFAULT_LENGTHS)
    delays = settings["delays"] if settings else list(DEFAULT_DELAYS)
    max_split = settings["maxSplit"] if settings else DEFAULT_MAX_SPLIT
    return {
        "mode": "on" if enable else "off",
        "enable": enable,
        "packets": packets,
        "lengths": lengths,
        "delays": delays,
        "maxSplit": max_split,
        "size": lengths[0] if lengths else DEFAULT_LENGTHS[0],
        "sleep": delays[0] if delays else DEFAULT_DELAYS[0],
    }


def to_finalmask(resolved: Mapping[str, Any]) -> dict[str, Any] | None:
    if not resolved.get("enable"):
        return None
    return build_fragment_finalmask(
        packets=resolved.get("packets"),
        lengths=resolved.get("lengths"),
        delays=resolved.get("delays"),
        max_split=resolved.get("maxSplit"),
    )


#: Scanner / UI presets (values feed ``build_fragment_finalmask``).
SCANNER_PRESETS: list[dict[str, Any]] = [
    {"id": "off", "mode": "off"},
    {"id": "default", "mode": "on", "packets": "tlshello", "lengths": ["10-100"], "delays": ["50-200"], "maxSplit": "3-6"},
    {"id": "fine", "mode": "on", "packets": "tlshello", "lengths": ["50-100"], "delays": ["10-20"], "maxSplit": "3-6"},
    {"id": "coarse", "mode": "on", "packets": "tlshello", "lengths": ["100-200"], "delays": ["10-20"], "maxSplit": "3-6"},
    {"id": "multi", "mode": "on", "packets": "tlshello", "lengths": ["3-5", "6-8", "10-20"], "delays": ["10-20"], "maxSplit": "3-6"},
    {"id": "1-3", "mode": "on", "packets": "1-3", "lengths": ["10-100"], "delays": ["50-200"], "maxSplit": "3-6"},
    {"id": "tight", "mode": "on", "packets": "tlshello", "lengths": ["1-10"], "delays": ["1-5"], "maxSplit": "2-4"},
]
