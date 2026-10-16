"""JSON5 parsing that is fast for the JSON5 our templates produce, and turning JSON5 into plain JSON for storage.

The json5 package is pure Python (~1000x slower than orjson / the stdlib json): parsing the rendered server configs with
it took most of dump-server-configs (~45 s on a server with 230 users). Rendered configs are plain JSON plus ``//`` /
``/* */`` comments (e.g. a commented-out ``"flow"`` per user) and trailing commas, so: try orjson, then again with those
stripped, and fall back to json5 only for other JSON5 (unquoted keys, single quotes, hex numbers, ...).

Stored JSON (users' / domains' extra params) is saved as plain JSON (``normalize``), so reading it never needs json5.
"""

from __future__ import annotations

import re
from typing import Any

import json5
import orjson

# A double-quoted string (kept as is), or what is dropped: a comment, then (second pass) a trailing comma before } or ].
# Strings are matched first so "https://..." and "a,]" inside values are never touched.
_STRING = r'"(?:[^"\\\n]|\\.)*"'
_COMMENTS = re.compile(_STRING + r"|//[^\n]*|/\*.*?\*/", re.DOTALL)
_TRAILING_COMMAS = re.compile(_STRING + r"|,(?=\s*[}\]])")

#: Shorter text holds no object worth parsing ("{}", "", "null"): read as empty.
MIN_OBJECT_LEN = 5


def _keep_strings(m: re.Match[str]) -> str:
    return m.group(0) if m.group(0).startswith('"') else ""


def _strip_comments_and_trailing_commas(text: str) -> str:
    return _TRAILING_COMMAS.sub(_keep_strings, _COMMENTS.sub(_keep_strings, text))


def loads(text: str | bytes) -> Any:
    try:
        return orjson.loads(text)
    except orjson.JSONDecodeError:
        pass
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    try:
        return orjson.loads(_strip_comments_and_trailing_commas(text))
    except orjson.JSONDecodeError:
        return json5.loads(text)


def dumps(value: Any) -> str:
    """Compact JSON (non-ASCII kept as is)."""
    return orjson.dumps(value).decode("utf-8")


def loads_object(text: str | None) -> dict[str, Any]:
    """A stored JSON object; empty / too short / invalid / not an object -> {}."""
    if not text or len(text) < MIN_OBJECT_LEN:
        return {}
    try:
        data = loads(text)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def normalize(text: str | None) -> str:
    """JSON5 (comments, trailing commas, ...) -> plain JSON, for storing. Empty / too short -> "{}"; text that does not
    parse is kept as it is (validation reports it)."""
    stripped = (text or "").strip()
    if len(stripped) < MIN_OBJECT_LEN:
        return stripped if stripped not in ("", "null") else "{}"
    try:
        return dumps(loads(stripped))
    except ValueError:
        return text or ""
