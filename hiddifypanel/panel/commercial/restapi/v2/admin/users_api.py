from apiflask import abort
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.drivers import user_driver
from hiddifypanel.models import User
from hiddifypanel.models.role import Role
from hiddifypanel.panel import hiddify

from . import resolve_added_by_uuid
from .schema import PostUserSchema, UserSchema


class UsersApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin, Role.agent})]

    @app.output(list[UserSchema])
    def get(self):
        """User: List users of current admin"""

        users = User.query.filter(
            User.added_by.in_(g.account.recursive_sub_admins_ids()),
            User.deleted.is_(False),
        ).all() or abort(404, "You have no user")
        return [user.to_schema() for user in users]

    @app.input(PostUserSchema, arg_name="data")
    @app.output(UserSchema)
    def post(self, data: PostUserSchema):
        """User: Create a user"""
        payload = data.model_dump(exclude_none=True)

        if not g.account.can_have_more_users():
            abort(
                400,
                f"User limit reached: max {g.account.max_users} users / {g.account.max_active_users} active",
            )

        if payload.get("uuid"):
            existing = User.query.filter(User.uuid == payload["uuid"]).first()
            if existing and not existing.deleted:
                abort(400, "The user exists")
            if existing and existing.deleted:
                existing.purge(commit=False)

        payload["added_by_uuid"] = resolve_added_by_uuid(payload.get("added_by_uuid"))

        dbuser = User.add_or_update(**payload) or abort(502, "Unknown issue: User is not added")
        user_driver.add_client(dbuser)
        hiddify.quick_apply_users()
        return dbuser.to_schema()
