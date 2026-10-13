"""The panel's ASGI app (Flask and the nodes' WebSocket) served in this process, for a debugger:

    python -m hiddifypanel.apps.asgi_dev --port 9000

The service runs ``granian --interface asgi hiddifypanel.apps.asgi_app:app``, which serves from worker processes; here granian's
embedded server runs on this process's event loop, so breakpoints work in the views, the a2wsgi threads and the WebSocket
code alike. There is no reload on file changes (granian has none in embedded mode): restart the debug session.

HTTP mode stays ``auto`` (the granian default): the same port accepts HTTP/1.1 and cleartext HTTP/2 prior knowledge, which
is what HAProxy sends with ``proto h2``. HTTP/2-only (``--http 2``) would refuse HTTP/1 and drop WebSockets.
"""

from __future__ import annotations

import argparse
import asyncio
import signal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--threads", type=int, default=None, help="Flask request threads (default: HIDDIFY_PANEL_THREADS or 10)")
    parser.add_argument("--no-node-client", action="store_true", help="do not open the WebSocket to the parent when this panel is a node")
    args = parser.parse_args()

    from granian.constants import Interfaces
    from granian.server.embed import Server

    from hiddifypanel import create_app
    from hiddifypanel.asgi import build_asgi

    # create_app_wsgi() tells web from CLI by granian's name in argv: here it is neither, so ask for the web app.
    app = build_asgi(create_app(app_mode="web"), threads=args.threads, node_client=not args.no_node_client)
    server = Server(app, address=args.host, port=args.port, interface=Interfaces.ASGI, websockets=True, log_access=True)

    async def serve() -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, server.stop)
        await server.serve()

    asyncio.run(serve())


if __name__ == "__main__":
    main()
