"""A node's sync with its parent, read only, for debugging (``hutils.node.sync_report``)."""

from __future__ import annotations

from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.hutils.node.sync_report import NodeSyncReport, build
from hiddifypanel.models.role import Role


class NodeSyncStatusApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(NodeSyncReport)
    def get(self) -> NodeSyncReport:
        """Node: what it holds and when each kind of data last synced with the parent (read only)"""
        return build()
