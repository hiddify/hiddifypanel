import secrets
import string

from apiflask import abort
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models.custom_proxy import (
    TEMPLATE_CATEGORIES_ACTIVE,
    ClientCore,
    CustomProxy,
    CustomProxyMode,
    CustomProxyTransport,
    InboundTcpUdp,
    ServerCore,
    TlsLayer,
    normalize_custom_path,
)
from hiddifypanel.models.proxy import ProxyProto
from hiddifypanel.models.role import Role
from hiddifypanel.proxy_v3.custom_proxy_validate import (
    EXAMPLE_USER_AGENTS,
    generate_enabled_proxies_bundle,
    generate_proxy_example,
    preview_proxy_template_fragment,
    validate_proxy_payload,
)
from hiddifypanel.proxy_v3.template_catalog.template_defaults import (
    default_server_inbound_template,
    default_sublink_link_template,
)

from .custom_proxy_schema import (
    CustomProxyEnableSchema,
    CustomProxyExportInputSchema,
    CustomProxyGenerateBundleResultSchema,
    CustomProxyGenerateBundleSchema,
    CustomProxyGenerateExampleByIdInputSchema,
    CustomProxyGenerateExampleWithIdSchema,
    CustomProxyGenerateResultSchema,
    CustomProxyImportResultSchema,
    CustomProxyImportSchema,
    CustomProxyMetaSchema,
    CustomProxyPreviewSchema,
    CustomProxySchema,
    CustomProxyValidateSchema,
    PatchCustomProxySchema,
    TemplatePreviewResultSchema,
    ValidationResultSchema,
)


def _parent_enable_conflict(proxy: CustomProxy) -> dict:
    from flask_babel import gettext as _

    blocked = proxy.blocked_parent_enables()
    names = ", ".join(item.get("label") or item.get("key") or "" for item in blocked)
    return {
        "message": _("You need to enable %(names)s globally to enable this proxy.", names=names),
        "blocked_by": blocked,
        "settings_url": _parent_enable_settings_url(),
    }


def _parent_enable_settings_url() -> str:
    from hiddifypanel.hutils.flask import hurl_for

    return hurl_for("admin.ProxyAdmin:index")


def _child_id() -> int:
    return g.child.id if g.child else 0


def _get_proxy_or_404(proxy_id: int) -> CustomProxy:
    proxy = CustomProxy.query.filter(CustomProxy.id == proxy_id, CustomProxy.child_id == _child_id()).first()
    if not proxy:
        abort(404, "Custom proxy not found")
    return proxy


def _generate_custom_path() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


def _proxy_mode(data: dict) -> str | CustomProxyMode | None:
    return data.get("mode")


def _proxy_mode_value(data: dict) -> str | None:
    mode = _proxy_mode(data)
    if isinstance(mode, CustomProxyMode):
        return mode.value
    return mode


def _prepare_server_config(data: dict) -> dict:
    data = dict(data)
    server_config = dict(data.get("server_config") or {})
    server_config.pop("categories", None)
    data["server_config"] = server_config
    categories = [t.strip() for t in (data.get("categories") or []) if t and str(t).strip()]
    data["categories"] = categories
    return data


def _collect_suggested_categories(child_id: int) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for proxy in CustomProxy.query.filter(CustomProxy.child_id == child_id).all():
        for raw in proxy.categories or []:
            category = (raw or "").strip()
            if category and category not in seen:
                seen.add(category)
                ordered.append(category)
    return ordered


def _default_server_config() -> dict:
    return {
        "core": ServerCore.xray.value,
        "inbound_tcp_ports": [],
        "inbound_udp_ports": [],
        "tcp_udp": "both",
        "tag": "",
        "direct_port_access": False,
        "inbound_template": default_server_inbound_template(),
    }


def _default_client_config() -> dict:
    return {
        "core_configs": [
            {
                "core": ClientCore.sublink.value,
                "version": "",
                "slug": "client-sublink",
                "outbounds_template": default_sublink_link_template(),
            }
        ],
    }


