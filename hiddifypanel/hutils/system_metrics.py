"""Structured system metrics for the Admin V2 dashboard.

Each metric group is exposed as a small function so views can pick what they
need, and `snapshot()` composes them for the dashboard endpoint.
Values are normalized (GB for sizes, 0-100 for percentages) so clients never
have to convert units.
"""

from __future__ import annotations

import os
import socket
import time

import psutil

from .system import get_folder_size

ONE_GB = 1024**3
HIDDIFY_DIR = "/opt/hiddify-manager/"
PANEL_PROCESS_USER = "hiddify-panel"
PANEL_PROCESS_LABEL = "Hiddify"

# walking the install directory is expensive, and the dashboard polls often
HIDDIFY_SIZE_TTL = 300.0
_hiddify_size: tuple[float, float] | None = None

# psutil reports cpu percent relative to the previous call. The first call of a
# worker has no reference point, so it is primed with a short blocking sample.
_PRIME_INTERVAL = 0.15
_cpu_primed = False
_processes_primed = False


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def _percent(used: float, total: float) -> float:
    if not total:
        return 0.0
    return _round(used * 100 / total, 1)


def cpu_metrics() -> dict:
    """Overall and per-core CPU load plus normalized load averages."""
    global _cpu_primed
    per_core = psutil.cpu_percent(interval=None if _cpu_primed else _PRIME_INTERVAL, percpu=True)
    _cpu_primed = True

    cores = len(per_core) or psutil.cpu_count() or 1
    overall = sum(per_core) / cores if per_core else 0.0
    load_avg = os.getloadavg()

    return {
        "percent": _round(overall, 1),
        "per_core": [_round(value, 1) for value in per_core],
        "cores": cores,
        "load_avg": [_round(value) for value in load_avg],
        # load average as a percentage of total capacity (1.0 per core)
        "load_percent": [_percent(value, cores) for value in load_avg],
    }


def memory_metrics() -> dict:
    """RAM and swap usage in GB."""
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cached = getattr(ram, "cached", 0) + getattr(ram, "buffers", 0)

    return {
        "used_gb": _round(ram.used / ONE_GB),
        "total_gb": _round(ram.total / ONE_GB),
        "available_gb": _round(ram.available / ONE_GB),
        "cached_gb": _round(cached / ONE_GB),
        "percent": _percent(ram.used, ram.total),
        "swap_used_gb": _round(swap.used / ONE_GB),
        "swap_total_gb": _round(swap.total / ONE_GB),
        "swap_percent": _percent(swap.used, swap.total),
    }


def hiddify_size_gb() -> float:
    """Size of the Hiddify installation, cached for `HIDDIFY_SIZE_TTL` seconds."""
    global _hiddify_size
    now = time.time()
    if _hiddify_size is None or now - _hiddify_size[0] > HIDDIFY_SIZE_TTL:
        _hiddify_size = (now, _round(get_folder_size(HIDDIFY_DIR) / ONE_GB))
    return _hiddify_size[1]


def disk_metrics(include_hiddify: bool = True) -> dict:
    """Root filesystem usage, plus the size of the Hiddify installation."""
    disk = psutil.disk_usage("/")
    hiddify_gb = hiddify_size_gb() if include_hiddify else None

    return {
        "used_gb": _round(disk.used / ONE_GB),
        "total_gb": _round(disk.total / ONE_GB),
        "free_gb": _round(disk.free / ONE_GB),
        "percent": _percent(disk.used, disk.total),
        "hiddify_gb": hiddify_gb,
    }


def network_metrics(include_connections: bool = True) -> dict:
    """Cumulative traffic counters; clients derive throughput from two samples."""
    net = psutil.net_io_counters()
    total_connections = 0
    unique_ips = 0

    if include_connections:
        try:
            connections = psutil.net_connections()
            total_connections = len(connections)
            unique_ips = len({conn.raddr.ip for conn in connections if conn.status == "ESTABLISHED" and conn.raddr})
        except (psutil.AccessDenied, PermissionError):
            total_connections = 0
            unique_ips = 0

    return {
        "bytes_sent": int(net.bytes_sent),
        "bytes_recv": int(net.bytes_recv),
        "sent_gb": _round(net.bytes_sent / ONE_GB),
        "recv_gb": _round(net.bytes_recv / ONE_GB),
        "total_gb": _round((net.bytes_sent + net.bytes_recv) / ONE_GB),
        "sampled_at": time.time(),
        "connections": total_connections,
        "unique_ips": unique_ips,
    }


def _process_rows() -> list[tuple[str, float, float]]:
    """(name, cpu percent of whole machine, memory GB) aggregated per program."""
    global _processes_primed
    cores = psutil.cpu_count() or 1
    attrs = ["name", "username", "cpu_percent", "memory_info"]

    if not _processes_primed:
        list(psutil.process_iter(attrs))
        time.sleep(_PRIME_INTERVAL)
        _processes_primed = True

    cpu_by_name: dict[str, float] = {}
    memory_by_name: dict[str, float] = {}

    for proc in psutil.process_iter(attrs):
        info = proc.info
        name = info.get("name") or ""
        if not name:
            continue
        if info.get("username") == PANEL_PROCESS_USER:
            name = PANEL_PROCESS_LABEL
        memory_info = info.get("memory_info")
        cpu_by_name[name] = cpu_by_name.get(name, 0.0) + (info.get("cpu_percent") or 0.0) / cores
        memory_by_name[name] = memory_by_name.get(name, 0.0) + (memory_info.rss if memory_info else 0) / ONE_GB

    return [(name, cpu_by_name[name], memory_by_name.get(name, 0.0)) for name in cpu_by_name]


def process_metrics(limit: int = 8) -> dict:
    """Top consumers by CPU and by memory."""
    rows = _process_rows()
    ram_total = psutil.virtual_memory().total / ONE_GB

    by_cpu = sorted(rows, key=lambda row: row[1], reverse=True)[:limit]
    by_memory = sorted(rows, key=lambda row: row[2], reverse=True)[:limit]

    return {
        "count": len(rows),
        "cpu": [{"name": name, "percent": _round(cpu, 1), "memory_gb": _round(memory)} for name, cpu, memory in by_cpu],
        "memory": [
            {"name": name, "memory_gb": _round(memory), "percent": _percent(memory, ram_total), "cpu_percent": _round(cpu, 1)}
            for name, cpu, memory in by_memory
        ],
    }


def host_metrics() -> dict:
    boot_time = psutil.boot_time()
    return {
        "hostname": socket.gethostname(),
        "boot_time": boot_time,
        "uptime_s": int(max(0, time.time() - boot_time)),
    }


def snapshot(process_limit: int = 8) -> dict:
    """All metric groups in one payload."""
    return {
        "cpu": cpu_metrics(),
        "memory": memory_metrics(),
        "disk": disk_metrics(),
        "network": network_metrics(),
        "host": host_metrics(),
        "processes": process_metrics(process_limit),
    }
