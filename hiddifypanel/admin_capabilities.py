"""Per-admin capabilities (``AdminUser.capabilities`` JSON).

A parent may grant only capabilities it has; a sub-admin cannot change its own
capabilities or grant one it lacks. Super admins always have every capability.
"""

from __future__ import annotations

from typing import Any

from hiddifypanel.models.admin import AdminMode

ADD_SUB_ADMINS = "add_sub_admins"
OVERRIDE_PREFERRED_OUTBOUND = "override_preferred_outbound"
ADD_EXTRA_SUBLINKS = "add_extra_sublinks"
MODIFY_USER_EXTRA = "modify_user_extra"
MODIFY_DOMAINS = "modify_domains"
MODIFY_OUTBOUNDS = "modify_outbounds"

ALL: tuple[str, ...] = (
    ADD_SUB_ADMINS,
    OVERRIDE_PREFERRED_OUTBOUND,
    ADD_EXTRA_SUBLINKS,
    MODIFY_USER_EXTRA,
    MODIFY_DOMAINS,
    MODIFY_OUTBOUNDS,
)


def empty() -> dict[str, bool]:
    return {k: False for k in ALL}


def full() -> dict[str, bool]:
    return {k: True for k in ALL}


def normalize(value: Any) -> dict[str, bool]:
    """Always every known key as bool (unknown keys dropped)."""
    src = value if isinstance(value, dict) else {}
    return {k: bool(src.get(k)) for k in ALL}


def defaults_for_mode(mode: AdminMode | str | None, *, can_add_admin: bool = False) -> dict[str, bool]:
    """Defaults used by the DB migration and when creating a new admin with no ``capabilities`` payload."""
    m = str(getattr(mode, "value", mode) or AdminMode.agent)
    if m == AdminMode.super_admin:
        return full()
    if m == AdminMode.admin:
        return {
            ADD_SUB_ADMINS: bool(can_add_admin),
            OVERRIDE_PREFERRED_OUTBOUND: True,
            ADD_EXTRA_SUBLINKS: True,
            MODIFY_USER_EXTRA: True,
            MODIFY_DOMAINS: True,
            MODIFY_OUTBOUNDS: False,
        }
    return {
        ADD_SUB_ADMINS: bool(can_add_admin),
        OVERRIDE_PREFERRED_OUTBOUND: False,
        ADD_EXTRA_SUBLINKS: True,
        MODIFY_USER_EXTRA: True,
        MODIFY_DOMAINS: False,
        MODIFY_OUTBOUNDS: False,
    }


def of(admin: Any) -> dict[str, bool]:
    """Effective capabilities of ``admin`` (super admin: all True)."""
    if admin is None:
        return empty()
    if getattr(admin, "mode", None) == AdminMode.super_admin or str(getattr(admin, "mode", "")) == AdminMode.super_admin:
        return full()
    caps = getattr(admin, "capabilities", None)
    if not caps:
        # Pre-migration / empty: fall back from can_add_admin + mode so old rows keep working.
        return defaults_for_mode(getattr(admin, "mode", None), can_add_admin=bool(getattr(admin, "can_add_admin", False)))
    return normalize(caps)


def has(admin: Any, capability: str) -> bool:
    return bool(of(admin).get(capability))


def require(capability: str) -> None:
    """Abort 403 when the signed-in admin lacks ``capability``."""
    from apiflask import abort

    from hiddifypanel import g

    if not has(g.account, capability):
        abort(403, f"Missing capability: {capability}")


def merge_for_actor(actor: Any, proposed: Any, *, existing: Any = None, creating: bool = False) -> dict[str, bool]:
    """Capabilities a parent may write onto a sub-admin.

    - Keys the actor lacks are left as in ``existing`` (creating: agent defaults).
    - The actor cannot turn on / change a capability it does not have.
    - ``proposed`` may be a partial dict; omitted keys keep the base.
    """
    # Creating: start empty so the parent must grant each capability explicitly.
    # Editing: keep capabilities the actor cannot touch.
    if existing is not None:
        base = normalize(existing)
    else:
        base = empty()
    actor_caps = of(actor)
    out = dict(base)
    if isinstance(proposed, dict):
        for key in ALL:
            if key not in proposed or not actor_caps[key]:
                continue
            out[key] = bool(proposed[key])
    for key in ALL:
        if out[key] and not actor_caps[key]:
            out[key] = base[key]
    return out


def sync_can_add_admin(capabilities: dict[str, bool]) -> bool:
    return bool(capabilities.get(ADD_SUB_ADMINS))
