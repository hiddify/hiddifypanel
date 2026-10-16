from urllib.parse import parse_qs, urlsplit

from apiflask import abort
from flask import request
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.role import Role
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel
from hiddifypanel.proxy_v3.config_builder.dump import render_client_configs


class MtproxySchema(ApiModel):
    link: str = ""
    title: str = ""


class MTProxiesAPI(MethodView):
    decorators = [login_required({Role.user})]

    @app.output(list[MtproxySchema])
    def get(self):
        if not hconfig(ConfigEnum.telegram_enable):
            abort(status_code=404, message="Telegram mtproxy is not enable")

        # Exactly the user's subscription (same domain, same custom proxies and templates), kept to its Telegram links:
        # what the Telegram custom proxies (proto telegram, sublink/telegram_*.j2) put in it.
        result = render_client_configs(user=g.account, child_id=0, sublink_domain=request.host, user_agent=request.user_agent.string, cores=("sublink",))
        links = [line.strip() for line in (result.configs.get("sublink") or "").splitlines() if line.strip().startswith("tg://")]
        # TODO: Remove duplicated domains mapped to a same ipv4 and v6
        return [MtproxySchema(title=_title(link), link=link) for link in dict.fromkeys(links)]


def _title(link: str) -> str:
    """The link's server; web-proxy links (server=<domain>/<path>) are marked "Web"."""
    parts = urlsplit(link)
    server = (parse_qs(parts.query).get("server") or [""])[0]
    if parts.netloc == "webproxy":
        return f"{server.split('/', 1)[0]} Web"
    return server
