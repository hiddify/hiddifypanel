from apiflask import abort
from flask.views import MethodView
from flask_babel import gettext as _
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel import hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import Child, ChildMode, ConfigEnum, PanelMode, Role, hconfig, set_hconfig

from .schema import RegisterWithParentInputSchema


class RegisterWithParentApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    # Called by a parent panel that is adding this panel as a node (Admin V2 "Nodes" page). The caller signs in with
    # this panel's own admin link, so it has the owner's permission: it may take the panel over even when the panel is a
    # parent itself or a node of another parent (it then leaves that one).
    @app.input(RegisterWithParentInputSchema, arg_name="data")
    def post(self, data: RegisterWithParentInputSchema):
        logger.info(f"Registering panel with parent called by {data.name}")
        was_parent = hutils.node.is_parent()
        old_parent = hconfig(ConfigEnum.parent_panel) or ""
        new_parent = data.parent_panel.rstrip("/")
        switching = was_parent or (hutils.node.is_child() and old_parent.rstrip("/") != new_parent)
        if switching:
            logger.warning(f"This panel was {'a parent' if was_parent else 'a node of ' + old_parent}: the owner moves it to {new_parent}")
        old_parent_ids = {c.id for c in Child.query.filter(Child.mode == ChildMode.parent).all()}

        set_hconfig(ConfigEnum.parent_panel, data.parent_panel)
        if data.name:
            set_hconfig(ConfigEnum.node_name, data.name)

        ok, msg = hutils.node.child.register_to_parent(data.name, data.apikey)
        if not ok:
            logger.error(f"Child registration to parent failed: {msg}")
            set_hconfig(ConfigEnum.parent_panel, old_parent)  # nothing changed: it stays what it was
            abort(400, f"{_('child.register-failed')}: {msg}")

        if switching:
            self._leave_old_relations(was_parent, old_parent_ids)
        set_hconfig(ConfigEnum.panel_mode, PanelMode.child)
        logger.info("Registered panel with parent, panel mode is now child")
        return {"status": 200, "msg": "ok"}

    @staticmethod
    def _leave_old_relations(was_parent: bool, old_parent_ids: set[int]) -> None:
        """The new parent has taken this panel: the old parent can no longer reach it, and its own nodes are let go
        (a node of a node is not a thing; each one is told to forget this panel and becomes standalone)."""
        if was_parent:
            for node in Child.query.filter(Child.mode == ChildMode.remote).all():
                try:
                    hutils.node.parent.remove_node(node)
                except Exception:  # noqa: BLE001  one unreachable node must not stop the move
                    logger.exception(f"Could not let node {node.id} go")
        if old_parent_ids:
            Child.query.filter(Child.id.in_(old_parent_ids)).delete(synchronize_session=False)
            db.session.commit()
