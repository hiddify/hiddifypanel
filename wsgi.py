#!/opt/hiddify-manager/.venv313/bin/python

from hiddifypanel import create_app_wsgi

app = application = create_app_wsgi()  # noqa
from hiddifypanel.asgi import build_asgi
asgi_app = build_asgi(app)
# celery_app=app.extensions["celery"]
if __name__ == "__main__":
    app.run()
