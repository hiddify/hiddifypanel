from __future__ import annotations

from datetime import datetime, timedelta

from flask.views import MethodView
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models import AdminUser, User
from hiddifypanel.panel.commercial.restapi.v2.admin.schema import AdminSchema, UserSchema
from hiddifypanel.panel.usage import add_users_usage_new

from .schema import UsageInputOutputSchema, UsageResponseSchema


class UsageApi(MethodView):
    decorators = [login_required(node_auth=True)]

    @app.input(UsageInputOutputSchema, arg_name="data")
    @app.output(UsageResponseSchema)
    def put(self, data: UsageInputOutputSchema) -> UsageResponseSchema:
        assert g.node, "The child does not exist"

        logger.debug(f"Received usage data from child {g.node.name}: {len(data.usages)} users")

        increased = [u for u in data.usages if u.usage > 0]
        logger.debug(f"Increased usages: {len(increased)} users")

        if increased:
            logger.info(f"Adding increased usages to parent for child_id={g.node.id}")
            add_users_usage_new(increased, int(g.node.id))

        return get_users_usage_data_for_api(from_time=data.last_users_sync - timedelta(minutes=1), include_uuids={u.uuid for u in data.usages})


def get_users_usage_data_for_api(from_time: datetime, include_uuids: set[str]):
    users: list[UserSchema] = []
    added_uuids = set()
    sync_time = datetime.now()
    for user in User.query.filter((User.last_modified_time >= from_time) | (User.uuid.in_(include_uuids))).all():
        added_uuids.add(user.uuid)
        users.append(user.to_schema())

    for uuid in include_uuids - added_uuids:
        users.append(
            UserSchema(
                uuid=uuid,
                name="deleted",
                deleted=True,
                enable=False,
            )
        )
    admin_users: list[AdminSchema] = []
    for user in AdminUser.query.filter(AdminUser.last_modified_time >= from_time).all():
        admin_users.append(user.to_schema())
    return UsageResponseSchema(usages=users, response_time=sync_time, admin_users=admin_users)
