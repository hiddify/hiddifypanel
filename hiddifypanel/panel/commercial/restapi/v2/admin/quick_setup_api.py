"""Admin V2 quick setup (first-run onboarding): language, password, domains; then protocols and
nodes use their own APIs, and finish hands over to the classic reinstall (with the live log)."""

from __future__ import annotations

import ipaddress
import re

from apiflask import abort
from flask import request
from flask.views import MethodView
from flask_babel import gettext as _

from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.hutils.flask import hurl_for
from hiddifypanel.models import Child, ConfigEnum, Domain, DomainType, FakeMode, Role, StrConfig, User, get_hconfigs, hconfig, set_hconfig
from hiddifypanel.models.domain import normalize_domain_name

DOMAIN_RE = re.compile(r"^([A-Za-z0-9\-\.]+\.[a-zA-Z]{2,})$")
LANGUAGES = ("en", "fa", "zh", "pt", "ru", "my")
COUNTRIES = ("ir", "zh", "ru", "other")


def needs_quick_setup() -> bool:
    """First setup: explicitly flagged, or still only the default user on the default sslip.io domain."""
    if hconfig(ConfigEnum.first_setup):
        return True
    only_default_user = User.query.filter(User.deleted.is_(False)).count() <= 1 and (
        User.query.filter(User.name == "default", User.deleted.is_(False)).first() is not None
    )
    return only_default_user and any("sslip.io" in (d.domain or "") for d in Domain.get_domains())


def _default_sslip() -> str:
    return f"{hutils.network.get_ip_str(4)}.sslip.io"


def _is_ip(name: str) -> bool:
    try:
        ipaddress.ip_address(name.strip("[]"))
        return True
    except ValueError:
        return False


# Modes the domain step offers (sub_link_only has its own field).
ENTRY_MODES = ("direct", "cdn", "reality", "relay")


def _entry_mode(d: Domain) -> str | None:
    """How the domain step shows an existing domain, or None when it is not one of its kinds."""
    if d.mode == DomainType.direct and d.fake_mode == FakeMode.reality:
        return "reality"
    if d.fake_mode != FakeMode.valid:
        return None
    if d.mode == DomainType.direct:
        return "direct"
    if d.mode == DomainType.cdn:
        return "cdn"
    if d.mode == DomainType.relay:
        return "relay"
    if d.mode == DomainType.sub_link_only:
        return "sublink"
    return None


def _wizard_domains(child_id: int) -> list[tuple[Domain, str]]:
    """Domains this step manages (the default sslip.io domain and other kinds stay on the Domains page)."""
    default = _default_sslip()
    out = []
    for d in Domain.query.filter(Domain.child_id == child_id).order_by(Domain.id).all():
        name = normalize_domain_name(d.domain)
        if not name or name == default:
            continue
        if mode := _entry_mode(d):
            out.append((d, mode))
    return out


def _state() -> dict:
    child_id = Child.current().id
    domains = _wizard_domains(child_id)
    return {
        "needs_setup": needs_quick_setup(),
        "is_node": hutils.node.is_child(),
        "admin_lang": str(hconfig(ConfigEnum.admin_lang) or "en"),
        "country": str(hconfig(ConfigEnum.country) or "other"),
        "languages": list(LANGUAGES),
        "countries": list(COUNTRIES),
        "ipv4": hutils.network.get_ip_str(4) or "",
        "ipv6": hutils.network.get_ip_str(6) or "",
        "entries": [{"domain": d.domain, "mode": mode} for d, mode in domains if mode != "sublink"],
        "sublink_domains": [d.domain for d, mode in domains if mode == "sublink"],
        "block_iran_sites": bool(hconfig(ConfigEnum.block_iran_sites)),
        "decoy_domain": hconfig(ConfigEnum.decoy_domain) or "",
    }


def _names(values) -> list[str]:
    """Accepts a list or a comma/space separated string; normalized and de-duplicated."""
    if isinstance(values, str):
        values = re.split(r"[\s,]+", values)
    out: list[str] = []
    for value in values or []:
        name = normalize_domain_name(str(value))
        if _is_ip(name):
            name = name.strip("[]")
        if name and name not in out:
            out.append(name)
    return out


