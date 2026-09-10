from apiflask import abort
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.drivers import user_driver
from hiddifypanel.models import Role, User
from hiddifypanel.panel import hiddify

from . import has_permission
from .schema import PatchUserSchema, SuccessfulSchema, UserSchema


class UserApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin, Role.agent})]

    @app.output(UserSchema)
    def get(self, uuid):
        """User: Get details of a user"""
        user = User.by_uuid(uuid) or abort(404, "User not found")
        if not has_permission(user):
            abort(403, "You don't have permission to access this user")

        return user.to_schema()

    @app.input(PatchUserSchema, arg_name="data")
    @app.output(UserSchema)
    def patch(self, uuid, data: PatchUserSchema):
        """User: Update a user"""
        user = User.by_uuid(uuid) or abort(404, "user not found")
        if not has_permission(user):
            abort(403, "You don't have permission to access this user")

        payload = data.model_dump(exclude_unset=True)
        payload["old_uuid"] = uuid
        user_driver.remove_client(user)
        dbuser = User.add_or_update(**payload) or abort(502, "Unknown issue! User is not patched")
        if dbuser.is_active:
            user_driver.add_client(dbuser)
        hiddify.quick_apply_users()
        return dbuser.to_schema()

    @app.output(SuccessfulSchema)
    def delete(self, uuid):
        """User: Delete a User"""
        user = User.by_uuid(uuid) or abort(404, "user not found")
        if not has_permission(user):
            abort(403, "You don't have permission to access this user")
        user.remove()
        hiddify.quick_apply_users()
        return {"status": 200, "msg": "ok"}
