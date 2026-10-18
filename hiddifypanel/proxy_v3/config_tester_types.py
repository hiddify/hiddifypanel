"""The shapes the config tester passes around: JSON values, and the events a test sends to the page.

Nothing here is ``Any``: a JSON value is one of its few kinds, and each event has its own typed dict.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
type JsonObject = dict[str, Json]

type Kind = Literal["xray", "core", "clash"]
type Source = Literal["xray", "core", "clash", "parsed"]
#: The client the subscription is for: what it cannot read is an error, not tested with another client.
type App = Literal["hiddify", "xray", "clash"]


class TesterError(Exception):
    """Something the admin can be told: the message is shown as it is."""


@dataclass
class Item:
    """One config to test."""

    index: int
    name: str
    kind: Kind
    config: JsonObject
    tag: str = ""  # core: the outbound / endpoint to route to
    original: Json = None  # the config as the subscription has it
    error: str = ""  # it could not be made at all (a link hiddify-core does not know): shown as its failure


@dataclass(frozen=True)
class PingResult:
    """One request through a config."""

    ok: bool
    delay_ms: int = 0
    status: int = 0
    connect_ms: int = 0
    ttfb_ms: int = 0
    error: str = ""
    curl_log: str = ""


# --------------------------------------------------------------------------- events


class FetchedHttp(TypedDict):
    user_agent: str
    status: int
    content_type: str
    bytes: int


class FetchedPasted(TypedDict):
    pasted: Literal[True]
    bytes: int


type Fetched = FetchedHttp | FetchedPasted


class ItemInfo(TypedDict):
    index: int
    name: str
    kind: Kind


class StartEvent(TypedDict):
    event: Literal["start"]
    source: Source
    total: int
    fetched: Fetched
    raw: str
    parsed: JsonObject | None
    items: list[ItemInfo]


class PingOut(TypedDict):
    ok: bool
    delay_ms: NotRequired[int]
    error: NotRequired[str]


class ResultEvent(TypedDict):
    event: Literal["result"]
    index: int
    name: str
    kind: Kind
    ok: bool
    tag: str
    original: Json
    run_config: NotRequired[JsonObject]
    error: NotRequired[str]
    pings: NotRequired[list[PingOut]]
    tries: NotRequired[int]
    ok_count: NotRequired[int]
    delay_ms: NotRequired[int]
    status: NotRequired[int]
    connect_ms: NotRequired[int]
    ttfb_ms: NotRequired[int]
    elapsed_ms: NotRequired[int]
    log: NotRequired[str]


class KeepAliveEvent(TypedDict):
    event: Literal["ping"]


class QueuedEvent(TypedDict):
    event: Literal["queued"]


class DoneEvent(TypedDict):
    event: Literal["done"]


class ErrorEvent(TypedDict):
    event: Literal["error"]
    error: str


type Event = StartEvent | ResultEvent | KeepAliveEvent | QueuedEvent | DoneEvent | ErrorEvent


class JobPage(TypedDict):
    """What the page gets when it asks for the events of a job."""

    events: list[Event]
    next: int
    done: bool
    lost: bool


# --------------------------------------------------------------------------- reading JSON without trusting it


def obj(value: Json | object) -> JsonObject:
    """The value if it is a JSON object, else an empty one."""
    return value if isinstance(value, dict) else {}


def objects(value: Json | object) -> list[JsonObject]:
    """The objects in a JSON list (anything else in it, or no list, gives nothing)."""
    return [o for o in value if isinstance(o, dict)] if isinstance(value, list) else []


def text(value: Json | object) -> str:
    """The value as text: a string as it is, a number or boolean written out, anything else empty."""
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return str(value)
    return ""
