from flask import g, request
from flask.views import MethodView
from flask import current_app as app

from hiddifypanel.auth import login_required
from hiddifypanel.models.role import Role
from hiddifypanel.proxy_v3.template_variables import build_template_variables

from .schemas import TemplateVariablesOut


def _child_id() -> int:
    return g.child.id if g.child else 0


def _locale() -> str:
    return getattr(g, 'locale', None) or 'en'


def _include_values() -> bool:
    values = request.args.get('values', '').lower()
    return values in ('1', 'true', 'yes')


class TemplateVariablesApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(TemplateVariablesOut)  # type: ignore
    def get(self):
        groups = build_template_variables(
            child_id=_child_id(),
            lang=_locale(),
            include_values=_include_values(),
        )
        return {'groups': groups}
