"""Global protocol/transport switches (the ``*_enable`` settings of the classic Proxy admin page)."""

from __future__ import annotations

from apiflask import abort
from bleach import clean as bleach_clean
from flask.views import MethodView
from flask_babel import gettext as _
from pydantic import Field

from hiddifypanel import current_app as app
from hiddifypanel import hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import BoolConfig, Child, ConfigEnum, Role, hconfig, set_hconfig
from hiddifypanel.models.config_enum import ApplyMode, is_protocol_switch
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel

# Descriptions are translations with a few links/line breaks; the page renders this sanitized HTML.
_DESCRIPTION_TAGS = frozenset({"a", "br", "strong", "b", "em", "i", "code"})
_DESCRIPTION_ATTRS = {"a": ["href", "target", "rel"]}
_APPLY_RANK = {ApplyMode.nothing: 0, ApplyMode.apply_config: 1, ApplyMode.reinstall: 2}


class ProtocolSwitch(ApiModel):
    key: str
    label: str
    # Sanitized HTML (links, line breaks, emphasis only).
    description: str = ""
    category: str
    enabled: bool
    # What saving a change needs: nothing | apply_config | reinstall
    apply_mode: str


class ProtocolSwitchesOut(ApiModel):
    items: list[ProtocolSwitch]
    # Strongest apply step the last save needs (PUT only).
    restart_mode: str = ApplyMode.nothing.value


class ProtocolSwitchesIn(ApiModel):
    values: dict[str, bool] = Field(description="config key -> enabled")


def _switches() -> list[ProtocolSwitch]:
    rows = BoolConfig.query.filter(BoolConfig.child_id == Child.current().id).all()
    return [
        ProtocolSwitch(
            key=str(row.key),
            label=_(f"config.{row.key}.label"),
            description=bleach_clean(_(f"config.{row.key}.description"), tags=_DESCRIPTION_TAGS, attributes=_DESCRIPTION_ATTRS, strip=True),
            category=str(row.key.category),
            enabled=bool(row.value),
            apply_mode=str(row.key.apply_mode.value if isinstance(row.key.apply_mode, ApplyMode) else row.key.apply_mode),
        )
        for row in rows
        if is_protocol_switch(row.key)
    ]


class ProtocolSwitchesApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(ProtocolSwitchesOut)
    def get(self):
        """Proxy: Global protocol switches"""
        return ProtocolSwitchesOut(items=_switches())

    @app.input(ProtocolSwitchesIn, arg_name="data")
    @app.output(ProtocolSwitchesOut)
    def put(self, data: ProtocolSwitchesIn):
        """Proxy: Update global protocol switches"""
        restart_mode = ApplyMode.nothing
        changed = False
        for raw_key, enabled in data.values.items():
            key = ConfigEnum[raw_key]
            if key == ConfigEnum.not_found or key.type is not bool or not is_protocol_switch(key):
                abort(400, f"Unknown protocol switch: {raw_key}")
            if bool(hconfig(key)) == bool(enabled):
                continue
            set_hconfig(key, bool(enabled), commit=False)
            changed = True
            mode = key.apply_mode if isinstance(key.apply_mode, ApplyMode) else ApplyMode(key.apply_mode)
            if _APPLY_RANK.get(mode, 0) > _APPLY_RANK[restart_mode]:
                restart_mode = mode
        if changed:
            db.session.commit()
            hutils.proxy.get_proxies.invalidate_all()
            if hutils.node.is_child():
                hutils.node.child.schedule_notify_parent_config_changed()
        return ProtocolSwitchesOut(items=_switches(), restart_mode=restart_mode.value)
