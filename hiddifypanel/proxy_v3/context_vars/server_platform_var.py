from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, ConfigDict

from hiddifypanel.cache import STATIC, cache

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


_XRAY_BIN = Path("/opt/hiddify-manager/services/xray/bin/xray")


def _binaries_stamp() -> tuple[int, ...]:
    """Modification times of the binaries whose versions are read: a new value whenever one is upgraded."""
    stamp = []
    for path in (shutil.which("haproxy"), _XRAY_BIN, _CORE_BIN):
        try:
            stamp.append(os.stat(path).st_mtime_ns if path else 0)
        except OSError:
            stamp.append(0)
    return tuple(stamp)


def get_server_platform_var() -> ServerPlatformVar:
    return _server_platform_var(_binaries_stamp())


# Running the binaries for their versions takes ~0.2 s: kept across config dumps (no setting changes them) and keyed by
# the binaries' modification times, so an upgraded core is seen at once.
@cache.cache(86400, modes=STATIC)
def _server_platform_var(_stamp: tuple[int, ...]) -> ServerPlatformVar:
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
        version = subprocess.check_output([str(_XRAY_BIN), "version"]).decode("utf-8").split(" ")[1]
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
