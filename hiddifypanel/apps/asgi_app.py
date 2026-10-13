#!/opt/hiddify-manager/.venv313/bin/python

from hiddifypanel import create_app_wsgi
from hiddifypanel.asgi import build_asgi

flask_app = create_app_wsgi()  # noqa
app = build_asgi(flask_app)
