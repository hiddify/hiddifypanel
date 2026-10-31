"""Every default of the proxy context models can be built.

A ``default_factory`` runs only when a value is missing, so one that refers to a renamed constant imports fine
and fails later, at validation time (``module 'hiddifypanel.proxy_v3.tls_fragment' has no attribute
'DEFAULT_SIZE'`` after DEFAULT_SIZE became DEFAULT_LENGTHS). Calling each factory here catches that at once.
"""

from __future__ import annotations

import importlib
import pkgutil
import unittest

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

import hiddifypanel.proxy_v3.context_vars as context_vars


def _context_models() -> list[type[BaseModel]]:
    models: dict[str, type[BaseModel]] = {}
    for info in pkgutil.walk_packages(context_vars.__path__, f"{context_vars.__name__}."):
        module = importlib.import_module(info.name)
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, BaseModel) and value.__module__ == module.__name__:
                models[f"{value.__module__}.{value.__qualname__}"] = value
    return list(models.values())


class ContextDefaultsTest(unittest.TestCase):
    def test_models_found(self):
        names = {m.__name__ for m in _context_models()}
        self.assertIn("DomainIPVar", names)

    def test_every_default_factory_runs(self):
        for model in _context_models():
            for name, field in model.model_fields.items():
                if field.default_factory is None:
                    continue
                with self.subTest(field=f"{model.__module__}.{model.__qualname__}.{name}"):
                    field.get_default(call_default_factory=True, validated_data={})

    def test_plain_defaults_are_set(self):
        for model in _context_models():
            for name, field in model.model_fields.items():
                with self.subTest(field=f"{model.__qualname__}.{name}"):
                    if field.default_factory is None and not field.is_required():
                        self.assertIsNot(field.default, PydanticUndefined)


if __name__ == "__main__":
    unittest.main()
