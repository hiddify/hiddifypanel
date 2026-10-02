"""Lazy MaxMind GeoLite DB access — single typesafe IP lookup API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger

from hiddifypanel.cache import cache

_IPASN: Any = None
_IPCOUNTRY: Any = None
_LOADED = False
_AVAILABLE = False

_ASN_SHORT_MAP: dict[str, str] = {
    "58224": "MKH",
    "197207": "MCI",
    "12880": "ITC",
    "44244": "MTN",
    "57218": "RTL",
    "16322": "PRS",
    "56402": "HWB",
    "41689": "AST",
    "43754": "AST",
    "31549": "SHT",
    "205647": "SHT",
    "50810": "MBT",
    "39308": "ASK",
    "205207": "RSP",
    "25184": "AFR",
    "394510": "ZTL",
    "206065": "ZTL",
    "49100": "PSM",
}

ASN_SHORT_NAMES: frozenset[str] = frozenset(_ASN_SHORT_MAP.values())


@dataclass(frozen=True, slots=True)
class IpInfo:
    """Geo / ASN details for an IP address."""

    ip: str
    country: str = "unknown"
    asn: str = "unknown"
    asn_org: str = "unknown"
    short_name: str = "unknown"
    db_available: bool = False


def _ensure_loaded() -> None:
    global _IPASN, _IPCOUNTRY, _LOADED, _AVAILABLE
    if _LOADED:
        return
    _LOADED = True
    try:
        import maxminddb

        _IPASN = maxminddb.open_database("GeoLite2-ASN.mmdb")
        _IPCOUNTRY = maxminddb.open_database("GeoLite2-Country.mmdb")
        _AVAILABLE = True
    except BaseException:
        logger.error("Error can not load maxminddb")
        _IPASN = {}
        _IPCOUNTRY = {}
        _AVAILABLE = False


def is_available() -> bool:
    """Whether MaxMind databases were loaded successfully."""
    _ensure_loaded()
    return _AVAILABLE


@cache.cache()
def get_ip_info(ip: str) -> IpInfo:
    """
    Look up country / ASN info for ``ip`` (lazy-loads MaxMind DBs on first call).

    Returns an :class:`IpInfo` with ``unknown`` fields when lookup fails.
    """
    if not ip:
        return IpInfo(ip="", db_available=is_available())

    if isinstance(ip, str) and "," in ip:
        ip = ip.split(",")[0].strip()

    _ensure_loaded()
    if not _AVAILABLE:
        return IpInfo(ip=ip, db_available=False)

    country = "unknown"
    asn = "unknown"
    asn_org = "unknown"
    short_name = "unknown"

    try:
        country_rec = _IPCOUNTRY.get(ip) or {}
        country = str(country_rec.get("country", {}).get("iso_code") or "unknown")
    except BaseException:
        pass

    try:
        asn_rec = _IPASN.get(ip) or {}
        asn_num = asn_rec.get("autonomous_system_number")
        if asn_num is not None:
            asn = str(asn_num)
            short_name = _ASN_SHORT_MAP.get(asn, "unknown")
        asn_org = str(asn_rec.get("autonomous_system_organization") or "unknown")
    except BaseException:
        pass

    return IpInfo(
        ip=ip,
        country=country,
        asn=asn,
        asn_org=asn_org,
        short_name=short_name,
        db_available=True,
    )
