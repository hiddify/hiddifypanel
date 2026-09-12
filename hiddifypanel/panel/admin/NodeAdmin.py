from datetime import datetime

from flask import request
from flask_babel import lazy_gettext as _
from markupsafe import Markup
from wtforms.validators import ValidationError

from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import *
from hiddifypanel.panel import hiddify

from .adminlte import AdminLTEModelView


class NodeAdmin(AdminLTEModelView):
    column_hide_backrefs = False
    column_list = ["name", "mode", "unique_id", "last_node_to_parent_time", "last_parent_to_node_time"]
    form_columns = ["name", "mode", "unique_id"]
    column_labels = {
        "name": _("node.name.label"),
        "mode": _("node.mode.label"),
        "unique_id": _("node.uuid.label"),
        "last_node_to_parent_time": _("Last node to parent"),
        "last_parent_to_node_time": _("Last parent to node"),
    }
    column_descriptions = {"name": _("node.name.dscr"), "mode": _("node.mode.dscr"), "unique_id": _("node.uuid.dscr")}

    def name_formater(view, context, model, name):

        # res = hiddify.get_account_panel_link(g.account, request.host, prefere_path_only=True, child_id=model.id)
        href = f"{model.node_base_url}/{g.account.uuid}/admin/"
        return Markup(f"<a href='{href}'>{model.name}</a>")

    def relative_time_formater(view, context, model, name):
        value = getattr(model, name, None)
        if not value:
            return Markup("-")
        diff = value - datetime.now()

        if diff.days < -1000:
            return Markup("-")
        if diff.total_seconds() > -60 * 2:
            return Markup(f"<span class='badge badge-success'>{_('Online')}</span>")
        state = "danger" if diff.days < -3 else ("success" if diff.days >= -1 else "warning")
        return Markup(f"<span class='badge badge-{state}'>{hutils.convert.format_timedelta(diff, granularity='min')}</span>")

    column_formatters = {
        "name": name_formater,
        "last_node_to_parent_time": relative_time_formater,
        "last_parent_to_node_time": relative_time_formater,
    }
    can_export = False

    def is_accessible(self):
        if login_required(roles={Role.super_admin})(lambda: True)() != True:
            return False
        if Child.current().id != 0:
            return False
        return True

    def on_model_change(self, form, model, is_created):
        if is_created and model.mode != ChildMode.virtual:
            raise ValidationError(_("Remote nodes are not supported yet!"))

    def after_model_change(self, form, model, is_created):
        # deprecated
        set_hconfig(ConfigEnum.is_parent, True)
        set_hconfig(ConfigEnum.panel_mode, PanelMode.parent)
        if is_created and model.mode == ChildMode.virtual:
            # for k, v in get_hconfigs().items():
            #     set_hconfig(k, v, model.id)

            items_to_dup = []
            for p in Proxy.query.filter(Proxy.child_id == 0).all():
                p = hiddify.clone_model(p)
                p.child_id = model.id
                items_to_dup.append(p)
            for c in StrConfig.query.filter(StrConfig.child_id == 0).all():
                c = hiddify.clone_model(c)
                c.child_id = model.id
                items_to_dup.append(c)
            for c in BoolConfig.query.filter(BoolConfig.child_id == 0).all():
                c = hiddify.clone_model(c)
                c.child_id = model.id
                items_to_dup.append(c)
            d = Domain()
            d.alias = f"{model.name}-def"
            d.domain = f"{model.id}.{hutils.network.get_ip_str(4)}.sslip.io"
            d.child_id = model.id
            items_to_dup.append(d)

            db.session.bulk_save_objects(items_to_dup)
            db.session.commit()
            set_hconfig(ConfigEnum.is_parent, False, model.id)
            set_hconfig(ConfigEnum.parent_panel, hiddify.get_account_panel_link(g.account, request.host), model.id)
