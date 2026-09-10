from apiflask import abort
from flask.views import MethodView
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, Child, ConfigEnum, Domain, PanelMode, Proxy, Role, User, bulk_register_configs, hconfig, set_hconfig

from .schema import RegisterInputSchema, RegisterOutputSchema


class RegisterApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(RegisterInputSchema, arg_name="data")
    @app.output(RegisterOutputSchema)
    def put(self, data: RegisterInputSchema):
        from hiddifypanel import hutils

        payload = data.model_dump()
        logger.info("Register child panel with unique_id: {}", payload["unique_id"])
        if hutils.node.is_child():
            logger.error("The panel in child, not a parent nor standalone")
            abort(400, "The panel in child, not a parent nor standalone")

        unique_id = payload["unique_id"]
        name = payload["name"]
        mode = payload["mode"]

        child = Child.query.filter(Child.unique_id == unique_id).first()
        if not child:
            logger.info("Adding new child with unique_id: {}", unique_id)
            child = Child(unique_id=unique_id, name=name, mode=mode)
            db.session.add(child)
            db.session.commit()
            child = Child.query.filter(Child.unique_id == unique_id).first()

        try:
            # add data
            logger.info("Adding admin users...")
            AdminUser.bulk_register(payload["panel_data"]["admin_users"], commit=False)
            logger.info("Adding users...")
            User.bulk_register(payload["panel_data"]["users"], commit=False)
            logger.info("Adding domains...")
            Domain.bulk_register(payload["panel_data"]["domains"], commit=False, force_child_unique_id=child.unique_id)
            logger.info("Adding hconfigs...")
            bulk_register_configs(payload["panel_data"]["hconfigs"], commit=False, froce_child_unique_id=child.unique_id)
            logger.info("Adding proxies...")
            Proxy.bulk_register(payload["panel_data"]["proxies"], commit=False, force_child_unique_id=child.unique_id)
            db.session.commit()
        except Exception as err:
            with logger.contextualize(error=err):
                logger.error("Error while registering data")
            abort(400, str(err))

        if not hutils.node.is_parent():
            logger.info("Setting panel to parent mode")
            set_hconfig(ConfigEnum.panel_mode, PanelMode.parent)

        logger.info("Returning register output")
        return RegisterOutputSchema(
            users=[u.to_schema() for u in User.query.all()],
            admin_users=[a.to_schema() for a in AdminUser.query.all()],
            parent_unique_id=hconfig(ConfigEnum.unique_id),
        )
