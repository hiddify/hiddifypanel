from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.models import Role

from .schema import PongOutputSchema


class PingPongApi(MethodView):
    decorators = [login_required(roles={Role.super_admin, Role.admin, Role.agent}, node_auth=True)]

    @app.output(PongOutputSchema)
    def get(self):
        """Ping Pong: Get"""
        return {"msg": "GET: PONG"}

    @app.output(PongOutputSchema)
    def post(self):
        """Ping Pong: Post"""
        return {"msg": "POST: PONG"}

    @app.output(PongOutputSchema)
    def patch(self):
        """Ping Pong: Patch"""
        return {"msg": "PATCH: PONG"}

    @app.output(PongOutputSchema)
    def delete(self):
        """Ping Pong: Delete"""
        return {"msg": "DELETE: PONG"}

    @app.output(PongOutputSchema)
    def put(self):
        """Ping Pong: Put"""
        return {"msg": "PUT: PONG"}
