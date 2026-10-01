import re

from flask_babel import gettext as __
from flask_babel import lazy_gettext as _
from markupsafe import Markup, escape
from wtforms.validators import Regexp, ValidationError

from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.hutils.flask import hurl_for
from hiddifypanel.models import ApplyMode, Child, ConfigEnum, CustomProxy, Domain, DomainType, FakeMode, Role, hconfig, set_hconfig
from hiddifypanel.panel import custom_widgets, hiddify
from hiddifypanel.proxy_v3.domain_proxy_options import REALITY_TERMINATION_SLUG

from .adminlte import AdminLTEModelView


class DomainAdmin(AdminLTEModelView):
    column_hide_backrefs = False

    edit_template = "model/domain_edit.html"
    # create_template = "model/domain_create.html"

    list_template = "model/domain_list.html"
    form_overrides = {
        "mode": custom_widgets.EnumSelectField,
        "fake_mode": custom_widgets.EnumSelectField,
        "extra_params": custom_widgets.JSONField,
    }
    form_widget_args = {
        "description": {"rows": 100, "style": "font-family: monospace; direction:ltr"},
    }
    column_descriptions = dict(
        domain=_("domain.description"),
        mode=_("Direct mode means you want to use your server directly (for usual use), CDN means that you use your server on behind of a CDN provider."),
        fake_mode=_("domain.fake_mode.description"),
        cdn_ip=_("config.cdn_forced_host.description"),
        show_domains=_("domain.show_domains_description"),
        alias=_("The name shown in the configs for this domain."),
        servernames=_("config.reality_server_names.description"),
        grpc=_("grpc-proxy.description"),
        download_domain=_("download_domain.description"),
        resolve_ip=_("domain.resolveip.description"),
        ech=_("domain.ech.description"),
        custom_proxy=_("domain.custom_proxy.description"),
        custom_proxies=_("domain.custom_proxy.description"),
        server_domain=_("domain.server_domain.description"),
        tls_status=_("domain.tls_status.description"),
    )
    can_export = False
    form_widget_args = {"show_domains": {"class": "form-control ltr"}, "download_domain": {"class": "form-control ltr"}, "custom_proxies": {"class": "form-control ltr"}}

    form_args = {
        "mode": {"enum": DomainType},
        "fake_mode": {"enum": FakeMode},
        "show_domains": {
            "query_factory": lambda: Domain.query.filter(Domain.mode != DomainType.sub_link_only).order_by(Domain.child_id, Domain.domain),
            "get_label": lambda d: DomainAdmin._domain_option_label(d),
        },
        "download_domain": {
            "query_factory": lambda: Domain.query.filter(Domain.mode != DomainType.sub_link_only, Domain.child_id == Child.current().id).order_by(Domain.domain),
            "get_label": lambda d: DomainAdmin._domain_option_label(d),
        },
        "custom_proxies": {
            "query_factory": lambda: CustomProxy.query.filter(
                CustomProxy.enable,
                CustomProxy.child_id == Child.current().id,
                CustomProxy.slug != REALITY_TERMINATION_SLUG,
            ).order_by(CustomProxy.sort_order, CustomProxy.name),
            "get_label": lambda p: p.name,
        },
        "domain": {
            "filters": [lambda x: x.strip() if x else x],
            "validators": [Regexp(r"^(\*\.)?([A-Za-z0-9\-\.]+\.[a-zA-Z]{2,})$|^$|^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-fA-F]{1,4}:){1,7}(:|[0-9a-fA-F]{1,4})$", message=__("Should be a valid domain"))],
        },
        "cdn_ip": {"validators": [Regexp(r"(((((25[0-5]|(2[0-4]|1\d|[1-9]|)\d).){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d))|^([A-Za-z0-9\-\.]+\.[a-zA-Z]{2,}))[ \t\n,;]*\w{3}[ \t\n,;]*)*", message=__("Invalid IP or domain"))]},
        "servernames": {"validators": [Regexp(r"^([\w-]+\.)+[\w-]+(,\s*([\w-]+\.)+[\w-]+)*$", re.IGNORECASE, _("Invalid REALITY hostnames"))]},
        "server_domain": {
            "query_factory": lambda: Domain.query.filter(
                Domain.child_id == Child.current().id,
                Domain.mode.in_([DomainType.direct, DomainType.relay]),
                Domain.fake_mode == FakeMode.valid,
            )
        },
    }
    column_list = ["domain", "alias", "mode", "tls_status", "custom_proxies", "show_domains"]
    column_editable_list = ["alias"]
    column_searchable_list = ["domain", "mode"]
    column_sortable_list = ["domain", "alias", "mode"]
    column_labels = {
        "domain": _("domain.domain"),
        "mode": _("domain.mode"),
        "fake_mode": _("domain.fake_mode.label"),
        "cdn_ip": _("config.cdn_forced_host.label"),
        "domain_ip": _("domain.ip"),
        "servernames": _("config.reality_server_names.label"),
        "server_domain": _("domain.server_domain.label"),
        "show_domains": _("Show Domains"),
        "alias": _("Alias"),
        "grpc": _("gRPC"),
        "download_domain": _("download_domain.label"),
        "resolve_ip": _("domain.resolveip.label"),
        "ech": _("domain.ech.label"),
        "custom_proxies": _("domain.custom_proxy.label"),
        "tls_status": _("TLS"),
    }

    form_columns = [
        "mode",
        "fake_mode",
        "domain",
        "alias",
        "custom_proxies",
        "show_domains",
        "resolve_ip",
        "ech",
        "download_domain",
        # "servernames",
        "server_domain",
        "cdn_ip",
        "extra_params",
    ]

    @staticmethod
    def _domain_option_label(d: Domain) -> str:
        child_name = d.child.name if d.child else ""
        alias = d.alias or ""
        mode = d.mode.value if d.mode else ""
        fake_mode = d.fake_mode.value if d.fake_mode else ""
        if d.child_id == Child.current().id:
            return f"{alias} [{d.domain}] {mode}({fake_mode})"
        return f"Node[{child_name}] {alias} [{d.domain}] {mode}({fake_mode})"

    def _domain_admin_link(view, context, model, name):
        server = model.get_server() or model.domain
        domain_tag = model.domain or ""
        if server and domain_tag != server:
            domain_tag = f"{domain_tag} → {server}" if domain_tag else str(server)
        if server:
            domain_ip = f'<a data-domain="{escape(domain_tag)}" href="{hurl_for("admin.Actions:get_domain_ip", domain=server)}" class="domain-ip-link"><i class="fa-solid fa-dharmachakra"></i></a>'
        else:
            domain_ip = ""
        if hiddify.is_fake_domain(model) or not model.is_accessible():
            badge = model.fake_mode.value if model.fake_mode else ""
            return Markup(f"<span class='badge'>{escape(model.domain or badge)}</span>" + domain_ip)
        d = model.domain
        if "*" in d:
            d = d.replace("*", hutils.random.get_random_string(5, 15))
        admin_link = hiddify.get_account_panel_link(g.account, d)
        return Markup(
            f'<div class="btn-group"><a href="{admin_link}" class="btn btn-xs btn-secondary">' + _("admin link") + f'</a><a href="{admin_link}" class="btn btn-xs btn-info ltr" target="_blank">{escape(model.domain)}</a></div>' + domain_ip
        )

    def _domain_ip(view, context, model, name):
        myips = set(hutils.network.get_ips())
        target = model.get_server() or model.domain
        dips = hutils.network.get_domain_ips_cached(target) if target else set()
        all_res = ""
        for dip in dips:
            if dip in myips and model.mode in [DomainType.direct, DomainType.sub_link_only]:
                badge_type = ""
            elif dip and dip not in myips and model.mode != DomainType.direct:
                badge_type = "warning"
            else:
                badge_type = "danger"
            res = f'<span class="badge badge-{badge_type}">{dip}</span>'
            if model.is_sub_link_only():
                res += f'<span class="badge badge-success">{_("SubLink")}</span>'
            all_res += res
        return Markup(all_res)

    def _show_domains_formater(view, context, model, name):
        if hiddify.is_fake_domain(model):
            return ""
        if not len(model.show_domains):
            return _("All")
        else:
            return Markup(" ".join([hiddify.get_domain_btn_link(d) for d in model.show_domains]))

    def _mode_formater(view, context, model, name):
        return f"{model.mode.value} ({model.fake_mode.value})"

    def _custom_proxies_formater(view, context, model, name):
        proxies = [proxy for proxy in (model.custom_proxies or [])]
        if not proxies:
            return ""
        links = []
        for proxy in model.custom_proxies:
            links.append(f"<a href='{hurl_for('admin.admin_v2')}custom-proxies/{proxy.id}' target='_blank'>{escape(proxy.name)}</a>")
        return Markup(" ".join(links))

    def _tls_status_formater(view, context, model, name):
        status = model.tls_status
        badges = {
            "valid": "success",
            "self_signed": "warning",
            "expired": "danger",
            "invalid": "danger",
            "missing": "secondary",
        }
        labels = {
            "valid": _("Valid"),
            "self_signed": _("Self-signed"),
            "expired": _("Expired"),
            "invalid": _("Invalid"),
            "missing": _("No certificate"),
        }
        label = labels.get(status, status)
        cert = model.certificate
        hint_parts = []
        if cert and cert.issuer:
            hint_parts.append(str(cert.issuer))
        if cert and cert.expires_at:
            hint_parts.append(cert.expires_at.strftime("%Y-%m-%d"))
        if cert and cert.last_renewal_error:
            hint_parts.append(str(cert.last_renewal_error))
        title = " — ".join(hint_parts)
        title_attr = f' title="{escape(title)}"' if title else ""
        return Markup(f'<span class="badge badge-{badges.get(status, "secondary")}"{title_attr}>{escape(str(label))}</span>')

    column_formatters = {
        "domain": _domain_admin_link,
        "show_domains": _show_domains_formater,
        "mode": _mode_formater,
        "custom_proxies": _custom_proxies_formater,
        "tls_status": _tls_status_formater,
    }

    def search_placeholder(self):
        return f"{_('search')} {_('domain.domain')} {_('domain.mode')}"

    def on_model_change(self, form, model: Domain, is_created):
        # Same rules as the Domains page of the new dashboard (panel/domain_rules.py).
        from hiddifypanel.panel import domain_rules

        try:
            warnings = domain_rules.validate_domain(model, is_created=is_created)
        except domain_rules.DomainRuleError as e:
            raise ValidationError(str(e))
        for warning in warnings:
            hutils.flask.flash(warning, "warning")

        old_db_domain = Domain.by_domain(model.domain)
        if is_created or not old_db_domain or old_db_domain.mode != model.mode:
            hutils.flask.flash_config_success(restart_mode=ApplyMode.apply_config, domain_changed=True)

    def on_model_delete(self, model):
        from hiddifypanel.panel import domain_rules

        try:
            warnings = domain_rules.before_delete(model)
        except domain_rules.DomainRuleError as e:
            raise ValidationError(str(e))
        for warning in warnings:
            hutils.flask.flash(warning, "warning")  # type: ignore
        hutils.flask.flash_config_success(restart_mode=ApplyMode.apply_config, domain_changed=True)

    def after_model_change(self, form, model, is_created):
        if hconfig(ConfigEnum.first_setup):
            set_hconfig(ConfigEnum.first_setup, False)
        from hiddifypanel.panel import domain_rules

        domain_rules.request_certificate(model)
        # Nodes notify the parent from the commit hook (models/cache_events.py).

    def is_accessible(self):
        if login_required(roles={Role.super_admin, Role.admin})(lambda: True)() != True:
            return False
        return True

    def get_query(self):
        from sqlalchemy.orm import joinedload

        query = super().get_query()
        return query.options(joinedload(Domain.certificate)).filter(Domain.child_id == Child.current().id)

    def get_count_query(self):

        query = super().get_count_query()
        return query.filter(Domain.child_id == Child.current().id)
