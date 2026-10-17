"""HAProxy's runtime API (``stats socket /run/hiddify-haproxy-api.sock``, ``haproxy/server/global.j2``).

The panel changes HAProxy at runtime through it, with no reload: in-memory maps (short links, ACME challenges) and the
TLS certificates it serves (``hiddifypanel/acme/store.py``). One command per connection.
"""

from __future__ import annotations

import socket
import threading

from loguru import logger

API_SOCKET = "/run/hiddify-haproxy-api.sock"

# Map changes of this process go one at a time: a reconcile (show, then add / del) must not interleave with an add.
map_lock = threading.RLock()


def command(cmd: str, payload: str | None = None, timeout: float = 3) -> str | None:
    """One command on HAProxy's API socket: its answer, or None when HAProxy can not be reached.

    ``payload``: the multi-line body of a ``<<`` command (``set ssl cert <file> <<``), sent after the command line and
    ended with an empty line.
    """
    data = cmd.encode()
    if payload is not None:
        # The payload ends at the first empty line: one inside it (e.g. between the certificates of a chain, as ACME
        # returns it) would cut it there and HAProxy would serve the certificate without its chain.
        body = "\n".join(line for line in payload.splitlines() if line.strip())
        data += b" <<\n" + body.encode() + b"\n\n"
    else:
        data += b"\n"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(API_SOCKET)
            s.sendall(data)
            chunks = []
            while chunk := s.recv(65536):
                chunks.append(chunk)
    except OSError as e:
        logger.debug(f"HAProxy API not reachable ({e}) for: {cmd}")
        return None
    return b"".join(chunks).decode(errors="replace").strip()


def show_map(map_name: str) -> dict[str, str] | None:
    """key -> value of a map, or None when HAProxy can not be reached."""
    shown = command(f"show map {map_name}")
    if shown is None:
        return None
    entries: dict[str, str] = {}
    for line in shown.splitlines():
        parts = line.split(" ", 2)  # "<id> <key> <value>"
        if len(parts) == 3 and parts[0].startswith("0x"):
            entries[parts[1]] = parts[2]
    return entries


def add_map(map_name: str, key: str, value: str) -> bool:
    """Add or replace one entry. False when HAProxy can not be reached or refused it."""
    with map_lock:
        current = show_map_entry(map_name, key)
        if current is None:
            return False
        answer = command(f"set map {map_name} {key} {value}" if current else f"add map {map_name} {key} {value}")
    if answer is None:
        return False
    if answer:
        logger.warning(f"HAProxy answered a change of map {map_name}: {answer}")
        return False
    return True


def show_map_entry(map_name: str, key: str) -> bool | None:
    """Whether the map has ``key`` (None: HAProxy can not be reached)."""
    answer = command(f"get map {map_name} {key}")
    if answer is None:
        return None
    return "found=yes" in answer and f'key="{key}"' in answer


def del_map(map_name: str, key: str) -> None:
    with map_lock:
        command(f"del map {map_name} {key}")


def sync_map(map_name: str, wanted: dict[str, str]) -> bool:
    """Make a map hold exactly ``wanted``: drop the other keys, add the missing ones. False when HAProxy is not reachable."""
    with map_lock:
        current = show_map(map_name)
        if current is None:
            return False
        for key in current.keys() - wanted.keys():
            command(f"del map {map_name} {key}")
        for key, value in wanted.items():
            if current.get(key) != value:
                command(f"set map {map_name} {key} {value}" if key in current else f"add map {map_name} {key} {value}")
    return True
