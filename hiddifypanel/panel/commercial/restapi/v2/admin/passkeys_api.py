"""My account: the signed-in admin's passkeys (list, add, remove). How passkeys work: ``hiddifypanel/passkeys.py``."""

from __future__ import annotations


from flask import request, session
from flask.views import MethodView

from hiddifypanel import g, passkeys
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.hutils.flask import hurl_for
from hiddifypanel.models import AdminPasskey, AdminUser, ConfigEnum, hconfig
from hiddifypanel.models.role import Role

ALL_ROLES = {Role.super_admin, Role.admin, Role.agent}


def _domain() -> str | None:
    """The domain a passkey added from this page belongs to (None on an IP: passkeys need a domain)."""
    return passkeys.rp_id_for(request.host)


def after_password_login(admin: AdminUser) -> None:
    """A password sign-in: suggest a passkey on the next dashboard page."""
    session["passkey_suggest"] = True


def take_suggestion(admin: AdminUser) -> dict | None:
    """Once after a password sign-in, when the admin has no passkey yet on this domain or another of the panel's.

    Also once per sign-in on a domain without my passkey while I use passkeys on others (e.g. after opening the panel
    on another domain with the admin link): the dashboard offers this one right away."""
    after_password = session.pop("passkey_suggest", False)
    here = _domain()
    if not after_password and (not here or session.get("passkey_offered")):
        return None
    try:
        missing = passkeys.missing_domains(admin, here)
        if not after_password:
            session["passkey_offered"] = True
            if here not in missing or not AdminPasskey.query.filter(AdminPasskey.admin_id == admin.id).first():
                return None
    except Exception:
        return None
    return {"domain": here, "missing": missing} if missing else None


class MyPasskeysApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def get(self):
        """My account: my passkeys (each works on its own domain), and the domain a new one is added for"""
        actor: AdminUser = g.account
        rows = AdminPasskey.query.filter(AdminPasskey.admin_id == actor.id).order_by(AdminPasskey.id).all()
        return {
            "passkeys": [p.to_dict() for p in rows],
            "domain": _domain(),
            # The panel's domains (this one first) where I have no passkey yet: "Add passkey" goes through them.
            "missing": passkeys.missing_domains(actor, _domain()),
        }

    def post(self):
        """My account: add a passkey (the browser made it with the options below)"""
        actor: AdminUser = g.account
        body = request.get_json(silent=True) or {}
        try:
            row = passkeys.register(actor, body.get("credential"), str(body.get("name") or ""), origin=f"https://{request.host}", user_agent=request.user_agent.string)
        except passkeys.PasskeyError as e:
            return {"message": str(e), "code": e.code}, 400
        return row.to_dict()


class MyPasskeyOptionsApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def post(self):
        """My account: start adding a passkey for this domain (the browser's options)"""
        actor: AdminUser = g.account
        domain = _domain()
        if not domain:
            return {"message": "Open the panel on one of its domains to add a passkey", "code": "needs_domain"}, 400
        title = str(hconfig(ConfigEnum.branding_title) or "Hiddify")
        return {"options": passkeys.creation_options(actor, domain, title)}


class MyPasskeyTourApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def post(self):
        """My account: the step pages (shown in a frame) that add my passkey on the panel's other domains"""
        actor: AdminUser = g.account
        try:
            lang = str((request.get_json(silent=True) or {}).get("lang") or "")
            steps = passkeys.plan_enrollment(actor, request.host, hurl_for("common_bp.LoginView:passkey_enroll"), lang)
        except Exception as e:  # no Redis: the other domains get their passkey when the admin signs in there
            return {"message": f"Could not prepare the other domains: {e}", "code": "tour_failed"}, 400
        return {"steps": steps}


class MyPasskeyItemApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def delete(self, passkey_id: int):
        """My account: remove one of my passkeys"""
        actor: AdminUser = g.account
        removed = AdminPasskey.query.filter(AdminPasskey.id == passkey_id, AdminPasskey.admin_id == actor.id).delete()
        db.session.commit()
        if not removed:
            return {"message": "No such passkey", "code": "not_found"}, 404
        return {"status": 200, "msg": "ok"}
