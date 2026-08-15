from __future__ import annotations

import json
import re
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
    stats: dict[str, dict[str, int]] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def errors(self) -> list[dict[str, Any]]:
        return error_messages(self.messages)

    @property
    def ok(self) -> bool:
        return not self.errors


def error_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [message for message in messages if message.get("level") == "error"]


def _line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def summarize_dumped_config(core: str, rendered: str) -> dict[str, int]:
    """Return file stats used by dump-server-configs CLI output."""
    stats: dict[str, int] = {"lines": _line_count(rendered)}
    text = rendered or ""

    if core in ("xray", "hiddify-core"):
        try:
            data = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            for key in ("inbounds", "outbounds", "endpoints"):
                value = data.get(key)
                stats[key] = len(value) if isinstance(value, list) else 0
        else:
            stats.update(inbounds=0, outbounds=0, endpoints=0)
    elif core == "haproxy":
        stats["frontends"] = len(re.findall(r"(?m)^\s*frontend\s+\S+", text))
        stats["backends"] = len(re.findall(r"(?m)^\s*backend\s+\S+", text))
    elif core == "rust-rpxy-l4":
        stats["services"] = len(re.findall(r"(?m)^\s*\[protocols\.[^\]]+\]", text))

    return stats


def format_dump_stats(filename: str, size: int, stats: dict[str, int] | None) -> str:
    stats = stats or {}

    def _n(count: int, singular: str, plural: str | None = None) -> str:
        label = singular if count == 1 else (plural or f"{singular}s")
        return f"{count} {label}"

    parts = [f"{size} bytes", _n(stats.get("lines", 0), "line")]
    if filename.endswith(".json"):
        parts.extend(
            [
                _n(stats.get("inbounds", 0), "inbound"),
                _n(stats.get("outbounds", 0), "outbound"),
                _n(stats.get("endpoints", 0), "endpoint"),
            ]
        )
    elif filename == "haproxy.cfg":
        parts.extend(
            [
                _n(stats.get("frontends", 0), "frontend"),
                _n(stats.get("backends", 0), "backend"),
            ]
        )
    elif filename.endswith(".toml"):
        parts.append(_n(stats.get("services", 0), "service"))
    return ", ".join(parts)


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
                rendered += "\n"
        dump.written[filename] = len(rendered.encode("utf-8"))
        dump.stats[filename] = summarize_dumped_config(core, rendered)

    return dump


def format_builder_messages(result: ConfigBuilderModel) -> list[dict[str, Any]]:
    return [message.model_dump() for message in result.messages]


CLIENT_CONFIG_FILES: tuple[tuple[str, str], ...] = (
    ("hiddify-core", "hiddify-core.json"),
    ("xray", "xray.json"),
    ("sublink", "sublink.txt"),
    ("clash", "clash.yaml"),
    ("singbox", "singbox.json"),
)

DEFAULT_CLIENT_UA = "HiddifyNext/3.0.0 (android) like ClashMeta v2ray sing-box"


@dataclass
class ClientConfigDumpResult:
    output_dir: Path
    child_id: int
    user_uuid: str | None = None
    user_name: str | None = None
    written: dict[str, int] = field(default_factory=dict)
    stats: dict[str, dict[str, int]] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[dict[str, Any]]:
        return error_messages(self.messages)

    @property
    def ok(self) -> bool:
        return not self.errors and not self.missing


def summarize_client_dumped_config(core: str, filename: str, rendered: str) -> dict[str, int]:
    stats: dict[str, int] = {"lines": _line_count(rendered)}
    text = rendered or ""

    if filename.endswith(".json"):
        try:
            data = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            for key in ("inbounds", "outbounds", "endpoints"):
                value = data.get(key)
                stats[key] = len(value) if isinstance(value, list) else 0
        else:
            stats.update(inbounds=0, outbounds=0, endpoints=0)
    elif core == "clash":
        try:
            import yaml

            data = yaml.safe_load(text) if text.strip() else {}
        except Exception:
            data = {}
        proxies = data.get("proxies") if isinstance(data, dict) else None
        stats["proxies"] = len(proxies) if isinstance(proxies, list) else 0
    elif core == "sublink":
        stats["links"] = len([line for line in text.splitlines() if line.strip() and "://" in line])

    return stats


