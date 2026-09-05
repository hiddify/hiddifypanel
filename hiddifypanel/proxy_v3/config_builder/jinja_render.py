from __future__ import annotations
from wcwidth import ljust

import json
import random
import re
import subprocess
import time
from typing import Any
from urllib.parse import quote, urlencode

from flask_babel import force_locale, gettext
from jinja2 import Environment, pass_context
from jinja2.loaders import DictLoader
from jinja2.runtime import Undefined
from jinja2.utils import Namespace

from hiddifypanel import hutils
from hiddifypanel.models.custom_proxy import ProxyTemplate
from hiddifypanel.proxy_v3.jinja_context import ConfigEnum, include_path, jsbool, skip_proxy
from hiddifypanel.proxy_v3.jinja_download import download


def _namespace_attrs(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Namespace):
        return object.__getattribute__(value, "_Namespace__attrs")
    try:
        raw = object.__getattribute__(value, "__dict__")
    except Exception:
        return None
    if isinstance(raw, dict) and "_Namespace__attrs" in raw:
        attrs = raw["_Namespace__attrs"]
        return attrs if isinstance(attrs, dict) else None
    return None


def _to_json_value(value: Any) -> Any:
    if isinstance(value, Undefined):
        return None
    if isinstance(value, dict):
        return {str(key): _to_json_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    attrs = _namespace_attrs(value)
    if attrs is not None:
        return _to_json_value(attrs)
    # Use the type's method so Jinja Undefined does not raise on hasattr().
    for name in ("model_dump", "dict"):
        method = getattr(type(value), name, None)
        if not callable(method):
            continue
        try:
            dumped = method(value)
        except Exception:
            continue
        if dumped is not value:
            return _to_json_value(dumped)
    return value


def _jinja_tojson(value: Any) -> str:
    return json.dumps(_to_json_value(value), ensure_ascii=False)


def _jinja_choose_random(value: Any) -> str:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    if not parts:
        return ""
    return random.choice(parts)


def _jinja_trim_no_line(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or ""))


