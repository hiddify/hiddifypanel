from apiflask import abort
from flask.views import MethodView
from flask_babel import gettext as _
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel import hutils
from hiddifypanel.auth import login_required
from hiddifypanel.models import ConfigEnum, PanelMode, Role, hconfig, set_hconfig

from .schema import RegisterWithParentInputSchema


class RegisterWithParentApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    # Called by a parent panel that is adding this panel as a node (Admin V2 "Nodes" page).
    @app.input(RegisterWithParentInputSchema, arg_name="data")
    def post(self, data: RegisterWithParentInputSchema):
        logger.info(f"Registering panel with parent called by {data.name}")
        if hutils.node.is_parent():
            logger.error("The panel is a parent panel")
            abort(400, "This panel is a parent panel and cannot become a node")
        if hutils.node.is_child() and (hconfig(ConfigEnum.parent_panel) or "").rstrip("/") != data.parent_panel.rstrip("/"):
            logger.error("The panel is already a node of another parent")
            abort(400, "This panel is already a node of another parent panel")

        old_parent = hconfig(ConfigEnum.parent_panel)
        set_hconfig(ConfigEnum.parent_panel, data.parent_panel)
        if data.name:
            set_hconfig(ConfigEnum.node_name, data.name)

        ok, msg = hutils.node.child.register_to_parent(data.name, data.apikey)
        if not ok:
            logger.error(f"Child registration to parent failed: {msg}")
            set_hconfig(ConfigEnum.parent_panel, old_parent or "")
            abort(400, f"{_('child.register-failed')}: {msg}")

        set_hconfig(ConfigEnum.panel_mode, PanelMode.child)
        logger.info("Registered panel with parent, panel mode is now child")
        return {"status": 200, "msg": "ok"}