def format_client_dump_stats(filename: str, size: int, stats: dict[str, int] | None) -> str:
    stats = stats or {}

    def _n(count: int, singular: str, plural: str | None = None) -> str:
        label = singular if count == 1 else (plural or f"{singular}s")
        return f"{count} {label}"

    parts = [f"{size} bytes", _n(stats.get("lines", 0), "line")]
    if filename.endswith(".json"):
        parts.extend(
            [
                _n(stats.get("inbounds", 0), "inbound"),
                _n(stats.get("outbounds", 0), "outbound"),
                _n(stats.get("endpoints", 0), "endpoint"),
            ]
        )
    elif filename.endswith(".yaml"):
        parts.append(_n(stats.get("proxies", 0), "proxy", "proxies"))
    elif filename.endswith(".txt"):
        parts.append(_n(stats.get("links", 0), "link"))
    return ", ".join(parts)


def _resolve_dump_user_obj(*, user_uuid: str | None):
    from hiddifypanel.models.user import User

    if user_uuid:
        user = User.by_uuid(user_uuid, create=False)
        if user is None:
            raise ValueError(f"User not found for uuid={user_uuid}")
        return user

    user = User.query.filter(User.enable.is_(True)).order_by(User.id).first()
    if user is None:
        raise ValueError("No enabled user found")
    return user


def _resolve_sublink_domain(child_id: int = 0) -> str:
    from hiddifypanel.models.domain import Domain

    row = (
        Domain.query.filter(Domain.child_id == child_id, Domain.sub_link_only != True)  # noqa: E712
        .order_by(Domain.id)
        .first()
    )
    if row is None:
        row = Domain.query.filter(Domain.child_id == child_id).order_by(Domain.id).first()
    return row.domain if row else ""


def _append_driver_messages(dump: ClientConfigDumpResult, core: str, messages: list[Any]) -> None:
    for message in messages:
        dump.messages.append(
            {
                "core": core,
                "level": getattr(message, "level", None) or (message.get("level") if isinstance(message, dict) else "info"),
                "message": getattr(message, "message", None) or (message.get("message") if isinstance(message, dict) else ""),
                "data": getattr(message, "data", None) or ((message.get("data") if isinstance(message, dict) else None) or {}),
            }
        )


def _build_merged_json_client_config(child_id: int, contexts: list[Any], *, core: str) -> ConfigBuilderModel:
    """Render each proxy with typed ClientContextVar, then compose one core config."""
    from hiddifypanel.models.custom_proxy import TemplateCore
    from hiddifypanel.models.proxy_base_config import BaseConfigSide
    from hiddifypanel.proxy_v3.config_builder.hiddify_core.client import HiddifyCoreClientDriver

    from hiddifypanel.proxy_v3.config_builder.singbox.client import SingboxClientDriver
    from hiddifypanel.proxy_v3.config_builder.xray.client import XrayClientDriver
    from hiddifypanel.proxy_v3.config_builder.hiddify_core.common import compose_config_from_blocks
    from hiddifypanel.proxy_v3.config_builder.models import MessageModel, ProxyBlock
    from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion

    drivers = {
        "hiddify-core": HiddifyCoreClientDriver(),
        "singbox": SingboxClientDriver(),
        "xray": XrayClientDriver(),
    }
    driver = drivers[core]
    messages: list[MessageModel] = []
    blocks: list[ProxyBlock] = []
    min_version = TemplateVersion("0.0.0")

    for ctx in contexts:
        client_config = driver._select_client_config(ctx)
        if client_config is None:
            continue
        min_version = driver._min_version(ctx)
        try:
            blocks.extend(driver.build_proxy_config(child_id, ctx, messages, client_config=client_config))
        except Exception as exc:
            messages.append(
                MessageModel(
                    level="error",
                    message=f"{ctx.proxy.tag or ctx.proxy.id}: {exc}",
                    data={"stacktrace": traceback.format_exc()},
                )
            )

    if not contexts:
        messages.append(MessageModel(level="error", message=f"No client proxies for {core}"))
        return ConfigBuilderModel(core=TemplateCore(core), side=BaseConfigSide.client, config="", messages=messages)

    # Base shells are versioned independently of the UA; use 0.0.0 like server drivers.
    return compose_config_from_blocks(
        child_id,
        contexts[0],
        blocks,
        core=TemplateCore(core),
        side=BaseConfigSide.client,
        block_names=driver.block_names,
        min_version=TemplateVersion("0.0.0"),
        messages=messages,
    )


