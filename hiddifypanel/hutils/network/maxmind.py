"""Lazy MaxMind GeoLite DB access — single typesafe IP lookup API."""

from __future__ import annotations

import ipaddress
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from hiddifypanel.cache import STATIC, cache

_IPASN: Any = None
_IPCOUNTRY: Any = None
_IPCITY: Any = None
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


def _db_folder() -> Path:
    """Where services/panel/install.sh downloads the databases (not the working directory: a panel started from
    elsewhere, e.g. the debugger, found nothing and saw every IP as unknown)."""
    candidates = [Path(os.environ.get("HIDDIFY_CONFIG_PATH", "/opt/hiddify-manager")) / "services/panel", Path("/opt/hiddify-manager/services/panel"), Path.cwd()]
    return next((c for c in candidates if (c / "GeoLite2-ASN.mmdb").is_file()), candidates[0])


def normalize_ip(ip: str) -> str:
    """The client address as a plain IP: the first of a list (X-Forwarded-For), no brackets or port, an IPv4 seen
    through an IPv6 socket (::ffff:1.2.3.4) as IPv4. "" when it is not an IP."""
    first = str(ip or "").split(",")[0].strip()
    if first.startswith("["):
        first = first[1:].split("]")[0]
    elif first.count(":") == 1:  # 1.2.3.4:5678
        first = first.split(":")[0]
    try:
        addr = ipaddress.ip_address(first)
    except ValueError:
        return ""
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return str(addr)


def _record(db: Any, ip: str) -> dict | None:
    if not db:
        return None
    try:
        row = db.get(ip)
    except BaseException:
        return None
    return row if isinstance(row, dict) else None


def _ensure_loaded() -> None:
    global _IPASN, _IPCOUNTRY, _IPCITY, _LOADED, _AVAILABLE
    if _LOADED:
        return
    _LOADED = True
    try:
        import maxminddb

        folder = _db_folder()
        _IPASN = maxminddb.open_database(str(folder / "GeoLite2-ASN.mmdb"))
        _IPCOUNTRY = maxminddb.open_database(str(folder / "GeoLite2-Country.mmdb"))
        _AVAILABLE = True
        city_path = folder / "GeoLite2-City.mmdb"
        if city_path.is_file():
            try:
                _IPCITY = maxminddb.open_database(str(city_path))
            except BaseException as e:
                logger.error(f"Error can not load GeoLite2-City: {e}")
                _IPCITY = None
    except BaseException as e:
        logger.error(f"Error can not load maxminddb: {e}")
        _IPASN = {}
        _IPCOUNTRY = {}
        _IPCITY = None
        _AVAILABLE = False


def is_available() -> bool:
    """Whether MaxMind databases were loaded successfully."""
    _ensure_loaded()
    return _AVAILABLE


def raw_records(ip: str) -> tuple[dict | None, dict | None, dict | None]:
    """City, country and ASN rows for ``ip``. City is None when GeoLite2-City is not installed."""
    ip = normalize_ip(ip)
    _ensure_loaded()
    if not ip or not _AVAILABLE:
        return None, None, None
    return _record(_IPCITY, ip), _record(_IPCOUNTRY, ip), _record(_IPASN, ip)


def get_ip_info(ip: str) -> IpInfo:
    """
    Look up country / ASN info for ``ip`` (lazy-loads MaxMind DBs on first call).

    Returns an :class:`IpInfo` with ``unknown`` fields when lookup fails. Only real lookups are cached: an answer from
    a moment the databases were missing is not kept.
    """
    ip = normalize_ip(ip)
    if not ip:
        return IpInfo(ip="", db_available=is_available())
    _ensure_loaded()
    if not _AVAILABLE:
        return IpInfo(ip=ip, db_available=False)
    return _lookup(ip)


@cache.cache(modes=STATIC)
def _lookup(ip: str) -> IpInfo:

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


_ASN_ORGS: dict[int, str] | None = None
_ASN_ORGS_LOCK = threading.Lock()


def asn_org(asn: int) -> str | None:
    """The company of an AS number ("Respina Networks & Beyond PJSC" for 42337), from GeoLite2-ASN.

    The database is keyed by IP range: the first call builds an AS number index from all of it (a few seconds, kept in
    memory for this process). None when the AS is not in it or the database is missing.
    """
    global _ASN_ORGS
    if _ASN_ORGS is None:
        with _ASN_ORGS_LOCK:
            if _ASN_ORGS is None:
                _ensure_loaded()
                index: dict[int, str] = {}
                if _AVAILABLE:
                    for _network, record in _IPASN:
                        number = (record or {}).get("autonomous_system_number")
                        if number and number not in index:
                            index[number] = str(record.get("autonomous_system_organization") or "")
                _ASN_ORGS = index
    return _ASN_ORGS.get(int(asn)) or None
