from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from apiflask import APIFlask

if TYPE_CHECKING:
    from hiddifypanel.models.admin import BaseAccount
    from hiddifypanel.models.child import Child
    from hiddifypanel.models.user import User


class TypedFlaskContext:
    """Static type for ``flask.g`` request-local values used across the panel.

    At runtime this is still Flask's ``g``; the cast in ``hiddifypanel.__init__``
    exists only for type checkers.
    """

    # url / request preprocessing (panel.common)
    proxy_path: str
    uuid: str
    force_proxy_path: str

    # auth / account
    account: BaseAccount
    account_uuid: str
    is_admin: bool
    node: Child

    # active child / node context
    child: Child

    # client / UI
    user_agent: dict[str, Any]
    darkmode: bool
    install_pwa: bool
    pwa: bool
    bot: Any | None
    locale: str
    asset_url: Callable[..., Any]
    temp_admin_link: str

    # legacy / rare
    user: User

    def get(self, name: str, default: Any = None) -> Any: ...

    def pop(self, name: str, default: Any = None) -> Any: ...

    def setdefault(self, name: str, default: Any = None) -> Any: ...


class TypedApiFlask(APIFlask): ...
