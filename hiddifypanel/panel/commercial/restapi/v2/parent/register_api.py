from apiflask import abort
from flask.views import MethodView
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.cache import cache
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, Child, ConfigEnum, Domain, PanelMode, Role, User, hconfig, set_hconfig

from .schema import RegisterInputSchema, RegisterOutputSchema


class RegisterApi(MethodView):
    # decorators = [login_required({Role.super_admin})]

    @app.input(RegisterInputSchema, arg_name="data")
    @app.output(RegisterOutputSchema)
    def put(self, data: RegisterInputSchema):
        if g.node.id != 0 and g.node.unique_id != data.unique_id:
            abort(403, "Unauthorized")
        if g.node.id == 0 and g.account.role != Role.super_admin:
            abort(403, "Unauthorized")

        if hconfig(ConfigEnum.unique_id) == data.unique_id:
            logger.error("The unique_id is the same as the parent's unique_id")
            abort(400, "The unique_id is the same as the parent's unique_id")

        from hiddifypanel import hutils

        logger.info("Register child panel with unique_id: {}", data.unique_id)
        if hutils.node.is_child():
            logger.error("The panel in child, not a parent nor standalone")
            abort(400, "The panel in child, not a parent nor standalone")

        child = Child.query.filter(Child.unique_id == data.unique_id).first()
        if not child:
            logger.info("Adding new child with unique_id: {}", data.unique_id)
            child = Child(unique_id=data.unique_id, name=data.name, mode=data.mode, node_base_url=data.node_base_url)
            child.mark_node_to_parent()
            db.session.add(child)
            db.session.commit()
            child = Child.query.filter(Child.unique_id == data.unique_id).first()
            if not child:
                abort(500, f"Failed to create child with unique_id: {data.unique_id}")

        else:
            child.name = data.name
            child.mode = data.mode
            child.node_base_url = data.node_base_url
            child.mark_node_to_parent()
            db.session.commit()

        try:
            # add data
            logger.info("Adding admin users...")
            AdminUser.bulk_register(data.panel_data.admin_users, commit=False)
            logger.info("Adding users...")
            User.bulk_register(data.panel_data.users, commit=False)
            logger.info("Adding domains...")
            Domain.bulk_register(data.panel_data.domains, remove=True, commit=False, force_child_unique_id=child.unique_id)
            # logger.info("Adding hconfigs...")
            # bulk_register_configs(data.panel_data.hconfigs, commit=False, froce_child_unique_id=child.unique_id)
            # logger.info("Adding proxies...")
            # Proxy.bulk_register(data.panel_data.proxies, commit=False, force_child_unique_id=child.unique_id)
            db.session.commit()
        except Exception as err:
            db.session.rollback()
            with logger.contextualize(error=err):
                logger.exception("Error while registering data")
            abort(400, str(err))

        if not hutils.node.is_parent():
            logger.info("Setting panel to parent mode")
            set_hconfig(ConfigEnum.panel_mode, PanelMode.parent)

        cache.invalidate_all_cached_functions()
        logger.info("Returning register output")
        try:
            return RegisterOutputSchema(
                users=[u.to_schema() for u in User.query.all()],
                admin_users=[a.to_schema() for a in AdminUser.query.all()],
                parent_unique_id=hconfig(ConfigEnum.unique_id),
            )
        except Exception as err:
            logger.exception("Error while building register output")
            abort(500, str(err))
