from __future__ import annotations

import ipaddress

from hiddifypanel import hutils
from hiddifypanel.database import db
from hiddifypanel.models.server_ip import ServerIp


def _discovered_addresses() -> set[tuple[str, int]]:
    found: set[tuple[str, int]] = set()
    for ip in hutils.network.get_ips():
        version = 6 if isinstance(ip, ipaddress.IPv6Address) else 4
        found.add((str(ip), version))
    return found


def sync_server_ips(child_id: int = 0, *, commit: bool = True) -> int:
    added = 0
    for address, version in _discovered_addresses():
        row = ServerIp.query.filter(
            ServerIp.child_id == child_id,
            ServerIp.address == address,
        ).first()
        if row:
            continue
        db.session.add(
            ServerIp(
                child_id=child_id,
                address=address,
                version=version,
                enabled=True,
                is_auto=True,
            )
        )
        added += 1
    if commit and added:
        db.session.commit()
    return added
