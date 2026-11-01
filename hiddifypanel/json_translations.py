"""Flask-Babel translations read straight from ``translations.i18n/<lang>.json``, the files admin_v2 uses too.

The keys are flattened (``a.b.c``) and used as msgids, exactly as the ``.po`` files were made from these JSON files, so
every ``_()`` / ``gettext()`` / ``lazy_gettext()`` call in Python and Jinja keeps working without compiled ``.mo``
files. A key missing in a language falls back to English, then to the msgid itself.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from babel import support
from flask_babel import Domain, get_locale

I18N_DIR = Path(__file__).parent / "translations.i18n"
FALLBACK_LANG = "en"


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, full))
        elif isinstance(value, str) and full.strip():
            out[full] = value
    return out


@lru_cache(maxsize=None)
def load(lang: str) -> support.Translations:
    """The catalog of one language (read once per process); English is the fallback of the others."""
    translations = support.Translations()  # no file: an empty catalog we fill
    path = I18N_DIR / f"{lang}.json"
    if path.is_file():
        translations._catalog = flatten(json.loads(path.read_text(encoding="utf-8")))
    translations.plural = lambda n: int(n != 1)
    if lang != FALLBACK_LANG:
        translations.add_fallback(load(FALLBACK_LANG))
    return translations


class JsonDomain(Domain):
    def get_translations(self) -> support.Translations:
        locale = get_locale()
        return load(locale.language if locale else FALLBACK_LANG)


def init_app(babel) -> None:
    """Use the JSON catalogs for every gettext call of this app (Python, lazy strings and Jinja)."""
    babel.domain_instance = JsonDomain()
