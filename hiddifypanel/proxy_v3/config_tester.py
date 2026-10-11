"""Config tester: fetch a subscription, run each config in its own xray / hiddify-core process (a local SOCKS port each, in parallel) and time a request through it.

* xray subscription (JSON config or list of configs): every config runs in ``xray`` with its inbounds replaced by one SOCKS inbound.
* hiddify-core / sing-box subscription (JSON with ``outbounds``): every proxy outbound runs alone in ``hiddify-core srun``.
* anything else (links, base64, clash...): ``hiddify-core parse`` turns it into a hiddify-core config first.
"""

from __future__ import annotations

import base64
import copy
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Any, Iterator

import requests

from hiddifypanel.proxy_v3.outbound_custom import CORE_BIN, CORE_DIR, XRAY_BIN

MAX_CONFIGS = 300
MAX_BODY = 20_000_000
RAW_LIMIT = 500_000
FETCH_TIMEOUT = 30
STARTUP_TIMEOUT = 8
DEFAULT_UA = "HiddifyNext/5.0.0 (linux) like ClashMeta v2ray sing-box"
DEFAULT_REPEATS = 3
DEFAULT_TEST_URL = "https://www.gstatic.com/generate_204"
PORT_RANGE = (21000, 29000)

#: sing-box outbounds that route or group other outbounds and are not a proxy themselves.
_NOT_PROXY = {"direct", "block", "dns", "selector", "urltest", "fallback", "loadbalance"}


class TesterError(Exception):
    pass


@dataclass
class Item:
    index: int
    name: str
    kind: str  # xray | core
    config: dict[str, Any]
    tag: str = ""  # core: the outbound / endpoint to route to
    original: Any = None  # the config as the subscription has it


# --------------------------------------------------------------------------- fetch and split


def fetch(url: str, user_agent: str) -> tuple[str, dict[str, Any]]:
    """The subscription text and what was asked / answered (so the page can show the user agent really sent)."""
    ua = user_agent.strip() or DEFAULT_UA
    try:
        res = requests.get(url, headers={"User-Agent": ua}, timeout=FETCH_TIMEOUT, stream=True)
        res.raise_for_status()
        body = res.raw.read(MAX_BODY + 1, decode_content=True)
    except requests.RequestException as e:
        raise TesterError(f"Could not fetch the subscription: {e}") from None
    if len(body) > MAX_BODY:
        raise TesterError("The subscription is too large")
    info = {"user_agent": ua, "status": res.status_code, "content_type": res.headers.get("Content-Type", ""), "bytes": len(body)}
    return body.decode("utf-8", errors="replace"), info


