from flask import jsonify, redirect, render_template

import hiddifypanel
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.hutils import flask as hutils_flask
from hiddifypanel.hutils.flask import hurl_for
from hiddifypanel.models import ConfigEnum, Role, hconfig

from .v2_menu import build_admin_v2_menu, build_admin_v2_notices, build_admin_v2_system_actions


def _panel_version() -> str:
    if not hiddifypanel.is_released_version:
        return "DEV"
    return hiddifypanel.__version__


def _panel_logo_url(proxy_path: str) -> str:
    static_path = hutils_flask.static_url_for(filename="images/WhiteLogo.png")
    if static_path.startswith("/"):
        return static_path
    return f"/{proxy_path}/{static_path.lstrip('/')}"


def _node_info() -> dict | None:
    """What a node's home page shows: its name and the parent it is connected to."""
    if not hutils.node.is_child():
        return None
    return {
        "node_name": hconfig(ConfigEnum.node_name) or "",
        "parent_host": hutils.node.child.parent_panel_host(),
        "parent_dashboard_url": hutils.node.child.parent_admin_dashboard_url(g.account.uuid),
    }


def _telegram_info() -> dict | None:
    """The panel's Telegram bot (when set up) and how this admin connects to it."""
    bot = g.get("bot")
    username = getattr(bot, "username", None) if bot else None
    if not username:
        return None
    return {
        "bot_username": username,
        "connect_url": f"tg://resolve?domain={username}&start=admin_{g.account.uuid}",
        "web_url": f"https://t.me/{username}?start=admin_{g.account.uuid}",
        "connected": bool(g.account.telegram_id),
    }


def _needs_quick_setup() -> bool:
    # Quick setup is owner-only: other admins never see it.
    if g.account.mode != "super_admin":
        return False
    from hiddifypanel.panel.commercial.restapi.v2.admin.quick_setup_api import needs_quick_setup

    return needs_quick_setup()


def _admin_v2_bootstrap_payload() -> dict:
    proxy_path = g.proxy_path or hconfig(ConfigEnum.proxy_path_admin)
    return {
        "proxy_path": proxy_path,
        "api_base": f"/{proxy_path}/api/v2/admin/",
        "router_base": f"/{proxy_path}/admin/v2/",
        "locale": hconfig(ConfigEnum.admin_lang) or "en",
        "panel_version": _panel_version(),
        "panel_logo_url": _panel_logo_url(proxy_path),
        "menu": build_admin_v2_menu(),
        "notices": build_admin_v2_notices(),
        "system_actions": build_admin_v2_system_actions(),
        "panel_mode": str(hconfig(ConfigEnum.panel_mode) or ""),
        "node_info": _node_info(),
        "account_mode": str(g.account.mode),
        "needs_quick_setup": _needs_quick_setup(),
        "telegram": _telegram_info(),
    }


# Same roles as the v2 dashboard API. Login sends every admin here; a
# super_admin-only gate bounces Role.admin / Role.agent through /?force=1 forever.
_ADMIN_V2_ROLES = {Role.super_admin, Role.admin, Role.agent}


def register_v2_routes(flask_app, admin_bp):
    @flask_app.route("/__admin_v2_bootstrap")
    @flask_app.route("/<proxy_path>/__admin_v2_bootstrap")
    @flask_app.doc(hide=True)
    @login_required(roles=_ADMIN_V2_ROLES)
    def admin_v2_bootstrap(**_values):
        """Bootstrap for Admin V2 dev (menu, notices, paths)."""
        return jsonify(_admin_v2_bootstrap_payload())

    @admin_bp.route("/v2/")
    @admin_bp.route("/v2/<path:subpath>")
    @login_required(roles=_ADMIN_V2_ROLES)
    def admin_v2(subpath=""):
        proxy_path = g.proxy_path or hconfig(ConfigEnum.proxy_path_admin)
        lang = hconfig(ConfigEnum.admin_lang) or "en"
        static_prefix = f"/{proxy_path}/static/admin-v2/assets"
        static_js = f"{static_prefix}/index.js"
        static_css = f"{static_prefix}/index.css"
        # First setup is handled by the SPA's /quick-setup route (super admins only; see bootstrap).

        return render_template(
            "admin_v2.html",
            api_base=f"/{proxy_path}/api/v2/admin/",
            router_base=f"/{proxy_path}/admin/v2/",
            static_js=static_js,
            static_css=static_css,
            proxy_path=proxy_path,
            locale=lang,
            panel_version=_panel_version(),
            panel_logo_url=_panel_logo_url(proxy_path),
            admin_menu=build_admin_v2_menu(),
            admin_notices=build_admin_v2_notices(),
            admin_system_actions=build_admin_v2_system_actions(),
            panel_mode=str(hconfig(ConfigEnum.panel_mode) or ""),
            node_info=_node_info(),
            account_mode=str(g.account.mode),
            needs_quick_setup=_needs_quick_setup(),
            telegram=_telegram_info(),
        )
