from __future__ import annotations

import copy
import json
import re
from typing import Any

from flask import has_app_context

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.base_config import resolve_base_config_content
from hiddifypanel.proxy_v3.config_builder.base_json_client_drivers import JsonClientOutboundDriver
from hiddifypanel.proxy_v3.config_builder.hiddify_core.common import client_selector_tags, merge_fragment
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel, ProxyBlock, RenderErrorDetail
from hiddifypanel.proxy_v3.config_builder.render import render_section
from hiddifypanel.proxy_v3.config_builder.template_blocks import extract_block_body, inject_named_fragment_blocks
from hiddifypanel.proxy_v3.context_vars.builder.utils import load_json5, make_jinja_context
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar
from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion
from hiddifypanel.proxy_v3.template_catalog.fragment_loader import load_template_slug

_STATUS_WRAPPER = "[{% include 'xray/client/subscription_status' %}]"
_INCLUDE_RE = re.compile(r"^\{%-?\s*include\s+['\"]([^'\"]+)['\"]\s*-?%\}$")
_XRAY_SHELL_OUTBOUND_TAGS = frozenset({"direct", "block", "fragment", "proxy", "freedom", "blackhole"})


def outbound_dicts_from_blocks(blocks: list[ProxyBlock]) -> list[dict[str, Any]]:
    """Parse rendered outbound fragments into independent outbound objects."""
    outbounds: list[dict[str, Any]] = []
    for block in blocks:
        if block.block_name != "outbounds" or not block.content.strip():
            continue
        try:
            items = load_json5(f"[{block.content}]")
        except Exception:
            continue
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                outbounds.append(item)
    return outbounds


