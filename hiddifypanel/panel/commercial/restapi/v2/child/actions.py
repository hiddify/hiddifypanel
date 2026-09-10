from flask.views import MethodView
from loguru import logger
from pydantic import Field

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel
from hiddifypanel.panel.run_commander import Command, commander


class Status(MethodView):
    decorators = [login_required(node_auth=True)]

    def post(self):
        logger.info(f"Status action called by parent: {g.node.unique_id}")
        commander(Command.status)
        return {"status": 200, "msg": "ok"}


class UpdateUsage(MethodView):
    decorators = [login_required(node_auth=True)]

    def post(self):
        logger.info(f"Update usage action called by parent: {g.node.unique_id}")
        commander(Command.update_usage)
        return {"status": 200, "msg": "ok"}


class Restart(MethodView):
    decorators = [login_required(node_auth=True)]

    def post(self):
        logger.info(f"Restart action called by parent: {g.node.unique_id}")
        commander(Command.restart_services)
        return {"status": 200, "msg": "ok"}


class ApplyConfig(MethodView):
    decorators = [login_required(node_auth=True)]

    def post(self):
        logger.info(f"Apply config action called by parent: {g.node.unique_id}")
        commander(Command.apply)
        return {"status": 200, "msg": "ok"}


class InstallSchema(ApiModel):
    full: bool = Field(default=True, description="full install")


class Install(MethodView):
    decorators = [login_required(node_auth=True)]

    @app.input(InstallSchema, arg_name="data")
    def post(self, data: InstallSchema):
        if data.full:
            logger.info(f"Install action called by parent: {g.node.unique_id}, full=True")
            commander(Command.install)
        else:
            logger.info(f"Install action called by parent: {g.node.unique_id}, full=False")
            commander(Command.apply)
        return {"status": 200, "msg": "ok"}
