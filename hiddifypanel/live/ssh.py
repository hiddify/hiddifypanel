"""SSH from the admin panel (super admins): a terminal and a file viewer for any SSH server, over the same transports as the live
channel (live/transport: a stream riding HTTP/3 or HTTP/2, or a WebSocket), served by the panel itself (asyncssh, on the ASGI
event loop).

Nothing is stored: the credentials come with ``connect`` and live as long as the connection. The server's host key is checked
before any credential is sent: the page sends the fingerprint it accepts (``fingerprint``); without it, or when it differs, the
answer is ``hostkey`` {fingerprint} and the page asks the admin (trust on first use, by the admin, every time).

page → server: ``connect`` {host, port, username, password | private_key (+passphrase), fingerprint, cols, rows},
               ``input`` {d}, ``resize`` {cols, rows}, ``ls`` {id, path}, ``read`` {id, path}, ``write`` {id, path, content},
               ``exec`` {id, command}, ``exec_stop`` {id}, ``close``
server → page: ``hostkey`` {fingerprint, algorithm}, ``ready`` {home}, ``data`` {d}, ``exit`` {status}, ``error`` {message},
               ``result`` {id, data}, ``failed`` {id, message}, ``exec_data`` {id, d}, ``exec_done`` {id, status, message}
"""

from __future__ import annotations

import asyncio
import base64
import codecs
import shlex
import stat
import time
from typing import Any

from loguru import logger

from hiddifypanel.asgi_types import Receive, Send
from hiddifypanel.hutils.node.ws_proto import ProtocolError

from .transport import Connection, Gone, JsonCodec, StreamConnection, WebSocketConnection, run_with_stream
from .transport import handle_post as post_to_stream
from .transport.stream import refuse

STREAM_CHANNEL = "admin-ssh"
CONNECT_TIMEOUT = 15.0
#: A file larger than this is not shown (download it with the file's own tools instead).
MAX_VIEW = 2 * 1024 * 1024
MAX_LIST = 5000
#: a file sent from the page, in pieces of at most this (each one a message)
MAX_CHUNK = 512 * 1024
MAX_UPLOAD = 1024 * 1024 * 1024
#: what `extract` opens, by the end of the name: the command (the archive and the folder are quoted in)
ARCHIVES = (
    (".zip", "unzip -o {archive} -d {dest}"),
    (".tar.gz", "tar -xf {archive} -C {dest}"),
    (".tgz", "tar -xf {archive} -C {dest}"),
    (".tar.xz", "tar -xf {archive} -C {dest}"),
    (".txz", "tar -xf {archive} -C {dest}"),
    (".tar.bz2", "tar -xf {archive} -C {dest}"),
    (".tbz2", "tar -xf {archive} -C {dest}"),
    (".tar.zst", "tar --zstd -xf {archive} -C {dest}"),
    (".tar", "tar -xf {archive} -C {dest}"),
    (".gz", "gunzip -kf {archive}"),
)
#: Where the terminal and the files open when the server has it (a Hiddify server), else the user's home.
START_DIR = "/opt/hiddify-manager"


class _MissingTool(RuntimeError):
    """A program the server needs for this (unzip, tar) is not installed there."""


#: what went wrong with a file, for the page to say it plainly: SFTP errors by their class name, then Python's own
_SFTP_CODES = {
    "SFTPPermissionDenied": "permission",
    "SFTPWriteProtect": "readonly",
    "SFTPNoSuchFile": "notFound",
    "SFTPNoSuchPath": "notFound",
    "SFTPFileAlreadyExists": "exists",
    "SFTPNoSpaceOnFilesystem": "noSpace",
    "SFTPQuotaExceeded": "noSpace",
    "SFTPConnectionLost": "connection",
    "SFTPNoConnection": "connection",
    "SFTPFileIsADirectory": "isDir",
    "SFTPNotADirectory": "notDir",
    "SFTPInvalidFilename": "badName",
    "SFTPDirNotEmpty": "notEmpty",
}


def _error_code(e: BaseException) -> str:
    for cls in type(e).__mro__:
        if cls.__name__ in _SFTP_CODES:
            return _SFTP_CODES[cls.__name__]
    if isinstance(e, _MissingTool):
        return "missingTool"
    if isinstance(e, PermissionError):
        return "permission"
    if isinstance(e, FileNotFoundError):
        return "notFound"
    if isinstance(e, FileExistsError):
        return "exists"
    if isinstance(e, TimeoutError):
        return "timeout"
    if isinstance(e, (ConnectionError, EOFError)) or type(e).__name__ in ("DisconnectError", "ConnectionLost", "ChannelOpenError"):
        return "connection"
    if isinstance(e, ValueError) and "too large" in str(e):
        return "tooLarge"
    return "other"


