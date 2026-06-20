"""Sidebar menu and panel notices for Admin V2 shell."""

from __future__ import annotations

from flask import g, request
from flask_babel import gettext as _, get_locale

from hiddifypanel import hutils
from hiddifypanel.hutils.flask import get_proxy_stats_url, hurl_for
from hiddifypanel.models import ConfigEnum, Domain, User, hconfig
from hiddifypanel.panel import hiddify


def _item(label: str, url: str, icon: str, *, target: str = '_self', badge: str | None = None) -> dict:
    row: dict = {'label': label, 'url': url, 'icon': icon, 'target': target}
    if badge:
        row['badge'] = badge
    return row


def _wiki_support_url() -> str:
    if get_locale() == 'fa':
        return 'https://github.com/hiddify/hiddify-manager/wiki/%D9%87%D9%85%D9%87-%D8%A2%D9%85%D9%88%D8%B2%D8%B4%E2%80%8C%D9%87%D8%A7-%D9%88-%D9%88%DB%8C%D8%AF%D8%A6%D9%88%D9%87%D8%A7'
    return 'https://github.com/hiddify/hiddify-manager/wiki/All-tutorials-and-videos'


def build_admin_v2_menu() -> list[dict]:
    """Grouped legacy panel menu (full-page links). V2 routes are added in the frontend."""
    groups: list[dict] = []
    badge_parent = _('in parent panel')

    home_label = _('Parent Panel') if hutils.node.is_parent() else _('admin.menu.home')
    groups.append({
        'label': _('master.page-title'),
        'items': [
            _item(home_label, hurl_for('admin.Dashboard:index'), 'pi pi-fw pi-home'),
            _item(
                _('admin.menu.user'),
                hconfig(ConfigEnum.parent_panel) + 'admin/user/'
                if hutils.node.is_child()
                else hurl_for('flask.user.index_view'),
                'pi pi-fw pi-users',
                badge=badge_parent if hutils.node.is_child() else None,
            ),
            _item(
                _('Admins'),
                hconfig(ConfigEnum.parent_panel) + 'admin/adminuser/'
                if hutils.node.is_child()
                else hurl_for('flask.adminuser.index_view'),
                'pi pi-fw pi-user-edit',
                badge=badge_parent if hutils.node.is_child() else None,
            ),
        ],
    })

    if g.account.mode != 'agent':
        settings_items = [
            _item(_('admin.menu.domain'), hurl_for('flask.domain.index_view'), 'pi pi-fw pi-link'),
            _item(_('admin.menu.proxy'), hurl_for('admin.ProxyAdmin:index'), 'pi pi-fw pi-sitemap'),
        ]
        if g.account.mode == 'super_admin':
            settings_items.extend([
                _item(_('admin.menu.config'), hurl_for('admin.SettingAdmin:index'), 'pi pi-fw pi-cog'),
                _item(_('Backup'), hurl_for('admin.Backup:index'), 'pi pi-fw pi-save'),
            ])
        if hconfig(ConfigEnum.telegram_bot_token) and getattr(g, 'bot', None):
            settings_items.append(
                _item(
                    _('Telegram Bot'),
                    f'tg://resolve?domain={g.bot.username}&start=admin_{g.account.uuid}',
                    'pi pi-fw pi-telegram',
                ),
            )
        if g.account.mode == 'super_admin':
            settings_items.append(
                _item(_('admin.menu.api'), hurl_for('openapi.docs'), 'pi pi-fw pi-code'),
            )
            settings_items.append(
                _item(_('admin.menu.proxy_stats'), get_proxy_stats_url(), 'pi pi-fw pi-chart-bar'),
            )
        groups.append({'label': _('admin.menu.config'), 'items': settings_items})

    if g.account.mode == 'super_admin':
        groups.append({
            'label': _('admin.actions.title'),
            'items': [
                _item(_('admin.actions.status'), hurl_for('admin.Actions:status'), 'pi pi-fw pi-chart-line'),
                _item(_('admin.actions.viewlogs'), hurl_for('admin.Actions:viewlogs'), 'pi pi-fw pi-inbox'),
                _item(_('admin.actions.apply_configs'), hurl_for('admin.Actions:apply_configs'), 'pi pi-fw pi-bolt'),
                _item(_('admin.actions.update'), hurl_for('admin.Actions:update'), 'pi pi-fw pi-upload'),
                _item(_('admin.actions.reinstall'), hurl_for('admin.Actions:reinstall'), 'pi pi-fw pi-refresh'),
                _item(_('admin.actions.reset'), hurl_for('admin.Actions:reset'), 'pi pi-fw pi-power-off'),
            ],
        })

    groups.append({
        'label': _('admin.menu.support'),
        'items': [
            _item(_('admin.menu.support'), _wiki_support_url(), 'pi pi-fw pi-question-circle', target='_blank'),
            _item(
                _('Bug'),
                hutils.github_issue.generate_github_issue_link_for_admin_sidebar(),
                'pi pi-fw pi-exclamation-circle',
                target='_blank',
            ),
            _item(_('Donation.title'), hurl_for('admin.Dashboard:index'), 'pi pi-fw pi-heart'),
        ],
    })

    return groups


def build_admin_v2_notices() -> list[dict]:
    """Panel warnings mirrored from the classic dashboard (no flash session)."""
    notices: list[dict] = []

    if hutils.utils.is_panel_outdated():
        notices.append({
            'severity': 'warn',
            'summary': _('outdated_panel'),
            'toast': True,
        })

    def_user = None if len(User.query.all()) > 1 else User.query.filter(User.name == 'default').first()
    domains = Domain.get_domains()
    sslip_domains = [d.domain for d in domains if 'sslip.io' in d.domain]

    if def_user and sslip_domains:
        quick_setup = hurl_for('admin.QuickSetup:index')
        notices.append({
            'severity': 'warn',
            'summary': _('admin.incomplete_setup_warning', quick_setup=quick_setup),
        })
        if hutils.node.is_parent():
            notices.append({
                'severity': 'error',
                'summary': _(
                    'Please understand that parent panel is under test and the plan and the condition of use maybe change at anytime.',
                ),
            })
    elif sslip_domains:
        notices.append({
            'severity': 'warn',
            'summary': _(
                'It seems that you are using default domain (%(domain)s) which is not recommended.',
                domain=sslip_domains[0],
            ),
        })
        if hutils.node.is_parent():
            notices.append({
                'severity': 'error',
                'summary': _(
                    'Please understand that parent panel is under test and the plan and the condition of use maybe change at anytime.',
                ),
            })
    elif def_user:
        d = domains[0] if domains else None
        if d:
            notices.append({
                'severity': 'info',
                'summary': _(
                    'admin.no_user_warning',
                    default_link=hiddify.get_html_user_link(def_user, d),
                ),
            })

    if hutils.network.is_ssh_password_authentication_enabled():
        notices.append({
            'severity': 'warn',
            'summary': _('serverssh.password-login.warning'),
        })

    return notices
