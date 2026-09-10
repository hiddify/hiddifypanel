from __future__ import annotations

from collections import defaultdict

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
    for driver in enabled_drivers():
        try:
            driver.add_client(user)
        except Exception as e:
            hiddify.error(f"ERROR! {driver.__class__.__name__} has error {e} in add client for user={user.uuid} {e}")
            logger.exception(f"ERROR! {driver.__class__.__name__} has error {e} in add client for user={user.uuid} {e}")


def remove_client(user: User):
    for driver in enabled_drivers():
        try:
            driver.remove_client(user)
        except Exception as e:
            hiddify.error(f"ERROR! {driver.__class__.__name__} has error {e} in remove client for user={user.uuid}")
            logger.exception(f"ERROR! {driver.__class__.__name__} has error {e} in remove client for user={user.uuid}")
