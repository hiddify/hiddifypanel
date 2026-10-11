from apiflask import abort
from flask import jsonify, request
from flask.views import MethodView
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.cache import cache
from hiddifypanel.database import db
from hiddifypanel.hutils.node import async_job, steplog
from hiddifypanel.models import AdminUser, Child, ConfigEnum, Domain, PanelMode, Role, User, hconfig, set_hconfig
from hiddifypanel.proxy_v3 import outbounds as ob

from .schema import RegisterInputSchema, RegisterOutputSchema, RegisterUsersInputSchema


class RegisterApi(MethodView):
    decorators = [login_required(roles={Role.super_admin}, node_auth=True)]

    @app.input(RegisterInputSchema, arg_name="data")
    @app.output(RegisterOutputSchema)
    def put(self, data: RegisterInputSchema):
        # Node peers may only register/update themselves; super_admin may register any child.
        node = g.get("node")
        if node is not None and node.id != 0 and node.unique_id != data.unique_id:
            abort(403, "Unauthorized")
        if node is None and (not g.account or g.account.role != Role.super_admin):
            abort(403, "Unauthorized")

        if hconfig(ConfigEnum.unique_id) == data.unique_id:
            logger.error("The unique_id is the same as the parent's unique_id")
            abort(400, "The unique_id is the same as the parent's unique_id")

        from hiddifypanel import hutils

        reg = request.headers.get(steplog.REG_HEADER, "")
        panel_data = data.panel_data
        logger.info(f"[register {reg or '-'} parent] node {data.name} ({data.unique_id}) registers: admins={len(panel_data.admin_users)} users={len(panel_data.users)} domains={len(panel_data.domains)} async={async_job.wants_job()}")
        if hutils.node.is_child():
            logger.error("The panel in child, not a parent nor standalone")
            abort(400, "The panel in child, not a parent nor standalone")

        if async_job.wants_job():  # storing a big panel's users takes long: answer now, the node asks for the result
            job = async_job.start(lambda: self._process(data, reg).model_dump(mode="json"))
            answer = jsonify({"job": job})
            answer.status_code = 202  # a Response is passed through by @app.output as it is; a (Response, 202) tuple would not be
            return answer
        return self._process(data, reg)

    def _process(self, data: RegisterInputSchema, reg: str) -> RegisterOutputSchema:
        from hiddifypanel import hutils

        panel_data = data.panel_data
        # Only the uuids of the node's other users came: the ones this panel does not have are asked for after, the others are not sent at all.
        missing = self._missing_user_uuids(data.user_uuids) if data.user_uuids is not None else None
        with steplog.step(reg, "parent", "store the node"):
            child = self._upsert_child(data)
        try:
            with steplog.step(reg, "parent", "store the node's admins, users and domains", admins=len(panel_data.admin_users), users=len(panel_data.users), domains=len(panel_data.domains)):
                AdminUser.bulk_register([a.model_dump(exclude={"default_outbound_slug"}) for a in panel_data.admin_users], commit=False)
                User.bulk_register([u.model_dump(exclude={"preferred_outbound_slug"}) for u in panel_data.users], commit=False)
                Domain.bulk_register(panel_data.domains, remove=True, commit=False, force_child_unique_id=child.unique_id)
                db.session.commit()
        except Exception as err:  # noqa: BLE001
            db.session.rollback()
            logger.exception(f"[register {reg or '-'} parent] storing the node's data failed")
            abort(400, str(err))

        if not hutils.node.is_parent():
            logger.info(f"[register {reg or '-'} parent] setting panel to parent mode")
            set_hconfig(ConfigEnum.panel_mode, PanelMode.parent)

        with steplog.step(reg, "parent", "build the answer for the node"):
            cache.invalidate_all_cached_functions()
            try:
                return RegisterOutputSchema(
                    users=[u.to_schema() for u in User.query.all()],
                    admin_users=[a.to_schema() for a in AdminUser.query.all()],
                    outbounds=ob.export_rows(),
                    parent_unique_id=hconfig(ConfigEnum.unique_id),
                    missing_user_uuids=missing if missing is not None else [],
                )
            except Exception as err:  # noqa: BLE001
                logger.exception(f"[register {reg or '-'} parent] building the answer failed")
                abort(500, str(err))

    @staticmethod
    def _missing_user_uuids(uuids: list[str]) -> list[str]:
        """Of ``uuids``, the users this panel does not have (a user removed here counts as having it: it is not brought back)."""
        have = {row[0] for row in db.session.query(User.uuid).all()}
        return [u for u in dict.fromkeys(uuids) if u not in have]

    @staticmethod
    def _upsert_child(data: RegisterInputSchema) -> Child:
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
        return child


class RegisterJobApi(MethodView):
    """The result of a registration started with ``X-Async-Job`` (see hutils/node/async_job.py)."""

    decorators = [login_required(roles={Role.super_admin}, node_auth=True)]

    def get(self, job_id: str):
        state = async_job.read(job_id)
        if state is None:
            abort(404, "This registration is gone")
        return jsonify(state)


class RegisterUsersApi(MethodView):
    """The users of a node that the parent did not have, sent in chunks after the registration (see ``user_uuids`` of the register call)."""

    decorators = [login_required(roles={Role.super_admin}, node_auth=True)]

    @app.input(RegisterUsersInputSchema, arg_name="data")
    def put(self, data: RegisterUsersInputSchema):
        reg = request.headers.get(steplog.REG_HEADER, "")
        node = g.get("node")
        if node is None and (not g.account or g.account.role != Role.super_admin):
            abort(403, "Unauthorized")
        with steplog.step(reg, "parent", "store users of the node that were missing here", users=len(data.users)):
            try:
                User.bulk_register([u.model_dump(exclude={"preferred_outbound_slug"}) for u in data.users], commit=True)
            except Exception as err:  # noqa: BLE001
                db.session.rollback()
                logger.exception(f"[register {reg or '-'} parent] storing the node's missing users failed")
                abort(400, str(err))
        return {"status": 200, "stored": len(data.users)}
