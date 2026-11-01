"""The name users see for a domain in config names, profile titles and subscription names when it has no alias.

A config's name ends up in screenshots, shared links and client logs, so by default it says nothing about the domain
(``domain_label_mode``):

- ``private`` (default): the kind of domain and a short code, e.g. ``☁️ CDN K7Q``. The code is a keyed hash
  (HMAC-SHA256 with the panel's secret key) of the name: stable and different per domain, but it cannot be turned back
  into the name, not even by trying a list of domain names, without the server's key.
- ``masked``: the name with most letters hidden, e.g. ``⚡ h*y.com``, ``⚡ x.h*y.com``, ``⚡ 94.*.*.*``.
- ``full``: the name itself (as before).

An alias set by the admin is always used as it is.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
from typing import Any

from hiddifypanel.models.config_enum import DomainLabelMode

#: The code's letters: no 0/O, 1/I/L look-alikes.
_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_CODE_LENGTH = 3
_IPV4 = re.compile(r"(?<![\d])(\d{1,3})[.-](\d{1,3})[.-](\d{1,3})[.-](\d{1,3})(?![\d])")


def _kind(mode: Any, fake_mode: Any) -> tuple[str, str]:
    """The emoji and the name of the kind of domain."""
    fake, kind = str(fake_mode or ""), str(mode or "")
    if fake == "reality":
        return "🔒", "Reality"
    if fake == "fake":
        return "🎭", "FakeTLS"
    return {
        "cdn": ("☁️", "CDN"),
        "worker": ("⚙️", "Worker"),
        "relay": ("🔁", "Relay"),
        "sub_link_only": ("🔗", "Link"),
    }.get(kind, ("⚡", "Direct"))


def _secret() -> bytes:
    try:
        from flask import current_app

        key = current_app.config.get("SECRET_KEY")
        if key:
            return key if isinstance(key, bytes) else str(key).encode()
    except RuntimeError:  # no app (a script): the server's own id is the next best server-only value
        pass
    from hiddifypanel.models import ConfigEnum, hconfig

    return str(hconfig(ConfigEnum.unique_id) or "hiddify").encode()


def code(name: str) -> str:
    """A short, stable code of ``name`` that does not reveal it (keyed hash)."""
    digest = hmac.new(_secret(), b"domain-label:" + name.strip().lower().encode(), hashlib.sha256).digest()
    value = int.from_bytes(digest[:8], "big")
    out = []
    for _ in range(_CODE_LENGTH):
        value, i = divmod(value, len(_ALPHABET))
        out.append(_ALPHABET[i])
    return "".join(out)


def _mask_label(label: str, keep_short: bool) -> str:
    if len(label) <= 2:
        return label if keep_short else "*"
    if len(label) == 3:
        return f"{label[0]}*"
    return f"{label[0]}*{label[-1]}"


def mask(name: str) -> str:
    """``name`` with most of it hidden: ``hiddify.com`` → ``h*y.com``, ``x.hiddify.com`` → ``x.h*y.com``, a name with an
    IP (``94.23.45.12.sslip.io``) or an IP → ``94.*.*.*``."""
    name = name.strip().lower().rstrip(".")
    try:
        ip = ipaddress.ip_address(name.strip("[]"))
        return f"{name.split('.')[0]}.*.*.*" if ip.version == 4 else f"{name.strip('[]').split(':')[0]}:*"
    except ValueError:
        pass
    if m := _IPV4.search(name):
        return f"{m.group(1)}.*.*.*"
    labels = name.split(".")
    if len(labels) < 2:
        return _mask_label(name, keep_short=False)
    # a two-part public suffix (co.uk, com.br): both parts stay
    suffix = 2 if len(labels) >= 3 and len(labels[-1]) == 2 and len(labels[-2]) <= 3 else 1
    head, main, tail = labels[: -suffix - 1], labels[-suffix - 1], labels[-suffix:]
    return ".".join([*(_mask_label(p, keep_short=True) for p in head), _mask_label(main, keep_short=False), *tail])


def public_name(name: str, *, alias: str | None = None, mode: Any = None, fake_mode: Any = None, label_mode: Any = None) -> str:
    """The name of a domain as users see it (see the module's description)."""
    if alias and alias.strip():
        return alias.strip()
    name = (name or "").strip()
    if not name:
        return ""
    if label_mode is None:
        from hiddifypanel.models import ConfigEnum, hconfig

        label_mode = hconfig(ConfigEnum.domain_label_mode)
    label_mode = str(label_mode or DomainLabelMode.private)
    if label_mode == DomainLabelMode.full:
        return name
    emoji, kind = _kind(mode, fake_mode)
    if label_mode == DomainLabelMode.masked:
        return f"{emoji} {mask(name)}"
    return f"{emoji} {kind} {code(name)}"


def for_domain(domain: Any) -> str:
    """``public_name`` of a Domain row (``domain``) or a domain context variable (``name``)."""
    name = getattr(domain, "domain", None) or getattr(domain, "name", None) or ""
    return public_name(str(name), alias=getattr(domain, "alias", None), mode=getattr(domain, "mode", None), fake_mode=getattr(domain, "fake_mode", None))
