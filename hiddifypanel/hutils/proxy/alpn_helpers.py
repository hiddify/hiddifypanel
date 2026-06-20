from __future__ import annotations

ALPN_TAG_VALUES: dict[str, list[str]] = {
    'tls_h3': ['h3'],
    'tls_h3_quic': ['h3'],
    'tls_h3_h2_h1': ['h3', 'h2', 'http/1.1'],
    'tls_h2_h1': ['h2', 'http/1.1'],
    'tls_h2': ['h2', 'http/1.1'],
    'tls_h1': ['http/1.1'],
    'h2c': [],
    'h1': [],
    'h2': [],
    'custom': [],
}

TLS_ALPN_TAGS = frozenset({
    'tls_h3',
    'tls_h3_quic',
    'tls_h3_h2_h1',
    'tls_h2_h1',
    'tls_h2',
    'tls_h1',
})

DEFAULT_OUTBOUND_TAG_TEMPLATE = '{{ proxy.tag }} {{ domain.alias or domain.name }} {{ proxy.alpn }}'

L3_ALPN_TAGS: dict[str, list[str]] = {
    'http': ['h1', 'h2c'],
    'tls': ['h1', 'tls_h1', 'tls_h2_h1'],
    'tls_h2': ['h1', 'tls_h2', 'tls_h2_h1'],
    'h3_quic': ['tls_h3', 'tls_h3_quic', 'tls_h3_h2_h1'],
    'reality': ['tls_h2_h1'],
}

L3_DOWNLOAD_ALPN_TAGS: dict[str, list[str]] = {
    'http': ['tls_h1', 'tls_h2'],
    'tls': ['tls_h1', 'tls_h2'],
    'tls_h2': ['tls_h1', 'tls_h2'],
    'h3_quic': ['tls_h1', 'tls_h2', 'tls_h3'],
}


def alpns_for_l3(l3: str | None) -> list[str]:
    if not l3:
        return ['tls_h2_h1']
    return list(L3_ALPN_TAGS.get(str(l3).lower(), ['tls_h2_h1']))


def download_alpns_for_l3(l3: str | None) -> list[str]:
    if not l3:
        return ['tls_h1', 'tls_h2']
    return list(L3_DOWNLOAD_ALPN_TAGS.get(str(l3).lower(), ['tls_h1', 'tls_h2']))


def alpns_for_combo(l3: str, transport: str) -> list[str]:
    tags = alpns_for_l3(l3)
    if str(transport).lower() == 'xhttp' and str(l3).lower() not in ('http', 'reality'):
        if 'h1' not in tags:
            tags = ['h1', *tags]
    return list(dict.fromkeys(tags))


def is_xhttp_proxy_data(data: dict) -> bool:
    tags = [str(t).lower() for t in (data.get('tags') or [])]
    if 'xhttp' in tags:
        return True
    name = str(data.get('name') or '').lower()
    slug = str(data.get('slug') or '').lower()
    return 'xhttp' in name or 'xhttp' in slug


def alpn_list_for_tag(tag: str | None) -> list[str]:
    if not tag:
        return []
    return list(ALPN_TAG_VALUES.get(tag, []))


def is_tls_alpn_tag(tag: str | None) -> bool:
    if not tag:
        return False
    if tag in TLS_ALPN_TAGS:
        return True
    return tag.startswith('tls_')


def stable_proxy_port(proxy_id: int | None, domain_id: int | None = None) -> int:
    """Deterministic port in [10000, 50000] from proxy and domain ids."""
    pid = int(proxy_id or 0)
    did = int(domain_id or 0)
    if pid <= 0:
        return 2080
    mixed = (pid * 1_000_003 + did * 1_009 + 17) % 40_001
    return 10_000 + mixed
