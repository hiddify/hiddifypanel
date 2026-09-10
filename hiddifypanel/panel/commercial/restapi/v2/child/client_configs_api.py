from __future__ import annotations

from apiflask import abort
from flask import Response
from flask.views import MethodView
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.proxy_v3.config_builder.dump import render_client_configs

from .schema import ClientConfigsIn, ClientConfigsOut


def _render(data: ClientConfigsIn) -> ClientConfigsOut:

    try:
        result = render_client_configs(
            user_uuid=data.user_uuid,
            child_id=0,
            domains=data.domains,
            user_agent=data.user_agent,
            pretty=data.pretty,
            cores=(data.core,),
            invalidate_cache=False,
        )
    except ValueError as err:
        logger.error(f"Failed to render client configs: {err}")
        abort(400, str(err))

    return ClientConfigsOut(
        status=200,
        msg="ok",
        config=result.configs.get(data.core) or "",
        user_uuid=result.user_uuid,
        user_name=result.user_name,
    )


def _maybe_raw(data: ClientConfigsIn, out: ClientConfigsOut) -> ClientConfigsOut | Response:
    if not data.raw:
        return out
    mime = "text/plain; charset=utf-8" if data.core == "sublink" else "application/json"
    return Response(out.config or "", mimetype=mime)


class ClientConfigsApi(MethodView):
    """Renders client configs for a user over an explicit list of domains (not a sublink domain)."""

    decorators = [login_required(node_auth=True)]

    @app.input(ClientConfigsIn, location="query", arg_name="data")
    @app.doc(
        tags=["Child"],
        summary="Render client configs for domains (GET)",
        description="Same as POST. Pass raw=true to return the config body only (for Jinja download()).",
    )
    def get(self, data: ClientConfigsIn) -> ClientConfigsOut | Response:
        return _maybe_raw(data, _render(data))

    @app.input(ClientConfigsIn, arg_name="data")
    @app.output(ClientConfigsOut)
    @app.doc(
        tags=["Child"],
        summary="Render client configs for domains",
        description="Renders client configs for a user over an explicit list of domains (not a sublink domain). Unknown domains are ignored. Empty domains uses all local domains.",
    )
    def post(self, data: ClientConfigsIn) -> ClientConfigsOut | Response:
        out = _render(data)
        if data.raw:
            return _maybe_raw(data, out)
        return out
