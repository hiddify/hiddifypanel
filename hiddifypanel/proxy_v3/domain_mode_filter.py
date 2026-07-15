from __future__ import annotations

from typing import Protocol

from hiddifypanel.models import Domain, DomainType, FakeMode

from hiddifypanel.proxy_v3.context_vars.domain import DomainIPVar

_CDN_MODES = {DomainType.cdn, DomainType.auto_cdn_ip, DomainType.worker}
_DIRECT_MODES = {DomainType.direct, DomainType.old_xtls_direct, DomainType.dnstt}


class _DomainLike(Protocol):
    mode: DomainType
    fake_mode: FakeMode


def _domain_matches_bucket(domain: _DomainLike, bucket: str) -> bool:
    bucket = (bucket or "").strip().lower()
    if not bucket:
        return False
    fm = domain.fake_mode
    mode = domain.mode

    if bucket == "fake":
        return fm == FakeMode.fake
    if bucket in ("reality", "special"):
        return fm == FakeMode.reality
    if bucket == "direct":
        return fm == FakeMode.valid and mode in (_DIRECT_MODES | {DomainType.sub_link_only})
    if bucket == "relay":
        return fm == FakeMode.valid and mode == DomainType.relay
    if bucket == "cdn":
        return fm == FakeMode.valid and mode in _CDN_MODES
    return False


def proxy_buckets_for_domain(mode: DomainType, fake_mode: FakeMode) -> list[str]:
    if fake_mode == FakeMode.reality:
        return ["reality"]
    if fake_mode == FakeMode.fake:
        return ["fake"]
    if mode == DomainType.sub_link_only:
        return ["direct"]
    if mode == DomainType.relay:
        return ["relay"]
    if mode.is_cdn() or mode == DomainType.worker:
        return ["cdn"]
    if mode in (DomainType.direct, DomainType.old_xtls_direct, DomainType.dnstt):
        return ["direct"]
    return ["direct", "cdn", "relay", "fake", "reality"]


def domain_matches_modes(domain: Domain, modes: list[str]) -> bool:
    if not modes:
        return True
    return any(_domain_matches_bucket(domain, bucket) for bucket in modes)


def domain_ip_matches_modes(domain: DomainIPVar, modes: list[str]) -> bool:
    if not modes:
        return True
    return any(_domain_matches_bucket(domain, bucket) for bucket in modes)