def _prepare_create_data(data: dict) -> dict:
    data = dict(data)
    if not data.get("server_config"):
        data["server_config"] = _default_server_config()
    data = _prepare_server_config(data)
    if not data.get("client_config"):
        data["client_config"] = _default_client_config()
    mode = _proxy_mode_value(data)
    if mode == CustomProxyMode.domains_l7_gateway.value:
        path = (data.get("custom_path") or "").strip()
        if not path or path == "/random_auto":
            data["custom_path"] = _generate_custom_path()
    if mode == CustomProxyMode.domains_sni_gateway.value:
        if not data.get("domain_modes"):
            data["domain_modes"] = ["direct-valid", "relay-valid"]
        data["custom_path"] = ""
    if mode == CustomProxyMode.domains_dns_gateway.value:
        if not data.get("domain_modes"):
            data["domain_modes"] = ["direct-dns"]
        data["custom_path"] = ""
        data["l7_reverse_proto"] = None
        server = dict(data.get("server_config") or {})
        server["inbound_tcp_ports"] = []
        server["inbound_udp_ports"] = []
        data["server_config"] = server
    if mode == CustomProxyMode.domains_auto_public_ports.value:
        data["custom_path"] = ""
        if not data.get("domain_modes"):
            data["domain_modes"] = ["direct-valid", "relay-valid"]
        server = dict(data.get("server_config") or {})
        server["inbound_tcp_ports"] = []
        server["inbound_udp_ports"] = []
        data["server_config"] = server
    if mode == CustomProxyMode.domains_single_public_port.value:
        data["custom_path"] = ""
        if not data.get("domain_modes"):
            data["domain_modes"] = ["direct-valid", "relay-valid"]
    if mode in (
        CustomProxyMode.domains_l7_gateway.value,
        CustomProxyMode.domains_sni_gateway.value,
        CustomProxyMode.domains_dns_gateway.value,
    ):
        server = dict(data.get("server_config") or {})
        server["inbound_tcp_ports"] = []
        server["inbound_udp_ports"] = []
        data["server_config"] = server
    if mode == CustomProxyMode.ip.value:
        from hiddifypanel.proxy_v3.domain_mode_filter import normalize_domain_modes

        data["domain_modes"] = normalize_domain_modes(data.get("domain_modes"), default=("direct-valid", "relay-valid"))
    data["custom_path"] = normalize_custom_path(data.get("custom_path"))
    return data


class CustomProxiesApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(list[CustomProxySchema])
    def get(self):
        proxies = CustomProxy.query.filter(CustomProxy.child_id == _child_id()).order_by(CustomProxy.sort_order, CustomProxy.id).all()
        return [p.to_dict() for p in proxies]

    @app.input(CustomProxySchema, arg_name="data")
    @app.output(CustomProxySchema)
    def post(self, data):
        data = _prepare_create_data(data)
        proxy = CustomProxy.add_or_update(child_id=_child_id(), **data)
        return proxy.to_dict()


class CustomProxyApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(CustomProxySchema)
    def get(self, proxy_id: int):
        return _get_proxy_or_404(proxy_id).to_dict()

    @app.input(PatchCustomProxySchema, arg_name="data")
    @app.output(CustomProxySchema)
    def patch(self, proxy_id: int, data):
        proxy = _get_proxy_or_404(proxy_id)
        merged = proxy.to_dict()
        merged.update(data)
        merged["id"] = proxy_id
        merged = _prepare_create_data(merged)

        proxy = CustomProxy.add_or_update(**merged)
        return proxy.to_dict()

    def delete(self, proxy_id: int):
        proxy = _get_proxy_or_404(proxy_id)
        if proxy.is_builtin:
            abort(400, "Cannot delete built-in custom proxy; duplicate it to customize")
        from hiddifypanel.database import db

        db.session.delete(proxy)
        db.session.commit()
        return "", 204


class CustomProxyEnableApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(CustomProxyEnableSchema, arg_name="data")
    @app.output(CustomProxySchema)
    def patch(self, proxy_id: int, data):
        proxy = _get_proxy_or_404(proxy_id)
        if data["enable"] and proxy.blocked_parent_enables():
            conflict = _parent_enable_conflict(proxy)
            abort(409, conflict["message"], extra_data=conflict)
        proxy.enable = data["enable"]
        from hiddifypanel.database import db

        db.session.commit()
        return proxy.to_dict()


class CustomProxyDuplicateApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(CustomProxySchema)
    def post(self, proxy_id: int):
        proxy = _get_proxy_or_404(proxy_id)
        new_proxy = proxy.duplicate(child_id=_child_id())
        return new_proxy.to_dict()


class CustomProxyValidateApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(CustomProxyValidateSchema, arg_name="data")
    @app.output(ValidationResultSchema)
    def post(self, data):
        try:
            return validate_proxy_payload(data, child_id=_child_id(), proxy_id=data.get("id"))
        except Exception as e:
            return {
                "ok": False,
                "errors": [{"code": "validate_internal", "message": str(e)}],
                "warnings": [],
                "compiled_preview": "",
                "compiled_json": None,
            }


class CustomProxyValidateByIdApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(CustomProxyValidateSchema, arg_name="data")
    @app.output(ValidationResultSchema)
    def post(self, proxy_id: int, data):
        try:
            proxy = _get_proxy_or_404(proxy_id)
            merged = proxy.to_dict()
            merged.update(data or {})
            merged["id"] = proxy_id
            sections = (data or {}).get("sections") or ["general", "server", "client"]
            return validate_proxy_payload(merged, child_id=_child_id(), proxy_id=proxy_id, sections=sections)
        except Exception as e:
            return {
                "ok": False,
                "errors": [{"code": "validate_internal", "message": str(e)}],
                "warnings": [],
                "compiled_preview": "",
                "compiled_json": None,
            }


def _resolve_generate_proxy_id(url_proxy_id: int | None, context: dict | None) -> int:
    ctx = context or {}
    body_id = ctx.get("custom_proxy_id") or ctx.get("id")
    if url_proxy_id is not None:
        if body_id is not None and int(body_id) != url_proxy_id:
            abort(422, "custom_proxy_id does not match URL")
        return url_proxy_id
    if body_id is None:
        abort(422, "custom_proxy_id is required")
    return int(body_id)


