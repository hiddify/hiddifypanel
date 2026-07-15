from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.base_config import extract_base_config_shell, resolve_base_config_content
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel, ProxyBlock
from hiddifypanel.proxy_v3.config_builder.render import render_fragment_section, render_section
from hiddifypanel.proxy_v3.config_builder.template_blocks import inject_named_fragment_blocks
from hiddifypanel.proxy_v3.context_vars.builder.utils import load_json5, make_jinja_context
from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion


def merge_fragment(blocks: list[ProxyBlock], block_names: tuple[str, ...]) -> str:
    parts: list[str] = []
    for block_name in block_names:
        bodies = [block.content.strip().rstrip(",") for block in blocks if block.block_name == block_name and block.content.strip()]
        if not bodies:
            continue
        body = ",\n".join(bodies)
        parts.append(f"{{% block {block_name} %}}\n{body}\n{{% endblock %}}")
    return "\n".join(parts)


def render_template_blocks(child_id: int, jinja_ctx: dict[str, Any], template: str, block_names: tuple[str, ...], proxy_label: str, messages: list[MessageModel]) -> list[ProxyBlock]:
    outbound_tpl = (template or "").strip()
    if not outbound_tpl:
        return []

    blocks: list[ProxyBlock] = []
    for block_name in block_names:
        frag = render_fragment_section(child_id, jinja_ctx, outbound_tpl, block_name, parse_json=False)
        if frag.skipped:
            # messages.append(
            #     MessageModel(
            #         level="warning",
            #         message=f"{proxy_label}/{block_name}: {frag.skipped}",
            #         data={"block": block_name, "content": outbound_tpl, "details": frag.skipped},
            #     )
            # )
            continue
        if frag.error:
            messages.append(
                MessageModel(
                    level="error",
                    message=f"{proxy_label}/{block_name}: {frag.error}",
                    data={"block": block_name, "content": outbound_tpl, "details": frag.error_detail},
                )
            )
            continue
        content = (frag.rendered or "").strip()
        if content:
            blocks.append(ProxyBlock(block_name=block_name, content=content))

    return extract_tags_convert_unique_ids(blocks)


def compose_config_from_blocks(
    child_id: int,
    ctx: BaseModel,
    proxy_blocks: list[ProxyBlock],
    *,
    core: TemplateCore,
    side: BaseConfigSide,
    block_names: tuple[str, ...],
    min_version: TemplateVersion,
    messages: list[MessageModel],
) -> ConfigBuilderModel:
    fragment = merge_fragment(proxy_blocks, block_names)
    base = resolve_base_config_content(
        child_id,
        side,
        core,
        min_version,
    )
    base = extract_base_config_shell(base)

    injected, ok = inject_named_fragment_blocks(base, fragment, block_names)
    if not ok and fragment.strip():
        injected = base

    section = render_section(injected, child_id, make_jinja_context(ctx), as_json_object=True)
    if section.error:
        data: dict[str, Any] = {}
        if section.error_detail is not None:
            data["details"] = section.error_detail
        messages.append(MessageModel(level="error", message=str(section.error), data=data))

    return ConfigBuilderModel(core=core, side=side, config=section.rendered or "", messages=messages)


def extract_tags_convert_unique_ids(blocks: list[ProxyBlock]) -> list[ProxyBlock]:
    names: set[str] = set()
    for block in blocks:
        data = load_json5(f"[{block.content}]")
        block_names: dict[str, str] = {}
        for item in data:
            if tag := item.get("tag"):
                newtag = tag
                if tag in names:
                    for i in range(1, 100):
                        if f"{tag}-{i}" not in names:
                            newtag = f"{tag}§{i}"
                            break
                    block_names[tag] = newtag
                block.extracted_tags.append(newtag)
                names.add(newtag)
                item["tag"] = newtag
        for item in data:
            if "detour" in item and (new_detour := block_names.get(item["detour"])):
                item["detour"] = new_detour
        if block_names:
            block.content = f"[{json.dumps(data, ensure_ascii=False).strip('[]')}]"
    return blocks
