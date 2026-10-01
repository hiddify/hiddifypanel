"""Sidebar menu and panel notices for Admin V2 shell."""

from __future__ import annotations

from bleach import clean as bleach_clean
from flask_babel import get_locale
from flask_babel import gettext as _

from hiddifypanel import g, hutils
from hiddifypanel.hutils.flask import hurl_for
from hiddifypanel.models import ConfigEnum, Domain, User, hconfig
from hiddifypanel.panel import hiddify


def _item(label: str, url: str, icon: str, *, target: str = "_self", badge: str | None = None) -> dict:
    row: dict = {"label": label, "url": url, "icon": icon, "target": target}
    if badge:
        row["badge"] = badge
    return row


def build_admin_v2_system_actions() -> dict[str, str]:
    """Legacy system action URLs used by the Admin V2 Actions page (super_admin only)."""
    if g.account.mode != "super_admin":
        return {}
    return {
        "status": hurl_for("admin.Actions:status"),
        "viewlogs": hurl_for("admin.Actions:viewlogs"),
        "apply_configs": hurl_for("admin.Actions:apply_configs"),
        "update": hurl_for("admin.Actions:update"),
        "reinstall": hurl_for("admin.Actions:reinstall"),
        "reset": hurl_for("admin.Actions:reset"),
    }


_DONATION_TAGS = frozenset({"a", "br", "ul", "ol", "li", "h5", "h6", "p", "strong", "b", "em", "div", "span"})
_DONATION_ATTRS = {"a": ["href", "target", "rel", "data-copy", "class"], "div": ["class"]}


def _donation_item() -> dict:
    """Opens the donation dialog in the shell (the classic UI shows it as a modal)."""
    html = bleach_clean(str(_("Donation.description")), tags=_DONATION_TAGS, attributes=_DONATION_ATTRS, strip=True)
    return {"label": _("Donation.title"), "icon": "pi pi-fw pi-heart", "action": "donation", "dialog_html": html}


def _wiki_support_url() -> str:
    if get_locale() == "fa":
        return "https://github.com/hiddify/hiddify-manager/wiki/%D9%87%D9%85%D9%87-%D8%A2%D9%85%D9%88%D8%B2%D8%B4%E2%80%8C%D9%87%D8%A7-%D9%88-%D9%88%DB%8C%D8%AF%D8%A6%D9%88%D9%87%D8%A7"
    return "https://github.com/hiddify/hiddify-manager/wiki/All-tutorials-and-videos"


# The shell shows exactly three groups, in this order. The frontend adds its own
# routes to them by id (useAdminMenu.ts): Dashboard/Node home and Utils to "manager",
# the Proxy Editor to the top of "settings"; it also sets the translated group titles.
MENU_GROUP_IDS = ("manager", "settings", "help")


def _group(group_id: str, label: str, items: list[dict]) -> dict:
    return {"id": group_id, "label": label, "items": items}


def _help_group() -> dict:
    return _group(
        "help",
        _("admin.menu.support"),
        [
            _item(_("admin.menu.support"), _wiki_support_url(), "pi pi-fw pi-question-circle", target="_blank"),
            _item(
                _("Bug"),
                hutils.github_issue.generate_github_issue_link_for_admin_sidebar(),
                "pi pi-fw pi-exclamation-circle",
                target="_blank",
            ),
            _donation_item(),
        ],
    )


def _settings_items(*, node: bool) -> list[dict]:
    if g.account.mode == "agent":
        return []
    items = [_item(_("admin.menu.domain"), hurl_for("flask.domain.index_view"), "pi pi-fw pi-link")]
    if g.account.mode == "super_admin":
        items.extend(
            [
                {"label": _("admin.menu.config"), "to": "/settings", "icon": "pi pi-fw pi-cog"},
                _item(_("Backup"), hurl_for("admin.Backup:index"), "pi pi-fw pi-save"),
                {"label": _("admin.actions.title"), "to": "/actions", "icon": "pi pi-fw pi-bolt"},
            ]
        )
    if node:
        # A node only manages its own domains, proxies and server.
        return items
    if hconfig(ConfigEnum.telegram_bot_token) and getattr(g, "bot", None):
        items.append(
            _item(
                _("Telegram Bot"),
                f"tg://resolve?domain={g.bot.username}&start=admin_{g.account.uuid}",
                "pi pi-fw pi-telegram",
            ),
        )
    if g.account.mode == "super_admin":
        items.append(_item(_("admin.menu.api"), hurl_for("openapi.docs"), "pi pi-fw pi-code"))
        # items.append(_item(_("admin.menu.proxy_stats"), get_proxy_stats_url(), "pi pi-fw pi-chart-bar"))
    return items