def _build_clash_client_config(child_id: int, contexts: list[Any]) -> tuple[str, list[Any]]:
    from hiddifypanel.models.custom_proxy import TemplateCore
    from hiddifypanel.models.proxy_base_config import BaseConfigSide
    from hiddifypanel.proxy_v3.config_builder.base_config import extract_base_config_shell, resolve_base_config_content
    from hiddifypanel.proxy_v3.config_builder.client_selection import select_client_config
    from hiddifypanel.proxy_v3.config_builder.models import MessageModel
    from hiddifypanel.proxy_v3.config_builder.render import render_section
    from hiddifypanel.proxy_v3.context_vars.builder.utils import load_json5, make_jinja_context

    import yaml

    messages: list[MessageModel] = []
    if not contexts:
        return "", messages

    base = resolve_base_config_content(child_id, BaseConfigSide.client, TemplateCore.clash, contexts[0].platform.app_version)
    base = extract_base_config_shell(base) or base
    base_section = render_section(base, child_id, make_jinja_context(contexts[0]), as_json_object=True)
    parsed = base_section.parsed if isinstance(base_section.parsed, dict) else {"proxies": []}
    proxies: list[dict[str, Any]] = list(parsed.get("proxies") or [])

    for ctx in contexts:
        client_config = select_client_config(ctx.proxy.client_configs, TemplateCore.clash, ctx.platform.app_version)
        if client_config is None or not (client_config.content or "").strip():
            continue
        section = render_section(client_config.content, child_id, make_jinja_context(ctx), as_json_object=False, parse_json=False)
        if section.error:
            messages.append(
                MessageModel(
                    level="error",
                    message=f"{ctx.proxy.tag or ctx.proxy.id}: {section.error}",
                    data={"details": section.error_detail.model_dump() if section.error_detail else {}},
                )
            )
            continue
        if section.skipped:
            continue
        raw = (section.rendered or "").strip().rstrip(",")
        if not raw:
            continue
        try:
            items = load_json5(f"[{raw}]")
        except Exception as exc:
            messages.append(MessageModel(level="error", message=f"{ctx.proxy.tag or ctx.proxy.id}: {exc}"))
            continue
        for item in items:
            if isinstance(item, dict):
                if item.get("name") and not item.get("tag"):
                    item["tag"] = item["name"]
                if item.get("tag") and not item.get("name"):
                    item["name"] = item["tag"]
                proxies.append(item)

    parsed["proxies"] = proxies
    return yaml.dump(parsed, sort_keys=False, allow_unicode=True) or "", messages


