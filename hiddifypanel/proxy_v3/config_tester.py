"""Config tester: fetch a subscription, run each config in its own xray / hiddify-core / mihomo process (a local SOCKS port each, in parallel) and time requests through it.

* xray subscription (JSON config or list of configs): every config runs in ``xray`` with its inbounds replaced by one SOCKS inbound.
* hiddify-core / sing-box subscription (JSON with ``outbounds``): every proxy outbound runs alone in ``hiddify-core srun``.
* Clash Meta / Mihomo YAML (``proxies`` list): every proxy runs alone in ``mihomo``.
* share links (also base64): each one goes through ``hiddify-core parse`` on its own.
* anything else: ``hiddify-core parse`` turns it into a hiddify-core config first.

Errors that belong to the input are ``TesterError`` (their text is shown to the admin); one config that fails never stops the others.
"""

from __future__ import annotations

import base64
import binascii
import copy
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote

import requests

from hiddifypanel.proxy_v3.config_tester_types import (
    App,
    DoneEvent,
    Event,
    Fetched,
    FetchedHttp,
    FetchedPasted,
    Item,
    ItemInfo,
    Json,
    JsonObject,
    KeepAliveEvent,
    Kind,
    PingOut,
    PingResult,
    ResultEvent,
    Source,
    StartEvent,
    TesterError,
    obj,
    objects,
    text,
)
from hiddifypanel.proxy_v3.outbound_custom import CLASH_BIN, CORE_BIN, CORE_DIR, XRAY_BIN

__all__ = ["DEFAULT_REPEATS", "DEFAULT_TEST_URL", "TesterError", "rerun", "run"]

MAX_CONFIGS = 300
MAX_BODY = 20_000_000
RAW_LIMIT = 500_000
FETCH_TIMEOUT = 30
STARTUP_TIMEOUT = 8
MAX_REPEATS = 10
MAX_WORKERS = 32
DEFAULT_UA = "HiddifyNext/5.0.0 (linux) like ClashMeta v2ray sing-box"
DEFAULT_REPEATS = 3
DEFAULT_TEST_URL = "https://www.gstatic.com/generate_204"
PORT_RANGE = (21000, 29000)
LOG_HEAD = 100_000
LOG_TAIL = 200_000
NO_CONFIG = "hiddify-core could not find any config in the subscription: "

#: sing-box outbounds that route or group other outbounds and are not a proxy themselves.
_NOT_PROXY = {"direct", "block", "dns", "selector", "urltest", "fallback", "loadbalance"}
_XRAY_NOT_PROXY = {"freedom", "blackhole", "dns", "loopback"}
_LINK = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


# --------------------------------------------------------------------------- fetch and split


def fetch(url: str, user_agent: str) -> tuple[str, FetchedHttp]:
    """The subscription text and what was asked / answered (so the page can show the user agent really sent)."""
    ua = user_agent.strip() or DEFAULT_UA
    try:
        res = requests.get(url, headers={"User-Agent": ua}, timeout=FETCH_TIMEOUT, stream=True)
        res.raise_for_status()
        body = res.raw.read(MAX_BODY + 1, decode_content=True)
    except Exception as e:  # requests, urllib3 and the network all have their own errors: all of them are "could not fetch"
        raise TesterError(f"Could not fetch the subscription: {e}") from None
    if len(body) > MAX_BODY:
        raise TesterError("The subscription is too large")
    info = FetchedHttp(user_agent=ua, status=res.status_code, content_type=res.headers.get("Content-Type", ""), bytes=len(body))
    return body.decode("utf-8", errors="replace"), info


def _parse_json(raw: str) -> Json:
    try:
        value: Json = json.loads(raw)
    except (ValueError, RecursionError):
        return None
    return value


def _is_xray(cfg: Json) -> bool:
    return any("protocol" in o for o in objects(obj(cfg).get("outbounds")))


def _is_core(cfg: Json) -> bool:
    config = obj(cfg)
    return any("type" in o for o in [*objects(config.get("outbounds")), *objects(config.get("endpoints"))])


