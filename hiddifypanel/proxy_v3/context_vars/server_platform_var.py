from __future__ import annotations

import subprocess

from loguru import logger
from pydantic import BaseModel, ConfigDict

from hiddifypanel.cache import cache

from .version import TemplateVersion


class ServerPlatformVar(BaseModel):
    """Typed server-side platform context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    haproxy_version: TemplateVersion
    xray_version: TemplateVersion
    hiddifycore_version: TemplateVersion
    singbox_version: TemplateVersion


@cache.cache(600)
def get_server_platform_var() -> ServerPlatformVar:
    return ServerPlatformVar(
        haproxy_version=(get_haproxy_version()),
        xray_version=(get_xray_version()),
        hiddifycore_version=(get_hiddifycore_version()),
        singbox_version=(get_singbox_version()),
    )


def get_haproxy_version() -> TemplateVersion:
    try:
        version = subprocess.check_output(["haproxy", "-v"]).decode("utf-8").split(" ")[2].split("-")[0]
        return TemplateVersion(version)
    except Exception as e:
        logger.error(f"Error getting haproxy version: {e}")
        return TemplateVersion("0.0.0")


def get_xray_version() -> TemplateVersion:
    try:
        version = subprocess.check_output(["/opt/hiddify-manager/xray/bin/xray", "version"]).decode("utf-8").split(" ")[1]
        return TemplateVersion(version)
    except Exception as e:
        logger.error(f"Error getting xray version: {e}")
        return TemplateVersion("0.0.0")


def _first_output_line(cmd: list[str]) -> str:
    return subprocess.check_output(cmd).decode("utf-8").splitlines()[0].strip()


def get_hiddifycore_version() -> TemplateVersion:
    try:
        line = _first_output_line(["/opt/hiddify-manager/singbox/hiddify-core", "version"])
        parts = line.split()
        version = parts[2].lstrip("v") if len(parts) > 2 else "0.0.0"
        return TemplateVersion(version)
    except Exception as e:
        logger.error(f"Error getting hiddifycore version: {e}")
        return TemplateVersion("0.0.0")


def get_singbox_version() -> TemplateVersion:
    try:
        line = _first_output_line(["/opt/hiddify-manager/singbox/hiddify-core", "version"])
        parts = line.split()
        version = parts[-1] if len(parts) > 5 else "0.0.0"
        return TemplateVersion(version)
    except Exception as e:
        logger.error(f"Error getting singbox version: {e}")
        return TemplateVersion("0.0.0")
