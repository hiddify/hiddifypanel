from __future__ import annotations

from hiddifypanel.models import Domain, DomainType

_SPECIAL_DOMAIN_TYPES = {
    DomainType.special_reality_tcp,
    DomainType.special_reality_xhttp,
    DomainType.special_reality_grpc,
}

_MODE_TO_DOMAIN_TYPES: dict[str, set[DomainType]] = {
    'direct': {DomainType.direct, DomainType.old_xtls_direct, DomainType.dnstt},
    'cdn': {DomainType.cdn, DomainType.auto_cdn_ip, DomainType.worker},
    'relay': {DomainType.relay},
    'fake': {DomainType.fake},
    'special': _SPECIAL_DOMAIN_TYPES,
}


def domain_matches_modes(domain: Domain, modes: list[str]) -> bool:
    if not modes:
        return True
    mode_value = domain.mode.value if domain.mode else ''
    allowed: set[DomainType] = set()
    for bucket in modes:
        if bucket == 'special':
            allowed |= _SPECIAL_DOMAIN_TYPES
            continue
        allowed |= _MODE_TO_DOMAIN_TYPES.get(bucket, set())
    if domain.mode in allowed:
        return True
    if 'special' in modes and 'special' in mode_value:
        return True
    return False
