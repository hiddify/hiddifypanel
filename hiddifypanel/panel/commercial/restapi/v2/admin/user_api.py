from apiflask import abort
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.drivers import user_driver
from hiddifypanel.models import Role, User
from hiddifypanel.panel import hiddify

from . import has_permission, resolve_added_by_uuid
from .schema import PatchUserSchema, SuccessfulSchema, UserSchema


class UserApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin, Role.agent})]

    def _scoped_user(self, uuid):
        user = User.by_uuid(uuid)
        if not user or not has_permission(user):
            abort(404, "User not found")
        return user

    @app.output(UserSchema)
    def get(self, uuid):
        """User: Get details of a user"""
        return self._scoped_user(uuid).to_schema()

    @app.input(PatchUserSchema, arg_name="data")
    @app.output(UserSchema)
    def patch(self, uuid, data: PatchUserSchema):
        """User: Update a user"""
        user = self._scoped_user(uuid)

        payload = data.model_dump(exclude_unset=True)
        # Re-enable respects max_active_users only; max_users must not block edits.
        if payload.get("enable") and not user.enable and g.account and not g.account.can_activate_more_users():
            abort(400, "Active user limit reached: disable another user or raise max active users")
        if "added_by_uuid" in payload:
            payload["added_by_uuid"] = resolve_added_by_uuid(payload.get("added_by_uuid"))
        user_driver.remove_client(user)
        dbuser = User.add_or_update(old_uuid=uuid, **payload) or abort(502, "Unknown issue! User is not patched")
        if dbuser.is_active:
            user_driver.add_client(dbuser)
        hiddify.quick_apply_users()
        hutils.node.parent.notify_childs_users_changed()
        return dbuser.to_schema()

    @app.output(SuccessfulSchema)
    def delete(self, uuid):
        """User: Delete a User"""
        user = self._scoped_user(uuid)
        user.remove()
        hiddify.quick_apply_users()
        hutils.node.parent.notify_childs_users_changed()
        return {"status": 200, "msg": "ok"}
