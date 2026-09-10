from apiflask import abort
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.models import AdminUser, Role

from . import has_permission
from .schema import AdminSchema, PatchAdminSchema, SuccessfulSchema


class AdminUserApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin})]

    @app.output(AdminSchema)
    def get(self, uuid):
        """Admin: Get an admin"""
        admin = AdminUser.by_uuid(uuid) or abort(404, "Admin not found")
        if not has_permission(admin):
            abort(403, "you don't have permission to access this admin")
        return admin.to_schema()

    @app.input(PatchAdminSchema, arg_name="data")
    @app.output(AdminSchema)
    def patch(self, uuid, data: PatchAdminSchema):
        """Admin: Update an admin"""
        admin = AdminUser.by_uuid(uuid) or abort(404, "Admin not found")
        if not has_permission(admin):
            abort(403, "You don't have permission to access this admin")

        payload = data.model_dump(exclude_unset=True)
        for field in AdminUser.__table__.columns.keys():
            if field in ["id", "parent_admin_id"]:
                continue
            if field not in payload:
                payload[field] = getattr(admin, field)
        payload["old_uuid"] = uuid
        admin = AdminUser.add_or_update(True, **payload) or abort(502, "Unknown issue: Admin is not patched")
        return admin.to_schema()

    @app.output(SuccessfulSchema)
    def delete(self, uuid):
        """Admin: Delete an admin"""
        admin = AdminUser.by_uuid(uuid) or abort(404, "Admin not found")
        if not has_permission(admin):
            abort(403, "You don't have permission to access this admin")
        admin.remove()
        return {"status": 200, "msg": "ok"}
