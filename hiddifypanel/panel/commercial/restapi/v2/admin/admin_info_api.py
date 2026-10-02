from apiflask import abort
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models.admin import AdminMode, AdminUser
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum, Lang
from hiddifypanel.models.role import Role

from .schema import AdminSchema


class AdminInfoApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin, Role.agent})]

    @app.output(AdminSchema)
    def get(self):
        """Current Admin Info"""
        admin = g.account or abort(404, "user not found")

        parent_admin_uuid = None
        if g.account.mode == AdminMode.super_admin:
            if parent := AdminUser.by_id(admin.parent_admin_id):
                parent_admin_uuid = parent.uuid

        return AdminSchema(
            name=admin.name,
            comment=admin.comment,
            uuid=admin.uuid,
            mode=admin.mode,
            can_add_admin=admin.can_add_admin,
            parent_admin_uuid=parent_admin_uuid,
            telegram_id=admin.telegram_id or 0,
            lang=Lang(hconfig(ConfigEnum.admin_lang)),
        )
