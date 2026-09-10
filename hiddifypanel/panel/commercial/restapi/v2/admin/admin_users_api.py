from apiflask import abort
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models import AdminUser
from hiddifypanel.models.role import Role

from .schema import AdminSchema


class AdminUsersApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin})]

    @app.output(list[AdminSchema])
    def get(self):
        """Admin: Get all admins"""
        admins = AdminUser.query.filter(AdminUser.id.in_(g.account.recursive_sub_admins_ids())).all() or abort(404, "You have no admin")
        return [admin.to_schema() for admin in admins]

    @app.input(AdminSchema, arg_name="data")
    @app.output(AdminSchema)
    def post(self, data: AdminSchema):
        """Admin: Create an admin"""
        payload = data.model_dump(exclude_none=True)
        if payload.get("uuid") and AdminUser.by_uuid(payload["uuid"]):
            abort(400, "The admin exists")

        if not payload.get("added_by_uuid"):
            payload["added_by_uuid"] = g.account.uuid

        admin = AdminUser.add_or_update(**payload) or abort(502, "Unknown issue: Admin is not added")
        return admin.to_schema()
