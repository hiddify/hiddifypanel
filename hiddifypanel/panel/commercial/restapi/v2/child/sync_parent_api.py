import threading

from flask import current_app
from flask.views import MethodView
from loguru import logger

from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required

# One full sync at a time. The parent asks for a sync after every user change; a full sync
# (all users from the parent, rewritten here) can take longer than the parent waits, and
# overlapping syncs rewriting the same rows fail each other (MariaDB error 1020) and roll back.
_lock = threading.Lock()
_state = {"running": False, "again": False}


def _sync_loop(app) -> None:
    while True:
        with app.app_context():
            try:
                if not hutils.node.child.sync_with_parent():
                    logger.error("Sync with parent failed")
            except Exception:
                logger.exception("Sync with parent failed")
        with _lock:
            if not _state["again"]:
                _state["running"] = False
                return
            _state["again"] = False  # a request came in meanwhile: run once more for its changes


def request_sync_in_background() -> None:
    """Start a full sync with the parent, or queue one more run if one is already going."""
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    with _lock:
        if _state["running"]:
            _state["again"] = True
            return
        _state["running"] = True
    threading.Thread(target=_sync_loop, args=(app,), daemon=True).start()


class SyncWithParentApi(MethodView):
    decorators = [login_required(node_auth=True)]

    def post(self):
        # Answer right away: the parent must not time out (and retry) while this node pulls
        # and rewrites every user; the sync runs in the background, one at a time.
        logger.info(f"Syncing panel with parent requested by {g.node.unique_id}")
        request_sync_in_background()
        return {"status": 200, "msg": "ok"}
