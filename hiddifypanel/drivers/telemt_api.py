import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal, TypedDict, cast

import redis
import requests

from hiddifypanel.models import ConfigEnum, User, hconfig
from hiddifypanel.models.usage_data import UsageData

from .abstract_driver import DriverABS

USERS_USAGE = "tele:users-usage"
API_URL = "http://localhost:10088/v1"
API_TIMEOUT = 5

HttpMethod = Literal["GET", "PATCH", "DELETE"]


class LocalUsage(TypedDict):
    """What is kept in redis per telemt username, to turn telemt's running total into increments."""

    uuid: str
    total: int


class PatchUserRequest(TypedDict, total=False):
    secret: str
    enabled: bool | None


@dataclass(frozen=True)
class TelemtUser:
    """The part of a `GET /v1/users` entry this driver uses."""

    username: str
    enabled: bool
    total_octets: int

    @classmethod
    def parse(cls, raw: object) -> "TelemtUser | None":
        if not isinstance(raw, dict):
            return None
        username = raw.get("username")
        if not isinstance(username, str) or not username:
            return None
        octets = raw.get("total_octets")
        return cls(
            username=username,
            enabled=raw.get("enabled") is True,
            total_octets=octets if isinstance(octets, int) and octets > 0 else 0,
        )


def tg_username(uuid: str) -> str:
    """telemt's username (and secret) for a user: the uuid without dashes."""
    return uuid.replace("-", "")


class TelemtApi(DriverABS):
    redis_client: "redis.Redis | None" = None

    def __init__(self) -> None:
        super().__init__()
        self.tg_uuid_map: dict[str, str] = {}

    def get_redis_client(self) -> "redis.Redis":
        if self.redis_client is None:
            self.redis_client = redis.from_url(os.environ.get("REDIS_URI_MAIN", ""))
        return self.redis_client

    def is_enabled(self) -> bool:
        return bool(hconfig(ConfigEnum.telegram_enable)) and hconfig(ConfigEnum.telegram_lib) == "telemt"

    def __load_tg_uuid_map(self) -> None:
        from hiddifypanel.database import db

        users = db.session.query(User).all()
        self.tg_uuid_map = {tg_username(str(u.uuid)): str(u.uuid) for u in users}

    def __convert_tg_to_uuid(self, usernames: Iterable[str]) -> dict[str, str]:
        res: dict[str, str] = {}
        can_reload_map = True
        for key in usernames:
            if uuid := self.tg_uuid_map.get(key):
                res[key] = uuid
            elif can_reload_map:
                self.__load_tg_uuid_map()
                can_reload_map = False
                if uuid := self.tg_uuid_map.get(key):
                    res[key] = uuid
        return res

    def __request(self, method: HttpMethod, path: str, body: PatchUserRequest | None = None) -> requests.Response:
        # requests wants a JSON mapping; a TypedDict is open, so hand it over as a plain dict of JSON values
        json_body = cast("dict[str, str | bool | None] | None", dict(body) if body is not None else None)
        return requests.request(method, f"{API_URL}{path}", json=json_body, timeout=API_TIMEOUT)

    def __get_tg_users(self) -> list[TelemtUser]:
        resp = self.__request("GET", "/users")
        resp.raise_for_status()
        payload: object = resp.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return []
        return [u for raw in data if (u := TelemtUser.parse(raw))]

    def __get_tg_usages(self) -> dict[str, int]:
        """Total octets per username; users at zero have not been seen yet, so they are left out."""
        return {u.username: u.total_octets for u in self.__get_tg_users() if u.total_octets > 0}

    def __get_local_usage(self) -> dict[str, LocalUsage]:
        raw = cast("bytes | None", self.get_redis_client().get(USERS_USAGE))
        if not raw:
            return {}
        try:
            data: Any = json.loads(raw)
        except ValueError:
            return {}
        if not isinstance(data, dict):
            return {}
        res: dict[str, LocalUsage] = {}
        for name, item in data.items():
            if not isinstance(item, dict) or not isinstance(item.get("uuid"), str) or not isinstance(item.get("total"), int):
                continue
            res[str(name)] = LocalUsage(uuid=item["uuid"], total=item["total"])
        return res

    def __sync_local_usages(self) -> dict[str, int]:
        local_usage = self.__get_local_usage()
        try:
            tg_usages = self.__get_tg_usages()
        except (requests.RequestException, ValueError) as e:
            print(f"Error getting tg usage: {e}")
            return {}

        # forget users telemt no longer has
        for name in list(local_usage):
            if name not in tg_usages:
                del local_usage[name]

        res: dict[str, int] = {}
        uuid_map = self.__convert_tg_to_uuid(tg_usages.keys())
        for name, total in tg_usages.items():
            uuid = uuid_map.get(name)
            if not uuid:
                continue
            if last := local_usage.get(name):
                res[uuid] = self.calculate_reset(last["total"], total)
            local_usage[name] = LocalUsage(uuid=uuid, total=total)

        self.get_redis_client().set(USERS_USAGE, json.dumps(local_usage))
        return res

    def calculate_reset(self, last_total: int, current_total: int) -> int:
        """Octets since the last read; a smaller total means telemt restarted and counted again from 0."""
        return current_total - last_total if current_total >= last_total else current_total

    def get_enabled_users(self) -> dict[str, int]:
        if not self.is_enabled():
            return {}
        names = [u.username for u in self.__get_tg_users() if u.enabled]
        return {uuid: 1 for uuid in self.__convert_tg_to_uuid(names).values()}

    def add_client(self, user: User) -> None:
        if not self.is_enabled():
            return
        name = tg_username(str(user.uuid))
        resp = self.__request("PATCH", f"/users/{name}", PatchUserRequest(secret=name, enabled=True))
        resp.raise_for_status()

    def remove_client(self, user: User) -> None:
        if not self.is_enabled():
            return
        resp = self.__request("DELETE", f"/users/{tg_username(str(user.uuid))}")
        if resp.status_code != 404:
            resp.raise_for_status()

    def get_all_usage(self, reset: bool = True) -> dict[str, UsageData]:
        if not self.is_enabled():
            return {}
        # telemt has no up/down split: the whole increment is reported as download
        return {uuid: UsageData(uuid=uuid, download=used) for uuid, used in self.__sync_local_usages().items()}
