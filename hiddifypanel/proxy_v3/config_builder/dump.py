from __future__ import annotations

import json
import re
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hiddifypanel.proxy_v3.config_builder.haproxy.server import HaproxyServerDriver
from hiddifypanel.proxy_v3.config_builder.rust_rpxy_l4.server import RustRpxyL4ServerDriver
from hiddifypanel.proxy_v3.config_builder.dns_proxy.server import DnsProxyServerDriver
from hiddifypanel.proxy_v3.config_builder.hiddify_core.server import HiddifyCoreServerDriver
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel
from hiddifypanel.proxy_v3.config_builder.nginx.server import NginxServerDriver
from hiddifypanel.proxy_v3.config_builder.xray.server import XrayServerDriver
from hiddifypanel.proxy_v3.context_vars.builder.server_builder import build_server_template_context
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar
from hiddifypanel.proxy_v3.jinja_context import HIDDIFY_MANAGER_ROOT

if TYPE_CHECKING:
    from hiddifypanel.models.user import User


SERVER_CONFIG_DRIVERS: dict[str, type] = {
    "hiddify-core": HiddifyCoreServerDriver,
    "xray": XrayServerDriver,
    "haproxy": HaproxyServerDriver,
    "nginx": NginxServerDriver,
    "rust-rpxy-l4": RustRpxyL4ServerDriver,
    "dns_proxy": DnsProxyServerDriver,
}

