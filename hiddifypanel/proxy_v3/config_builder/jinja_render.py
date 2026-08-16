from __future__ import annotations
from wcwidth import ljust

import json
import random
import re
import time
from typing import Any
from urllib.parse import quote, urlencode

from jinja2 import Environment
from jinja2.loaders import DictLoader

from hiddifypanel import hutils
from hiddifypanel.models.custom_proxy import ProxyTemplate
from hiddifypanel.proxy_v3.jinja_context import ConfigEnum, include_path, jsbool, skip_proxy
from hiddifypanel.proxy_v3.jinja_download import download


def _to_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_json_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # Jinja ``namespace(...)`` — attrs live under a private dict.
    try:
        raw = object.__getattribute__(value, "__dict__")
        if isinstance(raw, dict) and "_Namespace__attrs" in raw:
            return _to_json_value(raw["_Namespace__attrs"])
    except Exception:
        pass
    if hasattr(value, "dict") and callable(value.dict):
        return _to_json_value(value.dict())
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return _to_json_value(value.model_dump())
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
            value = json.loads(text)
        except json.JSONDecodeError:
            # Not JSON — collapse whitespace rather than double-encode.
            return re.sub(r"\s+", " ", text).strip()

    value = _omit_empty_json_values(_to_json_value(value))
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), cls=ProxyJsonEncoder)


def _jinja_urlencode(value: Any) -> str:
    normalized = _to_json_value(value)
    if isinstance(normalized, dict):
        return urlencode(normalized)
    return quote(str(normalized or ""), safe="")


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
    env.globals["ConfigEnum"] = ConfigEnum
    env.filters["jsbool"] = jsbool
    env.filters["tojson"] = _jinja_tojson
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