def _is_clash(cfg: Json) -> bool:
    """True when the value is a Clash / Mihomo document with at least one named proxy."""
    proxies = obj(cfg).get("proxies")
    return isinstance(proxies, list) and any(isinstance(p, dict) and text(p.get("name")) and text(p.get("type")) for p in proxies)


def _parse_clash(raw: str) -> JsonObject | None:
    """Clash YAML (or JSON) with a ``proxies`` list; ``None`` when the text is not that."""
    import yaml

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) and _is_clash(data) else None


def _clash_items(cfg: JsonObject) -> list[Item]:
    items: list[Item] = []
    for p in objects(cfg.get("proxies")):
        name = text(p.get("name"))
        if not name or not text(p.get("type")):
            continue
        items.append(Item(len(items), name, "clash", {"proxy": copy.deepcopy(p)}, tag=name, original=copy.deepcopy(p)))
        if len(items) >= MAX_CONFIGS:
            break
    return items


def _xray_name(cfg: JsonObject, i: int) -> str:
    if remarks := text(cfg.get("remarks")):
        return remarks
    for o in objects(cfg.get("outbounds")):
        protocol = text(o.get("protocol"))
        if protocol and protocol not in _XRAY_NOT_PROXY:
            return f"{protocol} {i + 1}"
    return f"config {i + 1}"


def _xray_item(index: int, cfg: JsonObject) -> Item:
    return Item(index, _xray_name(cfg, index), "xray", cfg, original=cfg)


def _decode_base64_links(raw: str) -> str:
    """The text of a base64 body of links; the text itself when it is not one."""
    stripped = raw.strip()
    try:
        decoded = base64.b64decode(stripped + "=" * (-len(stripped) % 4)).decode("utf-8")
    except (binascii.Error, ValueError):  # not base64, or not text (UnicodeDecodeError is a ValueError)
        return raw
    return decoded if "://" in decoded else raw


_APP_NAMES = {"hiddify": "Hiddify", "xray": "Xray", "clash": "Clash Mihomo"}
_FORMAT_NAMES = {"xray": "xray JSON", "core": "sing-box JSON", "clash": "Clash YAML", "parsed": "share links"}
#: What each client reads; share links are converted for it (Clash Mihomo does not take them).
_APP_FORMATS: dict[str, set[str]] = {"hiddify": {"core", "clash", "parsed"}, "xray": {"xray", "parsed"}, "clash": {"clash"}}


def _format_of(raw: str) -> Source:
    data = _parse_json(raw)
    if isinstance(data, list) and any(_is_xray(c) for c in objects(data)):
        return "xray"
    if isinstance(data, dict):
        if _is_xray(data):
            return "xray"
        if _is_core(data):
            return "core"
        if _is_clash(data):
            return "clash"
    if data is None and _parse_clash(raw):
        return "clash"
    return "parsed"


def split(raw: str, app: App | None = None) -> tuple[Source, list[Item], JsonObject | None]:
    """``(source, items, parsed)``: ``xray``, ``core``, ``clash``, or ``parsed`` (links converted by hiddify-core; that result is ``parsed``).

    With ``app``, a format that client cannot read is an error; links are converted to xray JSON for ``xray``."""
    if app is not None:
        fmt = _format_of(raw)
        if fmt not in _APP_FORMATS[app]:
            raise TesterError(f"{_APP_NAMES[app]} does not support this subscription ({_FORMAT_NAMES[fmt]})")
        if app == "xray" and fmt == "parsed":
            lines = _link_lines(_decode_base64_links(raw))
            if not lines:
                raise TesterError(f"{_APP_NAMES[app]} does not support this subscription")
            items, parsed = parse_links(lines, xray=True)
            return "parsed", items, parsed
    data = _parse_json(raw)
    if isinstance(data, list):
        configs = [c for c in objects(data) if _is_xray(c)]
        if configs:
            return "xray", [_xray_item(i, c) for i, c in enumerate(configs[:MAX_CONFIGS])], None
    elif isinstance(data, dict):
        if _is_xray(data):
            return "xray", [_xray_item(0, data)], None
        if _is_core(data):
            return "core", _core_items(data), None
        if _is_clash(data):
            return "clash", _clash_items(data), None
    # Clash Meta YAML (not JSON), then links / hiddify-core parse
    if data is None:
        if clash := _parse_clash(raw):
            return "clash", _clash_items(clash), None
    body = _decode_base64_links(raw) if data is None else raw
    lines = _link_lines(body)
    if lines:  # one link at a time: hiddify-core joins a link into the next line when it ends oddly, and one unknown link must not fail the rest
        items, parsed = parse_links(lines)
        return "parsed", items, parsed
    parsed_config = parse_with_core(body)
    return "parsed", _core_items(parsed_config), parsed_config


