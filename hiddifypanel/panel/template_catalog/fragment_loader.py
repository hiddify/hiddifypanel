from __future__ import annotations

import re
from pathlib import Path

from .paths import FRAGMENT_CORES, FRAGMENT_KINDS, TEMPLATES_ROOT

# Panel Jinja context uses users; deployment configs use users.
_NORMALIZE_RULES: tuple[tuple[str, str], ...] = (
    (r'{%\s*for\s+u\s+in\s+users\s*%}', '{% for user in users %}'),
    (r'{%\s*endfor\s*%}', '{% endfor %}'),
    (r"\{\{\s*u\['uuid'\]\s*\}\}", '{{ user.uuid }}'),
    (r'\{\{\s*flow\s*\}\}', '{{ FLOW }}'),
    (r'/\{\{\s*path\s*\}\}', '/{{ proxy.path }}'),
    (r'\{\{\s*path\s*\}\}', '{{ proxy.path }}'),
    (r'\{\{\s*PATH\s*\}\}', '{{ proxy.path }}'),
    (r'\{\{\s*TAG\s*\}\}', '{{ proxy.tag }}'),
    (r'\{\{\s*PORT\s*\}\}', '{{ proxy.port }}'),
    (r'\{\{\s*DOMAIN\s*\}\}', '{{ domain.server }}'),
    (r'\{\{\s*USER\.', '{{ user.'),
)

_HIDDIFY_KIND_ALIASES = {'streams': 'stream'}


def normalize_fragment(content: str) -> str:
    text = content.replace('\r\n', '\n')
    for pattern, repl in _NORMALIZE_RULES:
        text = re.sub(pattern, repl, text)
    return text.strip()


def slug_to_path(slug: str) -> Path:
    """Map template slug to file under proxy_templates/ (.pj2 or .j2)."""
    pj2 = TEMPLATES_ROOT / f'{slug}.pj2'
    if pj2.is_file():
        return pj2
    j2 = TEMPLATES_ROOT / f'{slug}.j2'
    if j2.is_file():
        return j2
    return pj2


def load_template_slug(slug: str, *, normalize: bool = True) -> str:
    path = slug_to_path(slug)
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding='utf-8')
    return normalize_fragment(text) if normalize and path.suffix == '.pj2' else text.strip()


def _normalize_kind(kind: str) -> str:
    return _HIDDIFY_KIND_ALIASES.get(kind, kind)


def _fragment_folder(core: str, kind: str, side: str = 'server') -> Path:
    kind = _normalize_kind(kind)
    if core == 'hiddify-core':
        return TEMPLATES_ROOT / core / side / kind
    return TEMPLATES_ROOT / core / 'common' / kind


def fragment_path(core: str, kind: str, name: str, side: str = 'server') -> Path:
    if core not in FRAGMENT_CORES:
        raise ValueError(f'Unknown core: {core}')
    kind = _normalize_kind(kind)
    if kind not in FRAGMENT_KINDS and kind not in ('stream', 'tls'):
        raise ValueError(f'Unknown fragment kind: {kind}')
    return _fragment_folder(core, kind, side) / f'{name}.pj2'


def load_fragment(core: str, kind: str, name: str, side: str = 'server') -> str:
    return load_template_slug(fragment_slug(core, kind, name, side=side))


def fragment_slug(core: str, kind: str, name: str, side: str = 'server') -> str:
    kind = _normalize_kind(kind)
    if core == 'hiddify-core':
        return f'{core}/{side}/{kind}/{name}'
    return f'{core}/common/{kind}/{name}'


def list_fragments(core: str, kind: str, side: str = 'server') -> list[str]:
    folder = _fragment_folder(core, kind, side)
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob('*.pj2'))


def iter_template_files() -> list[tuple[str, Path]]:
    """All .pj2 and base/*.j2 files as (slug, path)."""
    found: list[tuple[str, Path]] = []
    for path in sorted(TEMPLATES_ROOT.rglob('*')):
        if not path.is_file():
            continue
        rel = str(path.relative_to(TEMPLATES_ROOT)).replace('\\', '/')
        if path.suffix == '.pj2':
            slug = str(path.relative_to(TEMPLATES_ROOT).with_suffix('')).replace('\\', '/')
            found.append((slug, path))
        elif path.suffix == '.j2' and (rel.endswith('/base.j2') or '/base/' in rel):
            slug = str(path.relative_to(TEMPLATES_ROOT).with_suffix('')).replace('\\', '/')
            found.append((slug, path))
    return found
