from apiflask import abort
from flask.views import MethodView
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, Domain, Proxy, User, bulk_register_configs
from hiddifypanel.models.child import Child

from .schema import SyncInputSchema, SyncOutputSchema


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

        try:
            logger.info("Syncing domains...")
            if payload.get("domains"):
                logger.info("Inserting domains into database")
                Domain.bulk_register(payload["domains"], commit=False, force_child_unique_id=child.unique_id)
            else:
                logger.info("Domains field is empty")

            logger.info("Syncing hconfigs...")
            if payload.get("hconfigs"):
                logger.info("Inserting hconfigs into database")
                bulk_register_configs(payload["hconfigs"], commit=False, froce_child_unique_id=child.unique_id)
            else:
                logger.info("Hconfigs field is empty")

            logger.info("Syncing proxies...")
            if payload.get("proxies"):
                logger.info("Inserting proxies into database")
                Proxy.bulk_register(payload["proxies"], commit=False, force_child_unique_id=child.unique_id)
            else:
                logger.info("Proxies field is empty")

            logger.info("Commit changes to database")
            db.session.commit()
        except Exception as err:
            with logger.contextualize(error=err):
                logger.error("Error while syncing data")
            abort(400, str(err))

        res = SyncOutputSchema(
            users=[u.to_schema() for u in User.query.all()],
            admin_users=[a.to_schema() for a in AdminUser.query.all()],
        )

        logger.info("Returning sync output")
        return res
