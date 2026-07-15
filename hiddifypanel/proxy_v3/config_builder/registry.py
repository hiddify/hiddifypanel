from __future__ import annotations

from typing import TYPE_CHECKING

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide

from .base import BaseConfigBuilderDriver

if TYPE_CHECKING:
    pass

_DRIVERS: dict[tuple[TemplateCore, BaseConfigSide], BaseConfigBuilderDriver] = {}


def _register(driver: BaseConfigBuilderDriver) -> BaseConfigBuilderDriver:
    _DRIVERS[(driver.core, driver.side)] = driver
    return driver


def get_config_builder_driver(core: TemplateCore, side: BaseConfigSide) -> BaseConfigBuilderDriver | None:
    _load_drivers()
    return _DRIVERS.get((core, side))


def _load_drivers() -> None:
    if _DRIVERS:
        return
    from .haproxy import server as haproxy_server
    from .hiddify_core import client as hiddify_core_client
    from .hiddify_core import server as hiddify_core_server
    from .nginx import server as nginx_server
    from .rust_rpxy_l4 import server as rust_rpxy_l4_server
    from .xray import server as xray_server

    _register(hiddify_core_server.HiddifyCoreServerDriver())
    _register(hiddify_core_client.HiddifyCoreClientDriver())
    _register(xray_server.XrayServerDriver())
    _register(haproxy_server.HaproxyServerDriver())
    _register(nginx_server.NginxServerDriver())
    _register(rust_rpxy_l4_server.RustRpxyL4ServerDriver())


def ensure_drivers_loaded() -> None:
    _load_drivers()
