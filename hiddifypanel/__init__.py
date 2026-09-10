# from . import cache
from typing import cast

# from . import hutils
# from . import panel
from apiflask import APIFlask
from dotenv import load_dotenv
from flask import current_app as flask_current_app
from flask import g as flask_g

from .apps.typed_hiddify_flask import TypedFlaskContext, TypedApiFlask

current_app: TypedApiFlask = flask_current_app  # type: ignore
g: TypedFlaskContext = flask_g  # type: ignore

load_dotenv("/opt/hiddify-manager/services/hiddify-panel/app.cfg")
from . import Events
from .base import create_app, create_app_wsgi
from .VERSION import __release_time__, __version__, is_released_version

__all__ = ["create_app", "create_app_wsgi", "current_app", "__release_time__", "__version__", "is_released_version", "Events"]

# application = create_app_wsgi()