def asyncssh_devnull() -> Any:
    import asyncssh

    return asyncssh.DEVNULL


class _HostKeyCheck:
    """Asked by asyncssh before authenticating: the key must have the fingerprint the admin accepted."""

    def __init__(self, accepted: str) -> None:
        self.accepted = accepted
        self.fingerprint = ""
        self.algorithm = ""

    def client_factory(self) -> Any:
        import asyncssh

        check = self

        class Client(asyncssh.SSHClient):
            def validate_host_public_key(self, host: str, addr: str, port: int, key: asyncssh.SSHKey) -> bool:
                check.fingerprint = key.get_fingerprint("sha256")
                check.algorithm = key.get_algorithm()
                return bool(check.accepted) and check.fingerprint == check.accepted

        return Client


def _int(value: object, default: int, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return default
    try:
        return max(low, min(high, int(value)))
    except ValueError:
        return default


class _Session:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn
        self.ssh: Any = None
        self.process: Any = None
        self.sftp: Any = None
        self.start_dir = False
        #: the signed-in user's uid and groups (what it may do with each file); None: unknown
        self.ids: tuple[int, set[int]] | None = None
        self.ids_task: asyncio.Task[tuple[int, set[int]] | None] | None = None
        self.reader: asyncio.Task[None] | None = None
        #: commands run apart from the terminal (``exec``), by id
        self.jobs: dict[object, Any] = {}

    async def send(self, message: dict[str, Any]) -> None:
        try:
            await self.conn.send(message)
        except Gone:
            pass

    async def connect(self, m: dict[str, Any]) -> None:
        try:
            import asyncssh
        except ImportError:
            return await self.send({"type": "error", "message": "SSH is not available on this panel: the asyncssh package is missing (reinstall the panel)"})

        if self.ssh is not None:
            return await self.send({"type": "error", "message": "already connected"})
        host = str(m.get("host") or "").strip()
        username = str(m.get("username") or "").strip()
        if not host or not username:
            return await self.send({"type": "error", "message": "host and username are needed"})
        check = _HostKeyCheck(str(m.get("fingerprint") or ""))
        options: dict[str, Any] = {
            "port": _int(m.get("port"), 22, 1, 65535),
            "username": username,
            "known_hosts": ([], [], []),  # nothing trusted ahead: every key goes to the check (and an empty tuple would read ~/.ssh)
            "client_factory": check.client_factory(),
            "agent_path": None,
            "client_keys": None,
            "password": None,
            "connect_timeout": CONNECT_TIMEOUT,
            "keepalive_interval": 30,
        }
        if m.get("private_key"):
            try:
                options["client_keys"] = [asyncssh.import_private_key(str(m["private_key"]), m.get("passphrase") or None)]
            except (asyncssh.KeyImportError, ValueError) as e:
                return await self.send({"type": "error", "message": f"the private key could not be read: {e}"})
        if m.get("password"):
            options["password"] = str(m["password"])
        try:
            self.ssh = await asyncssh.connect(host, **options)
        except asyncssh.HostKeyNotVerifiable:
            return await self.send({"type": "hostkey", "fingerprint": check.fingerprint, "algorithm": check.algorithm, "changed": bool(check.accepted)})
        except (OSError, asyncssh.Error, TimeoutError) as e:
            return await self.send({"type": "error", "message": f"{type(e).__name__}: {e}"})
        cols, rows = _int(m.get("cols"), 80, 10, 500), _int(m.get("rows"), 24, 5, 300)
        start = ""
        try:
            self.sftp = await self.ssh.start_sftp_client()
            home = await self.sftp.realpath(".")
            if await self.sftp.isdir(START_DIR):
                home = start = START_DIR
                self.start_dir = True
        except (asyncssh.Error, OSError):
            self.sftp, home = None, ""  # a server without SFTP: the terminal only
        if self.sftp is not None:  # looked up beside the rest (the first listing waits for it)
            self.ids_task = asyncio.get_running_loop().create_task(self._ids())
        # In START_DIR when there is one: the user's own login shell, started there (not a shell of ours).
        command = f'cd {START_DIR} && exec "${{SHELL:-/bin/sh}}" -l' if start else None
        self.process = await self.ssh.create_process(command, term_type="xterm-256color", term_size=(cols, rows), encoding=None)
        logger.info(f"ssh: connected to {username}@{host}:{options['port']} ({check.fingerprint})")
        self.reader = asyncio.get_running_loop().create_task(self._read_output())
        await self.send({"type": "ready", "home": home, "fingerprint": check.fingerprint, "files": self.sftp is not None})

    async def _read_output(self) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        try:
            while True:
                chunk = await self.process.stdout.read(65536)
                if not chunk:
                    break
                await self.send({"type": "data", "d": decoder.decode(chunk)})
            status = self.process.exit_status
        except Exception as e:  # noqa: BLE001  the connection went away
            status = None
            await self.send({"type": "error", "message": f"{type(e).__name__}: {e}"})
        await self.send({"type": "exit", "status": status})

    async def files(self, m: dict[str, Any]) -> None:
        rid = m.get("id")
        if self.sftp is None:
            return await self.send({"type": "failed", "id": rid, "message": "no file access on this server"})
        path = str(m.get("path") or ".")
        try:
            if m["type"] == "ls":
                data = await self._ls(path)
            elif m["type"] == "write":
                data = await self._write(path, m.get("content"))
            elif m["type"] == "create":
                data = await self._create(path)
            elif m["type"] == "mkdir":
                await self.sftp.mkdir(path)
                data = {"path": await self.sftp.realpath(path)}
            elif m["type"] == "put":
                data = await self._put(path, m)
            elif m["type"] == "extract":
                data = await self._extract(path, str(m.get("dest") or ""), bool(m.get("remove")))
            else:
                data = await self._read(path)
        except Exception as e:  # noqa: BLE001  shown on the page
            return await self.send({"type": "failed", "id": rid, "message": f"{type(e).__name__}: {e}", "code": _error_code(e)})
        await self.send({"type": "result", "id": rid, "data": data})

    async def _ids(self) -> tuple[int, set[int]] | None:
        import asyncssh

        try:
            out = await self.ssh.run("id -u; id -G", check=False, timeout=5, stdin=asyncssh_devnull())
            uid, groups = str(out.stdout).split("\n")[:2]
            return int(uid), {int(g) for g in groups.split()}
        except (asyncssh.Error, OSError, TimeoutError, ValueError):
            return None

    def _access(self, a: Any) -> str | None:
        """What the signed-in user may do with an entry, as ``rwx`` (``-`` for each it may not); None when unknown."""
        if self.ids is None or a.permissions is None:
            return None
        mode, (uid, groups) = a.permissions, self.ids
        if uid == 0:  # root reads and writes anything; runs what anyone may run
            return "rw" + ("x" if mode & 0o111 or stat.S_ISDIR(mode) else "-")
        shift = 6 if a.uid == uid else 3 if a.gid in groups else 0
        bits = (mode >> shift) & 7
        return "".join(c if bits & b else "-" for c, b in (("r", 4), ("w", 2), ("x", 1)))

    async def _ls(self, path: str) -> dict[str, Any]:
        if self.ids_task is not None:
            self.ids, self.ids_task = await self.ids_task, None
        real = await self.sftp.realpath(path)
        entries = []
        for name in await self.sftp.readdir(real):
            if name.filename in (".", ".."):
                continue
            a = name.attrs
            mode = a.permissions or 0
            entries.append(
                {
                    "name": name.filename,
                    "dir": stat.S_ISDIR(mode),
                    "link": stat.S_ISLNK(mode),
                    "size": a.size,
                    "mtime": a.mtime,
                    "mode": stat.filemode(mode) if mode else "",
                    "access": self._access(a),
                }
            )
            if len(entries) >= MAX_LIST:
                break
        entries.sort(key=lambda e: (not e["dir"], str(e["name"]).lower()))
        return {"path": real, "entries": entries, "truncated": len(entries) >= MAX_LIST}

    async def _read(self, path: str) -> dict[str, Any]:
        real = await self.sftp.realpath(path)
        attrs = await self.sftp.stat(real)
        if attrs.size is not None and attrs.size > MAX_VIEW:
            return {"path": real, "size": attrs.size, "too_large": True}
        async with self.sftp.open(real, "rb") as f:
            raw = await f.read(MAX_VIEW + 1)
        try:
            return {"path": real, "size": len(raw), "text": raw.decode("utf-8"), "writable": await self._writable(real)}
        except UnicodeDecodeError:
            return {"path": real, "size": len(raw), "base64": base64.b64encode(raw).decode("ascii")}

    async def _writable(self, path: str) -> bool:
        """Whether this user may change the file: opened for appending, nothing written (the file and its time stay as they are);
        the server decides (owner, group, ACLs, a read-only mount)."""
        import asyncssh

        try:
            async with self.sftp.open(path, "ab"):
                return True
        except (asyncssh.Error, OSError):
            return False

    async def _write(self, path: str, content: object) -> dict[str, Any]:
        """Saves a text file (as it is edited in the page); its permissions stay what they were."""
        if not isinstance(content, str):
            raise ValueError("the content of a text file is expected")
        raw = content.encode("utf-8")
        if len(raw) > MAX_VIEW:
            raise ValueError(f"larger than {MAX_VIEW // 1024 // 1024} MB")
        async with self.sftp.open(path, "wb") as f:
            await f.write(raw)
        return {"path": await self.sftp.realpath(path), "size": len(raw)}

    async def _create(self, path: str) -> dict[str, Any]:
        """A new empty file; never one that is there already."""
        if await self.sftp.exists(path):
            raise FileExistsError(f"{path} exists already")
        async with self.sftp.open(path, "wb"):
            pass
        return {"path": await self.sftp.realpath(path), "size": 0}

    async def _put(self, path: str, m: dict[str, Any]) -> dict[str, Any]:
        """One piece of an uploaded file, in order (the page waits for each). Written beside it as ``<name>.part`` and put in
        place with the last piece, so a cut upload never leaves half a file under the real name."""
        offset = _int(m.get("offset"), 0, 0, MAX_UPLOAD)
        raw = base64.b64decode(str(m.get("data") or ""), validate=True)
        if len(raw) > MAX_CHUNK or offset + len(raw) > MAX_UPLOAD:
            raise ValueError("too large")
        part = f"{path}.part"
        if offset == 0:
            if not m.get("overwrite") and await self.sftp.exists(path):
                raise FileExistsError(f"{path} exists already")
            mode = "wb"
        else:
            if (await self.sftp.stat(part)).size != offset:
                raise ValueError("a piece is missing: upload it again")
            mode = "ab"
        async with self.sftp.open(part, mode) as f:
            await f.write(raw)
        if not m.get("last"):
            return {"size": offset + len(raw)}
        if await self.sftp.exists(path):
            await self.sftp.remove(path)
        await self.sftp.rename(part, path)
        return {"path": await self.sftp.realpath(path), "size": offset + len(raw)}

    async def _extract(self, path: str, dest: str, remove: bool = False) -> dict[str, Any]:
        """Unpacks an archive on the server (unzip or tar there) into ``dest`` (made when missing); ``remove``: the archive is
        deleted once it is unpacked (an upload made only to be unpacked)."""
        real = await self.sftp.realpath(path)
        command = next((c for end, c in ARCHIVES if real.lower().endswith(end)), None)
        if command is None:
            raise ValueError("not an archive this can open (zip, tar, tar.gz, tgz, tar.xz, tar.bz2, tar.zst, gz)")
        dest = dest or real.rsplit("/", 1)[0] or "/"
        script = f"mkdir -p {shlex.quote(dest)} && " + command.format(archive=shlex.quote(real), dest=shlex.quote(dest))
        out = await self.ssh.run(script, check=False, timeout=600, stdin=asyncssh_devnull())
        if out.exit_status != 0:
            message = (str(out.stderr or "") or str(out.stdout or "")).strip()[-2000:]
            if out.exit_status == 127:
                raise _MissingTool(command.split()[0])
            raise RuntimeError(message or f"exit {out.exit_status}")
        if remove:
            await self.sftp.remove(real)
        return {"path": real, "dest": dest}

    async def exec(self, m: dict[str, Any]) -> None:
        """A command run on its own (not typed into the terminal): its output as it comes, then its exit status. The page runs
        saved commands on many servers this way and shows each one's result."""
        rid = m.get("id")
        if self.ssh is None:
            return await self.send({"type": "exec_done", "id": rid, "status": None, "message": "not connected"})
        command = str(m.get("command") or "")
        cols, rows = _int(m.get("cols"), 120, 10, 500), _int(m.get("rows"), 40, 5, 300)
        cwd = f"cd {START_DIR} 2>/dev/null; " if self.start_dir else ""
        # In bash when there is one (the login shell may be sh, without `<(...)` and the like), else in sh.
        quoted = shlex.quote(command)
        command = f"if command -v bash >/dev/null 2>&1; then exec bash -c {quoted}; else exec sh -c {quoted}; fi"
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        try:
            # A terminal, so programs keep their colors and progress output; stdin closed: nothing waits for input.
            process = await self.ssh.create_process(cwd + command, term_type="xterm-256color", term_size=(cols, rows), encoding=None, stdin=asyncssh_devnull())
            self.jobs[rid] = process
            while chunk := await process.stdout.read(65536):
                await self.send({"type": "exec_data", "id": rid, "d": decoder.decode(chunk)})
            await process.wait()
            await self.send({"type": "exec_done", "id": rid, "status": process.exit_status})
        except Exception as e:  # noqa: BLE001  the connection went away
            await self.send({"type": "exec_done", "id": rid, "status": None, "message": f"{type(e).__name__}: {e}"})
        finally:
            self.jobs.pop(rid, None)

    def stop_exec(self, rid: object) -> None:
        process = self.jobs.get(rid)
        if process is not None:
            process.terminate()

    def close(self) -> None:
        for process in self.jobs.values():
            process.close()
        if self.reader is not None:
            self.reader.cancel()
        if self.ssh is not None:
            self.ssh.close()
            self.ssh = None

    async def run(self) -> None:
        conn = self.conn
        await self.send({"type": "hello", "server_time": time.time()})
        try:
            while True:
                try:
                    m = conn.poll()
                except ProtocolError:
                    continue
                except Gone:
                    return
                if m is None:
                    await conn.wait()
                    continue
                try:
                    await self._handle(m)
                except Gone:
                    return
                except Exception as e:  # noqa: BLE001  one message failed: say so, the session goes on
                    logger.exception("ssh: a message failed")
                    await self.send({"type": "error", "message": f"{type(e).__name__}: {e}"})
                if m.get("type") == "close":
                    return
        finally:
            self.close()

    async def _handle(self, m: dict[str, Any]) -> None:
        kind = m.get("type")
        if kind == "connect":
            await self.connect(m)
        elif kind == "input" and self.process is not None:
            self.process.stdin.write(str(m.get("d") or "").encode())
        elif kind == "resize" and self.process is not None:
            self.process.change_terminal_size(_int(m.get("cols"), 80, 10, 500), _int(m.get("rows"), 24, 5, 300))
        elif kind == "exec":
            asyncio.get_running_loop().create_task(self.exec(m))
        elif kind == "exec_stop":
            self.stop_exec(m.get("id"))
        elif kind in ("ls", "read", "write", "create", "mkdir", "put", "extract"):
            asyncio.get_running_loop().create_task(self.files(m))
        elif kind not in ("ping", "close"):
            await self.send({"type": "error", "message": f"unknown message {kind!r}"})


async def _super_admin(flask_app: Any, proxy_path: str, scope: dict[str, Any]) -> int | None:
    """None when a signed-in super admin opens it, else the close code that refuses it."""
    from .channel import CLOSE_UNAUTHORIZED, _authenticate

    who = await _authenticate(flask_app, proxy_path, scope)
    if isinstance(who, int):
        return who
    return None if who[1].get("mode") == "super_admin" else CLOSE_UNAUTHORIZED


async def handle(flask_app: Any, proxy_path: str, scope: dict[str, Any], receive: Receive, send: Send) -> None:
    """Over a WebSocket (``/<admin path>/api/v2/admin/ssh/``)."""
    if (await receive())["type"] != "websocket.connect":
        return
    if (refused := await _super_admin(flask_app, proxy_path, scope)) is not None:
        await send({"type": "websocket.close", "code": refused})
        return
    await send({"type": "websocket.accept"})
    conn = WebSocketConnection(receive, send, JsonCodec(), frozenset({"ping"}))
    try:
        await _Session(conn).run()
    finally:
        await conn.close()


async def handle_stream(flask_app: Any, proxy_path: str, scope: dict[str, Any], receive: Receive, send: Send) -> None:
    """Over a streamed response plus POSTs (``…/admin/ssh/stream/``, ``…/admin/ssh/<session>/``): rides HTTP/3 or HTTP/2."""
    if (refused := await _super_admin(flask_app, proxy_path, scope)) is not None:
        return await refuse(send, 401 if refused != 4401 else 403, "super admins only")
    conn = StreamConnection(STREAM_CHANNEL, JsonCodec(), frozenset({"ping"}))
    await run_with_stream(conn, asyncio.get_running_loop().create_task(_Session(conn).run()), receive, send)


async def handle_post(scope: dict[str, Any], receive: Receive, send: Send, session: str) -> None:
    from .channel import _origin_ok

    await post_to_stream(scope, receive, send, STREAM_CHANNEL, session, allowed=_origin_ok)