def _manager_items() -> list[dict]:
    if hutils.node.is_child():
        # Users, admins and the dashboard live on the parent; the shell adds the node's home page after this.
        parent_url = hutils.node.child.parent_admin_dashboard_url(g.account.uuid)
        return [_item(_("Parent Panel"), parent_url, "pi pi-fw pi-home")] if parent_url else []
    if hconfig(ConfigEnum.parent_panel):
        items = [
            _item(_("admin.menu.user"), hconfig(ConfigEnum.parent_panel) + "admin/user/", "pi pi-fw pi-users"),
            _item(_("Admins"), hconfig(ConfigEnum.parent_panel) + "admin/adminuser/", "pi pi-fw pi-user-edit"),
        ]
    else:
        items = [
            _item(_("admin.menu.user"), hurl_for("flask.user.index_view"), "pi pi-fw pi-users"),
            {"label": _("Admins"), "to": "/admins", "icon": "pi pi-fw pi-sitemap"},
        ]
    if g.account.mode == "super_admin":
        items.append({"label": _("Nodes"), "to": "/nodes", "icon": "pi pi-fw pi-server"})
    return items


def build_admin_v2_menu() -> list[dict]:
    """The shell's menu groups (Manager, Settings, Help); the frontend adds its own routes to them."""
    return [
        _group("manager", _("master.page-title"), _manager_items()),
        _group("settings", _("admin.menu.config"), _settings_items(node=hutils.node.is_child())),
        _help_group(),
    ]


def build_admin_v2_notices() -> list[dict]:
    """Panel warnings mirrored from the classic dashboard (no flash session)."""
    notices: list[dict] = []

    if hutils.utils.is_panel_outdated():
        notices.append(
            {
                "severity": "warn",
                "summary": _("outdated_panel"),
                "toast": True,
            }
        )

    def_user = None if len(User.query.all()) > 1 else User.query.filter(User.name == "default").first()
    domains = Domain.get_domains()
    sslip_domains = [d.domain for d in domains if "sslip.io" in d.domain]

    if def_user and sslip_domains:
        quick_setup = hurl_for("admin.QuickSetup:index")
        notices.append(
            {
                "severity": "warn",
                "summary": _("admin.incomplete_setup_warning", quick_setup=quick_setup),
            }
        )
        if hutils.node.is_parent():
            notices.append(
                {
                    "severity": "error",
                    "summary": _(
                        "Please understand that parent panel is under test and the plan and the condition of use maybe change at anytime.",
                    ),
                }
            )
    elif sslip_domains:
        notices.append(
            {
                "severity": "warn",
                "summary": _(
                    "It seems that you are using default domain (%(domain)s) which is not recommended.",
                    domain=sslip_domains[0],
                ),
            }
        )
        if hutils.node.is_parent():
            notices.append(
                {
                    "severity": "error",
                    "summary": _(
                        "Please understand that parent panel is under test and the plan and the condition of use maybe change at anytime.",
                    ),
                }
            )
    elif def_user:
        d = domains[0] if domains else None
        if d:
            notices.append(
                {
                    "severity": "info",
                    "summary": _(
                        "admin.no_user_warning",
                        default_link=hiddify.get_html_user_link(def_user, d),
                    ),
                }
            )

    if hutils.network.is_ssh_password_authentication_enabled():
        notices.append(
            {
                "severity": "warn",
                "summary": _("serverssh.password-login.warning"),
            }
        )

    return notices