def xray_balancer_tags(outbounds: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for outbound in outbounds:
        tag = outbound.get("tag")
        if not isinstance(tag, str) or not tag or tag in _XRAY_SHELL_OUTBOUND_TAGS or "§hide§" in tag:
            continue
        if tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return tags


def wrap_xray_outbounds_as_client_configs(shell: dict[str, Any], outbounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One full xray client config per proxy outbound, cloned from ``base_config``."""
    shell_outbounds = [item for item in shell.get("outbounds", []) if isinstance(item, dict)]
    configs: list[dict[str, Any]] = []
    for outbound in outbounds:
        tag = outbound.get("tag")
        cfg = copy.deepcopy(shell)
        cfg["remarks"] = tag if isinstance(tag, str) else ""
        cfg["outbounds"] = [copy.deepcopy(outbound), *copy.deepcopy(shell_outbounds)]
        configs.append(cfg)
    return configs


def apply_status_remarks(config: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    remarks = status.get("remarks")
    if isinstance(remarks, str) and remarks:
        config["remarks"] = remarks
    return config


def parsed_json_objects(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def expand_include_block(body: str, templates: dict[str, str]) -> str:
    """Replace a lone ``{% include 'slug' %}`` with that template's source."""
    match = _INCLUDE_RE.fullmatch(body.strip())
    if match is None:
        return body
    slug = match.group(1)
    included = templates.get(slug)
    return included if included is not None else body


def build_xray_subscription_array(
    proxy_group: dict[str, Any],
    base_config: dict[str, Any],
    proxy_outbounds: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """``[proxy_group, ...one base_config per outbound]``."""
    auto = copy.deepcopy(proxy_group)
    if not isinstance(auto.get("remarks"), str) or not auto["remarks"]:
        auto["remarks"] = "Auto"
    return [auto, *wrap_xray_outbounds_as_client_configs(base_config, proxy_outbounds)]


def load_client_template_source(child_id: int, slug: str) -> str:
    if has_app_context():
        from hiddifypanel.proxy_v3.config_builder.jinja_render import _cached_template_map

        mapped = _cached_template_map(child_id).get(slug)
        if mapped:
            return mapped
    return load_template_slug(slug, normalize=False)


class XrayClientDriver(JsonClientOutboundDriver):
    """v2rayNG / Streisand expect an array of complete configs, not one merged shell."""

    core = TemplateCore.xray
    block_names = ("outbounds",)

    def _assign_generated_proxy_tags(self, ctx: ClientContextVar, blocks: list[ProxyBlock]) -> None:
        ctx.client_proxy_tags = client_selector_tags(blocks)

    def build_all(self, child_id: int, contexts: list[ClientContextVar]) -> ConfigBuilderModel:
        messages: list[MessageModel] = []
        if not contexts:
            messages.append(MessageModel(level="error", message=f"No client proxies for {self.core.value}"))
            return ConfigBuilderModel(core=self.core, side=self.side, config="", messages=messages)

        proxy_blocks = self.collect_proxy_blocks(child_id, contexts, messages)
        compose_ctx = contexts[0]
        proxy_outbounds = outbound_dicts_from_blocks(proxy_blocks)
        compose_ctx.client_proxy_tags = client_selector_tags(proxy_blocks) or xray_balancer_tags(proxy_outbounds)

        if not compose_ctx.user.is_active:
            status_configs = self._render_status_configs(child_id, compose_ctx, messages)
            return ConfigBuilderModel(
                core=self.core,
                side=self.side,
                config=json.dumps(status_configs, ensure_ascii=False) if status_configs else "[]",
                messages=messages,
            )

        proxy_group, base_config = self._render_proxy_group_and_base_config(child_id, compose_ctx, proxy_blocks, messages)
        configs = build_xray_subscription_array(proxy_group, base_config, proxy_outbounds)
        return ConfigBuilderModel(
            core=self.core,
            side=BaseConfigSide.client,
            config=json.dumps(configs, ensure_ascii=False),
            messages=messages,
        )

    def _render_proxy_group_and_base_config(
        self,
        child_id: int,
        ctx: ClientContextVar,
        proxy_blocks: list[ProxyBlock],
        messages: list[MessageModel],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        source = resolve_base_config_content(child_id, self.side, self.core, TemplateVersion("0.0.0"))
        group_tpl = expand_include_block(
            extract_block_body(source, "proxy_group") or "",
            {"xray/client/proxies_group": load_client_template_source(child_id, "xray/client/proxies_group")},
        )
        if not group_tpl.strip() or _INCLUDE_RE.fullmatch(group_tpl.strip()):
            group_tpl = load_client_template_source(child_id, "xray/client/proxies_group")
        fragment = merge_fragment(proxy_blocks, self.block_names)
        injected, _ok = inject_named_fragment_blocks(group_tpl, fragment, self.block_names)
        jinja_ctx = make_jinja_context(ctx)
        group_section = render_section(injected, child_id, jinja_ctx, as_json_object=True)
        self._append_section_error(messages, "xray proxy_group", group_section.error, group_section.error_detail)

        item_tpl = extract_block_body(source, "base_config") or ""
        item_section = render_section(item_tpl, child_id, jinja_ctx, as_json_object=True)
        self._append_section_error(messages, "xray base_config", item_section.error, item_section.error_detail)

        group = group_section.parsed if isinstance(group_section.parsed, dict) else {}
        item = item_section.parsed if isinstance(item_section.parsed, dict) else {}
        return group, item

    def _append_section_error(
        self,
        messages: list[MessageModel],
        label: str,
        error: str | None,
        error_detail: RenderErrorDetail | None,
    ) -> None:
        if not error:
            return
        data: dict[str, Any] = {}
        if error_detail is not None:
            data["details"] = error_detail
        messages.append(MessageModel(level="error", message=f"{label}: {error}", data=data))

    def _render_status_configs(
        self,
        child_id: int,
        ctx: ClientContextVar,
        messages: list[MessageModel],
    ) -> list[dict[str, Any]]:
        section = render_section(
            _STATUS_WRAPPER,
            child_id,
            make_jinja_context(ctx),
            as_json_object=False,
        )
        if section.error:
            self._append_section_error(messages, "xray subscription status", section.error, section.error_detail)
            return []
        return parsed_json_objects(section.parsed)