def _omit_empty_json_values(value: Any) -> Any:
    """Drop null/empty-string/empty-container leaves before compact JSON emit."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            pruned = _omit_empty_json_values(item)
            if pruned is None or pruned == "" or pruned == [] or pruned == {}:
                continue
            out[key] = pruned
        return out
    if isinstance(value, list):
        out_list: list[Any] = []
        for item in value:
            pruned = _omit_empty_json_values(item)
            if pruned is None or pruned == "" or pruned == [] or pruned == {}:
                continue
            out_list.append(pruned)
        return out_list
    return value


def _jinja_compact_json(value: Any) -> str:
    """Serialize to minified JSON.

    Accepts dict/list/namespace objects, or a JSON text block (as produced by
    ``{% set x | compactjson %}...{% endset %}``) which is parsed then re-dumped.
    """
    from hiddifypanel.hutils.proxy.shared import ProxyJsonEncoder

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        try:
            from hiddifypanel.proxy_v3.config_builder.render import _parse_json5

            value, _ = _parse_json5(text)
        except json.JSONDecodeError:
            # Not JSON — collapse whitespace rather than double-encode.
            return re.sub(r"\s+", " ", text).strip()

    value = _omit_empty_json_values(_to_json_value(value))
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), cls=ProxyJsonEncoder)


def _jinja_exec(command: str) -> str:
    try:
        return subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError:
        return ""


def _urlencode_pair(key: Any, val: Any) -> tuple[str, Any] | None:
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        val = "true" if val else "false"
    elif isinstance(val, (dict, list)):
        val = json.dumps(val, ensure_ascii=False, separators=(",", ":"))
    return (str(key), val)


def _jinja_urlencode(value: Any) -> str:
    normalized = _to_json_value(value)
    if isinstance(normalized, dict):
        items = [pair for key, val in normalized.items() if (pair := _urlencode_pair(key, val))]
        return urlencode(items, quote_via=quote)
    if isinstance(normalized, list):
        items: list[tuple[str, Any]] = []
        for item in normalized:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            pair = _urlencode_pair(item[0], item[1])
            if pair:
                items.append(pair)
        return urlencode(items, quote_via=quote)
    if normalized is None:
        return ""
    return quote(str(normalized), safe="")


@pass_context
def _jinja_gettext(ctx: dict[str, Any], message: str, **kwargs: Any) -> str:
    user = ctx.get("user")
    if user is None:
        nested = ctx.get("ctx")
        if nested is not None:
            user = getattr(nested, "user", None)
            if user is None and hasattr(nested, "get"):
                user = nested.get("user")
    lang = None
    if user is not None:
        lang = getattr(user, "lang", None)
        if not lang and hasattr(user, "get"):
            lang = user.get("lang")
    child_id = int(ctx.get("child_id") or 0)
    if not child_id and ctx.get("ctx") is not None:
        nested = ctx["ctx"]
        child_id = int(getattr(nested, "get", lambda *_: 0)("child_id") or getattr(getattr(nested, "hconfig", None), "child_id", 0) or 0)
    if not lang:
        from hiddifypanel.models import hconfig

        lang = hconfig(ConfigEnum.lang, child_id)
    with force_locale(lang or "en"):
        text = gettext(message)
    if kwargs:
        return text % kwargs
    return text


_template_map_cache: dict[int, tuple[float, dict[str, str]]] = {}
_jinja_env_cache: dict[int, tuple[float, Environment]] = {}
_JINJA_CACHE_TTL = 60.0


def _template_map(child_id: int = 0) -> dict[str, str]:
    templates = ProxyTemplate.query.filter((ProxyTemplate.child_id == child_id) | (ProxyTemplate.child_id == 0)).all()
    return {template.slug: template.effective_content() for template in templates}


def _cached_template_map(child_id: int = 0) -> dict[str, str]:
    now = time.monotonic()
    cached = _template_map_cache.get(child_id)
    if cached and now - cached[0] < _JINJA_CACHE_TTL:
        return cached[1]
    mapping = _template_map(child_id)
    _template_map_cache[child_id] = (now, mapping)
    return mapping


def jinja_env(child_id: int = 0) -> Environment:
    now = time.monotonic()
    cached = _jinja_env_cache.get(child_id)
    if cached and now - cached[0] < _JINJA_CACHE_TTL:
        return cached[1]
    env = Environment(
        loader=DictLoader(_cached_template_map(child_id)),
        keep_trailing_newline=True,
        extensions=[],
    )
    env.globals["skip"] = skip_proxy
    env.globals["include_path"] = include_path
    env.globals["download"] = download
    env.globals["enumerate"] = enumerate
    env.globals["len"] = len
    env.globals["exec"] = _jinja_exec
    env.globals["ConfigEnum"] = ConfigEnum
    env.globals["_"] = _jinja_gettext
    env.filters["jsbool"] = jsbool
    env.filters["tojson"] = _jinja_tojson
    env.filters["asdict"] = _to_json_value
    env.filters["b64encode"] = hutils.encode.do_base_64
    env.filters["urlencoded"] = _jinja_urlencode

    env.filters["trim_no_line"] = _jinja_trim_no_line
    env.filters["compactjson"] = _jinja_compact_json
    env.filters["choose_random"] = _jinja_choose_random
    env.filters["ljust"] = ljust

    from slugify import slugify as _slugify

    env.filters["slugify"] = lambda value: _slugify(str(value or ""), lowercase=True)
    _jinja_env_cache[child_id] = (now, env)
    return env


def render_slug_template(slug: str, child_id: int, context: dict[str, Any]) -> str:
    mapping = _cached_template_map(child_id)
    if slug not in mapping:
        raise ValueError(f"Template slug not found: {slug!r}")
    return jinja_env(child_id).get_template(slug).render(**context)


def render_template_text(template_text: str, child_id: int, context: dict[str, Any]) -> str:
    return jinja_env(child_id).from_string(template_text).render(**context)
