"""Browser-like headers for rawhttp (xray's tcp ``http`` header) that the server can read.

Behind HAProxy the inbound has ``acceptProxyProtocol``: its first read holds only the first ~224 bytes of the request
(200 for an IPv6 client: a longer PROXY header). xray then parses what it has but the last 4 bytes, and rejects the
connection unless that piece ends inside a header value ("malformed MIME header: missing colon: User-Agent").
So the request is safe when no header name (or the request line) covers the bytes where the cut can fall. The
headers are chosen for that: as many as possible, in the order given (most important first).
"""

from __future__ import annotations

import itertools
import json
import random
from functools import lru_cache
from typing import Any

# Bytes of the request (after the PROXY header) parsed alone when the first read ends there: IPv6 .. IPv4 client,
# with a small margin.
CUT_RANGE = range(190, 224)


def _layouts_unsafe(request_line: int, lines: tuple[tuple[int, int], ...], ordered: bool) -> bool:
    """``lines``: (name part with ": ", whole line with CRLF) lengths. ``ordered``: sent as given; else in any order."""
    if not ordered:
        # any order: a header's name can follow any subset of the others
        for i, (name, _) in enumerate(lines):
            starts = {request_line}
            for j, (_, length) in enumerate(lines):
                if j != i:
                    starts |= {s + length for s in starts if s + length < CUT_RANGE.stop}
            if any(s <= cut < s + name for s in starts for cut in CUT_RANGE):
                return True
        return request_line > CUT_RANGE.start
    pos = request_line
    if pos > CUT_RANGE.start:
        return True
    for name, length in lines:
        if any(pos <= cut < pos + name for cut in CUT_RANGE):
            return True
        pos += length
    return False


@lru_cache(maxsize=256)
def _keep(request_line: int, lines: tuple[tuple[str, int, int], ...], required: int, ordered: bool) -> tuple[str, ...]:
    """Names to keep: the first ``required`` always, then the most optional ones that leave the request safe."""
    must, optional = lines[:required], lines[required:]

    def first_safe(count: int) -> tuple[tuple[str, int, int], ...] | None:
        for picked in itertools.combinations(optional, count):  # earlier (more important) headers first
            chosen = sorted(must + picked, key=lambda line: line[0].encode()) if ordered else must + picked
            if not _layouts_unsafe(request_line, tuple((n, l) for _, n, l in chosen), ordered):
                return must + picked
        return None

    best = must
    # in any order a header only adds risk, so the safe sets stop growing at the first size with none
    for count in range(len(optional), -1, -1) if ordered else range(1, len(optional) + 1):
        found = first_safe(count)
        if ordered and found:
            best = found
            break
        if not ordered:
            if not found:
                break
            best = found
    return tuple(name for name, _, _ in best)


def safe_headers(headers: dict[str, Any] | str, path: str, method: str = "GET", required: tuple[str, ...] = ("Host", "User-Agent"), xray: bool = True) -> dict[str, Any]:
    """``headers`` (a dict or its JSON) cut down to the ones the server can always read.

    ``xray``: the client is xray, which sends them sorted by name (byte order); else (sing-box) in a random order
    on each connection. A value that is a list (xray picks one per connection) is reduced to one choice here.
    """
    if isinstance(headers, str):
        headers = json.loads(headers)
    values = {k: random.choice(v) if isinstance(v, list) and v else v for k, v in headers.items()}
    order = [k for k in required if k in values] + [k for k in values if k not in required]
    lines = tuple((k, len(k) + 2, len(k) + 2 + len(str(values[k])) + 2) for k in order)
    keep = _keep(len(f"{method} {path} HTTP/1.1\r\n"), lines, sum(k in values for k in required), xray)
    kept = {k: [values[k]] if isinstance(headers[k], list) else values[k] for k in headers if k in keep}
    if not xray:
        kept.pop("Host", None)  # sing-box sends it from the transport's "host"
    return kept
