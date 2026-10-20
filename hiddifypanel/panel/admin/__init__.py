import flask_admin
from apiflask import APIBlueprint
from flask import redirect, render_template, request
from flask_admin import Admin, AdminIndexView, expose
from flask_adminlte3 import AdminLTE3

from hiddifypanel import Events, hutils
from hiddifypanel import g as g
from hiddifypanel.database import db
from hiddifypanel.models import *

from . import fix_flaskadmin_babel as fix_flaskadmin_babel
from .AdminstratorAdmin import AdminstratorAdmin
from .DomainAdmin import DomainAdmin

flask_bp = APIBlueprint("flask", __name__, template_folder="templates", enable_openapi=False)
admin_bp = APIBlueprint("admin", __name__, template_folder="templates", enable_openapi=False)



class LegacyIndexView(AdminIndexView):
    # The legacy Dashboard is only registered in debug mode; otherwise send /admin/ to admin_v2.
    @expose("/")
    def index(self):
        if hconfig(ConfigEnum.log_level) != "debug":
            return redirect(hutils.flask.hurl_for("admin.admin_v2"))
        return super().index()


flaskadmin = Admin(endpoint="admin", index_view=LegacyIndexView(), base_template="flaskadmin-layout.html", translations_path="./hiddifypanel/translations/")


@flask_bp.before_request
def redirect_legacy_admin():
    # The legacy Flask-Admin pages only work in debug mode (their layout needs the legacy Dashboard); otherwise use admin_v2.
    if hconfig(ConfigEnum.log_level) != "debug":
        return redirect(hutils.flask.hurl_for("admin.admin_v2"))


def init_app(app):

    from .UserAdmin import UserAdmin

    # admin_secret=StrConfig.query.filter(StrConfig.key==ConfigEnum.admin_secret).first()
    #
    # return
    # admin = Admin(endpoint="admin",index_view=Dashboard(),base_template='lte-master.html',static_url_path="/static/")
    flaskadmin.template_mode = "bootstrap4"
    flaskadmin.init_app(flask_bp)
    adminlte = AdminLTE3()
    adminlte.init_app(app)

    Events.admin_prehook.notify(flaskadmin=flaskadmin, admin_bp=admin_bp)

    @app.route("/<proxy_path>/admin")
    @app.doc(hide=True)
    def auto_route(proxy_path=None, user_secret=None):
        return redirect(request.url.replace("http://", "https://") + "/")

    flaskadmin.add_view(UserAdmin(User, db.session))
    flaskadmin.add_view(DomainAdmin(Domain, db.session))
    flaskadmin.add_view(AdminstratorAdmin(AdminUser, db.session))
    from .NodeAdmin import NodeAdmin

    flaskadmin.add_view(NodeAdmin(Child, db.session, endpoint="node", url="node", name="Node"))
    if hconfig(ConfigEnum.log_level) == "debug":
        from .Backup import Backup
        from .commercial_info import CommercialInfo
        from .Dashboard import Dashboard
        from .ProxyAdmin import ProxyAdmin
        from .QuickSetup import QuickSetup
        from .SettingAdmin import SettingAdmin

        Dashboard.register(admin_bp, route_base="/")
        SettingAdmin.register(admin_bp)
        ProxyAdmin.register(admin_bp)
        CommercialInfo.register(admin_bp)
        QuickSetup.register(admin_bp)
        Backup.register(admin_bp)

    from .Actions import Actions

    Actions.register(admin_bp)
    from .v2_view import register_v2_routes

    register_v2_routes(app, admin_bp)

    # admin_bp.add_url_rule('/admin/quicksetup/',endpoint="quicksetup",view_func=QuickSetup.index,methods=["GET"])
    # admin_bp.add_url_rule('/admin/quicksetup/',endpoint="quicksetup-save", view_func=QuickSetup.save,methods=["POST"])

    app.add_url_rule("/<proxy_path>/admin/static/<filename>/", endpoint="admin.static")  # fix bug in admin with blueprint

    flask_bp.debug = True
    app.register_blueprint(
        admin_bp,
        url_prefix="/<proxy_path>/admin/",
    )
    app.register_blueprint(admin_bp, name=f"child_{admin_bp.name}", url_prefix="/<proxy_path>/<int:child_id>/admin/")
    app.register_blueprint(flask_bp, url_prefix="/<proxy_path>/")
    app.register_blueprint(flask_bp, name=f"child_{flask_bp.name}", url_prefix="/<proxy_path>/<int:child_id>/")