def _mismatch(name: str, domain_ip: str, server_ips) -> str:
    return _(
        "Domain (%(domain)s)-> IP=%(domain_ip)s is not matched with your ip=%(server_ip)s which is required in direct mode",
        server_ip=", ".join(map(str, server_ips)),
        domain_ip=domain_ip,
        domain=name,
    )


def _check_entry(name: str, mode: str, *, taken: set[str], ours: set[str]) -> tuple[str | None, str | None]:
    """Rules per mode; returns (error, warning). A direct domain may also be this server's IP."""
    if name in taken and name not in ours:
        return _("config.Domain_already_used"), None
    server_ips = hutils.network.get_ips()
    if _is_ip(name):
        if mode != "direct":
            return _("config.Invalid_domain"), None
        return (None if ipaddress.ip_address(name) in server_ips else _mismatch(name, name, server_ips)), None
    if not DOMAIN_RE.match(name):
        return _("config.Invalid_domain"), None
    ip = hutils.network.get_domain_ip(name)
    if ip is None:
        return _("Domain can not be resolved! there is a problem in your domain"), None
    if mode == "direct" and ip not in server_ips:
        return _mismatch(name, str(ip), server_ips), None
    if mode in ("cdn", "relay") and ip in server_ips:
        return _("In CDN mode, Domain IP=%(domain_ip)s should be different to your ip=%(server_ip)s", server_ip=", ".join(map(str, server_ips)), domain_ip=str(ip)), None
    if mode == "reality" and not hutils.network.is_domain_reality_friendly(name):
        # Like the Domains page: REALITY without TLS 1.3 + h2 is allowed, but warned about.
        return None, f"{_('Domain is not REALITY friendly!')} {name}"
    return None, None


def _check_sublink(name: str, *, taken: set[str], ours: set[str]) -> str | None:
    """A subscription domain only has to resolve (to this server or, better, via a CDN)."""
    if name in taken and name not in ours:
        return _("config.Domain_already_used")
    if not DOMAIN_RE.match(name):
        return _("config.Invalid_domain")
    if hutils.network.get_domain_ip(name) is None:
        return _("Domain can not be resolved! there is a problem in your domain")
    return None


class QuickSetupApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """Quick setup: current state"""
        return _state()


class QuickSetupLanguageApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def put(self):
        """Quick setup: admin language and country"""
        body = request.get_json(silent=True) or {}
        lang, country = str(body.get("admin_lang") or ""), str(body.get("country") or "")
        if lang not in LANGUAGES or country not in COUNTRIES:
            abort(400, "invalid language or country")
        changed = lang != (hconfig(ConfigEnum.admin_lang) or "en")
        set_hconfig(ConfigEnum.admin_lang, lang, commit=False)
        set_hconfig(ConfigEnum.lang, lang, commit=False)
        set_hconfig(ConfigEnum.country, country, commit=False)
        db.session.commit()
        return {"reload": changed}


class QuickSetupPasswordApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def put(self):
        """Quick setup: admin password"""
        password = str((request.get_json(silent=True) or {}).get("password") or "")
        from hiddifypanel import admin_credentials as creds

        # Admins can not set a weak password (same rule as My account).
        if creds.password_problems(password, avoid=creds.admin_avoid(g.account)):
            return {"field_errors": {"password": [creds.PASSWORD_MESSAGE]}}, 422
        g.account.update_password(password)
        return {"status": 200, "msg": "ok"}


class QuickSetupDetectApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self):
        """Quick setup: guess a domain's mode (direct / CDN and which / REALITY)"""
        from hiddifypanel.hutils.network.domain_detect import detect_domain  # noqa: PLC0415

        names = _names([(request.get_json(silent=True) or {}).get("domain") or ""])
        if not names:
            abort(400, "domain is required")
        return detect_domain(names[0])


class QuickSetupDomainsApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def put(self):
        """Quick setup: domains ({domain, mode}), subscription domains, domestic-site blocking, decoy site"""
        body = request.get_json(silent=True) or {}
        entries: list[tuple[str, str]] = []
        seen: set[str] = set()
        for raw in body.get("entries") or []:
            names = _names([raw.get("domain") if isinstance(raw, dict) else ""])
            mode = str((raw or {}).get("mode") or "") if isinstance(raw, dict) else ""
            if names and names[0] not in seen and mode in ENTRY_MODES:
                seen.add(names[0])
                entries.append((names[0], mode))
        sublinks = [n for n in _names(body.get("sublink_domains")) if n not in seen]
        decoy = normalize_domain_name(body.get("decoy_domain"))
        child_id = Child.current().id
        # Users need a domain that reaches this server for the panel and their subscription links.
        if not sublinks and not any(mode in ("direct", "cdn") for _name, mode in entries):
            return {"field_errors": {"entries": {}, "required": True}, "errors": []}, 422

        existing = {normalize_domain_name(d.domain) for d in Domain.query.filter(Domain.child_id == child_id).all()}
        # Domains a previous run of this step added may be submitted again (Back, then Next).
        ours = {normalize_domain_name(d.domain) for d, _mode in _wizard_domains(child_id)}
        taken = existing | {normalize_domain_name(str(v)) for k, v in get_hconfigs().items() if "domain" in k and v}
        taken |= {normalize_domain_name(c.value) for c in StrConfig.query.all() if "fakedomain" in c.key and c.key != ConfigEnum.decoy_domain}

        entry_errors: dict[str, str] = {}
        sublink_errors: dict[str, str] = {}
        warnings: list[str] = []
        for name, mode in entries:
            err, warn = _check_entry(name, mode, taken=taken, ours=ours)
            if err:
                entry_errors[name] = err
            elif warn:
                warnings.append(warn)
        for name in sublinks:
            if err := _check_sublink(name, taken=taken, ours=ours):
                sublink_errors[name] = err
        decoy_error = None
        if decoy and (not DOMAIN_RE.match(decoy) or hutils.network.get_domain_ip(decoy) is None):
            decoy_error = _("Domain can not be resolved! there is a problem in your domain")
        if entry_errors or sublink_errors or decoy_error:
            return {"field_errors": {"entries": entry_errors, "sublink_domains": sublink_errors, "decoy_domain": decoy_error}, "errors": [_("config.validation-error")]}, 422

        # The default sslip.io domain served only until a real domain existed.
        for old in Domain.query.filter(Domain.child_id == child_id, Domain.domain == _default_sslip()).all():
            db.session.delete(old)
        kinds = {
            "direct": (DomainType.direct, FakeMode.valid),
            "cdn": (DomainType.cdn, FakeMode.valid),
            "relay": (DomainType.relay, FakeMode.valid),
            "reality": (DomainType.direct, FakeMode.reality),
        }
        for name, mode in entries:
            domain_type, fake_mode = kinds[mode]
            extra = {"servernames": name} if mode == "reality" else {}
            Domain.add_or_update(commit=False, child_id=child_id, domain=name, mode=domain_type, fake_mode=fake_mode, **extra)
        for name in sublinks:
            Domain.add_or_update(commit=False, child_id=child_id, domain=name, mode=DomainType.sub_link_only, fake_mode=FakeMode.valid)
        if any(mode == "reality" for _name, mode in entries) and not hconfig(ConfigEnum.reality_enable):
            set_hconfig(ConfigEnum.reality_enable, True, commit=False)
        set_hconfig(ConfigEnum.block_iran_sites, bool(body.get("block_iran_sites")), commit=False)
        if decoy:
            set_hconfig(ConfigEnum.decoy_domain, decoy, commit=False)
        db.session.commit()
        return {**_state(), "warnings": warnings}


class QuickSetupFinishApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self):
        """Quick setup: finish. Returns the classic reinstall to run (domain changed), shown with its log."""
        set_hconfig(ConfigEnum.first_setup, False)
        return {"reinstall_url": hurl_for("admin.Actions:reinstall", domain_changed="true")}