def _generate_example_response(proxy_id: int, context: dict | None):
    return generate_proxy_example(
        proxy_id,
        child_id=_child_id(),
        domain=(context or {}).get("domain"),
        domain_id=(context or {}).get("domain_id"),
        user_id=(context or {}).get("user_id"),
        user_uuid=(context or {}).get("user_uuid"),
        ip=(context or {}).get("ip"),
        user_agent=(context or {}).get("user_agent"),
        ignore_skip=bool((context or {}).get("ignore_skip", True)),
    )


class CustomProxyPreviewApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(CustomProxyPreviewSchema, arg_name="data")
    @app.output(TemplatePreviewResultSchema)
    def post(self, data):
        payload = dict(data or {})
        proxy = dict(payload.get("proxy") or {})
        return preview_proxy_template_fragment(
            proxy,
            child_id=_child_id(),
            proxy_id=payload.get("proxy_id"),
            side=payload.get("side") or "client",
            core=payload.get("core") or "",
            template=payload.get("template") or "",
            domain=payload.get("domain"),
            domain_id=payload.get("domain_id"),
            user_id=payload.get("user_id"),
            user_uuid=payload.get("user_uuid"),
            ip=payload.get("ip"),
            user_agent=payload.get("user_agent"),
            ignore_skip=bool(payload.get("ignore_skip", True)),
            require_user=bool(payload.get("require_user", False)),
        )


class CustomProxyGenerateExampleApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(CustomProxyGenerateExampleWithIdSchema, arg_name="data")
    @app.output(CustomProxyGenerateResultSchema)
    def post(self, data):
        proxy_id = _resolve_generate_proxy_id(None, data)
        _get_proxy_or_404(proxy_id)
        return _generate_example_response(proxy_id, data)


class CustomProxyGenerateExampleByIdApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(CustomProxyGenerateExampleByIdInputSchema, arg_name="data")
    @app.output(CustomProxyGenerateResultSchema)
    def post(self, proxy_id: int, data):
        resolved_id = _resolve_generate_proxy_id(proxy_id, data)
        _get_proxy_or_404(resolved_id)
        return _generate_example_response(resolved_id, data)


class CustomProxyGenerateBundleApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(CustomProxyGenerateBundleSchema, arg_name="data")
    @app.output(CustomProxyGenerateBundleResultSchema)
    def post(self, data):
        return generate_enabled_proxies_bundle(
            child_id=_child_id(),
            domain=(data or {}).get("domain"),
            domain_id=(data or {}).get("domain_id"),
            domains=(data or {}).get("domains"),
            domain_ids=(data or {}).get("domain_ids"),
            user_id=(data or {}).get("user_id"),
            user_uuid=(data or {}).get("user_uuid"),
            ip=(data or {}).get("ip"),
            user_agent=(data or {}).get("user_agent"),
        )


class CustomProxyMetaApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(CustomProxyMetaSchema)
    def get(self):
        from hiddifypanel.proxy_v3.template_catalog.template_defaults import default_sublink_link_template

        return {
            "modes": [p.value for p in CustomProxyMode],
            "protos": [p.value for p in ProxyProto],
            "transports": [t.value for t in CustomProxyTransport],
            "tls_layers": [layer.value for layer in TlsLayer],
            "l7_reverse_protos": ["h1", "h2", "h3"],
            "domain_modes": [
                "direct-valid",
                "direct-fake",
                "direct-reality",
                "direct-dns",
                "relay-valid",
                "relay-fake",
                "relay-reality",
                "cdn",
            ],
            "server_cores": ["hiddify-core", "xray", "haproxy", "nginx", "rust-rpxy-l4"],
            "client_cores": ["sublink", "xray", "singbox", "hiddify-core", "clash"],
            "template_categories": [c.value for c in TEMPLATE_CATEGORIES_ACTIVE],
            "suggested_categories": _collect_suggested_categories(_child_id()),
            "default_sublink_link": default_sublink_link_template(),
            "example_user_agents": EXAMPLE_USER_AGENTS,
            "tcp_udp_options": [p.value for p in InboundTcpUdp],
            "parent_enable_settings_url": _parent_enable_settings_url(),
        }


class CustomProxyExportApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(CustomProxyExportInputSchema, arg_name="data")
    def post(self, data):
        from hiddifypanel.proxy_v3.custom_proxy_bundle import build_export_bundle

        exclude_builtin = bool(data.pop("exclude_builtin_templates", False))
        return build_export_bundle(data, _child_id(), exclude_builtin=exclude_builtin)


class CustomProxyImportApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(CustomProxyImportSchema, arg_name="data")
    @app.output(CustomProxyImportResultSchema)
    def post(self, data):
        from hiddifypanel.proxy_v3.custom_proxy_bundle import import_bundle

        return import_bundle(data, _child_id())
