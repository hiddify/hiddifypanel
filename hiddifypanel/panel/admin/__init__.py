"""The admin panel: admin_v2 (Vue) only. Its API is in panel/commercial/restapi/v2/admin."""

from apiflask import APIBlueprint
from flask import redirect, request

admin_bp = APIBlueprint("admin", __name__, template_folder="templates", enable_openapi=False)


def init_app(app):
    from .v2_view import register_v2_routes

    @app.route("/<proxy_path>/admin")
    @app.doc(hide=True)
    def auto_route(proxy_path=None, user_secret=None):
        return redirect(request.url.replace("http://", "https://") + "/")

    @admin_bp.route("/")
    def index(**_values):
        # The old pages are gone: /admin/ and anything under it that is not admin_v2 opens admin_v2.
        from hiddifypanel.hutils.flask import hurl_for

        return redirect(hurl_for("admin.admin_v2"))

    register_v2_routes(app, admin_bp)

    app.register_blueprint(admin_bp, url_prefix="/<proxy_path>/admin/")
    app.register_blueprint(admin_bp, name=f"child_{admin_bp.name}", url_prefix="/<proxy_path>/<int:child_id>/admin/")
