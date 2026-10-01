"""Server outbounds: where matching traffic leaves the server (WARP, direct, block, SOCKS, Tor, Psiphon)."""

from __future__ import annotations

from enum import auto
from typing import Any

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from strenum import StrEnum

from hiddifypanel.database import db


class OutboundMode(StrEnum):
    warp = auto()
    psiphon = auto()
    direct = auto()
    socks = auto()
    tor = auto()
    block = auto()


#: Built in on every panel; can not be deleted.
BUILTIN_MODES = (OutboundMode.warp, OutboundMode.direct, OutboundMode.block)
#: Modes that may exist more than once.
MULTI_MODES = (OutboundMode.socks,)
#: Modes that connect to a SOCKS endpoint.
ENDPOINT_MODES = (OutboundMode.socks, OutboundMode.tor, OutboundMode.psiphon)
#: Of those, only SOCKS is configured by the admin; Tor and Psiphon use the local ports of the defaults file.
CONFIGURABLE_ENDPOINT_MODES = (OutboundMode.socks,)
#: Order given to outbounds from before they could be reordered: blocking first, exits, WARP, direct.
RULE_ORDER = (OutboundMode.block, OutboundMode.socks, OutboundMode.tor, OutboundMode.psiphon, OutboundMode.warp, OutboundMode.direct)

#: Routing list fields an admin can edit.
LIST_FIELDS = ("sites", "geosites", "rule_sets")


class Outbound(db.Model):  # type: ignore
    __tablename__ = "outbound"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), default=0)
    name: Mapped[str] = mapped_column(String(100))
    mode: Mapped[OutboundMode] = mapped_column(Enum(OutboundMode))
    enabled: Mapped[bool] = mapped_column(default=True)
    #: Rule order (1 = checked first). The last enabled outbound is the default (route final).
    position: Mapped[int | None] = mapped_column(default=None)
    #: Kept equal to "last enabled" (see proxy_v3.outbounds.finalize).
    is_default: Mapped[bool] = mapped_column(default=False)
    #: Also route the panel region's domestic sites here.
    domestic: Mapped[bool] = mapped_column(default=False)

    #: Domains (matched with subdomains).
    sites: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    #: xray geosite tags.
    geosites: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    #: hiddify-core rule-set names or URLs.
    rule_sets: Mapped[list[Any] | None] = mapped_column(JSON, default=list)

    host: Mapped[str | None] = mapped_column(String(255), default="")
    port: Mapped[int | None] = mapped_column(default=None)
    username: Mapped[str | None] = mapped_column(String(255), default="")
    password: Mapped[str | None] = mapped_column(String(255), default="")

    is_builtin: Mapped[bool] = mapped_column(default=False)
    #: The defaults file's lists (and `domestic`) at the last sync: refreshed on upgrade.
    builtin_lists: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    #: The admin edited the lists: upgrades no longer replace them.
    lists_override: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        return f"<Outbound {self.id} {self.mode} {self.name!r}>"
