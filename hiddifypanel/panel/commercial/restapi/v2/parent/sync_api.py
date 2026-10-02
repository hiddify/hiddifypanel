import threading

from apiflask import abort
from flask import request
from flask.views import MethodView
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.cache import cache
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, Domain, User
from hiddifypanel.models.child import Child
from hiddifypanel.proxy_v3 import outbounds as ob

from .schema import SyncInputSchema, SyncOutputSchema

# One sync per node at a time: two overlapping syncs of the same node would both find a new
# domain missing and insert it twice (and fight over the same rows).
_node_locks: dict[str, threading.Lock] = {}
_node_locks_guard = threading.Lock()


def _node_lock(unique_id: str) -> threading.Lock:
    with _node_locks_guard:
        return _node_locks.setdefault(unique_id, threading.Lock())


class SyncApi(MethodView):
    decorators = [login_required(node_auth=True)]

    @app.input(SyncInputSchema, arg_name="data")
    @app.output(SyncOutputSchema)
    def put(self, data: SyncInputSchema):
        payload = data.model_dump()

        unique_id = g.node.unique_id

        logger.info(f"Sync child with unique_id: {unique_id}")
        if not hutils.node.is_parent():
            logger.error("Not a parent")
            abort(400, "Not a parent")

        child = Child.query.filter(Child.unique_id == unique_id).first()
        if not child:
            logger.error("The child does not exist")
            abort(404, "The child does not exist")

        with _node_lock(child.unique_id):
            self._store(payload, child)

        if request.args.get("users") == "0":
            # The node only reported config changes: skip building (and sending) every user.
            return SyncOutputSchema()

        res = SyncOutputSchema(
            users=[u.to_schema() for u in User.query.all()],
            admin_users=[a.to_schema() for a in AdminUser.query.all()],
            outbounds=ob.export_rows(),
        )

        logger.info("Returning sync output")
        return res

    @staticmethod
    def _store(payload: dict, child: Child) -> None:
        try:
            logger.info("Syncing domains...")
            if payload.get("domains"):
                logger.info("Inserting domains into database")
                # remove=True: a domain deleted on the node disappears here too (the node sends all of them).
                Domain.bulk_register(payload["domains"], commit=False, remove=True, force_child_unique_id=child.unique_id)
            else:
                logger.info("Domains field is empty")

            # Only domains are synced; proxies/hconfigs sent by older nodes are ignored.

            logger.info("Commit changes to database")
            child.mark_node_to_parent()
            db.session.commit()
            cache.invalidate_all_cached_functions()
        except Exception as err:
            db.session.rollback()
            with logger.contextualize(error=err):
                logger.error("Error while syncing data")
            abort(400, str(err))
