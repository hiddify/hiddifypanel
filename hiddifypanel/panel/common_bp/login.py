from flask_classful import FlaskView, route
from hiddifypanel import g, current_app as app, hutils
from hiddifypanel.auth import login_required, current_account, login_user, logout_user, login_by_uuid
from flask import redirect, request, render_template, flash, jsonify
from hiddifypanel.hutils.flask import hurl_for
from flask_babel import lazy_gettext as _
from apiflask import abort
import hiddifypanel.panel.hiddify as hiddify
from hiddifypanel.models import *

from flask_wtf import FlaskForm
import wtforms as wtf

import re


class LoginForm(FlaskForm):
    secret_textbox = wtf.fields.StringField(_(f'login.secret.label'), [wtf.validators.Regexp(
        "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", re.IGNORECASE, _('config.invalid_uuid'))], default='',
        description=_(f'login.secret.description'), render_kw={
        'required': "",
        'pattern': "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        'message': _('config.invalid_uuid')
    })

    password_textbox = wtf.fields.PasswordField(_(f'login.password.label'), default='',
        description=_(f'login.password.description'), render_kw={    })
    submit = wtf.fields.SubmitField(_('login.button'))


class AdminLoginForm(FlaskForm):
    """Admin sign in: UUID or alias + password (field names browsers recognise, so they can save it)."""

    username = wtf.fields.StringField(default="")
    password = wtf.fields.PasswordField(default="")


_TEXTS_CACHE: dict[str, dict] = {}


def _login_texts() -> dict:
    """The page's texts from translations.i18n (adminV2.login), in the admin language, English as fallback."""
    import json
    from pathlib import Path

    lang = str(hconfig(ConfigEnum.admin_lang) or "en")
    if lang not in _TEXTS_CACHE:
        root = Path(__file__).resolve().parents[2] / "translations.i18n"

        def load(code: str) -> dict:
            try:
                return json.loads((root / f"{code}.json").read_text(encoding="utf-8")).get("adminV2", {}).get("login", {})
            except (OSError, ValueError):
                return {}

        _TEXTS_CACHE[lang] = {**load("en"), **load(lang)}
    return _TEXTS_CACHE[lang]


def _safe_next(value: str | None) -> str | None:
    """Only a path on this admin panel (no other site, no protocol-relative trick)."""
    if not value or not isinstance(value, str):
        return None
    if not value.startswith(f"/{g.proxy_path}/") or value.startswith("//") or "\\" in value or "://" in value:
        return None
    return value


def _client_ip() -> str:
    try:
        return hutils.network.auto_ip_selector.get_real_user_ip() or request.remote_addr or "?"
    except Exception:
        return request.remote_addr or "?"


def _render_admin_login(form: AdminLoginForm, *, error: str | None = None, status: int = 200):
    texts = _login_texts()
    return (
        render_template(
            "admin_login.html",
            form=form,
            error=error,
            texts=texts,
            next_url=_safe_next(request.values.get("next")) or "",
            lang=str(hconfig(ConfigEnum.admin_lang) or "en"),
            rtl=str(hconfig(ConfigEnum.admin_lang) or "en") in ("fa", "ar"),
            title=hconfig(ConfigEnum.branding_title) or texts.get("brand") or "Hiddify",
            logo_url=hutils.flask.static_url_for(filename="images/WhiteLogo.png"),
        ),
        status,
    )


