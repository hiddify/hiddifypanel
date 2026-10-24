"""The caller's own IP, from the local GeoLite databases plus country metadata.

Geo answers barely change, so a hit is kept for an hour. A moment when the databases are missing is not cached.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from babel.languages import get_territory_language_info
from babel.numbers import get_currency_name, get_territory_currencies

from hiddifypanel.cache import STATIC, cache

_OFFICIAL = {"official", "de_facto_official"}
_CACHE_TTL = 3600


def _en(node: dict | None) -> str:
    names = (node or {}).get("names") if isinstance(node, dict) else None
    if isinstance(names, dict) and names.get("en"):
        return str(names["en"])
    return ""


def _pick(primary: dict, secondary: dict, key: str):
    return primary.get(key) or secondary.get(key)


def _languages(country_code: str) -> str:
    """Official languages as BCP 47 tags, most spoken first (``en-CA,fr-CA``)."""
    if len(country_code) != 2:
        return ""
    try:
        info = get_territory_language_info(country_code) or {}
    except Exception:
        return ""
    ranked: list[tuple[float, str]] = []
    for code, meta in info.items():
        if not isinstance(meta, dict) or meta.get("official_status") not in _OFFICIAL:
            continue
        base = str(code).split("_", 1)[0]
        if not base.isalpha() or not 2 <= len(base) <= 3:
            continue
        ranked.append((-(float(meta.get("population_percent") or 0)), f"{base}-{country_code}"))
    seen: list[str] = []
    for _pct, tag in sorted(ranked):
        if tag not in seen:
            seen.append(tag)
    return ",".join(seen)


def _currency(country_code: str) -> tuple[str, str]:
    if len(country_code) != 2:
        return "", ""
    try:
        codes = get_territory_currencies(country_code, start_date=date.today(), tender=True)
    except Exception:
        return "", ""
    if not codes:
        return "", ""
    code = str(codes[0])
    try:
        name = get_currency_name(code, locale="en") or ""
    except Exception:
        name = ""
    return code, str(name)


def _utc_offset(tz_name: str) -> str:
    if not tz_name:
        return ""
    try:
        return datetime.now(ZoneInfo(tz_name)).strftime("%z")
    except Exception:
        return ""


def _coord(location: dict, key: str) -> float | None:
    value = location.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def describe_ip(ip: str, *, city: dict | None, country: dict | None, asn: dict | None) -> dict:
    """One lookup. Empty strings (and null coordinates) when that field is unknown."""
    place = city or {}
    fallback = country or {}
    country_node = _pick(place, fallback, "country") or _pick(place, fallback, "registered_country") or {}
    continent = _pick(place, fallback, "continent") or {}
    location = place.get("location") if isinstance(place.get("location"), dict) else {}
    subdivisions = place.get("subdivisions") if isinstance(place.get("subdivisions"), list) else []
    region = subdivisions[0] if subdivisions and isinstance(subdivisions[0], dict) else {}
    country_code = str(country_node.get("iso_code") or "")
    timezone = str(location.get("time_zone") or "")
    number = (asn or {}).get("autonomous_system_number")
    currency, currency_name = _currency(country_code)
    return {
        "ip": ip,
        "city": _en(place.get("city") if isinstance(place.get("city"), dict) else None),
        "region": _en(region),
        "region_code": str(region.get("iso_code") or ""),
        "country_name": _en(country_node),
        "country_code": country_code,
        "continent_code": str(continent.get("code") or ""),
        "latitude": _coord(location, "latitude"),
        "longitude": _coord(location, "longitude"),
        "timezone": timezone,
        "utc_offset": _utc_offset(timezone),
        "currency": currency,
        "currency_name": currency_name,
        "languages": _languages(country_code),
        "asn": f"AS{number}" if number else "",
        "org": str((asn or {}).get("autonomous_system_organization") or ""),
    }


@cache.cache(ttl=_CACHE_TTL, modes=STATIC)
def _cached_lookup(ip: str) -> dict:
    from hiddifypanel.hutils.network import maxmind

    city, country, asn = maxmind.raw_records(ip)
    return describe_ip(ip, city=city, country=country, asn=asn)


def lookup(ip: str) -> dict:
    """``ip`` is the caller's address. Unknown or not-yet-loaded databases return the address alone."""
    from hiddifypanel.hutils.network import maxmind

    ip = maxmind.normalize_ip(ip)
    if not ip or not maxmind.is_available():
        return describe_ip(ip, city=None, country=None, asn=None)
    return _cached_lookup(ip)
