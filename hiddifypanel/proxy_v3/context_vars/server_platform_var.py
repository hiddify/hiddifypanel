from __future__ import annotations

import re
import subprocess
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, ConfigDict

from hiddifypanel.cache import cache

from .version import TemplateVersion

# The binary's NEEDED entry is ./lib/hiddify-core.so, resolved from the process
# cwd. Running it from anywhere else makes the loader exit 127.
_CORE_DIR = Path("/opt/hiddify-manager/services/hiddify-core")
_CORE_BIN = _CORE_DIR / "hiddify-core"
_VERSION_TOKEN = re.compile(r"(\d+\.\d+\.\d+(?:[-.]?(?:rc|alpha|beta|a|b|pre)\.?\d*)?)")


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
        version = subprocess.check_output(["/opt/hiddify-manager/services/xray/bin/xray", "version"]).decode("utf-8").split(" ")[1]
        return TemplateVersion(version)
    except Exception as e:
        logger.error(f"Error getting xray version: {e}")
        return TemplateVersion("0.0.0")


def _first_output_line(cmd: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd).decode("utf-8").splitlines()[0].strip()


def _core_version_line() -> str:
    return _first_output_line([str(_CORE_BIN), "version"], cwd=_CORE_DIR)


def _version_token(token: str) -> str:
    match = _VERSION_TOKEN.search(token.lstrip("v"))
    return match.group(1) if match else "0.0.0"


def get_hiddifycore_version() -> TemplateVersion:
    try:
        parts = _core_version_line().split()
        version = _version_token(parts[2]) if len(parts) > 2 else "0.0.0"
        return TemplateVersion(version)
    except Exception as e:
        logger.error(f"Error getting hiddifycore version: {e}")
        return TemplateVersion("0.0.0")


def get_singbox_version() -> TemplateVersion:
    try:
        parts = _core_version_line().split()
        version = _version_token(parts[-1]) if len(parts) > 5 else "0.0.0"
        return TemplateVersion(version)
    except Exception as e:
        logger.error(f"Error getting singbox version: {e}")
        return TemplateVersion("0.0.0")
