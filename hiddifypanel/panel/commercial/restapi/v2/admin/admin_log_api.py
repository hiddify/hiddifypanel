import os
import re

from ansi2html import Ansi2HTMLConverter
from apiflask import abort
from flask import make_response, request
from flask.views import MethodView
from pydantic import Field

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models import ConfigEnum, hconfig
from hiddifypanel.models.role import Role
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel

_LOG_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class AdminInputLogfileSchema(ApiModel):
    file: str = Field(description="The log file name")


class AdminLogApi(MethodView):
    def _read_log(self, file_name):
        if not file_name or not _LOG_NAME_RE.match(file_name):
            abort(400, "Parameter issue: 'file'")

        log_dir = os.path.realpath(os.path.join(app.config["HIDDIFY_CONFIG_PATH"], "data/log/system"))
        file_path = os.path.realpath(os.path.join(log_dir, os.path.basename(file_name)))
        if os.path.commonpath([log_dir, file_path]) != log_dir or not os.path.isfile(file_path):
            abort(404, "Invalid log file")

        with open(file_path) as f:
            logs = "".join(f)

        conv = Ansi2HTMLConverter()
        html_log = f'<div style="background-color:black; color:white;padding:10px">{conv.convert(logs)}</div>'
        resp = make_response(html_log)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    @app.input(AdminInputLogfileSchema, arg_name="data", location="form")
    @login_required({Role.super_admin})
    def post(self, data: AdminInputLogfileSchema):
        """System: View Log file"""
        return self._read_log(data.file)

    @login_required({Role.super_admin})
    def get(self):
        """System: View Log file"""
        return self._read_log(request.args.get("file"))

    def options(self):
        if g.proxy_path != hconfig(ConfigEnum.proxy_path_admin):
            abort(403)
        resp = make_response("")
        resp.headers["Allow"] = "GET, POST"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Hiddify-API-Key"
        return resp
