from flask.views import MethodView
from loguru import logger

from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.cache import cache
from hiddifypanel.database import db
from hiddifypanel.models import Child, ChildMode, ConfigEnum, PanelMode, set_hconfig


class UnregisterParentApi(MethodView):
    """The parent removed this node: forget the parent and become a standalone panel again."""

    decorators = [login_required(node_auth=True)]

    def post(self):
        parent = g.node
        logger.info(f"Parent {parent.unique_id} removed this node: switching to standalone")
        set_hconfig(ConfigEnum.parent_panel, "", commit=False)
        set_hconfig(ConfigEnum.panel_mode, PanelMode.standalone, commit=False)
        # The parent's row on this node (mode=parent) is what authenticates it; drop it too.
        if parent is not None and parent.id != 0 and parent.mode == ChildMode.parent:
            Child.query.filter(Child.id == parent.id).delete(synchronize_session=False)
        db.session.commit()
        cache.invalidate_all_cached_functions()
        return {"status": 200, "msg": "ok"}
