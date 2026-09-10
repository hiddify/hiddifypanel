from __future__ import annotations

from apiflask import abort
from flask.views import MethodView
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.proxy_v3.config_builder.dump import render_client_configs

from .schema import ClientConfigsIn, ClientConfigsOut


class ClientConfigsApi(MethodView):
    """Renders client configs for a user over an explicit list of domains (not a sublink domain)."""

    decorators = [login_required(node_auth=True)]

    @app.input(ClientConfigsIn, arg_name="data")
    @app.output(ClientConfigsOut)
    @app.doc(tags=["Child"], summary="Render client configs for domains", description="Renders client configs for a user over an explicit list of domains (not a sublink domain). Unknown domains are ignored.")  # type: ignore
    def post(self, data: ClientConfigsIn) -> ClientConfigsOut:
        # Not Child.node: it is a classmethod+property, which python 3.13 no longer resolves.

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

        resolved_set = set(resolved)
        return ClientConfigsOut(
            status=200,
            msg="ok",
            core=core,
            config=result.configs.get(core) or "",
            user_uuid=result.user_uuid,
            user_name=result.user_name,
            domains=resolved,
            ignored_domains=[name for name in requested if name not in resolved_set],
        )
