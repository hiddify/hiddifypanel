"""Custom outbounds written by the admin as JSON: ONE hiddify-core outbound, ONE hiddify-core endpoint or ONE xray outbound.

The panel gives the object its tag (the outbound's slug, unique and stable), so the routing and the bridge can refer to it;
a ``tag`` written by the admin is ignored. A custom outbound runs in one core; the other core reaches it through a local SOCKS bridge:

* ``core_outbound`` / ``core_endpoint`` run in hiddify-core. Its routing uses the tag; xray gets a SOCKS outbound (same tag) to a
  local hiddify-core SOCKS inbound that routes into the object.
* ``xray_outbound`` runs in xray (routing by tag); hiddify-core gets a SOCKS outbound to a local xray SOCKS inbound.

Nothing is stored unless it is valid: the text is parsed, checked, and run through the real core (``xray run -test`` /
``hiddify-core srun``) before it is accepted.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from hiddifypanel.models.outbound import Outbound, OutboundMode

MANAGER_ROOT = Path(os.environ.get("HIDDIFY_CONFIG_PATH") or "/opt/hiddify-manager")
XRAY_BIN = MANAGER_ROOT / "services" / "xray" / "bin" / "xray"
CORE_DIR = MANAGER_ROOT / "services" / "hiddify-core"
CORE_BIN = CORE_DIR / "hiddify-core"

#: How long hiddify-core must stay up before its config counts as good (decode errors show in well under a second).
CORE_STARTUP_SECONDS = 4
XRAY_TEST_TIMEOUT = 20
MAX_TEXT = 200_000
MAX_ITEMS = 50
#: First local port of the SOCKS bridges; a bridge uses BRIDGE_PORT_BASE + the outbound's id.
BRIDGE_PORT_BASE = 27000

#: mode -> (the list key of a pasted wrapper, field that names the kind of object)
SHAPE: dict[OutboundMode, tuple[str, str]] = {
    OutboundMode.core_outbound: ("outbounds", "type"),
    OutboundMode.core_endpoint: ("endpoints", "type"),
    OutboundMode.xray_outbound: ("outbounds", "protocol"),
}

#: The tag the object has while the real core checks it.
CHECK_TAG = "custom-check"


class CustomOutboundError(ValueError):
    """The JSON can not be stored; ``str(e)`` is shown to the admin as is."""


@dataclass(frozen=True)
class CustomConfig:
    mode: OutboundMode
    #: The object as the admin wrote it, without a tag.
    item: dict[str, Any]

    def with_tag(self, tag: str) -> dict[str, Any]:
        """The object as the core gets it: ``tag`` first."""
        return {"tag": tag, **self.item}


def bridge_port(outbound_id: int) -> int:
    return BRIDGE_PORT_BASE + int(outbound_id)


def custom_tag(row: Outbound) -> str:
    """The tag of a custom outbound in the generated configs: its slug."""
    return row.slug or f"custom-{row.id}"


# --------------------------------------------------------------------------- structure


def parse(mode: OutboundMode | str, text: str | None) -> CustomConfig:
    """Parse and check the structure. Raises CustomOutboundError."""
    mode = OutboundMode(str(mode))
    if mode not in SHAPE:
        raise CustomOutboundError(f"{mode} outbounds have no JSON")
    key, kind = SHAPE[mode]
    what = "endpoint" if mode == OutboundMode.core_endpoint else "outbound"
    text = (text or "").strip()
    if not text:
        raise CustomOutboundError("The JSON is empty")
    if len(text) > MAX_TEXT:
        raise CustomOutboundError(f"The JSON is too long (at most {MAX_TEXT} characters)")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise CustomOutboundError(f"Not valid JSON: {e.msg} (line {e.lineno}, column {e.colno})") from e
    if not isinstance(data, dict):
        raise CustomOutboundError(f"The JSON must be one {what} object like {{\"{kind}\": ...}}")
    # A pasted {"outbounds": [ {...} ]} with one object inside is fine; more than one is not.
    if set(data) == {key} and isinstance(data[key], list):
        if len(data[key]) != 1:
            raise CustomOutboundError(f"Give exactly one {what}: each one is a separate entry here, so the panel can give it its own tag")
        data = data[key][0]
        if not isinstance(data, dict):
            raise CustomOutboundError(f"The {what} must be an object")
    elif key in data and isinstance(data[key], list):
        raise CustomOutboundError(f'Give one {what} object, not a "{key}" list with other settings')
    if not isinstance(data.get(kind), str) or not data[kind].strip():
        raise CustomOutboundError(f'The {what} needs a "{kind}"')
    item = {k: v for k, v in data.items() if k != "tag"}  # the panel sets the tag
    return CustomConfig(mode=mode, item=item)


# --------------------------------------------------------------------------- run it through the real core


def _base_singbox() -> list[dict[str, Any]]:
    # The tags the panel's own config always has, so entries can refer to them (detour, selector members).
    return [{"tag": "freedom", "type": "direct"}, {"tag": "direct", "type": "direct"}, {"tag": "WARP", "type": "direct"}, {"tag": "block", "type": "block"}]


def _base_xray() -> list[dict[str, Any]]:
    return [{"tag": "freedom", "protocol": "freedom"}, {"tag": "direct", "protocol": "freedom"}, {"tag": "WARP", "protocol": "freedom"}, {"tag": "blackhole", "protocol": "blackhole"}]


def test_config(cfg: CustomConfig) -> dict[str, Any]:
    """The smallest full config of the core that runs this object."""
    item = cfg.with_tag(CHECK_TAG)
    if cfg.mode == OutboundMode.xray_outbound:
        return {"log": {"loglevel": "error"}, "outbounds": [*_base_xray(), item]}
    base: dict[str, Any] = {"log": {"level": "error"}, "outbounds": _base_singbox()}
    if cfg.mode == OutboundMode.core_endpoint:
        base["endpoints"] = [item]
    else:
        base["outbounds"] = [*base["outbounds"], item]
    return base


def _clip(text: str, limit: int = 500) -> str:
    """The line of the core's output that says what is wrong (else the last line), without colours or the temp path."""
    lines = [re.sub(r"\x1b\[[0-9;]*m", "", ln).strip() for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if ln]
    pick = next((ln for ln in lines if re.search(r"Failed|FATAL|panic|error", ln, re.IGNORECASE)), lines[-1] if lines else "no details")
    pick = re.sub(r"/tmp/hiddify-outbound-test-\w+/config\.json", "config", pick)
    return pick if len(pick) <= limit else pick[:limit] + " …"


