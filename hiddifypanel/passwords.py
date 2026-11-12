"""Account passwords (admins and users) are kept as salted scrypt hashes, never as the password itself.

* ``hash_password`` makes the stored value (werkzeug's ``scrypt:N:r:p$salt$hash``, a new random salt each time). An empty
  password stays ``""``: it means "no password" (the account signs in with its link).
* ``verify_password`` checks a password against the stored value in constant time. A value stored before hashing
  (``is_hashed`` false, e.g. from an old backup) is still accepted once: ``needs_rehash`` tells the caller to store
  the hash instead, and the same happens when the hash parameters below get stronger.
* The models hash on assignment (``BaseAccount.password``), so no code path stores a password as it was typed.

A check costs about a tenth of a second (that is the point of scrypt). A correct check is remembered for a few minutes in
this process, so API clients that send their password with every request (HTTP basic auth) do not pay it each time; the
memo is keyed by the stored hash, so a new password is never answered from it.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import OrderedDict

from werkzeug.security import check_password_hash, generate_password_hash

#: How new passwords are hashed. A stored hash made with other parameters is replaced at its next sign-in.
METHOD = "scrypt:32768:8:1"
_PREFIXES = ("scrypt:", "pbkdf2:")

_MEMO_SECONDS = 300
_MEMO_SIZE = 2048
_memo_key = secrets.token_bytes(32)
_memo: OrderedDict[bytes, float] = OrderedDict()
_memo_lock = threading.Lock()


def is_hashed(stored: str | None) -> bool:
    """Whether ``stored`` is a hash this module made (else: no password, or one kept before hashing)."""
    return bool(stored) and stored.startswith(_PREFIXES) and stored.count("$") == 2


def hash_password(password: str | None) -> str:
    """The value to store for ``password`` ("" stays "": no password)."""
    if not password:
        return ""
    return generate_password_hash(password, method=METHOD)


def needs_rehash(stored: str | None) -> bool:
    """A stored value that should be replaced by a new hash after a correct sign-in."""
    return bool(stored) and not (is_hashed(stored) and stored.startswith(METHOD + "$"))


def _memo_id(stored: str, password: str) -> bytes:
    return hmac.new(_memo_key, f"{stored}\0{password}".encode(), hashlib.sha256).digest()


def verify_password(stored: str | None, password: str | None) -> bool:
    """Whether ``password`` is the account's password. No password stored: only an empty one matches."""
    stored, password = stored or "", password or ""
    if not stored:
        return not password
    if not password:
        return False
    if not is_hashed(stored):  # kept before hashing: the caller stores the hash (needs_rehash)
        return secrets.compare_digest(stored.encode(), password.encode())
    key = _memo_id(stored, password)
    now = time.monotonic()
    with _memo_lock:
        seen = _memo.get(key)
        if seen is not None and now - seen < _MEMO_SECONDS:
            return True
    try:
        ok = check_password_hash(stored, password)
    except (ValueError, TypeError):
        return False
    if ok:
        with _memo_lock:
            _memo[key] = now
            _memo.move_to_end(key)
            while len(_memo) > _MEMO_SIZE:
                _memo.popitem(last=False)
    return ok
