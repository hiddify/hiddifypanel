from __future__ import annotations

import threading
from collections import defaultdict
from types import SimpleNamespace

from flask import current_app
from loguru import logger

from hiddifypanel.drivers.telemt_api import TelemtApi
from hiddifypanel.models import User
from hiddifypanel.models.usage_data import UsageData
from hiddifypanel.panel import hiddify

from .singbox_api import SingboxApi
from .ssh_liberty_bridge_api import SSHLibertyBridgeApi
from .wireguard_api import WireguardApi
from .xray_api import XrayApi

drivers = [
    XrayApi(),
    SingboxApi(),
    SSHLibertyBridgeApi(),
    WireguardApi(),
    TelemtApi(),
]


def enabled_drivers():
    return [d for d in drivers if d.is_enabled()]


def get_users_usage(reset: bool = True) -> dict[str, UsageData]:
    """Aggregate upload/download usage across all enabled drivers."""
    del reset  # drivers currently always reset/consume counters where applicable
    res: dict[str, UsageData] = {}
    for driver in enabled_drivers():
        try:
            all_usage = driver.get_all_usage()
            for uuid, usage in all_usage.items():
                if not usage or not usage.usage:
                    continue
                key = str(uuid)
                row = usage if usage.uuid else UsageData(uuid=key, upload=usage.upload, download=usage.download, devices=usage.devices)
                res[key] = res[key].add(row) if key in res else row
        except Exception as e:
            print(driver)
            hiddify.error(f"ERROR! {driver.__class__.__name__} has error in update usage {e}")
            logger.exception(f"ERROR! {driver.__class__.__name__} has error in update usage {e}")
    return res


def get_enabled_users():
    d: dict[str, int] = defaultdict(int)
    total = 0
    for driver in enabled_drivers():
        try:
            for u, v in driver.get_enabled_users().items():
                if not v:
                    continue
                d[u] += 1
            total += 1
        except Exception as e:
            print(driver)
            hiddify.error(f"ERROR! {driver.__class__.__name__} has error in get_enabled users {e}")
            logger.exception(f"ERROR! {driver.__class__.__name__} has error in get_enabled users {e}")
    res: dict[str, bool] = defaultdict(bool)
    for u, v in d.items():
        res[u] = v >= 1
    return res


def add_client(user: User):
    _note_wish(str(user.uuid), "add")
    _add_one(user)


def _add_one(user) -> None:
    for driver in enabled_drivers():
        try:
            driver.add_client(user)
        except Exception as e:
            hiddify.error(f"ERROR! {driver.__class__.__name__} has error {e} in add client for user={user.uuid} {e}")
            logger.exception(f"ERROR! {driver.__class__.__name__} has error {e} in add client for user={user.uuid} {e}")


#: Batches running in the background: per uuid, how many batches still hold it and the last thing asked for it
#: ("add" / "remove"). A user enabled while a disable batch runs (or the other way round) gets that last wish
#: again once the batch is done, so the batch cannot undo it.
_batch_lock = threading.Lock()
_batch_holds: dict[str, int] = {}
_batch_wish: dict[str, str] = {}


def add_clients(users: list[User], *, background: bool = False):
    """Many users into the cores at once (bulk create / enable): one call per driver instead of one per user.

    ``background``: return at once and do it in a thread (10 000 users on 50 xray inbounds take about two minutes,
    too long for the request). The users are already saved; they can connect once it is done."""
    _batch("add", users, background)


def remove_clients(users: list[User], *, background: bool = False):
    """Many users out of the cores at once (bulk disable / delete); ``background`` as for add_clients."""
    _batch("remove", users, background)


def _batch(op: str, users: list[User], background: bool) -> None:
    if not users:
        return
    # Plain copies: a background thread outlives the request's database session.
    batch = [SimpleNamespace(uuid=str(u.uuid), ed25519_public_key=u.ed25519_public_key) for u in users]
    if not background:
        _run_batch(op, batch)
        return
    uuids = [u.uuid for u in batch]
    with _batch_lock:
        for uuid in uuids:
            _batch_holds[uuid] = _batch_holds.get(uuid, 0) + 1
            _batch_wish[uuid] = op
    app = current_app._get_current_object()  # type: ignore[attr-defined]

    def work() -> None:
        try:
            with app.app_context():
                _run_batch(op, batch)
                with _batch_lock:
                    changed = [uuid for uuid in uuids if _batch_wish.get(uuid, op) != op]
                    wishes = {uuid: _batch_wish[uuid] for uuid in changed}
                    _release(uuids)
                # Asked otherwise while the batch ran: the batch may have undone it
                for uuid, wish in wishes.items():
                    user = SimpleNamespace(uuid=uuid, ed25519_public_key=None)
                    (_add_one if wish == "add" else _remove_one)(user)
        except Exception as e:
            logger.exception(f"{op} of {len(batch)} users in the cores failed: {e}")
        finally:
            with _batch_lock:
                _release(uuids)

    threading.Thread(target=work, name=f"{op}-clients-{len(batch)}", daemon=True).start()


def _release(uuids: list[str]) -> None:
    """Drop this batch's hold on its uuids (the lock is held). Idempotent per batch: ``uuids`` is emptied."""
    for uuid in uuids:
        left = _batch_holds.get(uuid, 0) - 1
        if left > 0:
            _batch_holds[uuid] = left
        else:
            _batch_holds.pop(uuid, None)
            _batch_wish.pop(uuid, None)
    uuids.clear()


def _run_batch(op: str, batch: list) -> None:
    for driver in enabled_drivers():
        try:
            driver.add_clients(batch) if op == "add" else driver.remove_clients(batch)
        except Exception as e:
            hiddify.error(f"ERROR! {driver.__class__.__name__} has error {e} in {op} clients for {len(batch)} users")
            logger.exception(f"ERROR! {driver.__class__.__name__} has error {e} in {op} clients for {len(batch)} users")


def _note_wish(uuid: str, op: str) -> None:
    with _batch_lock:
        if uuid in _batch_holds:
            _batch_wish[uuid] = op


def remove_client(user: User):
    _note_wish(str(user.uuid), "remove")
    _remove_one(user)


def _remove_one(user) -> None:
    for driver in enabled_drivers():
        try:
            driver.remove_client(user)
        except Exception as e:
            hiddify.error(f"ERROR! {driver.__class__.__name__} has error {e} in remove client for user={user.uuid}")
            logger.exception(f"ERROR! {driver.__class__.__name__} has error {e} in remove client for user={user.uuid}")
