from urllib.parse import parse_qs, urlsplit

from apiflask import abort
from flask import request
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models.proxy import ProxyProto
from hiddifypanel.models.role import Role
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel
from hiddifypanel.panel.user.user import get_common_data
from hiddifypanel.proxy_v3.config_builder.dump import render_sublink_links
from hiddifypanel.proxy_v3.context_vars.builder.client_builder import build_client_template_context


class MtproxySchema(ApiModel):
    link: str = ""
    title: str = ""


class MTProxiesAPI(MethodView):
    decorators = [login_required({Role.user})]

    @app.output(list[MtproxySchema])
    def get(self):
        c = get_common_data(g.account.uuid, "new")

        if not c["telegram_enable"]:
            abort(status_code=404, message="Telegram mtproxy is not enable")

        # Every enabled Telegram custom proxy (proto telegram), rendered by its own sublink template, as in the sub link.
        contexts = [ctx for ctx in build_client_template_context(c["user"], request.host, request.user_agent.string) if ctx.proxy.proto == ProxyProto.telegram]
        links, _messages = render_sublink_links(0, contexts)
        # TODO: Remove duplicated domains mapped to a same ipv4 and v6
        return [MtproxySchema(title=_title(link), link=link) for link in dict.fromkeys(links)]


def _title(link: str) -> str:
    """The link's server; web-proxy links (server=<domain>/<path>) are marked "Web"."""
    parts = urlsplit(link)
    server = (parse_qs(parts.query).get("server") or [""])[0]
    if parts.netloc == "webproxy":
        return f"{server.split('/', 1)[0]} Web"
    return server
