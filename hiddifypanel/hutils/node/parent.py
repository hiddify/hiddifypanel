import threading

from flask import has_request_context
from pydantic import BaseModel
from flask_babel import lazy_gettext as _
from loguru import logger

from hiddifypanel import g, hutils
from hiddifypanel.cache import cache
from hiddifypanel.database import db
from hiddifypanel.models import Child, ChildMode, ConfigEnum, Domain, hconfig
from hiddifypanel.panel.commercial.restapi.v2.child.schema import RegisterWithParentInputSchema

from .api_client import NodeApiClient, NodeApiErrorSchema


def get_child_base_url(child: Child) -> str:
    return child.node_base_url


def request_childs_to_sync():
    # Only remote nodes can be asked (virtual ones live in this panel and have no address).
    for c in Child.query.filter(Child.id != 0, Child.mode == ChildMode.remote).all():
        if not request_child_to_sync(c):
            logger.error(f"{c.name}: {_('parent.sync-req-failed')}")
            if has_request_context():
                hutils.flask.flash(f"{c.name}: " + _("parent.sync-req-failed"), "danger")  # just for debug


def notify_childs_users_changed() -> None:
    """After an admin creates/changes/deletes users or admins, ask every node to pull them (in the background)."""
    from . import shared

    if not shared.is_parent():
        return
    if has_request_context():
        shared.run_node_op_in_bg(request_childs_to_sync)
        return
    from flask import current_app, has_app_context

    if not has_app_context():
        return
    app = current_app._get_current_object()  # type: ignore[attr-defined]

    def _run() -> None:
        with app.app_context():
            request_childs_to_sync()

    threading.Thread(target=_run, daemon=True).start()


def request_child_to_sync(child: Child) -> bool:
    """Requests to a child to sync itself with the current panel"""
    base_url = get_child_base_url(child)
    if not base_url:
        logger.error(f"Child {child.name} has no node_base_url")
        return False

    path = "/api/v2/child/sync-parent/"
    # No retries: the node answers at once and syncs in the background; a retry would only
    # start another full sync there.
    res = NodeApiClient(base_url, max_retry=1).post(path, payload=None, output=dict)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while requesting child {child.name} to sync: {res.msg}")
        return False
    if res["msg"] == "ok":
        logger.success(f"Successfully requested child {child.name} to sync")
        child.mark_parent_to_node(commit=True)
        cache.invalidate_all_cached_functions()
        return True

    logger.error(f"Request to child {child.name} to sync failed")
    return False


def _panel_base_url_for_nodes() -> str:
    """``https://<host>/<admin proxy path>/`` a node can call back.

    Prefer the host the admin is using when it is one of our domains (it has a
    certificate); otherwise the first main domain.
    """
    from flask import has_request_context, request

    host = request.host if has_request_context() else ""
    domains = Domain.get_domains()
    known = {d.domain.lower() for d in domains}
    if not host or host.split(":", 1)[0].lower() not in known:
        host = domains[0].domain if domains else host
    return f"https://{host}/{hconfig(ConfigEnum.proxy_path_admin)}/"


class _NodeName(BaseModel):
    name: str


