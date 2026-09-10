from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from apiflask import APIFlask

if TYPE_CHECKING:
    from hiddifypanel.models.admin import BaseAccount


@dataclass
class TypedFlaskContext:
    proxy_path: str
    uuid: str
    account: BaseAccount


class TypedApiFlask(APIFlask): ...
