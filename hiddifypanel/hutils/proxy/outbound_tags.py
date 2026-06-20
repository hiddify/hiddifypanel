from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

from jinja2 import Environment

from .alpn_helpers import DEFAULT_OUTBOUND_TAG_TEMPLATE


def config_content_hash(item: dict[str, Any]) -> str:
    payload = {k: v for k, v in item.items() if k not in ('tag', 'name')}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def deduplicate_client_tags(items: list[dict[str, Any]], *, tag_key: str = 'tag') -> list[dict[str, Any]]:
    if not items:
        return items

    tags = [str(i.get(tag_key) or '') for i in items if i.get(tag_key)]
    dup_tags = {t for t, count in Counter(tags).items() if count > 1}
    if not dup_tags:
        return items

    hash_dup_index: dict[tuple[str, str], int] = defaultdict(int)
    hash_dup_total: dict[tuple[str, str], int] = Counter()
    for item in items:
        tag = str(item.get(tag_key) or '')
        if tag not in dup_tags:
            continue
        h = config_content_hash(item)
        hash_dup_total[(tag, h)] += 1

    result: list[dict[str, Any]] = []
    for item in items:
        row = dict(item)
        tag = str(row.get(tag_key) or '')
        if not tag or tag not in dup_tags:
            result.append(row)
            continue
        h = config_content_hash(row)
        hash_dup_index[(tag, h)] += 1
        idx = hash_dup_index[(tag, h)]
        prefix = f'[duplicate {idx}] ' if hash_dup_total[(tag, h)] > 1 else ''
        row[tag_key] = f'{prefix}{tag} § {h}'
        result.append(row)
    return result


def render_outbound_tag(env: Environment, template: str, context: dict[str, Any]) -> str:
    tpl = (template or '').strip() or DEFAULT_OUTBOUND_TAG_TEMPLATE
    rendered = env.from_string(tpl).render(**context).strip()
    return ' '.join(rendered.split())
