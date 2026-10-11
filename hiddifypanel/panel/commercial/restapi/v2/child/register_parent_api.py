from apiflask import abort
from flask import jsonify, request
from flask.views import MethodView
from flask_babel import gettext as _
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel import hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.hutils.node import async_job, endpoints, steplog
from hiddifypanel.models import Child, ChildMode, ConfigEnum, PanelMode, Role, hconfig, set_hconfig

from .schema import RegisterWithParentInputSchema


class RegisterWithParentApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    # Called by a parent panel that is adding this panel as a node (Admin V2 "Nodes" page). The caller signs in with
    # this panel's own admin link, so it has the owner's permission: it may take the panel over even when the panel is a
    # parent itself or a node of another parent (it then leaves that one).
    @app.input(RegisterWithParentInputSchema, arg_name="data")
    def post(self, data: RegisterWithParentInputSchema):
        reg = request.headers.get(steplog.REG_HEADER, "")
        parent_host = steplog.host_of(data.parent_panel)
        if async_job.wants_job():  # registering waits for the parent, which can take long: answer now, the parent asks for the result
            job = async_job.start(lambda: self._run(data, reg, parent_host))
            return jsonify({"job": job}), 202
        return self._run(data, reg, parent_host)

    def _run(self, data: RegisterWithParentInputSchema, reg: str, parent_host: str) -> dict[str, str | int]:
        with steplog.step(reg, "node", "registration asked by the parent", parent=parent_host, name=data.name):
            return self._register(data, reg, parent_host)

    def _register(self, data: RegisterWithParentInputSchema, reg: str, parent_host: str):
        was_parent = hutils.node.is_parent()
        old_parent = hconfig(ConfigEnum.parent_panel) or ""
        new_parent = data.parent_panel.rstrip("/")
        switching = was_parent or (hutils.node.is_child() and old_parent.rstrip("/") != new_parent)
        if switching:
            logger.warning(f"[register {reg or '-'} node] this panel was {'a parent' if was_parent else 'a node of ' + steplog.host_of(old_parent)}: the owner moves it to {parent_host}")
        old_parent_ids = {c.id for c in Child.query.filter(Child.mode == ChildMode.parent).all()}

        if data.parent_hosts:  # the parent's other domains: used when the one in parent_panel is down
            endpoints.remember_parent_hosts(endpoints.PanelHost(h.domain, h.mode) for h in data.parent_hosts)
        set_hconfig(ConfigEnum.parent_panel, data.parent_panel)
        if data.name:
            set_hconfig(ConfigEnum.node_name, data.name)

        failure = hutils.node.child.register_to_parent_detailed(data.name, data.apikey, defer_apply=True, reg=reg)
        if failure is not None:
            logger.error(f"[register {reg or '-'} node] failed at '{failure.step}' ({failure.kind}): {failure.reason}")
            set_hconfig(ConfigEnum.parent_panel, old_parent)  # nothing changed: it stays what it was
            # Told in a form the parent shows: which side failed, doing what, and why.
            abort(400, f"{_('child.register-failed')}: {failure.text()}", detail={"where": "node", "kind": failure.kind, "step": failure.step, "reason": failure.reason, "parent_host": failure.parent_host})

        with steplog.step(reg, "node", "leave the old relations", was_parent=was_parent, old_parents=len(old_parent_ids)):
            if switching:
                self._leave_old_relations(was_parent, old_parent_ids)
        set_hconfig(ConfigEnum.panel_mode, PanelMode.child)
        logger.info(f"[register {reg or '-'} node] panel mode is now child")
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


class RegisterWithParentJobApi(MethodView):
    """The result of a registration started with ``X-Async-Job`` (see hutils/node/async_job.py)."""

    decorators = [login_required({Role.super_admin})]

    def get(self, job_id: str):
        state = async_job.read(job_id)
        if state is None:
            abort(404, "This registration is gone")
        return jsonify(state)
