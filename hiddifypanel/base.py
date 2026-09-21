# from hiddifypanel.cache import cache


import os
import sys

from dotenv import dotenv_values


def create_app(*args, app_mode="web", **config):
    from dynaconf import FlaskDynaconf

    if app_mode == "web":
        # apiflask (and the flask_marshmallow it pulls in) is only needed for
        # the web app's OpenAPI docs/schema validation. The CLI process never
        # touches that, so avoid the import/memory cost there.
        from apiflask import APIFlask

        app = APIFlask(
            __name__,
            static_url_path="/<proxy_path>/static/",
            instance_relative_config=True,
            version="2.2.0",
            title="Hiddify API",
            openapi_blueprint_url_prefix="/<proxy_path>/api",
            docs_ui="elements",
            json_errors=False,
            enable_openapi=True,
        )
    else:
        from flask import Flask

        app = Flask(
            __name__,
            static_url_path="/<proxy_path>/static/",
            instance_relative_config=True,
        )
    # app = Flask(__name__, static_url_path="/<proxy_path>/static/", instance_relative_config=True)
    # app.asgi_app = WsgiToAsgi(app)

    _cfg_path = os.environ.get("HIDDIFY_CFG_PATH", "/opt/hiddify-manager/data/hiddify-panel/app.cfg")
    for c, v in dotenv_values(_cfg_path).items():
        if not v:
            continue
        if v.isdecimal():
            v = int(v)
        else:
            v = True if v.lower() == "true" else (False if v.lower() == "false" else v)
        app.config[c] = v
    dyn = FlaskDynaconf(app, settings_files=[_cfg_path])

    extensions = [
        # "hiddifypanel.cache:init_app",
        "hiddifypanel.database:init_app",
        "hiddifypanel.panel.hlogger:init_cli",
    ]

    if app_mode == "cli":
        extensions.append("hiddifypanel.panel.cli:init_app")
    else:
        extensions.extend(
            [
                "hiddifypanel.base_setup:init_app",
                "hiddifypanel.health_check:init_app",
                "hiddifypanel.panel.common:init_app",
                "hiddifypanel.panel.common_bp:init_app",
                "hiddifypanel.panel.admin:init_app",
                "hiddifypanel.panel.user:init_app",
                "hiddifypanel.panel.commercial:init_app",
                "hiddifypanel.panel.node:init_app",
                "hiddifypanel.scheduler:init_app",
            ]
        )

    app.config["EXTENSIONS"] = extensions

    app.config.update(config)  # Override with passed config

    app.config.load_extensions("EXTENSIONS")
    return app


def create_app_wsgi(*args, **kwargs):
    # workaround for Flask issue
    # that doesn't allow **config
    # to be passed to create_app
    # https://github.com/pallets/flask/issues/4170
    cli = len(sys.argv) <= 1 or sys.argv[1] != "run"
    # cli = (sys.argv[1] in ["update-usage", "all-configs", "admin_links", "admin_path","get-setting"])
    # cli=True
    app = create_app(app_mode="cli" if cli else "web")
    return app
