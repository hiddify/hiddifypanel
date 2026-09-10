from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from flask import request
from flask.views import MethodView

from hiddifypanel import g, current_app as app, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.models import ConfigEnum, Role, hconfig
from hiddifypanel.panel.user.user import get_common_data
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel


class ConfigSchema(ApiModel):
    name: str = ""
    domain: str = ""
    link: str = ""
    protocol: str = ""
    transport: str = ""
    security: str = ""
    type: str = ""


def _enum_str(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value) or "")


def _security_label(proxy: Any) -> str:
    if getattr(proxy, "is_reality", False):
        return "reality"
    return _enum_str(getattr(proxy, "tls_layer", None)) or "tls"


def _render_sublink_for_context(child_id: int, ctx: Any) -> str | None:
    from hiddifypanel.models.custom_proxy import TemplateCore
    from hiddifypanel.proxy_v3.config_builder.client_selection import select_client_config
    from hiddifypanel.proxy_v3.config_builder.render import render_section
    from hiddifypanel.proxy_v3.context_vars.builder.utils import make_jinja_context

    client_config = select_client_config(ctx.proxy.client_configs, TemplateCore.sublink, ctx.platform.app_version)
    if client_config is None or not (client_config.content or "").strip():
        return None
    section = render_section(
        client_config.content,
        child_id,
        make_jinja_context(ctx),
        as_json_object=False,
        parse_json=False,
    )
    if section.error or section.skipped:
        return None
    for line in (section.rendered or "").splitlines():
        text = line.strip().strip('"')
        if text and "://" in text:
            return text
    return None


def iter_proxy_v3_config_items(user, *, sublink_domain: str, user_agent: str, child_id: int = 0) -> list[dict[str, str]]:
    """Build per-proxy share-link rows from proxy_v3 client contexts."""
    from hiddifypanel.proxy_v3.context_vars.builder.client_builder import build_client_template_context
    from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar

    contexts = build_client_template_context(user, sublink_domain, user_agent)
    items: list[dict[str, str]] = []
    for ctx in contexts:
        if (ctx.proxy.slug or "") == "additional-config":
            continue
        for dctx in ctx.iter_ctx_domains():
            domain = dctx.proxy.domain
            single = ClientContextVar(
                user=ctx.user,
                platform=ctx.platform,
                hconfig=ctx.hconfig,
                proxy=ctx.proxy.model_copy(update={"domains": [domain]}),
                shared_cert=ctx.shared_cert,
            )
            link = _render_sublink_for_context(int(domain.child_id or child_id or 0), single)
            if not link:
                continue
            tag = (dctx.proxy.tag or dctx.proxy.slug or "").replace("_", " ").strip()
            domain_label = (domain.alias or domain.name or "").strip()
            name = f"{tag} {domain_label}".strip() if domain_label and domain_label not in tag else tag
            if domain.is_fake_tls():
                domain_field = "FakeTLS"
            else:
                domain_field = _enum_str(domain.mode)
            items.append(
                {
                    "name": name or tag or "proxy",
                    "domain": domain_field,
                    "type": dctx.proxy.server,
                    "protocol": _enum_str(dctx.proxy.proto),
                    "transport": _enum_str(dctx.proxy.transport),
                    "security": _security_label(dctx.proxy),
                    "link": link,
                }
            )
    return items


class AllConfigsAPI(MethodView):
    decorators = [login_required({Role.user})]

    @app.output(list[ConfigSchema])  # type: ignore
    def get(self):
        def create_item(name, domain, type, protocol, transport, security, link):
            dto = ConfigSchema()
            dto.name = name
            dto.type = type
            dto.domain = domain
            dto.protocol = protocol
            dto.transport = transport
            dto.security = security
            dto.link = link
            return dto

        items = []
        base_url = f"https://{urlparse(request.base_url).hostname}/{g.proxy_path}/{g.account.uuid}/"
        c = get_common_data(g.account.uuid, "new")
        config_name = hutils.encode.url_encode(c["user"].name)
        child_id = int(getattr(c.get("db_domain"), "child_id", 0) or 0)

        # Add Auto
        items.append(
            create_item(
                "Auto",
                "ALL",
                "",
                "",
                "",
                "",
                f"{base_url}auto/?asn={c['asn']}#{config_name}",
            )
        )

        if hconfig(ConfigEnum.sub_full_singbox_enable):
            items.append(
                create_item(
                    "Full Singbox",
                    "ALL",
                    "",
                    "",
                    "",
                    "",
                    f"{base_url}singbox/?asn={c['asn']}#{config_name}",
                )
            )

        if hconfig(ConfigEnum.sub_full_xray_json_enable):
            items.append(
                create_item(
                    "Full Xray",
                    "ALL",
                    "",
                    "",
                    "",
                    "",
                    f"{base_url}xray/#{config_name}",
                )
            )

        if hconfig(ConfigEnum.sub_full_links_enable):
            items.append(
                create_item(
                    "Subscription link",
                    "ALL",
                    "",
                    "",
                    "",
                    "",
                    f"{base_url}sub/?asn={c['asn']}#{config_name}",
                )
            )

        if hconfig(ConfigEnum.sub_full_links_b64_enable):
            items.append(
                create_item(
                    "Subscription link b64",
                    "ALL",
                    "",
                    "",
                    "",
                    "",
                    f"{base_url}sub64/?asn={c['asn']}#{config_name}",
                )
            )
        if hconfig(ConfigEnum.sub_full_clash_meta_enable):
            items.append(
                create_item(
                    "Clash Meta",
                    "ALL",
                    "",
                    "",
                    "",
                    "",
                    f"{base_url}clashmeta/?asn={c['asn']}#{config_name}",
                )
            )

        if hconfig(ConfigEnum.sub_full_clash_enable):
            items.append(
                create_item(
                    "Clash",
                    "ALL",
                    "Except VLess",
                    "",
                    "",
                    "",
                    f"{base_url}clash/?asn={c['asn']}#{config_name}",
                )
            )

        if hconfig(ConfigEnum.wireguard_enable):
            items.append(
                create_item(
                    "Wireguard",
                    "Wireguard",
                    "",
                    "",
                    "",
                    "",
                    f"{base_url}wireguard/#{config_name}",
                )
            )
        if hconfig(ConfigEnum.sub_singbox_ssh_enable) and hconfig(ConfigEnum.ssh_server_enable):
            items.append(
                create_item(
                    "Singbox: SSH",
                    "SSH",
                    "",
                    "",
                    "",
                    "",
                    f"{base_url}singbox-ssh/?asn={c['asn']}#{config_name}",
                )
            )

        for row in iter_proxy_v3_config_items(
            c["user"],
            sublink_domain=request.host,
            user_agent=request.user_agent.string,
            child_id=child_id,
        ):
            items.append(
                create_item(
                    row["name"],
                    row["domain"],
                    row["type"],
                    row["protocol"],
                    row["transport"],
                    row["security"],
                    row["link"],
                )
            )

        return items