def _core_items(cfg: JsonObject) -> list[Item]:
    sections = ("outbounds", "endpoints")
    by_tag: dict[str, tuple[str, JsonObject]] = {}
    for sec in sections:
        for o in objects(cfg.get(sec)):
            if tag := text(o.get("tag")):
                by_tag[tag] = (sec, o)
    items: list[Item] = []
    for section in sections:
        for o in objects(cfg.get(section)):
            tag = text(o.get("tag"))
            if not tag or text(o.get("type")) in _NOT_PROXY:
                continue
            # the entry and the chain it dials through (detour); nothing else needs to run
            base: JsonObject = {}
            seen: set[str] = set()
            current: tuple[str, JsonObject] | None = (section, o)
            while current is not None and text(current[1].get("tag")) not in seen:
                sec, node = current
                seen.add(text(node.get("tag")))
                chain = base.setdefault(sec, [])
                if isinstance(chain, list):
                    chain.append(copy.deepcopy(node))
                current = by_tag.get(text(node.get("detour")))
            items.append(Item(len(items), tag, "core", base, tag=tag, original=o))
            if len(items) >= MAX_CONFIGS:
                return items
    return items


def _link_lines(raw: str) -> list[str]:
    """The lines when the text is nothing but share links (comments aside), else none."""
    lines = [line.strip() for line in raw.splitlines() if line.strip() and not line.strip().startswith(("#", "//"))]
    return lines if lines and all(_LINK.match(line) for line in lines) else []


def _clean(raw: str) -> str:
    return _ANSI.sub("", raw)


def _core_error(message: str) -> str:
    """The line of hiddify-core's complaint that says what is wrong."""
    lines = [_clean(line).strip() for line in message.splitlines() if line.strip()]
    useful = [line for line in lines if not line.startswith(("Error in", "FATAL", "Convert using")) and "unable to determine" not in line]
    return (useful or lines or ["could not be parsed"])[0][:200]


def _xray_error(message: str) -> str:
    """What ``parse --xray`` says is wrong (its FATAL line, without the prefix)."""
    lines = [_clean(line).strip() for line in message.splitlines() if line.strip()]
    fatal = [line.removeprefix("FATAL").split("]", 1)[-1].strip() for line in lines if line.startswith("FATAL")]
    return (fatal or lines or ["could not be parsed"])[-1][:200]


def _failed_link(index: int, name: str, line: str, error: str) -> Item:
    return Item(index, name, "core", {}, original={"link": line}, error=error)


def _link_name(line: str) -> str:
    name = unquote(line.split("#", 1)[1]).strip() if "#" in line else ""
    return name or line[:60]


def _parse_link_xray(index: int, line: str) -> Item:
    name = _link_name(line)
    try:
        cfg = parse_with_core(line, xray=True)
    except TesterError as e:
        return Item(index, name, "xray", {}, original={"link": line}, error=str(e).removeprefix(NO_CONFIG))
    proxies = [o for o in objects(cfg.get("outbounds")) if text(o.get("protocol")) not in _XRAY_NOT_PROXY]
    if not proxies:
        return Item(index, name, "xray", {}, original={"link": line}, error="nothing to test in this link")
    outbound = proxies[0]
    return Item(index, text(outbound.get("tag")) or name, "xray", {"outbounds": [outbound]}, original=outbound)


