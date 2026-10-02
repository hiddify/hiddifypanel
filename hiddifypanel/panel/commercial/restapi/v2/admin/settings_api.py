"""Panel settings for Admin V2, described from (and saved through) the classic settings form.

The WTForms form in ``panel/admin/SettingAdmin.py`` stays the single source of
truth for which settings exist, their widgets, choices and validators; this API
only translates it to JSON and back.
"""

from __future__ import annotations

from typing import Any

import wtforms as wtf
from bleach import clean as bleach_clean
from flask import request
from flask.views import MethodView
from flask_babel import gettext as _
from werkzeug.datastructures import MultiDict

from hiddifypanel.auth import login_required
from hiddifypanel.models import ConfigEnum, Role, hconfig, set_hconfig
from hiddifypanel.models.config_enum import ApplyMode, is_protocol_switch

# Shown by default; everything else is "advanced" and only shown on request (search always finds it).
ESSENTIAL_KEYS = frozenset(
    {
        ConfigEnum.admin_lang,
        ConfigEnum.lang,
        ConfigEnum.node_name,
        ConfigEnum.parent_panel,
        ConfigEnum.branding_title,
        ConfigEnum.branding_site,
        ConfigEnum.country,
        ConfigEnum.auto_update,
        ConfigEnum.firewall,
        ConfigEnum.torrent_block,
        ConfigEnum.block_iran_sites,
        ConfigEnum.decoy_domain,
        ConfigEnum.telegram_bot_token,
        ConfigEnum.tls_ports,
        ConfigEnum.http_ports,
        ConfigEnum.warp_mode,
        ConfigEnum.package_mode,
    }
)

_HTML_TAGS = frozenset({"a", "br", "strong", "b", "em", "i", "code", "p", "ul", "ol", "li", "span"})
_HTML_ATTRS = {"a": ["href", "target", "rel"]}
_APPLY_RANK = {ApplyMode.nothing: 0, ApplyMode.apply_config: 1, ApplyMode.reinstall: 2}
_SKIP_FIELDS = frozenset({"description_for_fieldset", "csrf_token", "submit"})


def _html(text: Any) -> str:
    return bleach_clean(str(text or ""), tags=_HTML_TAGS, attributes=_HTML_ATTRS, strip=True)


def _apply_mode(key: ConfigEnum) -> ApplyMode:
    mode = key.apply_mode
    return mode if isinstance(mode, ApplyMode) else ApplyMode(mode)


def _field_type(field: wtf.Field) -> str:
    from hiddifypanel.panel.custom_widgets import CKTextAreaField

    if isinstance(field, wtf.BooleanField):
        return "bool"
    if isinstance(field, wtf.SelectField):
        return "select"
    if isinstance(field, CKTextAreaField):
        return "html"
    if isinstance(field, wtf.TextAreaField):
        return "textarea"
    return "text"


def _describe_field(field: wtf.Field) -> dict[str, Any]:
    key = ConfigEnum[field.short_name]
    kind = _field_type(field)
    render_kw = field.render_kw or {}
    row: dict[str, Any] = {
        "key": field.short_name,
        "label": str(field.label.text),
        "description": _html(field.description),
        "type": kind,
        "value": bool(field.data) if kind == "bool" else ("" if field.data is None else str(field.data)),
        "apply_mode": _apply_mode(key).value,
        "essential": key in ESSENTIAL_KEYS,
        "protocol_switch": kind == "bool" and is_protocol_switch(key),
        "required": "required" in render_kw,
    }
    if kind == "select":
        row["choices"] = [{"value": str(value), "label": str(label)} for value, label in field.choices]
    if pattern := render_kw.get("pattern"):
        row["pattern"] = pattern
        row["pattern_message"] = str(render_kw.get("title") or "")
    if maxlength := render_kw.get("maxlength"):
        row["maxlength"] = int(maxlength)
    return row


