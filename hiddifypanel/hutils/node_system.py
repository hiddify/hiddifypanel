"""Live CPU/RAM snapshots from this panel and remote child nodes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import hiddifypanel
from hiddifypanel import hutils
from hiddifypanel.hutils.node.api_client import NodeApiClient, NodeApiErrorSchema
from hiddifypanel.models.child import Child, ChildMode
from hiddifypanel.panel.commercial.restapi.v2.admin.dashboard_schema import (
    DashboardNodeStats,
    DashboardOutputSchema,
    MetricsSnapshot,
    NodeSystemCollection,
)

# One retry, short timeout — the dashboard polls every few seconds.
_NODE_TIMEOUT = 3.0
_NODE_RETRIES = 1
_MAX_WORKERS = 8


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


def _fetch_child(child: Child, process_limit: int) -> DashboardNodeStats:
    name = child.name or f"node-{child.id}"
    mode = str(child.mode)
    base = (child.node_base_url or "").strip()
    if not base:
        return _failed_node(child.id, name, mode, "no_url")
    client = NodeApiClient(base, timeout=_NODE_TIMEOUT, max_retry=_NODE_RETRIES)
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


def collect_system_stats(child_id: int | None, process_limit: int = 8) -> NodeSystemCollection:
    """Local stats, a single remote node, or every node in parallel.

    Usage traffic is *not* fetched here — that lives in the parent DB.
    Local snapshot and remote node APIs run concurrently.
    """
    remotes: list[Child] = []
    include_local = False

    if child_id == 0:
        include_local = True
    elif child_id is None:
        include_local = True
        if hutils.node.is_parent():
            remotes = Child.query.filter(Child.id != 0, Child.mode == ChildMode.remote).order_by(Child.id).all()
    else:
        remotes = Child.query.filter(Child.id == child_id, Child.mode == ChildMode.remote).order_by(Child.id).all()
        if not remotes:
            child = Child.by_id(child_id)
            if child and child.id == 0:
                include_local = True
            else:
                return NodeSystemCollection(node_stats=[_failed_node(child_id, "unknown", "remote", "unknown_node")])

    local: MetricsSnapshot | None = None
    node_stats: list[DashboardNodeStats] = []
    workers = int(include_local) + len(remotes)

    if workers <= 1 and include_local and not remotes:
        local = _local_snapshot(process_limit)
        local_node = _local_node(local)
        return NodeSystemCollection(system=local_node.system(), processes=local.processes, node_stats=[local_node])

    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, max(1, workers))) as pool:
        local_future = pool.submit(_local_snapshot, process_limit) if include_local else None
        remote_futures = {pool.submit(_fetch_child, child, process_limit): child for child in remotes}

        if local_future is not None:
            local = local_future.result()
            node_stats.append(_local_node(local))

        for future in as_completed(remote_futures):
            child = remote_futures[future]
            try:
                node_stats.append(future.result())
            except Exception as exc:
                node_stats.append(_failed_node(child.id, child.name or f"node-{child.id}", str(child.mode), str(exc)))

    node_stats.sort(key=lambda row: row.id)

    if child_id is not None and node_stats:
        chosen = node_stats[0]
        return NodeSystemCollection(system=chosen.system(), processes=chosen.processes, node_stats=node_stats)

    local_node = node_stats[0] if node_stats else _local_node(local or _local_snapshot(process_limit))
    return NodeSystemCollection(
        system=local_node.system() if local is None else _local_node(local).system(),
        processes=(local.processes if local is not None else local_node.processes),
        node_stats=node_stats or [local_node],
    )
