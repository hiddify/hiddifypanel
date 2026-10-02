
from urllib.parse import urlparse
from pydantic import Field
from flask import request
from flask.views import MethodView
from hiddifypanel.auth import login_required
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.role import Role
from hiddifypanel.panel import hiddify
from hiddifypanel import g, current_app as app
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel


class ShortSchema(ApiModel):
    short: str = Field(default="", description="the short url slug")
    full_url: str = Field(default="", description="full short url")
    expire_in: int = Field(default=0, description="expire_in is in seconds")


class ShortAPI(MethodView):
    decorators = [login_required({Role.user})]

    @app.output(ShortSchema)
    def get(self):
        short, expire_in = hiddify.add_short_link(hiddify.get_account_panel_link(g.account, request.host))
        full_url = f"https://{request.host}/{short}"
        dto = ShortSchema()
        dto.full_url = full_url
        dto.short = short
        # expire_in is in seconds
        dto.expire_in = expire_in
        return dto