def run_core_check(cfg: CustomConfig) -> None:
    """Run the entries through xray / hiddify-core. Raises CustomOutboundError when the core refuses them.

    When the core program is not installed on this machine the structure check above is all that can be done.
    """
    xray = cfg.mode == OutboundMode.xray_outbound
    binary = XRAY_BIN if xray else CORE_BIN
    if not binary.exists() and shutil.which(binary.name) is None:
        logger.warning(f"{binary} not found: the custom outbound was only checked for structure")
        return
    exe = str(binary) if binary.exists() else str(shutil.which(binary.name))
    with tempfile.TemporaryDirectory(prefix="hiddify-outbound-test-") as tmp:
        path = Path(tmp) / "config.json"
        path.write_text(json.dumps(test_config(cfg)), encoding="utf-8")
        try:
            if xray:
                res = subprocess.run([exe, "run", "-test", "-c", str(path)], capture_output=True, text=True, timeout=XRAY_TEST_TIMEOUT, cwd=tmp)
                if res.returncode != 0:
                    raise CustomOutboundError("xray rejected it: " + _clip(res.stdout + "\n" + res.stderr))
                return
            # hiddify-core has no dry run: it must stay up for a few seconds; a bad config makes it exit at once.
            proc = subprocess.run([exe, "srun", "-c", str(path), "-D", tmp], capture_output=True, text=True, timeout=CORE_STARTUP_SECONDS, cwd=str(CORE_DIR if CORE_DIR.is_dir() else tmp))
            raise CustomOutboundError("hiddify-core rejected it: " + _clip(proc.stdout + "\n" + proc.stderr))
        except subprocess.TimeoutExpired:
            if xray:
                raise CustomOutboundError("xray did not finish checking in time") from None
            return  # still running: accepted
        except OSError as e:
            logger.warning(f"Could not run {exe} to check a custom outbound: {e}")


def validate(mode: OutboundMode | str, text: str | None, *, run_core: bool = True) -> CustomConfig:
    """Everything a custom outbound must pass before it is stored. Raises CustomOutboundError."""
    cfg = parse(mode, text)
    if run_core:
        run_core_check(cfg)
    return cfg


def normalized(cfg: CustomConfig) -> str:
    """What is stored: the object, indented, without a tag."""
    return json.dumps(cfg.item, indent=2, ensure_ascii=False)