SERVER_CONFIG_FILES: tuple[tuple[str, str], ...] = (
    ("xray", "xray.json"),
    ("hiddify-core", "hiddify-core.json"),
    ("haproxy", "haproxy.cfg"),
    ("nginx", "nginx.cfg"),
    ("rust-rpxy-l4", "rust-rpxy-l4.toml"),
    ("dns_proxy", "dnstm.json"),
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

    if core in ("xray", "hiddify-core", "dns_proxy"):
        try:
            data = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            if core == "dns_proxy":
                tunnels = data.get("tunnels")
                stats["tunnels"] = len(tunnels) if isinstance(tunnels, list) else 0
            else:
                for key in ("inbounds", "outbounds", "endpoints"):
                    value = data.get(key)
                    stats[key] = len(value) if isinstance(value, list) else 0
        else:
            if core == "dns_proxy":
                stats["tunnels"] = 0
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
        if filename == "dnstm.json":
            parts.append(_n(stats.get("tunnels", 0), "tunnel"))
        else:
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


def _is_empty_dump_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _omit_empty_values(value: Any) -> Any:
    """Drop null/empty-string/empty-container leaves from dumped JSON/YAML trees."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            pruned = _omit_empty_values(item)
            if _is_empty_dump_value(pruned):
                continue
            out[key] = pruned
        return out
    if isinstance(value, list):
        out_list: list[Any] = []
        for item in value:
            pruned = _omit_empty_values(item)
            if _is_empty_dump_value(pruned):
                continue
            out_list.append(pruned)
        return out_list
    return value


def _pretty_json_config(rendered: str, *, pretty: bool) -> str:
    if not rendered.strip():
        return rendered
    try:
        parsed = _omit_empty_values(json.loads(rendered))
        if pretty:
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
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
    _clear_dns_proxy_generated(target)

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
        if core in ("xray", "hiddify-core", "dns_proxy"):
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

        if core == "dns_proxy":
            _collect_dns_proxy_sidecars(dump, target)

    return dump


def _clear_dns_proxy_generated(target: Path) -> None:
    import shutil

    manager_gen = Path(HIDDIFY_MANAGER_ROOT) / "generated" / "dns_proxy"
    dump_gen = target / "dns_proxy"
    for path in {manager_gen, dump_gen}:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


def _collect_dns_proxy_sidecars(dump: ServerConfigDumpResult, target: Path) -> None:
    """Record sizes of include_path sidecars under generated/dns_proxy/."""
    manager_gen = Path(HIDDIFY_MANAGER_ROOT) / "generated" / "dns_proxy"
    dump_gen = target / "dns_proxy"
    for gen_root in (manager_gen, dump_gen):
        if not gen_root.is_dir():
            continue
        for path in gen_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = str(path.relative_to(target))
            except ValueError:
                rel = str(path.relative_to(gen_root.parent))
            dump.written[rel] = path.stat().st_size


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


def _resolve_dump_user_obj(*, user_uuid: str | None) -> User:
    from hiddifypanel.models.user import User

    if user_uuid:
        user = User.by_uuid(user_uuid, create=False)
        if not isinstance(user, User):
            raise ValueError(f"User not found for uuid={user_uuid}")
        return user

    user = User.query.filter(User.enable.is_(True)).order_by(User.id).first()
    if not isinstance(user, User):
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


@dataclass
class ClientConfigRenderResult:
    configs: dict[str, str] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)
    user_uuid: str | None = None
    user_name: str | None = None

    @property
    def errors(self) -> list[dict[str, Any]]:
        return error_messages(self.messages)

    @property
    def ok(self) -> bool:
        return not self.errors


def _append_render_messages(result: ClientConfigRenderResult, core: str, messages: list[MessageModel]) -> None:
    for message in messages:
        result.messages.append(
            {
                "core": core,
                "level": message.level,
                "message": message.message,
                "data": message.data,
            }
        )


def render_client_configs(
    *,
    user: Any | None = None,
    user_uuid: str | None = None,
    child_id: int = 0,
    sublink_domain: str | None = None,
    domains: list[str] | None = None,
    user_agent: str | None = None,
    pretty: bool = True,
    cores: tuple[str, ...] | None = None,
    invalidate_cache: bool = False,
) -> ClientConfigRenderResult:
    """Render client configs for one user via typed ``ClientContextVar`` (one ctx per proxy).

    ``domains`` renders an explicit list of domain names instead of the ones
    ``sublink_domain`` exposes; names with no matching domain are ignored.
    """
    from hiddifypanel.cache import cache
    from hiddifypanel.models.user import User
    from hiddifypanel.proxy_v3.context_vars.builder.client_builder import build_client_template_context

    if invalidate_cache:
        cache.invalidate_all_cached_functions()

    user_obj = user if isinstance(user, User) else _resolve_dump_user_obj(user_uuid=user_uuid)
    result = ClientConfigRenderResult(
        user_uuid=str(user_obj.uuid or ""),
        user_name=user_obj.name,
    )

    ua = (user_agent or "").strip() or DEFAULT_CLIENT_UA
    domain = (sublink_domain or "").strip()
    if not domain and not domains:
        domain = _resolve_sublink_domain(child_id)
    wanted = cores or tuple(core for core, _filename in CLIENT_CONFIG_FILES)

    try:
        contexts = build_client_template_context(user_obj, domain, ua, domains)
    except Exception as exc:
        result.messages.append(
            {
                "core": "*",
                "level": "error",
                "message": str(exc),
                "data": {"stacktrace": traceback.format_exc()},
            }
        )
        return result

    if not contexts:
        result.messages.append(
            {
                "core": "*",
                "level": "error",
                "message": "No client proxies available for this user/domain",
            }
        )
        return result

    for core in ("hiddify-core", "xray", "singbox"):
        if core not in wanted:
            continue
        try:
            built = _build_merged_json_client_config(child_id, contexts, core=core)
        except Exception as exc:
            result.messages.append(
                {
                    "core": core,
                    "level": "error",
                    "message": str(exc),
                    "data": {"stacktrace": traceback.format_exc()},
                }
            )
            continue
        _append_render_messages(result, core, built.messages)
        result.configs[core] = _pretty_json_config(built.config or "", pretty=pretty)

    if "clash" in wanted:
        try:
            clash_text, clash_msgs = _build_clash_client_config(child_id, contexts)
            _append_render_messages(result, "clash", clash_msgs)
            result.configs["clash"] = clash_text
        except Exception as exc:
            result.messages.append(
                {
                    "core": "clash",
                    "level": "error",
                    "message": str(exc),
                    "data": {"stacktrace": traceback.format_exc()},
                }
            )

    if "sublink" in wanted:
        try:
            sublink_text, sublink_msgs = _build_sublink_client_config(child_id, contexts)
            _append_render_messages(result, "sublink", sublink_msgs)
            result.configs["sublink"] = sublink_text
        except Exception as exc:
            result.messages.append(
                {
                    "core": "sublink",
                    "level": "error",
                    "message": str(exc),
                    "data": {"stacktrace": traceback.format_exc()},
                }
            )

    return result


def dump_all_client_configs(
    output_dir: str | Path,
    child_id: int = 0,
    *,
    user_uuid: str | None = None,
    pretty: bool = True,
    ip: str | None = None,
    user_agent: str | None = None,
) -> ClientConfigDumpResult:
    """Render client configs for one user and write them under ``output_dir``."""
    del ip  # reserved; domains are resolved by client_builder

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    rendered = render_client_configs(
        user_uuid=user_uuid,
        child_id=child_id,
        user_agent=user_agent,
        pretty=pretty,
        invalidate_cache=True,
    )
    dump = ClientConfigDumpResult(
        output_dir=target,
        child_id=child_id,
        user_uuid=rendered.user_uuid,
        user_name=rendered.user_name,
        messages=list(rendered.messages),
    )

    for core, filename in CLIENT_CONFIG_FILES:
        text = rendered.configs.get(core) or ""
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


def _build_merged_json_client_config(child_id: int, contexts: list[ClientContextVar], *, core: str) -> ConfigBuilderModel:
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


def _build_clash_client_config(child_id: int, contexts: list[ClientContextVar]) -> tuple[str, list[MessageModel]]:
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
    parsed = _omit_empty_values(parsed)
    return yaml.dump(parsed, sort_keys=False, allow_unicode=True) or "", messages


def _build_sublink_client_config(child_id: int, contexts: list[ClientContextVar]) -> tuple[str, list[MessageModel]]:
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
    links_text = "\n".join(links)
    if not contexts:
        return links_text, messages
    try:
        from hiddifypanel.models.custom_proxy import TemplateCore
        from hiddifypanel.models.proxy_base_config import BaseConfigSide
        from hiddifypanel.proxy_v3.config_builder.base_config import extract_base_config_shell, resolve_base_config_content
        from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion

        base = resolve_base_config_content(
            child_id,
            BaseConfigSide.client,
            TemplateCore.sublink,
            TemplateVersion("0.0.0"),
        )
        base = extract_base_config_shell(base) or base
        base = re.sub(
            r"\{%\s*block\s+links\s*%\}.*?\{%\s*endblock\s*%\}",
            "{{ links }}",
            base or "",
            flags=re.DOTALL,
        )
        if "{{ links }}" in (base or "") or "{{links}}" in (base or ""):
            compose_ctx = make_jinja_context(contexts[0])
            compose_ctx["links"] = links_text
            wrapped = render_section(base, child_id, compose_ctx, as_json_object=False, parse_json=False)
            if wrapped.error:
                messages.append(
                    MessageModel(
                        level="error",
                        message=f"sublink base: {wrapped.error}",
                        data={"details": wrapped.error_detail.model_dump() if wrapped.error_detail else {}},
                    )
                )
            elif wrapped.rendered and not wrapped.skipped:
                return wrapped.rendered.strip(), messages
    except Exception as exc:
        messages.append(MessageModel(level="error", message=f"sublink base: {exc}", data={}))
    return links_text, messages