def _parse_link(index: int, line: str) -> Item:
    name = _link_name(line)
    try:
        cfg = parse_with_core(line)
    except TesterError as e:
        return _failed_link(index, name, line, str(e).removeprefix(NO_CONFIG))
    got = _core_items(cfg)
    if not got:
        return _failed_link(index, name, line, "nothing to test in this link")
    item = got[0]
    item.index = index
    if item.tag:  # hiddify-core numbers tags by their place in what it was given: here, the place in the whole list
        new = re.sub(r" § \d+$", f" § {index}", item.tag)
        for sec in ("outbounds", "endpoints"):
            for o in objects(item.config.get(sec)):
                if text(o.get("tag")) == item.tag:
                    o["tag"] = new
        if isinstance(item.original, dict):
            item.original["tag"] = new
        item.name = item.tag = new
    return item


def parse_links(lines: list[str], xray: bool = False) -> tuple[list[Item], JsonObject]:
    """Each link through ``hiddify-core parse`` (``--xray``: to xray JSON) a few at once. A link that fails is an item that failed, in its place."""
    chosen = lines[:MAX_CONFIGS]
    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(_parse_link_xray if xray else _parse_link, range(len(chosen)), chosen))
    working = [i for i in items if not i.error]
    parsed: JsonObject = {}
    if xray:
        if outbounds := [i.original for i in working]:
            parsed["outbounds"] = outbounds
        return items, parsed
    if outbounds := [i.original for i in working if i.config.get("outbounds")]:
        parsed["outbounds"] = outbounds
    if endpoints := [i.original for i in working if i.config.get("endpoints") and not i.config.get("outbounds")]:
        parsed["endpoints"] = endpoints
    return items, parsed


def parse_with_core(raw: str, xray: bool = False) -> JsonObject:
    """The hiddify-core (sing-box) config of the text; with ``xray``, the xray JSON of share links (``parse --xray``)."""
    if not CORE_BIN.exists():
        raise TesterError("hiddify-core is not installed")
    with tempfile.TemporaryDirectory(prefix="cfgtest-parse-") as tmp:
        src = Path(tmp) / "sub.txt"
        src.write_text(raw, encoding="utf-8")
        cmd = [str(CORE_BIN), "parse", str(src), *(["--xray"] if xray else []), "-D", tmp]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(CORE_DIR if CORE_DIR.is_dir() else tmp), check=False)
        except subprocess.TimeoutExpired:
            raise TesterError("hiddify-core parse timed out") from None
        except OSError as e:
            raise TesterError(f"hiddify-core could not be run: {e}") from None
    start = res.stdout.find("{")
    cfg = _parse_json(res.stdout[start:]) if start >= 0 else None
    if xray:
        if not isinstance(cfg, dict) or not _is_xray(cfg):
            raise TesterError(NO_CONFIG + _xray_error(res.stderr or res.stdout))
        return cfg
    if not isinstance(cfg, dict) or not _is_core(cfg):
        raise TesterError(NO_CONFIG + _core_error(res.stderr or res.stdout))
    return cfg


# --------------------------------------------------------------------------- run one


def _free_port(taken: set[int], lock: threading.Lock) -> int:
    """A local port nothing listens on, reserved in ``taken`` until the caller discards it."""
    for _ in range(200):
        port = PORT_RANGE[0] + int.from_bytes(os.urandom(2), "big") % (PORT_RANGE[1] - PORT_RANGE[0])
        with lock:
            if port in taken:
                continue
            with socket.socket() as s:
                try:
                    s.bind(("127.0.0.1", port))
                except OSError:  # in use
                    continue
            taken.add(port)
            return port
    raise TesterError("No free local port")