def describe_settings(form) -> list[dict[str, Any]]:
    categories = []
    for cat_field in form:
        if not isinstance(cat_field, wtf.FormField):
            continue
        cat = cat_field.short_name
        fields = [_describe_field(f) for f in cat_field.form if f.short_name not in _SKIP_FIELDS]
        if not fields:
            continue
        categories.append(
            {
                "id": cat,
                "label": _(f"config.{cat}.label"),
                "description": _html(_(f"config.{cat}.description")),
                "fields": fields,
            }
        )
    return categories


def _formdata(current_form, values: dict[str, Any]) -> MultiDict:
    """Every field (current value unless overridden), named like the HTML form posts them."""
    data = MultiDict()
    for cat_field in current_form:
        if not isinstance(cat_field, wtf.FormField):
            continue
        for field in cat_field.form:
            if field.short_name in _SKIP_FIELDS:
                continue
            value = values[field.short_name] if field.short_name in values else field.data
            name = f"{cat_field.short_name}-{field.short_name}"
            if isinstance(field, wtf.BooleanField):
                if value:
                    data.add(name, "y")
            else:
                data.add(name, "" if value is None else str(value))
    return data


def _restart_mode(old_configs: dict) -> str:
    """Same decision as ``hiddify.check_need_reset``, without flashing or running anything."""
    if old_configs.get(ConfigEnum.package_mode) != hconfig(ConfigEnum.package_mode):
        return "update"
    mode = ApplyMode.nothing
    for key, old in old_configs.items():
        key_mode = _apply_mode(key)
        if key_mode == ApplyMode.nothing or old == hconfig(key):
            continue
        if _APPLY_RANK[key_mode] > _APPLY_RANK[mode]:
            mode = key_mode
    return mode.value


def _field_errors(form) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    for name, value in form.errors.items():
        if isinstance(value, dict):  # FormField: {field: [msgs]}
            for key, messages in value.items():
                errors.setdefault(key, []).extend(str(m) for m in messages)
        else:
            errors.setdefault(name, []).extend(str(m) for m in value)
    return errors


class SettingsApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """Settings: All panel settings grouped by category"""
        from hiddifypanel.panel.admin.SettingAdmin import get_config_form

        return {"categories": describe_settings(get_config_form(formdata=None, meta={"csrf": False}))}

    def put(self):
        """Settings: Save changed settings (`{"values": {key: value}}`)"""
        from hiddifypanel.panel.admin.SettingAdmin import get_config_form, save_config_form

        body = request.get_json(silent=True) or {}
        values = body.get("values")
        if not isinstance(values, dict) or not values:
            return {"errors": ["values is required"], "field_errors": {}}, 400

        current = get_config_form(formdata=None, meta={"csrf": False})
        known = {f.short_name for c in current if isinstance(c, wtf.FormField) for f in c.form}
        unknown = sorted(set(values) - known)
        if unknown:
            return {"errors": [f"Unknown settings: {', '.join(unknown)}"], "field_errors": {}}, 400

        form = get_config_form(formdata=_formdata(current, values), meta={"csrf": False})
        if not form.validate():
            return {"errors": [_("config.validation-error")], "field_errors": _field_errors(form)}, 422

        set_hconfig(ConfigEnum.first_setup, False)
        admin_lang = hconfig(ConfigEnum.admin_lang)
        admin_path = hconfig(ConfigEnum.proxy_path_admin)
        result = save_config_form(form)
        if result.errors:
            return {"errors": result.errors, "field_errors": {}}, 422

        new_admin_path = hconfig(ConfigEnum.proxy_path_admin)
        return {
            "categories": describe_settings(get_config_form(formdata=None, meta={"csrf": False})),
            "restart_mode": _restart_mode(result.old_configs),
            "warnings": result.warnings,
            "changed": sorted(str(k) for k in result.changed_configs),
            # The UI language changed: the page must reload to pick it up.
            "reload": hconfig(ConfigEnum.admin_lang) != admin_lang,
            # Takes effect after applying configs; the admin UI then lives here.
            "new_admin_path": f"/{new_admin_path}/admin/v2/" if new_admin_path != admin_path else None,
        }
