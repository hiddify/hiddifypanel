from __future__ import annotations

# from . import cache
from typing import TYPE_CHECKING, cast
import os

# from . import hutils
# from . import panel
from dotenv import load_dotenv
from flask import current_app as flask_current_app
from flask import g as flask_g

if TYPE_CHECKING:
    # Only needed for type checkers; importing apiflask/flask_marshmallow at
    # runtime here would force that (heavy) import for every process,
    # including CLI invocations that never touch the web app.
    from .apps.typed_hiddify_flask import TypedFlaskContext, TypedApiFlask

current_app: TypedApiFlask = flask_current_app  # type: ignore
g: TypedFlaskContext = flask_g  # type: ignore

load_dotenv(os.environ.get("HIDDIFY_CFG_PATH", "/opt/hiddify-manager/data/hiddify-panel/app.cfg"))
from . import Events
from .base import create_app, create_app_wsgi
from .VERSION import __release_time__, __version__, is_released_version

__all__ = [
    "create_app",
    "create_app_wsgi",
    "current_app",
    "g",
    "__release_time__",
    "__version__",
    "is_released_version",
    "Events",
]

# application = create_app_wsgi()
