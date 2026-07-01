from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .domain import DomainIPVar
from .hconfig import HConfigVar
from .ip import IPVar
from .proxy import ProxyVar
from .user import UserVar


class ServerContextVar(BaseModel):
    """Typed server-side template context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    users: list[UserVar]
    domains: list[DomainIPVar]
    hconfig: HConfigVar
    proxies: list[ProxyVar]
    ips: IPVar
