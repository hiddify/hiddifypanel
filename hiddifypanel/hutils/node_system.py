"""Live CPU/RAM snapshots from this panel and remote child nodes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import hiddifypanel
from hiddifypanel import hutils
from hiddifypanel.hutils.flask import hurl_for
from hiddifypanel.hutils.node.api_client import NodeApiClient, NodeApiErrorSchema
from hiddifypanel.models import ConfigEnum, hconfig
from hiddifypanel.models.child import Child, ChildMode
from hiddifypanel.panel.commercial.restapi.v2.admin.dashboard_schema import (
    DashboardDiskDetail,
    DashboardNodeStats,
    DashboardOutputSchema,
    MetricsSnapshot,
    NodeSystemCollection,
)

# One retry, short timeout — the dashboard polls every few seconds.
_NODE_TIMEOUT = 30.0
_NODE_RETRIES = 1
_MAX_WORKERS = 8
# Disk detail is fetched on demand (a popup, not the poll loop) and involves a
# `du` scan on the remote side (capped by its own short deadline), so it gets
# a bit more budget than the polled metrics, but the remote side itself now
# answers quickly.
_DISK_DETAIL_TIMEOUT = 15.0
# `?debug_node=1`: fake node ids (copies of this server) to simulate a multi-node panel.
DEBUG_NODE_IDS = (-1, -2, -3)


def is_debug_node(node_id: int | None) -> bool:
    return node_id in DEBUG_NODE_IDS


def debug_node_name(node_id: int) -> str:
    return f"debug-node{-node_id}"


def _local_snapshot(process_limit: int) -> MetricsSnapshot:
    return hutils.system_metrics.snapshot(process_limit=process_limit).with_panel_version(hiddifypanel.__version__)


def _node_from_snapshot(node_id: int, name: str, mode: str, metrics: MetricsSnapshot) -> DashboardNodeStats:
    return DashboardNodeStats(
        id=node_id,
        name=name,
        mode=mode,
        ok=True,
        cpu=metrics.cpu,
        memory=metrics.memory,
        disk=metrics.disk,
        network=metrics.network,
        host=metrics.host,
        processes=metrics.processes,
    )


def _failed_node(node_id: int, name: str, mode: str, error: str) -> DashboardNodeStats:
    return DashboardNodeStats(id=node_id, name=name, mode=mode, ok=False, error=error)


def _local_node(metrics: MetricsSnapshot) -> DashboardNodeStats:
    return _node_from_snapshot(0, "this-server", "local", metrics)


def _fetch_child(child: Child, process_limit: int, parent_key: str) -> DashboardNodeStats:
    name = child.name or f"node-{child.id}"
    mode = str(child.mode)
    base = (child.node_base_url or "").strip()
    if not base:
        return _failed_node(child.id, name, mode, "no_url")
    try:
        client = NodeApiClient(base, timeout=_NODE_TIMEOUT, max_retry=_NODE_RETRIES, apikey=parent_key)
        res = client.get(f"/api/v2/admin/dashboard/?include=system&processes={process_limit}", DashboardOutputSchema)
        if isinstance(res, NodeApiErrorSchema):
            return _failed_node(child.id, name, mode, res.msg)
        return DashboardNodeStats(
            id=child.id,
            name=name,
            mode=mode,
            ok=True,
            cpu=res.system.cpu,
            memory=res.system.memory,
            disk=res.system.disk,
            network=res.system.network,
            host=res.system.host,
            processes=res.processes,
        )
    except BaseException as exc:
        return _failed_node(child.id, name, mode, str(exc))


def fetch_disk_detail(child_id: int | None) -> DashboardDiskDetail:
    """Disk usage + top folders for the disk popup — local, or proxied to a remote node."""
    if child_id in (None, 0) or is_debug_node(child_id):
        res = hutils.system_metrics.disk_detail(node_id=0)
        res.node_id = child_id or 0
        return res

    child = Child.by_id(child_id)
    if not child or child.mode != ChildMode.remote:
        return DashboardDiskDetail(node_id=child_id, error="unknown_node")

    base = (child.node_base_url or "").strip()
    if not base:
        return DashboardDiskDetail(node_id=child_id, error="no_url")

    client = NodeApiClient(base, timeout=_DISK_DETAIL_TIMEOUT, max_retry=1)
    res = client.get("/api/v2/admin/dashboard/disk/", DashboardDiskDetail)
    if isinstance(res, NodeApiErrorSchema):
        return DashboardDiskDetail(node_id=child_id, error=res.msg)
    res.node_id = child_id
    return res


def attach_panel_urls(node_stats: list[DashboardNodeStats], account_uuid: str, admin_base: str) -> None:
    """Link each remote node (online or offline) to its panel, same link as the legacy Node admin.

    Nodes without a base URL fall back to their edit page in this panel's Node admin.
    """
    remote_ids = [row.id for row in node_stats if row.id != 0]
    if not remote_ids:
        return
    bases = {child.id: (child.node_base_url or "").strip().rstrip("/") for child in Child.query.filter(Child.id.in_(remote_ids)).all()}
    for row in node_stats:
        if row.id == 0 or is_debug_node(row.id):
            continue
        base = bases.get(row.id)
        row.panel_url = f"{base}/{account_uuid}/" if base else hurl_for('flask.node.edit_view', id=row.id)


def collect_system_stats(child_id: int | None, process_limit: int = 8, debug_nodes: bool = False) -> NodeSystemCollection:
    """Local + every remote node, in parallel.

    `node_stats` always lists every node (so multi-node views — the network
    breakdown chart/table, node health, … — have full data regardless of which
    node is selected). `system`/`processes` are the metrics for the requested
    `child_id` (or the local node when None), picked out of that same fetch.

    Usage traffic is *not* fetched here — that lives in the parent DB.
    """
    remotes: list[Child] = []
    if hutils.node.is_parent():
        remotes = Child.query.filter(Child.id != 0, Child.mode == ChildMode.remote).order_by(Child.id).all()

    node_stats: list[DashboardNodeStats] = []
    workers = 1 + len(remotes)

    if workers <= 1:
        local = _local_snapshot(process_limit)
        node_stats = [_local_node(local)]
    else:
        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, max(1, workers))) as pool:
            local_future = pool.submit(_local_snapshot, process_limit)
            remote_futures = {pool.submit(_fetch_child, child, process_limit, hconfig(ConfigEnum.unique_id)): child for child in remotes}

            local = local_future.result()
            node_stats.append(_local_node(local))

            for future in as_completed(remote_futures):
                child = remote_futures[future]
                try:
                    node_stats.append(future.result())
                except Exception as exc:
                    node_stats.append(_failed_node(child.id, child.name or f"node-{child.id}", str(child.mode), str(exc)))
    
    if debug_nodes:
        local_row = next(row for row in node_stats if row.id == 0)
        for node_id in DEBUG_NODE_IDS:
            node_stats.append(local_row.model_copy(deep=True, update={"id": node_id, "name": debug_node_name(node_id), "mode": "debug"}))

    # This server first, then real nodes, then the debug copies.
    node_stats.sort(key=lambda row: (row.id < 0, abs(row.id)))

    if child_id is not None:
        chosen = next((row for row in node_stats if row.id == child_id), None)
        if chosen is None:
            chosen = _failed_node(child_id, "unknown", "remote", "unknown_node")
            node_stats = [*node_stats, chosen]
        return NodeSystemCollection(system=chosen.system(), processes=chosen.processes, node_stats=node_stats)

    local_node = node_stats[0]
    return NodeSystemCollection(
        system=local_node.system(),
        processes=local_node.processes,
        node_stats=node_stats,
    )