def _json(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return None


def _is_xray(cfg: Any) -> bool:
    return isinstance(cfg, dict) and any(isinstance(o, dict) and "protocol" in o for o in cfg.get("outbounds") or [])


def _is_core(cfg: Any) -> bool:
    return isinstance(cfg, dict) and any(isinstance(o, dict) and "type" in o for o in [*(cfg.get("outbounds") or []), *(cfg.get("endpoints") or [])])


def _xray_name(cfg: dict[str, Any], i: int) -> str:
    if cfg.get("remarks"):
        return str(cfg["remarks"])
    for o in cfg.get("outbounds") or []:
        if o.get("protocol") not in ("freedom", "blackhole", "dns", "loopback"):
            return f"{o.get('protocol')} {i + 1}"
    return f"config {i + 1}"


def split(text: str) -> tuple[str, list[Item], dict[str, Any] | None]:
    """``(source kind, items, parsed)``: ``xray``, ``core`` or ``parsed`` (links converted by hiddify-core, that result is ``parsed``)."""
    data = _json(text)
    if data is None:
        stripped = text.strip()
        try:  # a base64 body of links
            decoded = base64.b64decode(stripped + "=" * (-len(stripped) % 4), validate=False).decode("utf-8")
            if "://" in decoded:
                text = decoded
        except Exception:
            pass
    if isinstance(data, dict) and not _is_xray(data) and not _is_core(data):
        data = None
    if isinstance(data, list):
        configs = [c for c in data if _is_xray(c)]
        if configs:
            return "xray", [Item(i, _xray_name(c, i), "xray", c, original=c) for i, c in enumerate(configs[:MAX_CONFIGS])], None
        data = None
    if data is not None and _is_xray(data):
        return "xray", [Item(0, _xray_name(data, 0), "xray", data, original=data)], None
    if data is not None:
        return "core", _core_items(data), None
    parsed = parse_with_core(text)
    return "parsed", _core_items(parsed), parsed


def _core_items(cfg: dict[str, Any]) -> list[Item]:
    sections = ("outbounds", "endpoints")
    by_tag = {str(o["tag"]): (sec, o) for sec in sections for o in cfg.get(sec) or [] if isinstance(o, dict) and o.get("tag")}
    items: list[Item] = []
    for section in sections:
        for o in cfg.get(section) or []:
            if not isinstance(o, dict) or not o.get("tag") or str(o.get("type")) in _NOT_PROXY:
                continue
            # the entry and the chain it dials through (detour); nothing else needs to run
            base: dict[str, Any] = {}
            sec, cur, seen = section, o, set()
            while cur is not None and str(cur["tag"]) not in seen:
                seen.add(str(cur["tag"]))
                base.setdefault(sec, []).append(copy.deepcopy(cur))
                nxt = by_tag.get(str(cur.get("detour") or ""))
                sec, cur = nxt if nxt else (sec, None)
            items.append(Item(len(items), str(o["tag"]), "core", base, tag=str(o["tag"]), original=o))
            if len(items) >= MAX_CONFIGS:
                return items
    return items


def parse_with_core(text: str) -> dict[str, Any]:
    if not CORE_BIN.exists():
        raise TesterError("hiddify-core is not installed")
    with tempfile.TemporaryDirectory(prefix="cfgtest-parse-") as tmp:
        src = Path(tmp) / "sub.txt"
        src.write_text(text, encoding="utf-8")
        try:
            res = subprocess.run([str(CORE_BIN), "parse", str(src), "-D", tmp], capture_output=True, text=True, timeout=60, cwd=str(CORE_DIR if CORE_DIR.is_dir() else tmp))
        except subprocess.TimeoutExpired:
            raise TesterError("hiddify-core parse timed out") from None
    out = res.stdout
    start = out.find("{")
    cfg = _json(out[start:]) if start >= 0 else None
    if not isinstance(cfg, dict) or not _is_core(cfg):
        raise TesterError("hiddify-core could not find any config in the subscription: " + (res.stderr or out)[-300:].strip())
    return cfg


# --------------------------------------------------------------------------- run one


def _free_port(taken: set[int]) -> int:
    for _ in range(200):
        port = PORT_RANGE[0] + int.from_bytes(os.urandom(2), "big") % (PORT_RANGE[1] - PORT_RANGE[0])
        if port in taken:
            continue
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
        taken.add(port)
        return port
    raise TesterError("No free local port")


def build_config(item: Item, port: int) -> dict[str, Any]:
    if item.kind == "xray":
        cfg = copy.deepcopy(item.config)
        cfg["log"] = {"loglevel": "debug"}
        cfg["inbounds"] = [{"tag": "test-in", "listen": "127.0.0.1", "port": port, "protocol": "socks", "settings": {"udp": False}}]
        cfg.pop("routing", None)  # the first outbound is the default
        cfg.pop("api", None)
        cfg.pop("stats", None)
        cfg.pop("policy", None)
        return cfg
    cfg = copy.deepcopy(item.config)
    cfg["log"] = {"level": "trace", "timestamp": True}
    cfg.setdefault("outbounds", [])
    have = {o.get("tag") for o in cfg["outbounds"]}
    for t, typ in (("direct", "direct"), ("freedom", "direct")):
        if t not in have:
            cfg["outbounds"].append({"tag": t, "type": typ})
    cfg["inbounds"] = [{"type": "mixed", "tag": "test-in", "listen": "127.0.0.1", "listen_port": port}]
    cfg["route"] = {"final": item.tag, "auto_detect_interface": False}
    return cfg


def _wait_port(port: int, proc: subprocess.Popen, timeout: float) -> bool:
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


def _tail(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return (lines[-1] if lines else "")[-300:]


_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
LOG_HEAD = 100_000
LOG_TAIL = 200_000


def _clean(text: str) -> str:
    return _ANSI.sub("", text)


def _read_log(path: Path) -> str:
    """The core's trace log without colours; a huge one keeps its start and its end."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return ""
    if len(data) > LOG_HEAD + LOG_TAIL:
        data = data[:LOG_HEAD] + b"\n... (log cut) ...\n" + data[-LOG_TAIL:]
    return _clean(data.decode("utf-8", errors="replace"))


def _ping(port: int, test_url: str, timeout: int) -> dict[str, Any]:
    """One request through the local SOCKS port."""
    try:
        res = subprocess.run(
            ["curl", "-sS", "-v", "-o", "/dev/null", "-x", f"socks5h://127.0.0.1:{port}", "--max-time", str(timeout), "-w", "%{http_code} %{time_connect} %{time_starttransfer} %{time_total}", test_url],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    parts = res.stdout.split()
    if res.returncode == 0 and len(parts) == 4 and parts[0].startswith(("2", "3")):
        return {"ok": True, "status": int(parts[0]), "connect_ms": int(float(parts[1]) * 1000), "ttfb_ms": int(float(parts[2]) * 1000), "delay_ms": int(float(parts[3]) * 1000), "curl_log": res.stderr}
    err_lines = [l for l in res.stderr.splitlines() if l.startswith("curl:")]
    return {"ok": False, "error": (err_lines[-1] if err_lines else "") or (f"HTTP {parts[0]}" if parts else "failed"), "curl_log": res.stderr}


def run_one(item: Item, port: int, test_url: str, timeout: int, repeats: int = 3) -> dict[str, Any]:
    out: dict[str, Any] = {"index": item.index, "name": item.name, "kind": item.kind, "ok": False, "original": item.original, "tag": item.tag}
    tmp = tempfile.mkdtemp(prefix="cfgtest-")
    proc: subprocess.Popen | None = None
    log_path = Path(tmp) / "core.log"
    curl_log = ""
    try:
        path = Path(tmp) / "config.json"
        run_cfg = build_config(item, port)
        out["run_config"] = run_cfg
        path.write_text(json.dumps(run_cfg), encoding="utf-8")
        if item.kind == "xray":
            binary = XRAY_BIN
            cmd = [str(binary), "run", "-c", str(path)]
        else:
            binary = CORE_BIN
            cmd = [str(binary), "srun", "-c", str(path), "-D", tmp]
        if not binary.exists():
            out["error"] = f"{binary.name} is not installed"
            return out
        with open(log_path, "wb") as log_file:  # a file, not a pipe: a trace log would fill the pipe and stop the core
            proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, cwd=str(CORE_DIR if item.kind == "core" and CORE_DIR.is_dir() else tmp))
        if not _wait_port(port, proc, STARTUP_TIMEOUT):
            if proc.poll() is not None:
                out["error"] = "config rejected: " + _tail(_read_log(log_path))
            else:
                out["error"] = "the core did not start in time"
            return out
        pings: list[dict[str, Any]] = []
        started = time.monotonic()
        for n in range(max(1, repeats)):
            pings.append(_ping(port, test_url, timeout))
            curl_log += f"\n----- test {n + 1} -----\n" + pings[-1].pop("curl_log", "")
        out["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        good = [p for p in pings if p["ok"]]
        out["pings"] = pings
        out["tries"] = len(pings)
        out["ok_count"] = len(good)
        if good:
            out.update(ok=True, delay_ms=round(sum(p["delay_ms"] for p in good) / len(good)), status=good[-1]["status"], connect_ms=good[-1]["connect_ms"], ttfb_ms=good[-1]["ttfb_ms"])
        else:
            out["error"] = pings[-1].get("error") or "failed"
        return out
    except Exception as e:  # one bad config must never stop the others
        out["error"] = str(e)[:300]
        return out
    finally:
        if proc and proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
        log = _read_log(log_path)
        if curl_log:
            log += "\n\n===== curl =====\n" + curl_log
        out["log"] = log
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- the whole run


def run(url: str, user_agent: str, *, test_url: str = DEFAULT_TEST_URL, workers: int = 8, timeout: int = 10, repeats: int = DEFAULT_REPEATS) -> Iterator[dict[str, Any]]:
    """Events: ``{"event": "start", source, total, items}``, one ``{"event": "result", ...}`` per config, then ``{"event": "done"}``."""
    text, fetched = fetch(url, user_agent)
    source, items, parsed = split(text)
    if not items:
        raise TesterError("No config found in the subscription")
    yield {"event": "start", "source": source, "total": len(items), "fetched": fetched, "raw": text[:RAW_LIMIT], "parsed": parsed, "items": [{"index": i.index, "name": i.name, "kind": i.kind} for i in items]}
    yield from _execute(items, test_url, workers, timeout, repeats)


def rerun(raw_items: list[dict[str, Any]], *, test_url: str = DEFAULT_TEST_URL, workers: int = 8, timeout: int = 10, repeats: int = DEFAULT_REPEATS) -> Iterator[dict[str, Any]]:
    """Test configs again. Each is ``{index, name, kind, tag, config}`` as the page has it from an earlier result (``config`` is its ``run_config``)."""
    items: list[Item] = []
    for r in raw_items[:MAX_CONFIGS]:
        cfg = r.get("config")
        if r.get("kind") not in ("xray", "core") or not isinstance(cfg, dict):
            raise TesterError("Bad config to test again")
        original = r.get("original")
        items.append(Item(int(r["index"]), str(r.get("name") or ""), str(r["kind"]), cfg, tag=str(r.get("tag") or ""), original=original if original is not None else cfg))
    yield from _execute(items, test_url, workers, timeout, repeats)


def _execute(items: list[Item], test_url: str, workers: int, timeout: int, repeats: int) -> Iterator[dict[str, Any]]:
    workers = max(1, min(int(workers), 32))
    q: Queue = Queue()
    taken: set[int] = set()

    def job(item: Item) -> None:
        try:
            port = _free_port(taken)
        except TesterError as e:
            q.put({"event": "result", "index": item.index, "name": item.name, "kind": item.kind, "ok": False, "error": str(e)})
            return
        try:
            q.put({"event": "result", **run_one(item, port, test_url, timeout, max(1, min(int(repeats), 10)))})
        finally:
            taken.discard(port)

    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        for i in items:
            pool.submit(job, i)
        for _ in items:
            yield q.get()
    finally:  # also when the client went away: stop what has not started
        pool.shutdown(wait=False, cancel_futures=True)
    yield {"event": "done"}