class LoginView(FlaskView):

    # @route("/")
    def index(self, force=None, next=None):
        force_arg = request.args.get('force')
        redirect_arg = request.args.get('redirect')
        username_arg = (request.args.get('user') or '').split("?")[0]
        if not current_account:
            if hutils.flask.is_admin_proxy_path():
                # The UUID from the link (or an alias) is filled in already.
                form = AdminLoginForm()
                form.username.data = form.username.data or username_arg
                return _render_admin_login(form)
            form=LoginForm()
            form.secret_textbox.data=form.secret_textbox.data or username_arg
            return render_template('login.html', form=form)

            # abort(401, "Unauthorized1")

        if redirect_arg:
            return redirect(redirect_arg)
        if hutils.flask.is_admin_proxy_path() and g.account.role in {Role.super_admin, Role.admin, Role.agent}:
            return redirect(hurl_for('admin.admin_v2'))
        # if g.user_agent['is_browser'] and hutils.flask.is_client_proxy_path():
        #     return redirect(hurl_for('client.UserView:index'))

        from hiddifypanel.panel.user import UserView
        return UserView().auto_sub()

    def post(self):
        if hutils.flask.is_admin_proxy_path():
            return self._admin_post()
        form = LoginForm()
        if form.validate_on_submit():
            uuid = form.secret_textbox.data.strip()
            if login_by_uuid(uuid,form.password_textbox.data, hutils.flask.is_admin_proxy_path()):
                return redirect(f'/{g.proxy_path}/')
        hutils.flask.flash(_('config.invalid_uuid'), 'danger')  # type: ignore
        return render_template('login.html', form=LoginForm())

    @route("/logout/", methods=["POST"])
    def logout(self):
        """Sign out and go to the sign-in page. POST from this panel only (another site can not sign you out)."""
        from urllib.parse import urlparse

        source = request.headers.get("Origin") or request.headers.get("Referer") or ""
        if source and urlparse(source).netloc != request.host:
            abort(403, "Cross-site sign out refused")
        logout_user()
        back = _safe_next(request.values.get("next"))
        return redirect(hurl_for("common_bp.LoginView:index", next=back) if back else f"/{g.proxy_path}/")

    def _admin_post(self):
        from hiddifypanel import admin_credentials as creds

        form = AdminLoginForm()
        if not form.validate_on_submit():  # CSRF token missing or expired: the page was open too long
            return _render_admin_login(form, error="expired", status=400)
        ip = _client_ip()
        if creds.login_locked(ip):
            return _render_admin_login(form, error="locked", status=429)
        admin = creds.check_admin_login(form.username.data or "", form.password.data or "")
        if admin is None:
            creds.record_failure(ip)
            form.password.data = ""
            return _render_admin_login(form, error="invalid", status=401)
        creds.clear_failures(ip)
        login_user(admin, force=True)
        return redirect(_safe_next(request.form.get("next")) or hurl_for("admin.admin_v2"))

    @ route("/l/<path:path>/")
    @ route("/l/<path:path>")
    @ route("/l/")
    @ route("/l")
    def basic(self, path=None):
        if path:
            redirect_arg = f"/{g.proxy_path}/{path}"
        else:
            redirect_arg = request.args.get('next')

        if hutils.flask.is_admin_proxy_path() and not current_account:
            # Admins: straight to the panel's login page (no browser username/password popup).
            username = request.authorization.username if request.authorization else g.uuid
            return redirect(hurl_for('common_bp.LoginView:index', next=redirect_arg, user=username))

        if not current_account or (not request.headers.get('Authorization')):
            username = request.authorization.username if request.authorization else g.uuid

            loginurl = hurl_for('common_bp.LoginView:index', next=redirect_arg, user=username)
            if g.user_agent['is_browser'] and request.headers.get('Authorization') or (current_account and len(username) > 0 and current_account.username != username):
                hutils.flask.flash(_('Incorrect Password'), 'error')  # type: ignore
                logout_user()
                g.__account_store = None
                # hutils.flask.flash(request.authorization.username, 'error')
                return redirect(loginurl)

            return render_template("redirect.html", url=loginurl), 401
            # abort(401, "Unauthorized1")
        if redirect_arg:
            return redirect(redirect_arg)

        if hutils.flask.is_admin_proxy_path() and g.account.role in {Role.super_admin, Role.admin, Role.agent}:
            return redirect(hurl_for('admin.admin_v2'))

        if g.user_agent['is_browser'] and hutils.flask.is_client_proxy_path():
            return redirect(hurl_for('client.UserView:index'))

        from hiddifypanel.panel.user import UserView
        # return redirect(url_for("user.")) UserView().auto_sub()

    # @route('/<uuid:uuid>/<path:path>')
    # @route('/<uuid:uuid>/')

    # def uuid(self, uuid, path=''):
    #     proxy_path = hiddify.flask.get_proxy_path_from_url(request.url)
    #     g.__account_store = None
    #     uuid = str(uuid)
    #     if proxy_path == hconfig(ConfigEnum.proxy_path_client):
    #         g.__account_store = User.by_uuid(uuid)
    #         path = f'client/{path}'
    #     elif proxy_path == hconfig(ConfigEnum.proxy_path_admin):
    #         g.__account_store = AdminUser.by_uuid(uuid)
    #     if not g.account:
    #         abort(403)
    #     if not g.user_agent['is_browser'] and proxy_path == hconfig(ConfigEnum.proxy_path_client):
    #         userview = UserView()
    #         if "all.txt" in path:
    #             return userview.all_configs()
    #         if 'singbox.json' in path:
    #             return userview.singbox()
    #         if 'full-singbox.json' in path:
    #             return userview.full_singbox()
    #         if 'clash' in path:
    #             splt = path.split("/")
    #             meta_or_normal = 'meta' if splt[-2] == 'meta' else 'normal'
    #             typ = splt[-1].split('.yml')[0]
    #             return userview.clash_config(meta_or_normal=meta_or_normal, typ=typ)
    #         return userview.force_sub()

    #     login_user(g.account, force=True)

    #     return redirect(f"/{proxy_path}/{path}")

    @ route('/<secret_uuid>/manifest.webmanifest')
    def create_pwa_manifest(self):
        domain = request.host
        admin_call=hutils.flask.is_admin_panel_call()
        account=AdminUser.by_uuid(g.uuid) if admin_call else User.by_uuid(g.uuid)
        name = (domain if admin_call  else account.name)
        return jsonify({
            "name": f"Hiddify {name}",
            "short_name": f"{name}"[:12],
            "theme_color": "#f2f4fb",
            "background_color": "#1a1b21",
            "display": "standalone",
            "scope": f"/",
            "start_url": hiddify.get_account_panel_link(account, domain) + "?pwa=true",
            "description": "Hiddify, for a free Internet",
            "orientation": "any",
            "icons": [
                {
                    "src": hutils.flask.static_url_for(filename='images/hiddify-dark.png'),
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable any"
                }
            ]
        })
