from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.hutils.node.sync_report import NodeSyncReport, build


class NodeSyncStatusForParentApi(MethodView):
    """The parent's Nodes page asks how this node's sync is going (read only)."""

    decorators = [login_required(node_auth=True)]

    @app.output(NodeSyncReport)
    def get(self) -> NodeSyncReport:
        return build()
