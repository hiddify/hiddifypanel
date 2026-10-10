"""Config tester (super admins): run every config of a subscription through xray / hiddify-core and time a request through each.

The answer streams as NDJSON (one event per line) so the page shows results as they arrive.
"""

from __future__ import annotations

import json

from apiflask import abort
from flask import Response, request, stream_with_context
from flask.views import MethodView

from hiddifypanel.auth import login_required
from hiddifypanel.models.role import Role
from hiddifypanel.proxy_v3 import config_tester


class ConfigTesterApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self):
        """Config tester: test the configs of a subscription link (streams NDJSON events)"""
        body = request.get_json(silent=True) or {}
        url = str(body.get("url") or "").strip()
        if not body.get("items") and not url.startswith(("http://", "https://")):
            abort(400, "Give the subscription link (http or https)")
        test_url = str(body.get("test_url") or config_tester.DEFAULT_TEST_URL).strip()
        if not test_url.startswith(("http://", "https://")):
            abort(400, "The test URL must be http or https")
        try:
            workers = int(body.get("workers") or 8)
            timeout = int(body.get("timeout") or 10)
            repeats = int(body.get("repeats") or config_tester.DEFAULT_REPEATS)
        except (TypeError, ValueError):
            abort(400, "workers and timeout must be numbers")
        timeout = max(2, min(timeout, 60))
        rerun = body.get("items")
        if isinstance(rerun, list) and rerun:  # test given configs again (no link needed)
            events = config_tester.rerun(rerun, test_url=test_url, workers=workers, timeout=timeout, repeats=repeats)
        else:
            events = config_tester.run(url, str(body.get("user_agent") or ""), test_url=test_url, workers=workers, timeout=timeout, repeats=repeats)
        try:
            first = next(events)  # fetch and parse errors are a normal HTTP error
        except config_tester.TesterError as e:
            abort(400, str(e))

        def generate():
            yield json.dumps(first) + "\n"
            try:
                for ev in events:
                    yield json.dumps(ev) + "\n"
            except config_tester.TesterError as e:
                yield json.dumps({"event": "error", "error": str(e)}) + "\n"

        resp = Response(stream_with_context(generate()), mimetype="application/x-ndjson")
        resp.headers["X-Accel-Buffering"] = "no"
        resp.headers["Cache-Control"] = "no-store"
        return resp
