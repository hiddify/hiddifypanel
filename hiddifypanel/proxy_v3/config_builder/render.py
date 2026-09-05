from __future__ import annotations

import json
import re
from typing import Any

import json5
from jinja2 import TemplateSyntaxError, UndefinedError
from jinja2.exceptions import TemplateError

from hiddifypanel.proxy_v3.context_vars.builder.utils import fix_duplicate_json_commas
from hiddifypanel.proxy_v3.jinja_context import TemplateSkip

from .models import RenderErrorDetail, RenderSectionResult
from .template_blocks import extract_block_body, fragment_block_body


def _trim_leading_empty_lines(text: str) -> str:
    if not text:
        return text
    lines = text.splitlines()
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start == 0:
        return text
    trimmed = "\n".join(lines[start:])
    if text.endswith("\n") and not trimmed.endswith("\n"):
        trimmed += "\n"
    return trimmed


def _wrap_as_json_object(fragment: str) -> str:
    fragment = fragment.strip().rstrip(",")
    if not fragment:
        return "{}"
    if fragment.startswith("["):
        return fragment
    if re.search(r"\}\s*,\s*\{", fragment):
        return "[\n" + fragment + "\n]"
    if fragment.startswith("{"):
        return fragment
    return "{\n" + fragment + "\n}"


def _looks_like_jinja_template(text: str) -> bool:
    return "{%" in (text or "") or "{{" in (text or "")


def _json5_text_for_parse(text: str) -> str:
    stripped = (text or "").strip().rstrip(",")
    if not stripped:
        return stripped
    if stripped.startswith("["):
        return stripped
    if re.search(r"\}\s*,\s*\{", stripped):
        return _wrap_as_json_object(stripped)
    if not stripped.startswith("{"):
        return _wrap_as_json_object(stripped)
    return stripped


def _parse_json5(text: str) -> tuple[Any | None, str | None]:
    stripped = _trim_leading_empty_lines(fix_duplicate_json_commas(text.strip()))
    if not stripped:
        return None, None
    try:
        return json5.loads(stripped), None
    except Exception as exc:
        return None, str(exc)


def _parse_error_location(message: str) -> tuple[int | None, int | None]:
    line_match = re.search(r"<string>:(\d+)", message or "")
    col_match = re.search(r"column (\d+)", message or "")
    line = int(line_match.group(1)) if line_match else None
    column = int(col_match.group(1)) if col_match else None
    return line, column


def _error_excerpt(source: str, line: int | None, *, context: int = 4) -> str:
    if not source:
        return ""
    if not line or line < 1:
        return source
    lines = source.splitlines()
    start = max(0, line - 1 - context)
    end = min(len(lines), line + context)
    parts: list[str] = []
    for index in range(start, end):
        marker = ">>>" if index == line - 1 else "   "
        parts.append(f"{marker} {index + 1:4}| {lines[index]}")
    return "\n".join(parts)


def _infer_jinja_error_line(template_source: str, message: str) -> int | None:
    if not template_source:
        return None
    lower_msg = (message or "").lower()
    lines = template_source.splitlines()
    if "non-namespace" in lower_msg or "cannot assign attribute" in lower_msg:
        for idx, line in enumerate(lines, 1):
            if re.search(r"\{%[-\s]*set\s+\w+\.\w+\s*=", line):
                return idx
    if "unexpected end" in lower_msg or "endblock" in lower_msg:
        depth = 0
        last_open: int | None = None
        for idx, line in enumerate(lines, 1):
            for match in re.finditer(r"\{%-?\s*(block|endblock)\b", line):
                if match.group(1) == "block":
                    depth += 1
                    last_open = idx
                elif depth > 0:
                    depth -= 1
        if depth > 0 and last_open:
            return last_open
    return None


def _error_detail_phase(message: str) -> str:
    return "json5" if _parse_error_location(message)[0] else "jinja"


