from flask import jsonify, render_template, g
import hiddifypanel
from hiddifypanel.auth import login_required
from hiddifypanel.hutils import flask as hutils_flask
from hiddifypanel.models import ConfigEnum, Role, hconfig

from .v2_menu import build_admin_v2_menu, build_admin_v2_notices


def _panel_version() -> str:
    if not hiddifypanel.is_released_version:
        return 'DEV'
    return hiddifypanel.__version__


def _panel_logo_url(proxy_path: str) -> str:
    static_path = hutils_flask.static_url_for(filename='images/WhiteLogo.png')
    if static_path.startswith('/'):
        return static_path
    return f'/{proxy_path}/{static_path.lstrip("/")}'


def register_v2_routes(flask_app, admin_bp):
    @flask_app.route('/__admin_v2_bootstrap')
    @flask_app.doc(hide=True)
    @login_required(roles={Role.super_admin})
    def admin_v2_bootstrap():
        """Fixed-path bootstrap for Admin V2 dev (proxy_path is random per installation)."""
        proxy_path = g.proxy_path or hconfig(ConfigEnum.proxy_path_admin)
        return jsonify({
            'proxy_path': proxy_path,
            'api_base': f'/{proxy_path}/api/v2/admin/',
            'router_base': f'/{proxy_path}/admin/v2/',
            'locale': hconfig(ConfigEnum.admin_lang) or 'en',
            'panel_version': _panel_version(),
            'panel_logo_url': _panel_logo_url(proxy_path),
            'menu': build_admin_v2_menu(),
            'notices': build_admin_v2_notices(),
        })

    @admin_bp.route('/v2/')
    @admin_bp.route('/v2/<path:subpath>')
    @login_required(roles={Role.super_admin})
    def admin_v2(subpath=''):
        proxy_path = g.proxy_path or hconfig(ConfigEnum.proxy_path_admin)
        lang = hconfig(ConfigEnum.admin_lang) or 'en'
        static_prefix = f'/{proxy_path}/static/admin-v2/assets'
        static_js = f'{static_prefix}/index.js'
        static_css = f'{static_prefix}/index.css'
        return render_template(
            'admin_v2.html',
            api_base=f'/{proxy_path}/api/v2/admin/',
            router_base=f'/{proxy_path}/admin/v2/',
            static_js=static_js,
            static_css=static_css,
            proxy_path=proxy_path,
            locale=lang,
            panel_version=_panel_version(),
            panel_logo_url=_panel_logo_url(proxy_path),
            admin_menu=build_admin_v2_menu(),
            admin_notices=build_admin_v2_notices(),
        )
