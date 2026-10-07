"""Domain rows for the fake-TLS front domains (Telegram MTProxy, Shadowsocks FakeTLS, ShadowTLS).

Each row (``fake_mode`` telegram / shadowtls / ssfaketls, one per node) is kept in sync, both ways, with the matching
``*_fakedomain`` setting: saving the row writes the setting, changing the setting updates (or creates) the row.
"""

from __future__ import annotations

from loguru import logger

from hiddifypanel.database import db
from hiddifypanel.models import ConfigEnum, Domain, DomainType, FakeMode, hconfig, set_hconfig
from hiddifypanel.models.domain import FAKE_PROXY_MODES

#: fake mode -> (setting holding the domain, setting that turns the feature on)
FAKE_PROXY_CONFIGS: dict[FakeMode, tuple[ConfigEnum, ConfigEnum]] = {
    FakeMode.telegram: (ConfigEnum.telegram_fakedomain, ConfigEnum.telegram_enable),
    FakeMode.shadowtls: (ConfigEnum.shadowtls_fakedomain, ConfigEnum.shadowtls_enable),
    FakeMode.ssfaketls: (ConfigEnum.ssfaketls_fakedomain, ConfigEnum.ssfaketls_enable),
}

_WATCHED_KEYS = {key for pair in FAKE_PROXY_CONFIGS.values() for key in pair}


def fake_proxy_row(fake_mode: FakeMode, child_id: int) -> Domain | None:
    return Domain.query.filter(Domain.fake_mode == fake_mode, Domain.child_id == child_id).order_by(Domain.id).first()


def sync_domain_to_config(domain: Domain) -> None:
    """Row saved: write its name to the setting."""
    if domain.fake_mode not in FAKE_PROXY_MODES:
        return
    key = FAKE_PROXY_CONFIGS[domain.fake_mode][0]
    name = (domain.domain or "").strip().lower()
    if name and (hconfig(key, domain.child_id) or "").strip().lower() != name:
        set_hconfig(key, name, domain.child_id, commit=False)


def sync_config_to_domain(fake_mode: FakeMode, child_id: int, *, changed: dict | None = None) -> Domain | None:
    """Setting changed: rename the row, or create it when there is none yet.

    ``changed`` holds new values not committed yet (setting -> value); they win over the stored ones."""
    domain_key = FAKE_PROXY_CONFIGS[fake_mode][0]
    changed = changed or {}

    def value(key):
        return changed[key] if key in changed else hconfig(key, child_id)

    name = str(value(domain_key) or "").strip().lower()
    if not name:
        return None
    row = fake_proxy_row(fake_mode, child_id)
    if row is not None:
        if (row.domain or "").lower() != name and _name_is_free(name, child_id, row):
            row.domain = name
            row.alias = name
        return row
    if not _name_is_free(name, child_id, None):
        logger.warning(f"{fake_mode.value} fake domain {name} is already a domain row; not adding a second one")
        return None
    row = Domain(child_id=child_id, domain=name, alias=name, mode=DomainType.direct, fake_mode=fake_mode, cdn_ip="", servernames="", extra_params="{}")
    db.session.add(row)
    return row


def sync_all_configs_to_domains(child_id: int | None = None) -> None:
    """Make sure every fake domain setting has its row (after migrations, and when the Domains page opens)."""
    from hiddifypanel.models import Child

    child_ids = [child_id] if child_id is not None else [c.id for c in Child.query.all()]
    for cid in child_ids:
        for fake_mode in FAKE_PROXY_CONFIGS:
            sync_config_to_domain(fake_mode, cid)
    if db.session.dirty or db.session.new:  # the Domains page calls this on every open; skip the empty commit
        db.session.commit()


def domains_taken_by_others(setting: ConfigEnum, child_id: int) -> list[str]:
    """Names in the domains table a ``*_domain`` setting must not take: all of them except its own fake-domain row
    (the Telegram / ShadowTLS / SS FakeTLS setting is that row)."""
    own = {mode for mode, (key, _) in FAKE_PROXY_CONFIGS.items() if key == setting}
    return [d.domain.lower() for d in Domain.query.all() if not (d.fake_mode in own and d.child_id == child_id)]


def _name_is_free(name: str, child_id: int, ignore: Domain | None) -> bool:
    same = Domain.query.filter(Domain.domain == name, Domain.child_id == child_id).all()
    return all(d is ignore or (ignore is not None and d.id == ignore.id) for d in same)


def _on_config_changed(conf, old_value=None, **_) -> None:
    key = conf.key
    if key not in _WATCHED_KEYS:
        return
    for fake_mode, keys in FAKE_PROXY_CONFIGS.items():
        if key in keys:
            sync_config_to_domain(fake_mode, conf.child_id, changed={key: conf.value})


def subscribe_events() -> None:
    from hiddifypanel import Events

    if _on_config_changed not in Events.config_changed.callbacks:
        Events.config_changed.subscribe(_on_config_changed)
