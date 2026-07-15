from __future__ import annotations

import re

_BLOCK_OPEN_RE = re.compile(r"\{%-?\s*block\s+(\w+)\s*-?%\}")
_BLOCK_CLOSE_RE = re.compile(r"\{%-?\s*endblock\s*-?%\}")


def _balanced_block_body(text: str, start_pos: int) -> str | None:
    depth = 1
    pos = start_pos
    while pos < len(text) and depth > 0:
        next_open = _BLOCK_OPEN_RE.search(text, pos)
        next_close = _BLOCK_CLOSE_RE.search(text, pos)
        if next_close is None:
            return None
        if next_open is not None and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
            continue
        depth -= 1
        if depth == 0:
            return text[start_pos : next_close.start()]
        pos = next_close.end()
    return None


def extract_block_body(fragment: str, block_name: str) -> str | None:
    text = (fragment or "").strip()
    if not text:
        return None
    for open_match in _BLOCK_OPEN_RE.finditer(text):
        if open_match.group(1) != block_name:
            continue
        body = _balanced_block_body(text, open_match.end())
        if body is not None:
            return body.strip()
    return None


def fragment_block_body(fragment: str, block_name: str) -> str:
    body = extract_block_body(fragment, block_name)
    if body is not None:
        return body
    stripped = (fragment or "").strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        inner = stripped[1:-1].strip().rstrip(",")
        return f"{inner},\n" if inner else ""
    return stripped


def inject_template_block(base: str, block_name: str, fragment: str) -> tuple[str, bool]:
    body = fragment_block_body(fragment, block_name)
    replacement = f"{{% block {block_name} %}}\n{body}\n{{% endblock %}}"
    pattern = re.compile(
        rf"\{{%\-?\s*block\s+{re.escape(block_name)}\s*\-?%\}}\s*\{{%\-?\s*endblock\s*\-?%\}}",
    )
    merged, count = pattern.subn(replacement, base, count=1)
    return merged, count > 0


def inject_named_fragment_blocks(base: str, fragment: str, block_names: tuple[str, ...]) -> tuple[str, bool]:
    merged = base
    any_ok = False
    for block_name in block_names:
        body = extract_block_body(fragment, block_name)
        if body is None:
            continue
        injected, ok = inject_template_block(merged, block_name, body)
        if ok:
            merged = injected
            any_ok = True
    if any_ok:
        return merged, True
    if len(block_names) == 1:
        return inject_template_block(merged, block_names[0], fragment)
    return merged, False