def build_config(item: Item, port: int) -> JsonObject:
    """The config as it runs: the same, with one local SOCKS inbound and logs on."""
    cfg = copy.deepcopy(item.config)
    if item.kind == "xray":
        cfg["log"] = {"loglevel": "debug"}
        cfg["inbounds"] = [{"tag": "test-in", "listen": "127.0.0.1", "port": port, "protocol": "socks", "settings": {"udp": False}}]
        for key in ("routing", "api", "stats", "policy"):  # without routing the first outbound is the default
            cfg.pop(key, None)
        return cfg
    if item.kind == "clash":
        # First run stores {"proxy": <one proxy>}; a UI retest sends the previous run_config
        # (full mihomo doc with "proxies": [...]). Without unwrapping, proxies[0] is only
        # {name} and mihomo fatals with "proxy 0: missing type".
        proxy = obj(cfg.get("proxy"))
        if not text(proxy.get("type")):
            for candidate in objects(cfg.get("proxies")):
                if text(candidate.get("type")):
                    proxy = candidate
                    break
        proxy = copy.deepcopy(proxy)
        name = text(proxy.get("name")) or item.name or "proxy"
        proxy["name"] = name
        return {
            "mixed-port": port,
            "allow-lan": False,
            "bind-address": "127.0.0.1",
            "mode": "rule",
            "log-level": "debug",
            "ipv6": True,
            "proxies": [proxy],
            "proxy-groups": [{"name": "PROXY", "type": "select", "proxies": [name]}],
            "rules": ["MATCH,PROXY"],
        }
    outbounds = objects(cfg.get("outbounds"))
    have = {text(o.get("tag")) for o in outbounds}
    extra: list[Json] = [{"tag": tag, "type": "direct"} for tag in ("direct", "freedom") if tag not in have]
    cfg["outbounds"] = [*outbounds, *extra]
    cfg["log"] = {"level": "trace", "timestamp": True}
    cfg["inbounds"] = [{"type": "mixed", "tag": "test-in", "listen": "127.0.0.1", "listen_port": port}]
    cfg["route"] = {"final": item.tag, "auto_detect_interface": False}
    return cfg


def _wait_port(port: int, proc: subprocess.Popen[bytes], timeout: float) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if proc.poll() is not None:
            return False
        with socket.socket() as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.15)
    return False


def _last_line(raw: str) -> str:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return (lines[-1] if lines else "")[-300:]


def _read_log(path: Path) -> str:
    """The core's trace log without colours; a huge one keeps its start and its end."""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) > LOG_HEAD + LOG_TAIL:
        data = data[:LOG_HEAD] + b"\n... (log cut) ...\n" + data[-LOG_TAIL:]
    return _clean(data.decode("utf-8", errors="replace"))


def _ping(port: int, test_url: str, timeout: int) -> PingResult:
    """One request through the local SOCKS port."""
    cmd = ["curl", "-sS", "-v", "-o", "/dev/null", "-x", f"socks5h://127.0.0.1:{port}", "--max-time", str(timeout), "-w", "%{http_code} %{time_connect} %{time_starttransfer} %{time_total}", test_url]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5, check=False)
    except subprocess.TimeoutExpired:
        return PingResult(ok=False, error="timeout")
    except OSError as e:
        return PingResult(ok=False, error=f"curl could not be run: {e}")
    parts = res.stdout.split()
    if res.returncode == 0 and len(parts) == 4 and parts[0].startswith(("2", "3")):
        try:
            return PingResult(ok=True, status=int(parts[0]), connect_ms=int(float(parts[1]) * 1000), ttfb_ms=int(float(parts[2]) * 1000), delay_ms=int(float(parts[3]) * 1000), curl_log=res.stderr)
        except ValueError:
            pass  # curl wrote something else than numbers: counted as a failure below
    err_lines = [line for line in res.stderr.splitlines() if line.startswith("curl:")]
    return PingResult(ok=False, error=(err_lines[-1] if err_lines else "") or (f"HTTP {parts[0]}" if parts else "failed"), curl_log=res.stderr)


def _ping_out(p: PingResult) -> PingOut:
    out = PingOut(ok=p.ok)
    if p.ok:
        out["delay_ms"] = p.delay_ms
    else:
        out["error"] = p.error
    return out


def _failed_result(item: Item, error: str, *, log: str = "") -> ResultEvent:
    """A result for a config that did not get to run (or that no test could pass)."""
    result = ResultEvent(event="result", index=item.index, name=item.name, kind=item.kind, ok=False, tag=item.tag, original=item.original, error=error, pings=[PingOut(ok=False, error=error)], tries=1, ok_count=0)
    if log:
        result["log"] = log
    return result


