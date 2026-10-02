from apiflask import abort
from flask.views import MethodView
from loguru import logger
from pydantic import Field

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models import ConfigEnum, set_hconfig
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel


class NodeNameInputSchema(ApiModel):
    name: str = Field(min_length=1, max_length=100, description="The node's new name")


class NodeNameApi(MethodView):
    """The parent renamed this node: keep the name here too, so the next registration does not revert it."""

    decorators = [login_required(node_auth=True)]

    @app.input(NodeNameInputSchema, arg_name="data")
    def post(self, data: NodeNameInputSchema):
        name = data.name.strip()
        if not name:
            abort(400, "name is required")
        logger.info(f"Node renamed to {name!r} by parent {g.node.unique_id}")
        set_hconfig(ConfigEnum.node_name, name)
        return {"status": 200, "msg": "ok"}