def _build_error_detail(
    message: str,
    *,
    source: str = "",
    phase: str = "render",
    line: int | None = None,
    column: int | None = None,
    template_source: str | None = None,
) -> RenderErrorDetail:
    parsed_line, parsed_column = _parse_error_location(message)
    resolved_line = line or parsed_line
    resolved_column = column if column is not None else parsed_column
    resolved_phase = phase if phase != "render" else _error_detail_phase(message)
    template_text = template_source or ""
    if resolved_phase == "jinja":
        if not resolved_line and template_text:
            resolved_line = _infer_jinja_error_line(template_text, message)
        display_source = template_text or source
    else:
        display_source = source or template_text
    return RenderErrorDetail(
        phase=resolved_phase,
        line=resolved_line,
        column=resolved_column,
        message=message,
        source=display_source,
        excerpt=_error_excerpt(display_source, resolved_line),
        template_source=template_text if template_text and template_text != display_source else None,
        template_excerpt=(_error_excerpt(template_text, resolved_line) if template_text and template_text != display_source else None),
    )


def _render_template_text(template_text: str, child_id: int, context: dict[str, Any]) -> str:
    from hiddifypanel.proxy_v3.config_builder.jinja_render import render_template_text

    return render_template_text(template_text, child_id, context)


def render_section(
    template_text: str,
    child_id: int,
    context: dict[str, Any],
    *,
    as_json_object: bool = True,
    parse_json: bool = True,
) -> RenderSectionResult:
    if not (template_text or "").strip():
        return RenderSectionResult()

    try:
        rendered = _render_template_text(template_text, child_id, context)
        if as_json_object and rendered.strip() and not rendered.strip().startswith(("[", "{")):
            wrapped = _wrap_as_json_object(rendered)
        else:
            wrapped = rendered
        wrapped = _trim_leading_empty_lines(wrapped)
        if wrapped.strip().startswith(("{", "[")):
            wrapped = fix_duplicate_json_commas(wrapped)

        parsed: Any | None = None
        parse_err: str | None = None
        error_detail: RenderErrorDetail | None = None
        if parse_json and wrapped.strip().startswith(("{", "[")):
            to_parse = _json5_text_for_parse(wrapped)
            parsed, parse_err = _parse_json5(to_parse)
            if parse_err:
                error_detail = _build_error_detail(parse_err, source=wrapped, phase="json5")
            elif as_json_object and isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
                parsed = parsed[0]
                wrapped = json.dumps(parsed, indent=2, ensure_ascii=False)

        return RenderSectionResult(
            rendered=wrapped,
            parsed=parsed,
            skipped=False,
            error=parse_err,
            error_detail=error_detail,
        )
    except TemplateSkip:
        return RenderSectionResult(rendered="SKIP", skipped=True)
    except (TemplateError, TemplateSyntaxError, UndefinedError) as exc:
        message = str(exc)
        lineno = getattr(exc, "lineno", None) or _infer_jinja_error_line(template_text, message)
        return RenderSectionResult(
            error=message,
            error_detail=_build_error_detail(
                message,
                template_source=template_text,
                phase="jinja",
                line=lineno,
                column=getattr(exc, "colno", None),
            ),
        )


def _resolve_fragment_block_name(fragment: str, block_name: str | None) -> str:
    preferred = block_name or "outbounds"
    raw = (fragment or "").strip()
    for name in (preferred, "inbounds", "inbound", "endpoints", "outbounds"):
        if extract_block_body(raw, name) is not None:
            return name
    return preferred


def render_fragment_section(
    child_id: int,
    context: dict[str, Any],
    fragment: str,
    block_name: str,
    *,
    parse_json: bool = True,
) -> RenderSectionResult:
    raw = (fragment or "").strip()
    resolved = _resolve_fragment_block_name(raw, block_name)
    body = extract_block_body(raw, resolved)
    if body is None:
        return RenderSectionResult(skipped=True)

    if body.strip().startswith("["):
        return render_section(body, child_id, context, as_json_object=False, parse_json=parse_json)
    if body.strip().startswith("{") and not _looks_like_jinja_template(body):
        return render_section(body, child_id, context, as_json_object=True, parse_json=parse_json)
    if _looks_like_jinja_template(body):
        return render_section(body, child_id, context, as_json_object=False, parse_json=parse_json)
    return render_section(_wrap_as_json_object(body), child_id, context, as_json_object=True, parse_json=parse_json)
