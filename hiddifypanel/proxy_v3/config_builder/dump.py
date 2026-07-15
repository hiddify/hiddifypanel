from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from hiddifypanel.proxy_v3.config_builder.haproxy.server import HaproxyServerDriver
from hiddifypanel.proxy_v3.config_builder.rust_rpxy_l4.server import RustRpxyL4ServerDriver
from hiddifypanel.proxy_v3.config_builder.hiddify_core.server import HiddifyCoreServerDriver
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel
from hiddifypanel.proxy_v3.config_builder.nginx.server import NginxServerDriver
from hiddifypanel.proxy_v3.config_builder.xray.server import XrayServerDriver
from hiddifypanel.proxy_v3.context_vars.builder.server_builder import build_server_template_context

SERVER_CONFIG_DRIVERS: dict[str, type] = {
    "hiddify-core": HiddifyCoreServerDriver,
    "xray": XrayServerDriver,
    "haproxy": HaproxyServerDriver,
    "nginx": NginxServerDriver,
    "rust-rpxy-l4": RustRpxyL4ServerDriver,
}

SERVER_CONFIG_FILES: tuple[tuple[str, str], ...] = (
    ("xray", "xray.json"),
    ("hiddify-core", "hiddify-core.json"),
    ("haproxy", "haproxy.cfg"),
    ("nginx", "nginx.cfg"),
    ("rust-rpxy-l4", "rust-rpxy-l4.toml"),
)


@dataclass
class ServerConfigDumpResult:
    output_dir: Path
    child_id: int
    written: dict[str, int] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def errors(self) -> list[dict[str, Any]]:
        return error_messages(self.messages)

    @property
    def ok(self) -> bool:
        return not self.errors


def error_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [message for message in messages if message.get("level") == "error"]


def build_server_config_for_core(child_id: int, core: str) -> ConfigBuilderModel:
    driver_cls = SERVER_CONFIG_DRIVERS.get(core)
    if driver_cls is None:
        raise ValueError(f"Unsupported server core: {core}")
    ctx = build_server_template_context(child_id)
    return driver_cls().build(child_id, ctx)


def build_hiddify_core_server_config(child_id: int = 0) -> ConfigBuilderModel:
    return build_server_config_for_core(child_id, "hiddify-core")


def _pretty_json_config(rendered: str, *, pretty: bool) -> str:
    if not pretty or not rendered.strip():
        return rendered
    try:
        parsed = json.loads(rendered)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return rendered


def dump_hiddify_core_server_config(
    child_id: int = 0,
    *,
    pretty: bool = True,
) -> tuple[str, ConfigBuilderModel]:
    result = build_hiddify_core_server_config(child_id)
    rendered = _pretty_json_config(result.config or "", pretty=pretty)
    return rendered, result


def dump_all_server_configs(
    output_dir: str | Path,
    child_id: int = 0,
    *,
    pretty: bool = True,
) -> ServerConfigDumpResult:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    dump = ServerConfigDumpResult(output_dir=target, child_id=child_id)
    for core, filename in SERVER_CONFIG_FILES:
        try:
            result = build_server_config_for_core(child_id, core)
        except Exception as exc:
            dump.messages.append(
                {
                    "core": core,
                    "level": "error",
                    "message": str(exc),
                    "data": {"stacktrace": traceback.format_exc()},
                }
            )
            continue

        rendered = result.config or ""
        if core in ("xray", "hiddify-core"):
            rendered = _pretty_json_config(rendered, pretty=pretty)

        for message in result.messages:
            dump.messages.append(
                {
                    "core": core,
                    "level": message.level,
                    "message": message.message,
                    "data": message.data,
                }
            )

        out_path = target / filename
        with open(out_path, "w", encoding="utf-8") as fp:
            fp.write(rendered)
            if rendered and not rendered.endswith("\n"):
                fp.write("\n")
        dump.written[filename] = len(rendered.encode("utf-8"))

    return dump


def format_builder_messages(result: ConfigBuilderModel) -> list[dict[str, Any]]:
    return [message.model_dump() for message in result.messages]