def _build_sublink_client_config(child_id: int, contexts: list[Any]) -> tuple[str, list[Any]]:
    from hiddifypanel.models.custom_proxy import TemplateCore
    from hiddifypanel.proxy_v3.config_builder.client_selection import select_client_config
    from hiddifypanel.proxy_v3.config_builder.models import MessageModel
    from hiddifypanel.proxy_v3.config_builder.render import render_section
    from hiddifypanel.proxy_v3.context_vars.builder.utils import make_jinja_context

    messages: list[MessageModel] = []
    links: list[str] = []
    for ctx in contexts:
        client_config = select_client_config(ctx.proxy.client_configs, TemplateCore.sublink, ctx.platform.app_version)
        if client_config is None or not (client_config.content or "").strip():
            continue
        section = render_section(client_config.content, child_id, make_jinja_context(ctx), as_json_object=False, parse_json=False)
        if section.error:
            messages.append(
                MessageModel(
                    level="error",
                    message=f"{ctx.proxy.tag or ctx.proxy.id}: {section.error}",
                    data={"details": section.error_detail.model_dump() if section.error_detail else {}},
                )
            )
            continue
        if section.skipped:
            continue
        for line in (section.rendered or "").splitlines():
            text = line.strip().strip('"')
            if text and "://" in text:
                links.append(text)
    return "\n".join(links), messages


def dump_all_client_configs(
    output_dir: str | Path,
    child_id: int = 0,
    *,
    user_uuid: str | None = None,
    pretty: bool = True,
    ip: str | None = None,
    user_agent: str | None = None,
) -> ClientConfigDumpResult:
    """Render client configs for one user via typed ``ClientContextVar`` (one ctx per proxy)."""
    del ip  # reserved; domains are resolved by client_builder

    from hiddifypanel.cache import cache
    from hiddifypanel.proxy_v3.context_vars.builder.client_builder import build_client_template_context

    # Client bases / domains are Redis-cached; always refresh so dumps see latest templates.
    cache.invalidate_all_cached_functions()

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    user = _resolve_dump_user_obj(user_uuid=user_uuid)
    dump = ClientConfigDumpResult(
        output_dir=target,
        child_id=child_id,
        user_uuid=str(user.uuid),
        user_name=getattr(user, "name", None),
    )

    ua = (user_agent or "").strip() or DEFAULT_CLIENT_UA
    sublink_domain = _resolve_sublink_domain(child_id)

    try:
        contexts = build_client_template_context(user, sublink_domain, ua)
    except Exception as exc:
        dump.messages.append(
            {
                "core": "*",
                "level": "error",
                "message": str(exc),
                "data": {"stacktrace": traceback.format_exc()},
            }
        )
        return dump

    if not contexts:
        dump.messages.append(
            {
                "core": "*",
                "level": "error",
                "message": "No client proxies available for this user/domain",
            }
        )
        return dump

    rendered_by_core: dict[str, str] = {}

    for core in ("hiddify-core", "xray", "singbox"):
        try:
            result = _build_merged_json_client_config(child_id, contexts, core=core)
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
        _append_driver_messages(dump, core, result.messages)
        rendered_by_core[core] = _pretty_json_config(result.config or "", pretty=pretty)

    try:
        clash_text, clash_msgs = _build_clash_client_config(child_id, contexts)
        _append_driver_messages(dump, "clash", clash_msgs)
        rendered_by_core["clash"] = clash_text
    except Exception as exc:
        dump.messages.append(
            {
                "core": "clash",
                "level": "error",
                "message": str(exc),
                "data": {"stacktrace": traceback.format_exc()},
            }
        )

    try:
        sublink_text, sublink_msgs = _build_sublink_client_config(child_id, contexts)
        _append_driver_messages(dump, "sublink", sublink_msgs)
        rendered_by_core["sublink"] = sublink_text
    except Exception as exc:
        dump.messages.append(
            {
                "core": "sublink",
                "level": "error",
                "message": str(exc),
                "data": {"stacktrace": traceback.format_exc()},
            }
        )

    for core, filename in CLIENT_CONFIG_FILES:
        text = rendered_by_core.get(core) or ""
        if not text.strip():
            dump.missing.append(filename)
            continue
        out_path = target / filename
        with open(out_path, "w", encoding="utf-8") as fp:
            fp.write(text)
            if text and not text.endswith("\n"):
                fp.write("\n")
                text += "\n"
        dump.written[filename] = len(text.encode("utf-8"))
        dump.stats[filename] = summarize_client_dumped_config(core, filename, text)

    return dump