class NodeRegisterError(Exception):
    """``code`` is stable for the UI to translate; ``detail`` is the technical reason."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def register_node(node_admin_link: str, name: str = "") -> Child | None:
    """Add a panel as a node of this panel, given the node's full admin link.

    The node is asked to register itself here (``/api/v2/child/register-parent/``),
    which runs the normal node→parent registration. Raises ``NodeRegisterError``.
    """
    link = (node_admin_link or "").strip()
    if link and not link.endswith("/"):
        link += "/"
    base_url, node_apikey = hutils.flask.extract_parent_info_from_url(link)
    if not base_url or not node_apikey:
        raise NodeRegisterError("invalid_link")

    parent_base = _panel_base_url_for_nodes()
    if base_url.rstrip("/").lower() == parent_base.rstrip("/").lower():
        raise NodeRegisterError("self")

    active, error = hutils.node.is_panel_active(base_url, node_apikey)
    if not active:
        raise NodeRegisterError("unreachable", error)

    before = {c.id for c in Child.query.filter(Child.mode == ChildMode.remote).all()}
    payload = RegisterWithParentInputSchema(
        parent_panel=parent_base,
        name=(name or "").strip() or base_url.split("://", 1)[-1].split("/", 1)[0],
        apikey=str(g.account.uuid),
    )
    # The node calls back while we wait, so allow for its own round trip; do not retry (not idempotent).
    res = NodeApiClient(base_url, node_apikey, max_retry=1, timeout=60).post("/api/v2/child/register-parent/", payload, dict)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while registering node {base_url}: {res.msg}")
        raise NodeRegisterError("rejected", res.msg)

    db.session.expire_all()
    remotes = Child.query.filter(Child.mode == ChildMode.remote).order_by(Child.id.desc()).all()
    child = next((c for c in remotes if c.id not in before), None) or next((c for c in remotes if c.name == payload.name), None)
    cache.invalidate_all_cached_functions()
    logger.success(f"Registered node {payload.name} ({base_url})")
    return child


def rename_node(child: Child, name: str) -> bool:
    """Rename a node here and on the node itself. Returns whether the node took the new name.

    The name is saved here even when the node cannot be reached (or is too old to
    know the call); it then shows again the next time the node registers.
    """
    child.name = name
    db.session.commit()
    base_url = (child.node_base_url or "").strip()
    if not base_url:
        return False
    res = NodeApiClient(base_url, max_retry=1).post("/api/v2/child/node-name/", _NodeName(name=name), dict)
    if isinstance(res, NodeApiErrorSchema):
        logger.warning(f"Node {child.id} renamed here but not on the node: {res.msg}")
        return False
    return True


def remove_node(child: Child) -> bool:
    """Remove a node: tell it to forget this parent, then delete it (and its domains) here.

    Returns whether the node confirmed; it is removed here either way (it may be offline).
    """
    from hiddifypanel.models import CustomProxy, Domain, ProxyBaseConfig, ProxyTemplate, ServerIp, UserDetail

    unlinked = False
    base_url = (child.node_base_url or "").strip()
    if base_url and child.mode == ChildMode.remote:
        res = NodeApiClient(base_url, max_retry=1, timeout=15).post("/api/v2/child/unregister-parent/", None, dict)
        unlinked = not isinstance(res, NodeApiErrorSchema)
        if not unlinked:
            logger.warning(f"Node {child.name} did not confirm leaving this parent: {res.msg}")
    # The node's domains (and their links) go with it; deleted one by one for the before_delete hook.
    for domain in Domain.query.filter(Domain.child_id == child.id).all():
        db.session.delete(domain)

    # Rows that reference the node without a cascade on the relationship.
    for model in (CustomProxy, ProxyTemplate, ProxyBaseConfig, ServerIp, UserDetail):
        model.query.filter(model.child_id == child.id).delete(synchronize_session=False)
    db.session.delete(child)
    db.session.commit()
    cache.invalidate_all_cached_functions()
    return unlinked


def is_child_domain_active(child: Child, domain: Domain) -> bool:
    """Checks whether a child's domain is responsive"""
    if not domain.need_valid_ssl:
        return False
    child_admin_proxy_path = hconfig(ConfigEnum.proxy_path_admin, child.id)
    if not child_admin_proxy_path:
        return False

    return hutils.node.is_panel_active(domain.domain, child_admin_proxy_path)


def get_child_active_domains(child: Child) -> list[Domain]:
    actives = []
    for d in child.domains:  # type: ignore
        if is_child_domain_active(child, d):
            actives.append(d)
    return actives


def is_child_active(child: Child) -> bool:
    for d in child.domains:  # type: ignore
        if is_child_domain_active(child, d):
            return True
    return False
