import re

from flask_babel import gettext as __
from flask_babel import lazy_gettext as _
from loguru import logger
from markupsafe import Markup, escape
from wtforms.validators import Regexp, ValidationError

from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.hutils.flask import hurl_for
from hiddifypanel.models import ApplyMode, Child, ConfigEnum, CustomProxy, CustomProxyMode, Domain, DomainType, FakeMode, Role, get_hconfigs, hconfig, set_hconfig
from hiddifypanel.panel import custom_widgets, hiddify
from hiddifypanel.panel.run_commander import Command, commander
from hiddifypanel.proxy_v3.domain_mode_filter import domain_modes_use_reality, expand_domain_mode_tokens, proxy_buckets_for_domain
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
        model.domain = (model.domain or "").lower().strip()
        model.mode = DomainType(model.mode)
        if model.server_domain:
            model.cdn_ip = ""
            sd = model.server_domain
            if sd.mode not in (DomainType.direct, DomainType.relay) or sd.fake_mode != FakeMode.valid or sd.is_sub_link_only():
                raise ValidationError(_("domain.server_domain.must_be_valid_direct_or_relay"))

        if model.download_domain and model.domain == model.download_domain.domain:
            model.download_domain_id = None
            model.download_domain = None

        if model.mode == DomainType.sub_link_only:
            model.fake_mode = FakeMode.valid

        if model.mode.is_cdn() or model.mode == DomainType.worker:
            if model.fake_mode != FakeMode.valid:
                raise ValidationError(_("CDN and worker domains must use valid fake mode"))

        if model.domain == "" and model.fake_mode != FakeMode.fake:
            raise ValidationError(_("domain.empty.allowed_for_fake_only"))

        self._validate_not_used_before(model, is_created)
        ipv4_list = hutils.network.get_ips(4)
        ipv6_list = hutils.network.get_ips(6)
        server_ips = [*ipv4_list, *ipv6_list]

        if not server_ips:
            raise ValidationError(_("Couldn't find your ip addresses"))

        if "*" in model.domain and model.mode != DomainType.cdn:
            raise ValidationError(_("Domain can not be resolved! there is a problem in your domain"))

        if model.mode == DomainType.relay and model.fake_mode != FakeMode.valid and not (model.cdn_ip or "").strip():
            raise ValidationError(_("Relay domains with non-valid fake mode require an IP address"))

        if model.custom_proxies:
            model.custom_proxies = [p for p in model.custom_proxies if p and p.slug != REALITY_TERMINATION_SLUG]

        if model.fake_mode == FakeMode.reality:
            selected = list(model.custom_proxies or [])
            for proxy in selected:
                if proxy.mode != CustomProxyMode.domains_l7_gateway or not domain_modes_use_reality(proxy.domain_modes):
                    raise ValidationError(_("domain.custom_proxy.reality_only"))
            buckets = set(proxy_buckets_for_domain(model.mode, model.fake_mode))
            model.custom_proxies = [p for p in selected if buckets & expand_domain_mode_tokens(p.domain_modes)]
        elif model.custom_proxies:
            sni_count = sum(1 for p in model.custom_proxies if p and p.mode == CustomProxyMode.domains_sni_gateway)
            has_l7 = any(p and p.mode == CustomProxyMode.domains_l7_gateway for p in model.custom_proxies)
            if sni_count > 1:
                raise ValidationError(_("domain.custom_proxy.sni_single_only"))
            if sni_count and has_l7:
                raise ValidationError(_("domain.custom_proxy.sni_l7_mutex"))
            buckets = set(proxy_buckets_for_domain(model.mode, model.fake_mode))
            valid = []
            for proxy in model.custom_proxies:
                proxy_buckets = expand_domain_mode_tokens(proxy.domain_modes)
                if buckets & proxy_buckets:
                    valid.append(proxy)
            model.custom_proxies = valid

        cloudflare_updated = self._update_cloudflare(model, ipv4_list, ipv6_list)

        if not cloudflare_updated:
            self._validate_domain_ips(model, server_ips)

        if model.mode == DomainType.direct and model.cdn_ip:
            model.cdn_ip = ""
            raise ValidationError(_("Specifying CDN IP is only valid for CDN mode"))

        if not model.mode.is_cdn():
            model.ech = False
        elif model.ech and not hconfig(ConfigEnum.tls_ech_enable):
            raise ValidationError(_("Enable TLS ECH in panel settings before using ECH on a CDN domain"))

        if model.fake_mode == FakeMode.fake and not model.cdn_ip:
            model.cdn_ip = str(server_ips[0])

        if model.cdn_ip:
            try:
                hutils.network.auto_ip_selector.get_clean_ip(str(model.cdn_ip))
            except Exception:
                raise ValidationError(_("Error in auto cdn format"))

        model.show_domains = [d for d in (model.show_domains or []) if not d.is_sub_link_only()]

        if len(model.show_domains) == Domain.query.count():
            model.show_domains = []

        if model.fake_mode == FakeMode.reality:
            self._validate_reality_settings(model, server_ips)

        old_db_domain = Domain.by_domain(model.domain)
        if is_created or not old_db_domain or old_db_domain.mode != model.mode:
            hutils.flask.flash_config_success(restart_mode=ApplyMode.apply_config, domain_changed=True)

    def _update_cloudflare(self, model, ipv4_list, ipv6_list):
        if hconfig(ConfigEnum.cloudflare) and model.fake_mode == FakeMode.valid and model.mode not in [DomainType.relay]:
            try:
                proxied = model.mode == DomainType.cdn
                if ipv4_list:
                    hutils.network.cf_api.add_or_update_dns_record(model.domain, str(ipv4_list[0]), "A", proxied=proxied)
                if ipv6_list:
                    hutils.network.cf_api.add_or_update_dns_record(model.domain, str(ipv6_list[0]), "AAAA", proxied=proxied)
                return True
            except Exception as e:
                raise ValidationError(__("cloudflare.error") + f" {e}")
        return False

    def _validate_reality_settings(self, model, server_ips):
        if not hconfig(ConfigEnum.reality_enable):
            set_hconfig(ConfigEnum.reality_enable, True)
            hutils.proxy.get_proxies.invalidate_all()

        model.servernames = (model.servernames or model.domain).lower().strip()
        domains_to_check = set()
        for v in [model.domain, model.servernames]:
            domains_to_check.update(d.strip() for d in v.split(",") if d.strip())

        for d in domains_to_check:
            if not hutils.network.is_domain_reality_friendly(d):
                # raise ValidationError(_("Domain is not REALITY friendly!") + f" {d}")
                hutils.flask.flash(_("Domain is not REALITY friendly!") + f" {d}", "warning")

            try:
                if not hutils.network.is_in_same_asn(d, server_ips[0]):
                    domain_ips = hutils.network.get_domain_ips(d)
                    if domain_ips:
                        dip = next(iter(domain_ips))
                        server_asn = hutils.network.get_ip_asn(server_ips[0])
                        domain_asn = hutils.network.get_ip_asn(dip)
                        msg = _("domain.reality.asn_issue")
                        if server_asn or domain_asn:
                            msg += f"<br> Server ASN={server_asn}<br>{d}_ASN={domain_asn}"
                        hutils.flask.flash(msg, "warning")
            except Exception as e:
                logger.warning(f"ASN check failed for domain {d}: {str(e)}")

        for d in model.servernames.split(","):
            if d.strip() and not hutils.network.fallback_domain_compatible_with_servernames(model.domain, d):
                msg = _("REALITY Fallback domain is not compatible with server names!") + f" {d} != {model.domain}"
                hutils.flask.flash(msg, "warning")

    def _validate_not_used_before(self, model, is_created):
        configs = get_hconfigs()
        for c in configs:
            if "domain" in c and c not in [ConfigEnum.decoy_domain, ConfigEnum.reality_fallback_domain] and c.category != "hidden":
                if model.domain == configs[c]:
                    raise ValidationError(_("You have used this domain in: ") + _(f"config.{c}.label"))

        for td in Domain.query.filter(Domain.fake_mode == FakeMode.reality, Domain.domain != model.domain).all():
            if td.servernames and (model.domain in td.servernames.split(",")):
                raise ValidationError(_("You have used this domain in: ") + _("config.reality_server_names.label") + td.domain)

        if is_created and Domain.query.filter(Domain.domain == model.domain, Domain.child_id == model.child_id).count() > 1:
            raise ValidationError(_("You have used this domain in: "))

    def _validate_domain_ips(self, model, server_ips):
        if (model.domain.startswith("*") or not model.domain) and model.mode not in [DomainType.direct]:
            return True
        if model.fake_mode in (FakeMode.fake, FakeMode.reality, FakeMode.dns):
            return True
        if model.mode in [DomainType.relay]:
            return True
        try:
            dips = hutils.network.get_domain_ips(model.domain)
        except Exception as e:
            logger.error(f"Error resolving domain {model.domain}: {str(e)}")
            raise ValidationError(_("Domain cannot be resolved! Please check DNS settings"))

        if not dips:
            raise ValidationError(_("Domain cannot be resolved! Please check DNS settings"))

        domain_ip_matches_server = any(ip in dips for ip in server_ips)
        server_ips_str = ", ".join(map(str, server_ips))
        dips_str = ", ".join(map(str, dips))

        if not domain_ip_matches_server and model.mode in [DomainType.direct]:
            raise ValidationError(__("Domain IP=%(domain_ip)s is not matched with your ip=%(server_ip)s which is required in direct mode", server_ip=server_ips_str, domain_ip=dips_str))

        if domain_ip_matches_server and model.mode in [DomainType.cdn, DomainType.relay]:
            raise ValidationError(__("In CDN mode, Domain IP=%(domain_ip)s should be different to your ip=%(server_ip)s", server_ip=server_ips_str, domain_ip=dips_str))

        return True

    def on_model_delete(self, model):
        if len(Domain.query.all()) <= 1:
            raise ValidationError("at least one domain should exist")
        if hconfig(ConfigEnum.cloudflare) and model.fake_mode == FakeMode.valid and model.mode not in [DomainType.relay]:
            if not hutils.network.cf_api.delete_dns_record(model.domain):
                hutils.flask.flash(_("cf-delete.failed"), "warning")  # type: ignore
        model.showed_by_domains = []
        hutils.flask.flash_config_success(restart_mode=ApplyMode.apply_config, domain_changed=True)

    def after_model_delete(self, model):
        if hutils.node.is_child():
            hutils.node.run_node_op_in_bg(hutils.node.child.sync_with_parent, hutils.node.child.SyncFields.domains)

    def after_model_change(self, form, model, is_created):
        if hconfig(ConfigEnum.first_setup):
            set_hconfig(ConfigEnum.first_setup, False)
        if model.need_valid_ssl and "*" not in model.domain:
            commander(Command.get_cert, domain=model.domain)
        if hutils.node.is_child():
            hutils.node.run_node_op_in_bg(hutils.node.child.sync_with_parent, hutils.node.child.SyncFields.domains)

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
