from apiflask import abort
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.drivers import user_driver
from hiddifypanel.models import AdminUser, User
from hiddifypanel.models.role import Role

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

        if payload.get("uuid"):
            existing = User.query.filter(User.uuid == payload["uuid"]).first()
            if existing and not existing.deleted:
                abort(400, "The user exists")
            if existing and existing.deleted:
                existing.purge(commit=False)

        payload["added_by_uuid"] = resolve_added_by_uuid(payload.get("added_by_uuid"))
        # The owner's limits (and those above it): max users / active / online, and the traffic it may still give out.
        owner = AdminUser.by_uuid(str(payload["added_by_uuid"])) if payload.get("added_by_uuid") else g.account
        gb = float(payload.get("usage_limit_GB", 1000) or 0)  # 1000 GB: User.usage_limit's default
        owner = owner or g.account
        if not owner.can_have_more_users(gb):
            left = owner.traffic_left_GB()
            if left is not None and left < max(gb, 1e-6) - 1e-6:
                abort(400, f"Not enough traffic: you (or an admin above you) can give out {left:g} GB more")
            abort(400, "User limit reached: you (or an admin above you) reached the max users, active users or online users")

        dbuser = User.add_or_update(**payload) or abort(502, "Unknown issue: User is not added")
        user_driver.add_client(dbuser)
        hutils.apply_users.quick_apply_users(users_only=True)
        hutils.node.parent.notify_childs_users_changed()
        return dbuser.to_schema()
