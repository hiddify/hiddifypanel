"""Admin sign-in rules: strong passwords, aliases (usernames instead of the UUID), and a login throttle.

* Passwords admins set must be strong (``password_problems``): generated ones already are.
* An alias lets an admin sign in with ``alias + password`` instead of the UUID link. It is lowercase,
  unique, 6–64 of ``a-z 0-9 . _ -``, never UUID-shaped, never for super admins, and only works while the
  admin's password is strong (a weak or empty password can not be guessed through a known name).
* Failed sign-ins are counted per client IP; after ``MAX_FAILURES`` the IP waits ``LOCK_SECONDS``.
"""

from __future__ import annotations

import re
import secrets
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from hiddifypanel.models import AdminUser

MIN_PASSWORD = 10
ALIAS_MIN = 6
ALIAS_MAX = 64
_ALIAS_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$", re.IGNORECASE)
_COMMON = {
    "password", "password1", "passw0rd", "123456789", "1234567890", "12345678", "qwerty123", "qwertyuiop",
    "iloveyou", "admin123", "administrator", "letmein123", "welcome123", "abc123456", "hiddify", "hiddify123",
}  # fmt: skip

MAX_FAILURES = 10
LOCK_SECONDS = 15 * 60


# --------------------------------------------------------------------------- passwords


def password_problems(password: str, *, avoid: tuple[str | None, ...] = ()) -> list[str]:
    """Why ``password`` is weak (empty list: strong). Codes are translated by the UI."""
    problems: list[str] = []
    pw = password or ""
    if len(pw) < MIN_PASSWORD:
        problems.append("too_short")
    if not re.search(r"[a-z]", pw):
        problems.append("needs_lower")
    if not re.search(r"[A-Z]", pw):
        problems.append("needs_upper")
    if not re.search(r"\d", pw):
        problems.append("needs_digit")
    lowered = pw.lower()
    if lowered in _COMMON or len(set(pw)) < 5:
        problems.append("too_common")
    for word in avoid:
        if word and len(word) >= 4 and word.lower() in lowered:
            problems.append("contains_name")
            break
    return problems


def is_strong(password: str | None, *, avoid: tuple[str | None, ...] = ()) -> bool:
    return bool(password) and not password_problems(password or "", avoid=avoid)


def admin_avoid(admin: AdminUser) -> tuple[str | None, ...]:
    return (admin.name, admin.alias, admin.uuid)


# --------------------------------------------------------------------------- aliases


def normalize_alias(value: str | None) -> str:
    return (value or "").strip().lower()


def alias_problem(alias: str, admin: AdminUser) -> str | None:
    """Why ``alias`` can not be set on ``admin`` (None: it can). An empty alias always can (removes it)."""
    from hiddifypanel.models import AdminMode, AdminUser

    if not alias:
        return None
    if admin.mode == AdminMode.super_admin:
        return "super_admin"
    if len(alias) < ALIAS_MIN:
        return "too_short"
    if len(alias) > ALIAS_MAX:
        return "too_long"
    if not _ALIAS_RE.match(alias):
        return "bad_chars"
    if _UUID_RE.match(alias):
        return "looks_like_uuid"
    taken = AdminUser.query.filter(AdminUser.alias == alias, AdminUser.id != (admin.id or 0)).first()
    if taken:
        return "taken"
    if not is_strong(admin.password, avoid=admin_avoid(admin)):
        return "weak_password"
    return None


ALIAS_MESSAGES = {
    "super_admin": "Super admins sign in with their link only (no alias)",
    "too_short": f"The alias needs at least {ALIAS_MIN} characters",
    "too_long": f"The alias can have at most {ALIAS_MAX} characters",
    "bad_chars": "Use only a-z, 0-9, dot, dash and underscore, starting with a letter or digit",
    "looks_like_uuid": "The alias can not look like a UUID",
    "taken": "Another admin uses this alias",
    "weak_password": "Set a strong password first: an alias only works with a strong password",
}
PASSWORD_MESSAGE = f"Use a strong password: at least {MIN_PASSWORD} characters with lowercase and uppercase letters and digits, not a common one and not your name"


# --------------------------------------------------------------------------- sign in


def find_admin(identifier: str) -> AdminUser | None:
    """The admin for a UUID or an alias."""
    from hiddifypanel.models import AdminUser

    ident = (identifier or "").strip()
    if not ident:
        return None
    if _UUID_RE.match(ident):
        return AdminUser.by_uuid(ident.lower())
    alias = normalize_alias(ident)
    return AdminUser.query.filter(AdminUser.alias == alias).first() if alias else None


def check_admin_login(identifier: str, password: str) -> AdminUser | None:
    """The admin if ``identifier`` + ``password`` sign in, else None.

    UUID: the password must match (an admin without a password signs in with an empty one, as before).
    Alias: the password must match and be strong; super admins have no alias.
    """
    from hiddifypanel.models import AdminMode

    admin = find_admin(identifier)
    if admin is None or admin.deleted:
        return None
    stored = admin.password or ""
    if not secrets.compare_digest(stored.encode(), (password or "").encode()):
        return None
    by_alias = not _UUID_RE.match((identifier or "").strip())
    if by_alias and (admin.mode == AdminMode.super_admin or not is_strong(stored, avoid=admin_avoid(admin))):
        return None
    return admin


def _fail_key(ip: str) -> str:
    return f"admin_login_fail:{ip}"


def login_locked(ip: str) -> bool:
    try:
        from hiddifypanel.cache import redis_client

        return int(redis_client.get(_fail_key(ip)) or 0) >= MAX_FAILURES
    except Exception as e:  # no redis: no throttle
        logger.debug(f"login throttle unavailable: {e}")
        return False


def record_failure(ip: str) -> None:
    try:
        from hiddifypanel.cache import redis_client

        key = _fail_key(ip)
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, LOCK_SECONDS)
    except Exception as e:
        logger.debug(f"login throttle unavailable: {e}")


def clear_failures(ip: str) -> None:
    try:
        from hiddifypanel.cache import redis_client

        redis_client.delete(_fail_key(ip))
    except Exception:
        pass
