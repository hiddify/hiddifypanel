from __future__ import annotations

from typing import Literal

from hiddifypanel.database import db
from hiddifypanel.models.custom_proxy import CustomProxy

from .sync import (
    apply_builtin_override_base_config,
    apply_builtin_override_template,
    effective_base_config_content,
    effective_template_content,
    has_custom_proxy_overrides,
)

StaleAction = Literal['removed', 'demoted']


def prepare_repromotion_template(row, catalog_content: str) -> None:
    if row.is_builtin:
        return
    if (row.content or '').strip() != (catalog_content or '').strip():
        apply_builtin_override_template(row, override=True)
    row.is_builtin = True


def prepare_repromotion_base_config(row, catalog_content: str) -> None:
    if row.is_builtin:
        return
    if (row.content or '').strip() != (catalog_content or '').strip():
        apply_builtin_override_base_config(row, override=True)
    row.is_builtin = True


def demote_builtin_template(row) -> None:
    row.content = effective_template_content(row)
    row.is_builtin = False
    row.builtin_override = False
    row.builtin_content = ''


def demote_builtin_base_config(row) -> None:
    row.content = effective_base_config_content(row)
    row.is_builtin = False
    row.builtin_override = False
    row.builtin_content = ''


def demote_builtin_custom_proxy(row: CustomProxy) -> None:
    row.is_builtin = False
    row.builtin = {}
    row.builtin_overrides = {}
    row.builtin_server_config = ''
    row.server_override = False
    for cc in list(row.client_cores):
        if cc.is_builtin:
            cc.is_builtin = False
            cc.builtin_outbounds_template = ''
            if cc.override:
                cc.override = True


def handle_stale_template(row) -> StaleAction:
    if row.builtin_override:
        demote_builtin_template(row)
        return 'demoted'
    db.session.delete(row)
    return 'removed'


def handle_stale_base_config(row) -> StaleAction:
    if row.builtin_override:
        demote_builtin_base_config(row)
        return 'demoted'
    db.session.delete(row)
    return 'removed'


def handle_stale_custom_proxy(row: CustomProxy) -> StaleAction:
    if has_custom_proxy_overrides(row):
        demote_builtin_custom_proxy(row)
        return 'demoted'
    db.session.delete(row)
    return 'removed'
