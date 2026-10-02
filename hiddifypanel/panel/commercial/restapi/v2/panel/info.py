from flask.views import MethodView

from hiddifypanel import __version__
from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.models import Role

from .schema import PanelInfoOutputSchema


class PanelInfoApi(MethodView):
    decorators = [login_required(roles={Role.super_admin, Role.admin, Role.agent}, node_auth=True)]

    @app.output(PanelInfoOutputSchema)
    def get(self):
        res = PanelInfoOutputSchema()
        res.version = __version__
        return res