def run_one(item: Item, port: int, test_url: str, timeout: int, repeats: int = DEFAULT_REPEATS) -> ResultEvent:
    """Start the config in its core, send ``repeats`` requests through it, stop it. The result tells how it went; it never raises."""
    result = ResultEvent(event="result", index=item.index, name=item.name, kind=item.kind, ok=False, tag=item.tag, original=item.original)
    tmp = tempfile.mkdtemp(prefix="cfgtest-")
    proc: subprocess.Popen[bytes] | None = None
    log_path = Path(tmp) / "core.log"
    curl_logs: list[str] = []
    try:
        run_cfg = build_config(item, port)
        result["run_config"] = run_cfg
        if item.kind == "clash":
            import yaml

            path = Path(tmp) / "config.yaml"
            path.write_text(yaml.dump(run_cfg, sort_keys=False, allow_unicode=True) or "", encoding="utf-8")
            binary = CLASH_BIN
            cmd = [str(binary), "-f", str(path), "-d", tmp]
            cwd = tmp
        else:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(run_cfg), encoding="utf-8")
            binary = XRAY_BIN if item.kind == "xray" else CORE_BIN
            cmd = [str(binary), "run", "-c", str(path)] if item.kind == "xray" else [str(binary), "srun", "-c", str(path), "-D", tmp]
            cwd = str(CORE_DIR) if item.kind == "core" and CORE_DIR.is_dir() else tmp
        if not binary.exists():
            result["error"] = f"{binary.name} is not installed"
            return result
        with log_path.open("wb") as log_file:  # a file, not a pipe: a trace log would fill the pipe and stop the core
            proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, cwd=cwd)
        if not _wait_port(port, proc, STARTUP_TIMEOUT):
            result["error"] = ("config rejected: " + _last_line(_read_log(log_path))) if proc.poll() is not None else "the core did not start in time"
            return result
        started = time.monotonic()
        pings: list[PingResult] = []
        for n in range(max(1, min(repeats, MAX_REPEATS))):
            pings.append(_ping(port, test_url, timeout))
            curl_logs.append(f"----- test {n + 1} -----\n{pings[-1].curl_log}")
        good = [p for p in pings if p.ok]
        result["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        result["pings"] = [_ping_out(p) for p in pings]
        result["tries"] = len(pings)
        result["ok_count"] = len(good)
        if good:
            result["ok"] = True
            result["delay_ms"] = round(sum(p.delay_ms for p in good) / len(good))
            result["status"], result["connect_ms"], result["ttfb_ms"] = good[-1].status, good[-1].connect_ms, good[-1].ttfb_ms
        else:
            result["error"] = pings[-1].error or "failed"
        return result
    except Exception as e:  # one bad config must never stop the others  # noqa: BLE001
        result["error"] = str(e)[:300] or type(e).__name__
        return result
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass  # it is killed; the system collects it
        log = _read_log(log_path)
        if curl_logs:
            log += "\n\n===== curl =====\n" + "\n".join(curl_logs)
        result["log"] = log
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- the whole run


def run(
    url: str,
    user_agent: str,
    *,
    content: str | None = None,
    app: App | None = None,
    test_url: str = DEFAULT_TEST_URL,
    workers: int = 8,
    timeout: int = 10,
    repeats: int = DEFAULT_REPEATS,
    should_stop: Callable[[], bool] | None = None,
) -> Iterator[Event]:
    """Events: ``start`` (once), a ``result`` per config, ``ping`` while nothing finishes, then ``done``."""
    fetched: Fetched
    if content is not None:  # pasted: nothing to fetch
        size = len(content.encode())
        if size > MAX_BODY:
            raise TesterError("The contents are too large")
        raw, fetched = content, FetchedPasted(pasted=True, bytes=size)
    else:
        raw, fetched = fetch(url, user_agent)
    source, items, parsed = split(raw, app)
    if not items:
        raise TesterError("No config found in the subscription")
    yield StartEvent(
        event="start",
        source=source,
        total=len(items),
        fetched=fetched,
        raw=raw[:RAW_LIMIT],
        parsed=parsed,
        items=[ItemInfo(index=i.index, name=i.name, kind=i.kind) for i in items],
    )
    yield from _execute(items, test_url, workers, timeout, repeats, should_stop)


def _rerun_item(raw: object, split_cache: dict[str, list[Item]], app: App | None = None) -> Item:
    """One config to test again, as the page sends it: ``{index, name, kind, tag, original, config, content}``."""
    entry = obj(raw)
    index = entry.get("index")
    if isinstance(index, bool) or not isinstance(index, int):
        raise TesterError("Bad config to test again: it has no place number")
    name = text(entry.get("name"))
    edited = text(entry.get("content"))
    if edited.strip():  # the link or the JSON was edited: test what it says now
        lines = _link_lines(edited)
        if lines and app == "xray":
            item = _parse_link_xray(index, lines[0])
        elif lines and app != "clash":
            item = _parse_link(index, lines[0])
        else:
            if edited not in split_cache:
                split_cache[edited] = split(edited, app)[1]
            same = next((i for i in split_cache[edited] if i.index == index), None)
            if same is None:
                raise TesterError("The edited subscription has no config in the place of this one")
            item = copy.copy(same)
        item.index = index
        item.name = name or item.name
        return item
    kind = entry.get("kind")
    config = entry.get("config")
    if kind not in ("xray", "core", "clash") or not isinstance(config, dict):
        raise TesterError("Bad config to test again")
    original = entry.get("original")
    typed_kind: Kind = "xray" if kind == "xray" else "clash" if kind == "clash" else "core"
    return Item(index, name, typed_kind, config, tag=text(entry.get("tag")), original=config if original is None else original)


def rerun(
    raw_items: list[object],
    *,
    app: App | None = None,
    test_url: str = DEFAULT_TEST_URL,
    workers: int = 8,
    timeout: int = 10,
    repeats: int = DEFAULT_REPEATS,
    should_stop: Callable[[], bool] | None = None,
) -> Iterator[Event]:
    """Test configs again (the ones the page has from an earlier result, or edited)."""
    split_cache: dict[str, list[Item]] = {}
    items = [_rerun_item(raw, split_cache, app) for raw in raw_items[:MAX_CONFIGS]]
    yield from _execute(items, test_url, workers, timeout, repeats, should_stop)


def _execute(items: list[Item], test_url: str, workers: int, timeout: int, repeats: int, should_stop: Callable[[], bool] | None = None) -> Iterator[Event]:
    # Finished tests are handed over with a condition, not a queue with a timeout: that raises an exception on every quiet
    # moment, and a debugger stopping on exceptions would freeze the whole panel there.
    results: deque[ResultEvent] = deque()
    cond = threading.Condition()
    taken: set[int] = set()
    taken_lock = threading.Lock()

    def put(ev: ResultEvent) -> None:
        with cond:
            results.append(ev)
            cond.notify()

    def job(item: Item) -> None:
        try:
            if item.error:  # nothing to run: it is its own failure
                put(_failed_result(item, item.error, log=item.error))
                return
            port = _free_port(taken, taken_lock)
            try:
                put(run_one(item, port, test_url, timeout, repeats))
            finally:
                with taken_lock:
                    taken.discard(port)
        except Exception as e:  # whatever happens, the page gets a result for it and does not wait for it  # noqa: BLE001
            put(_failed_result(item, str(e) or type(e).__name__))

    pool = ThreadPoolExecutor(max_workers=max(1, min(workers, MAX_WORKERS)))
    try:
        for item in items:
            pool.submit(job, item)
        done = 0
        while done < len(items):
            if should_stop is not None and should_stop():  # asked to stop: leave through the end below, nothing not started will start
                break
            with cond:
                if not results:
                    cond.wait(5)
                ev = results.popleft() if results else None
            if ev is None:  # nothing finished for a while: a line anyway, so nothing takes the test for dead
                yield KeepAliveEvent(event="ping")
            else:
                done += 1
                yield ev
    finally:  # also when the reader went away: stop what has not started
        pool.shutdown(wait=False, cancel_futures=True)
    yield DoneEvent(event="done")
